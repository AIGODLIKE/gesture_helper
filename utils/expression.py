"""Parse poll expressions and operator property literals without eval/exec."""

from __future__ import annotations

import ast

import bpy

_ALLOWED_COMPARE_OPS = {
    ast.Eq: lambda a, b: a == b,
    ast.NotEq: lambda a, b: a != b,
    ast.Lt: lambda a, b: a < b,
    ast.LtE: lambda a, b: a <= b,
    ast.Gt: lambda a, b: a > b,
    ast.GtE: lambda a, b: a >= b,
    ast.Is: lambda a, b: a is b,
    ast.IsNot: lambda a, b: a is not b,
    ast.In: lambda a, b: a in b,
    ast.NotIn: lambda a, b: a not in b,
}


def __check_addon_is_enabled__(addon_name):
    """Check add-on enable state."""
    return addon_name in bpy.context.preferences.addons


def get_active_tool_idname(context) -> str | None:
    """Return the active workspace tool idname for the current editor context."""
    workspace = getattr(context, 'workspace', None)
    if workspace is None:
        return None
    tools = getattr(workspace, 'tools', None)
    if tools is None:
        return None

    area = getattr(context, 'area', None)
    mode = getattr(context, 'mode', None)

    try:
        if area and area.type == 'VIEW_3D' and mode:
            tool = tools.from_space_view3d_mode(mode, create=False)
            if tool is not None:
                return tool.idname
        if area and area.type == 'IMAGE_EDITOR':
            ui_mode = getattr(context.space_data, 'ui_mode', None)
            if getattr(area, 'ui_type', None) == 'UV':
                image_mode = 'UV'
            elif ui_mode == 'PAINT':
                image_mode = 'PAINT'
            elif ui_mode == 'MASK':
                image_mode = 'MASK'
            else:
                image_mode = 'VIEW'
            tool = tools.from_space_image_mode(image_mode, create=False)
            if tool is not None:
                return tool.idname
        tool = getattr(tools, 'active', None)
        if tool is not None:
            return tool.idname
    except (AttributeError, RuntimeError, TypeError):
        return None
    return None


def get_condition_names():
    """Build the name mapping used by poll condition expressions."""
    context = bpy.context
    active_object = getattr(context, "object", None)
    data = active_object.data if active_object else None

    return {
        'bpy': bpy,
        'C': context,
        'D': bpy.data,
        'O': active_object,
        'data': data,
        'mesh': data,
        'mode': context.mode,
        'tool': context.tool_settings,
        'active_tool': get_active_tool_idname(context),
    }


def resolve_context_path(context, data_path: str):
    """Resolve a dotted context path without eval."""
    path = data_path.strip()
    if path.startswith('bpy.context.'):
        path = path[len('bpy.context.'):]
    elif path.startswith('context.'):
        path = path[len('context.'):]
    return context.path_resolve(path)


def literal_to_dict(value) -> dict:
    """Parse operator property strings into a dict using ast.literal_eval."""
    if value is None:
        return {}
    if isinstance(value, dict):
        return value
    if not isinstance(value, str):
        raise TypeError(f"Expected str or dict, got {type(value)!r}")

    text = value.strip()
    if not text or text == "{}":
        return {}

    if text.startswith('dict'):
        text = text[4:].strip()
    if text.startswith('(') and text.endswith(')'):
        text = text[1:-1].strip()

    parsed = ast.literal_eval(text)
    if isinstance(parsed, dict):
        return parsed
    raise ValueError(f"Expected dict literal, got {type(parsed)!r}")


def _ast_literal_value(node):
    """Extract a literal Python value from an AST node."""
    if isinstance(node, ast.Constant):
        return node.value
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
        operand = _ast_literal_value(node.operand)
        if isinstance(operand, (int, float)):
            return -operand
    if isinstance(node, (ast.List, ast.Tuple)):
        return type(node.elts)([_ast_literal_value(elt) for elt in node.elts])
    if isinstance(node, ast.Set):
        return {_ast_literal_value(elt) for elt in node.elts}
    if isinstance(node, ast.Dict):
        return {
            _ast_literal_value(key): _ast_literal_value(value)
            for key, value in zip(node.keys, node.values)
        }
    return ast.literal_eval(ast.unparse(node))


def parse_operator_properties(text: str) -> dict:
    """Parse operator property text as a dict literal or keyword arguments."""
    if not text or not str(text).strip():
        return {}

    body = str(text).strip()
    if body.startswith('(') and body.endswith(')'):
        body = body[1:-1].strip()
    if not body:
        return {}

    try:
        return literal_to_dict(body)
    except (ValueError, SyntaxError, TypeError):
        pass

    tree = ast.parse(f"_f({body})", mode='eval')
    call = tree.body
    if not isinstance(call, ast.Call):
        raise ValueError(f"Expected operator properties, got {body!r}")

    result = {}
    for kw in call.keywords:
        if kw.arg is None:
            raise ValueError("Positional operator properties are not supported")
        result[kw.arg] = _ast_literal_value(kw.value)
    return result


class _ConditionExpressionParser:
    """Parse a restricted subset of Python expressions for poll checks."""

    def __init__(self, names: dict):
        self._names = names
        self._allowed_calls = {
            'len': len,
            'getattr': getattr,
            'hasattr': hasattr,
            'is_enabled_addon': __check_addon_is_enabled__,
            'max': max,
            'min': min,
        }

    def parse(self, expression: str):
        if not expression or not expression.strip():
            return True
        tree = ast.parse(expression, mode='eval')
        return self._parse_node(tree.body)

    def _parse_node(self, node):
        if isinstance(node, ast.Constant):
            return node.value
        if isinstance(node, ast.Name):
            if node.id in self._names:
                return self._names[node.id]
            if node.id in ('True', 'False', 'None'):
                return {'True': True, 'False': False, 'None': None}[node.id]
            raise ValueError(f"Name '{node.id}' is not allowed")
        if isinstance(node, ast.Attribute):
            base = self._parse_node(node.value)
            return getattr(base, node.attr)
        if isinstance(node, ast.Subscript):
            base = self._parse_node(node.value)
            sl = node.slice
            if isinstance(sl, ast.Slice):
                lower = self._parse_node(sl.lower) if sl.lower else None
                upper = self._parse_node(sl.upper) if sl.upper else None
                step = self._parse_node(sl.step) if sl.step else None
                key = slice(lower, upper, step)
            else:
                key = self._parse_node(sl)
            return base[key]
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not):
            return not self._parse_node(node.operand)
        if isinstance(node, ast.BoolOp):
            if isinstance(node.op, ast.And):
                for value in node.values:
                    if not self._parse_node(value):
                        return False
                return True
            if isinstance(node.op, ast.Or):
                for value in node.values:
                    if self._parse_node(value):
                        return True
                return False
        if isinstance(node, ast.Compare):
            left = self._parse_node(node.left)
            for op, comparator in zip(node.ops, node.comparators):
                right = self._parse_node(comparator)
                if not _ALLOWED_COMPARE_OPS[type(op)](left, right):
                    return False
                left = right
            return True
        if isinstance(node, ast.Call):
            if not isinstance(node.func, ast.Name):
                raise ValueError("Only direct function calls are allowed")
            func = self._allowed_calls.get(node.func.id)
            if func is None:
                raise ValueError(f"Function '{node.func.id}' is not allowed")
            args = [self._parse_node(arg) for arg in node.args]
            kwargs = {kw.arg: self._parse_node(kw.value) for kw in node.keywords}
            return func(*args, **kwargs)
        if isinstance(node, ast.List):
            return [self._parse_node(elt) for elt in node.elts]
        if isinstance(node, ast.Tuple):
            return tuple(self._parse_node(elt) for elt in node.elts)
        if isinstance(node, ast.Set):
            return {self._parse_node(elt) for elt in node.elts}
        if isinstance(node, ast.Dict):
            return {
                self._parse_node(key): self._parse_node(value)
                for key, value in zip(node.keys, node.values)
            }
        raise ValueError(f"Unsupported expression node: {type(node).__name__}")


def evaluate_condition(expression: str, names: dict | None = None):
    """Evaluate poll-style boolean expressions without eval/exec."""
    if names is None:
        names = get_condition_names()
    return _ConditionExpressionParser(names).parse(expression)

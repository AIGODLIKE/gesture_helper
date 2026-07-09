import ast

import bpy
from bpy.props import StringProperty

from ...utils.expression import resolve_context_path


class GestureContextSetEnumFlag(bpy.types.Operator):
    """Set an ENUM_FLAG context property to a set of identifiers."""

    bl_idname = 'wm.gesture_context_set_enum_flag'
    bl_label = 'Set Enum Flag'
    bl_options = {'INTERNAL'}

    data_path: StringProperty(name='Data Path')
    # Comma-separated identifiers, e.g. "VERTEX,EDGE" or empty for empty set.
    value: StringProperty(name='Value', default='')

    @classmethod
    def poll(cls, context):
        return context is not None

    @staticmethod
    def parse_flag_value(value: str) -> set[str]:
        text = (value or '').strip()
        if not text:
            return set()
        if text.startswith('{') and text.endswith('}'):
            parsed = ast.literal_eval(text)
            if isinstance(parsed, (set, frozenset, list, tuple)):
                return {str(item) for item in parsed}
            raise ValueError(f"Expected set literal, got {type(parsed)!r}")
        return {part.strip() for part in text.split(',') if part.strip()}

    def execute(self, context):
        if not self.data_path:
            return {'CANCELLED'}
        try:
            path = self.data_path.strip()
            if '.' in path:
                parent_path, attr = path.rsplit('.', 1)
                parent = resolve_context_path(context, parent_path)
            else:
                parent = context
                attr = path
            if parent is None:
                return {'CANCELLED'}
            setattr(parent, attr, self.parse_flag_value(self.value))
        except (AttributeError, TypeError, ValueError, SyntaxError, KeyError, RuntimeError):
            return {'CANCELLED'}
        return {'FINISHED'}

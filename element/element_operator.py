import bpy
from bpy.app.translations import pgettext, pgettext_n
from bpy.props import StringProperty, EnumProperty, BoolProperty, CollectionProperty
from mathutils import Vector

from .element_modal_operator import ElementModalOperatorEventItem
from ..utils.enum import ENUM_OPERATOR_CONTEXT, ENUM_OPERATOR_TYPE, from_rna_get_enum_items
from ..utils.public import get_debug, debug_print
from ..utils.property import set_property_to_kmi_properties
from ..utils.public_cache import cache_update_lock
from ..utils.expression import literal_to_dict, parse_operator_properties


def resolve_operator_bl_idname(bl_idname: str) -> str:
    """Return the operator bl_idname used at runtime."""
    return bl_idname


class ModalProperty:
    modal_events_index: bpy.props.IntProperty(name='Modal Event Index', default=-1)
    modal_events: CollectionProperty(type=ElementModalOperatorEventItem)

    last_modal_operator_property: bpy.props.StringProperty(name='Last Modal Operator Property', default="{}")

    @property
    def is_not_recommended_as_modal(self):
        """Some operators should not use modal control.
        e.g. operators that already implement modal (transform, etc.).
        Properties with is_array are not recommended.
        """
        if self.operator_is_modal:
            if self.operator_bl_idname in [
                "transform.translate",
                "transform.rotate",
                "transform.resize",
            ]:
                return True
            if self.operator_func:
                if rna := self.operator_func.get_rna_type():
                    for prop in rna.properties:
                        if getattr(prop, "is_array", False):
                            return True
        return False

    @property
    def active_event(self) -> ElementModalOperatorEventItem | None:
        """Active modal event item."""
        if len(self.modal_events) > self.modal_events_index and self.modal_events:
            return self.modal_events[self.modal_events_index]
        return None

    def __running_by_modal__(self):
        with bpy.context.temp_override(element=self, gesture=self.parent_gesture):
            bpy.ops.wm.gesture_element_modal_event("INVOKE_DEFAULT", False)

    def draw_modal_property(self, layout):
        if self.active_event:
            self.active_event.draw_modal(layout)
        else:
            layout.label(text='No active modal event')

    @property
    def modal_properties(self):
        """Get operator property dict."""
        try:
            return literal_to_dict(self.last_modal_operator_property)
        except Exception as e:
            from ..utils.debug_util import debug_traceback, debug_trace_stack
            debug_print('Properties Error', key='operator')
            debug_print(self.name, key='operator')
            debug_print(f"bpy.ops.{self.operator_bl_idname}", key='operator')
            debug_print(self.last_modal_operator_property, key='operator')
            debug_print(e.args, key='operator')
            debug_trace_stack(key='operator')
            debug_traceback(key='operator')
            self['last_modal_operator_property'] = "{}"
            return {}

    @property
    def last_properties(self):
        """Return last-used properties, or defaults if none."""
        if self.modal_properties:
            return self.modal_properties
        return self.properties

    def run_element_modal_event(self, ops, context, event) -> bool:
        if event.type in ("MOUSEMOVE", "INBETWEEN_MOUSEMOVE"):
            last_mouse = getattr(ops, "mouse", None)
            mouse = Vector((event.mouse_x, event.mouse_y))
            is_change = False
            for e in self.modal_events:
                if e.is_mouse_move_event and last_mouse != mouse:
                    is_change |= e.number_mouse_move_execute(ops, context, event)  # Mouse delta path
            if is_change:  # Value changed via mouse move
                ops.start_mouse(event)
            return is_change  # Re-run operator after value change
        else:
            for e in self.modal_events:
                if not e.is_mouse_move_event:
                    if e.modal_execute(ops, context, event):
                        return True
            return False

    def get_header_text(self, properties: dict):
        from bpy.app.translations import pgettext_iface as translate
        def gkn(k, v):
            prop = self.operator_func.get_rna_type().properties[k]
            text = prop.name
            name = bpy.app.translations.pgettext_iface(text)
            value = v
            if isinstance(v, str):
                value = translate(v)
            if prop.type == "ENUM":  # Resolve enum display name
                items = from_rna_get_enum_items(prop)
                for (i, n, d, icon, index) in items:
                    if v == i:
                        value = translate(n)
            return f"{name}:{value}"

        return "    ".join([gkn(k, v) for k, v in properties.items()])


class RunOperatorPropertiesSync:
    def to_operator_tmp_kmi(self) -> None:
        """Sync element properties to temp KMI."""
        from ..utils.public_cache import PublicCache
        if PublicCache._suppress_operator_tmp_kmi:
            return
        if not self.is_operator or not self.operator_is_operator:
            return
        if not self.operator_bl_idname or not self.__operator_id_name_is_validity__:
            return
        kmi = self.operator_tmp_kmi
        if kmi is None or kmi.properties is None:
            return
        self.operator_tmp_kmi_properties_clear()
        set_property_to_kmi_properties(kmi.properties, self.properties)

    def from_tmp_kmi_operator_update_properties(self) -> None:
        """Sync temp KMI properties to element."""
        if not get_debug('operator'):
            temp_kmi_properties = self.operator_tmp_kmi_properties
            if self.properties != temp_kmi_properties:
                self['operator_properties'] = str(temp_kmi_properties)
            return
        debug_print("from_tmp_kmi_operator_update_properties", key='operator')
        temp_kmi_properties = self.operator_tmp_kmi_properties
        debug_print(temp_kmi_properties, key='operator')
        debug_print(self.properties, key='operator')
        if self.properties != temp_kmi_properties:
            self['operator_properties'] = str(temp_kmi_properties)

    def operator_tmp_kmi_properties_clear(self):
        """Clear temp KMI operator properties."""
        properties = self.operator_tmp_kmi.properties
        for key in list(properties.keys()):
            properties.pop(key)

    def update_operator_properties_sync_from_temp_properties(self, _):
        if self.is_operator:
            self.from_tmp_kmi_operator_update_properties()
            self['operator_properties_sync_from_temp_properties'] = False

    def update_operator_properties_sync_to_properties(self, _):
        if self.is_operator:
            self.to_operator_tmp_kmi()
            self['operator_properties_sync_to_properties'] = False

    operator_properties_sync_from_temp_properties: BoolProperty(
        name='From Prop Update',
        update=update_operator_properties_sync_from_temp_properties)
    operator_properties_sync_to_properties: BoolProperty(
        name='Update To Prop',
        update=update_operator_properties_sync_to_properties)

    @property
    def operator_tmp_kmi(self) -> 'bpy.types.KeyMapItem':
        """Temp KMI for operator preview."""
        from ..gesture.temp_keymap import get_temp_kmi_by_id_name
        return get_temp_kmi_by_id_name(self.operator_bl_idname)

    @property
    def operator_tmp_kmi_properties(self) -> dict:
        """Temp KMI operator property dict."""
        from ..gesture.addon_keymap import get_kmi_operator_properties
        properties = get_kmi_operator_properties(self.operator_tmp_kmi)
        return properties


class RunOperator:
    """Blender operator element mixin."""

    @property
    def __operator_name__(self) -> str | None:
        if self.operator_type == "OPERATOR":
            func = self.operator_func
            if func:
                rna = func.get_rna_type()
                return pgettext(rna.name, rna.translation_context)
        return None

    @property
    def __operator_original_name__(self) -> str | None:
        """Original untranslated operator name."""
        if self.operator_type == "OPERATOR":
            func = self.operator_func
            if func:
                rna = func.get_rna_type()
                return pgettext_n(rna.name, rna.translation_context)
        return None

    def __running_by_bl_idname__(self, operator_properties: str = None):
        """Run operator by bl_idname."""
        if operator_properties is None:
            operator_properties = self.operator_properties
        try:
            if func := self.operator_func:
                if isinstance(operator_properties, dict):
                    prop = operator_properties
                else:
                    prop = literal_to_dict(operator_properties)

                func(self.operator_context, True, **prop)

                def g(v):
                    return f'"{v}"' if type(v) is str else v

                ops_property = ", ".join(
                    (f"{key}={g(value)}" for key, value in prop.items()))
                debug_print(
                    f'running_operator bpy.ops.{self.operator_bl_idname}'
                    f'("{self.operator_context}"{", " + ops_property if ops_property else ops_property})',
                    prop,
                    key='operator',
                )
        except Exception as e:
            from ..utils.debug_util import debug_traceback, debug_trace_stack
            debug_trace_stack(key='operator')
            debug_traceback(key='operator')
            debug_print('__running_by_bl_idname__ ERROR', e, key='operator')
            return e


class OperatorProperty:
    def __analysis_operator_properties__(self, properties_string):
        """Parse operator property string."""
        try:
            ps = properties_string.strip()
            if ps.startswith('(') and ps.endswith(')'):
                ps = ps[1:-1].strip()
            debug_print("__analysis_operator_properties__\n", ps, key='operator')
            properties = parse_operator_properties(ps)
            if properties:
                self["operator_properties"] = str(properties)
        except Exception as e:
            debug_print(e.args, key='operator')
            from ..utils.debug_util import debug_trace_stack, debug_traceback
            debug_trace_stack(key='operator')
            debug_traceback(key='operator')

    @cache_update_lock
    def update_operator(self) -> None:
        """Normalize operator id: bpy.ops.mesh.primitive_plane_add() -> mesh.primitive_plane_add
        bpy.ops.object.transform_apply(location=True, rotation=False, scale=False)
        bpy.ops.transform.translate(value=(0.109431, 2.16517, 0), orient_type='GLOBAL', orient_matrix=((1, 0, 0), (0, 1, 0), (0, 0, 1)), orient_matrix_type='GLOBAL', mirror=False, use_proportional_edit=False, proportional_edit_falloff='SMOOTH', proportional_size=1, use_proportional_connected=False, use_proportional_projected=False, snap=False, snap_elements={'INCREMENT'}, use_snap_project=False, snap_target='CLOSEST', use_snap_self=True, use_snap_edit=True, use_snap_nonedit=True, use_snap_selectable=False)
        """
        if self.is_operator:
            value = self.operator_bl_idname
            key = 'operator_bl_idname'
            if value.startswith('bpy.ops.'):
                self[key] = value = value[8:]
            if ('(' in value) and (')' in value):
                if value.endswith('()'):
                    self[key] = value[:-2]
                else:
                    index = value.index('(')
                    self[key] = value[:index]  # Strip call suffix
                    self.__analysis_operator_properties__(value[index:])
            if self.operator_is_operator:
                self.to_operator_tmp_kmi()

    @cache_update_lock
    def update_operator_properties(self) -> None:
        if not self.operator_is_operator:
            return
        debug_print("update_operator_properties:", self.operator_properties, key='operator')
        self.to_operator_tmp_kmi()

    operator_bl_idname: StringProperty(name='Operator bl_idname',
                                       description='Default is to add the monkey head \n only take the back identifier \nbpy.ops.mesh.primitive_monkey_add -> mesh.primitive_monkey_add',
                                       update=lambda self, context: self.update_operator())

    operator_context: EnumProperty(name='Operator Context',
                                   items=ENUM_OPERATOR_CONTEXT)

    operator_properties: StringProperty(name='Operator Property',
                                        default="{}",
                                        update=lambda self, context: self.update_operator_properties())

    operator_type: EnumProperty(name='Operator Type',
                                items=ENUM_OPERATOR_TYPE,
                                default='OPERATOR'
                                )

    # Operator self passed to element for execution

    @property
    def properties(self):
        """Get operator property dict."""
        try:
            return literal_to_dict(self.operator_properties)
        except Exception as e:
            from ..utils.debug_util import debug_trace_stack, debug_traceback
            debug_print('Properties Error', key='operator')
            debug_print(self.name, key='operator')
            debug_print(f"bpy.ops.{self.operator_bl_idname}", key='operator')
            debug_print(self.operator_properties, key='operator')
            debug_print(e.args, key='operator')
            debug_trace_stack(key='operator')
            debug_traceback(key='operator')
            self['operator_properties'] = "{}"
            return {}

    @property
    def operator_func(self) -> 'bpy.types.Operator | None':
        """Get operator callable

        Returns:
            bpy.types.Operator: _description_
        """
        bl_idname = resolve_operator_bl_idname(self.operator_bl_idname)
        sp = bl_idname.split('.')
        if len(sp) != 2:
            return None
        prefix, suffix = sp
        ops_module = getattr(bpy.ops, prefix, None)
        if ops_module is None:
            return None
        func = getattr(ops_module, suffix, None)
        if func is None:
            return None
        try:
            func.get_rna_type()
        except (AttributeError, RuntimeError, TypeError, KeyError):
            return None
        return func

    @property
    def __operator_id_name_is_validity__(self) -> bool:
        """Return whether operator bl_idname is valid."""
        try:
            fun = self.operator_func
            fun.get_rna_type()
            return fun is not None
        except Exception as e:
            debug_print(e.args, key='operator')
            from ..utils.debug_util import debug_trace_stack, debug_traceback
            debug_trace_stack(key='operator')
            debug_traceback(key='operator')
            return False

    @property
    def __operator_properties_is_validity__(self) -> bool:
        """Return whether operator_properties string is valid."""
        try:
            literal_to_dict(self.operator_properties)
            return True
        except Exception as e:
            debug_print(e.args, key='operator')
            from ..utils.debug_util import debug_trace_stack, debug_traceback
            debug_trace_stack(key='operator')
            debug_traceback(key='operator')
            return False


class ElementOperator(OperatorProperty, ModalProperty, RunOperator, RunOperatorPropertiesSync):

    @property
    def operator_is_operator(self):
        return self.operator_type == "OPERATOR"

    @property
    def operator_is_modal(self):
        return self.operator_type == "MODAL"

    def running_operator(self) -> BaseException | None:
        """Run this element operator; return an exception on failure."""
        if self.operator_is_operator:
            return self.__running_by_bl_idname__()
        if self.operator_is_modal:
            return self.__running_by_modal__()
        return RuntimeError(f'{self!s} invalid operator type')

    def __init_operator__(self):
        """Init operator defaults when element is added."""
        self.__init_direction_by_sort__()
        self.operator_context = 'INVOKE_DEFAULT'
        self.operator_bl_idname = 'mesh.primitive_monkey_add'
        self.operator_properties = r'{}'

    def check_operator_poll(self):
        if self.operator_is_operator or self.operator_is_modal:
            func = self.operator_func
            if func is None:
                debug_print(
                    f"Gesture poll failed {self.parent_gesture} {self.operator_bl_idname}: invalid operator",
                    key='operator',
                )
                return False
            try:
                poll = func.poll()
            except (AttributeError, KeyError):
                debug_print(
                    f"Gesture poll failed {self.parent_gesture} {self.operator_bl_idname}: operator not found",
                    key='operator',
                )
                return False
            if not poll:
                context = bpy.context
                at = context.area.type
                debug_print(
                    f"Gesture poll failed {self.parent_gesture} {self.operator_bl_idname} "
                    f"area:{at} mode:{context.mode}",
                    key='operator',
                )
            return poll
        return True

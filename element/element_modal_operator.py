from functools import cache

import bpy

from ..debug import DEBUG_CACHE

all_event = list((e.identifier, e.name, e.description) for e in bpy.types.Event.bl_rna.properties['type'].enum_items)
all_id = list((i[0] for i in all_event))
from ..utils.public_cache import cache_update_lock, PublicCache
from ..utils.public import PublicSortAndRemovePropertyGroup, PublicProperty
from ..utils.enum import from_rna_get_enum_items, ENUM_NUMBER_VALUE_CHANGE_MODE, ENUM_BOOL_VALUE_CHANGE_MODE
from bpy.app.translations import pgettext_iface


class NumberControl:
    number_value_mode: bpy.props.EnumProperty(
        name="Number Value Mode",
        items=[
            ("ADD", "Add", ""),
            ("SUBTRACT", "Subtract", ""),
            *ENUM_NUMBER_VALUE_CHANGE_MODE
        ])

    @property
    def number_explanation(self):
        nm = self.number_value_mode
        if nm == "ADD":
            return "+"
        elif nm == "SUBTRACT":
            return "-"
        elif nm == "SET_VALUE":
            return pgettext_iface("Set to")
        elif nm == "MOUSE_CHANGES_HORIZONTAL":
            return pgettext_iface("Horizontal Move")
        elif nm == "MOUSE_CHANGES_VERTICAL":
            return pgettext_iface("Vertical Move")
        elif nm == "MOUSE_CHANGES_ARBITRARY":
            return pgettext_iface("Arbitrary Move")
        return "NE"

    @property
    def control_is_number(self):
        """控制的属性是数字"""
        return self.control_property_type in ["INT", "FLOAT"]

    @property
    def default_value(self):
        if rna := self.control_property_rna:
            return rna.default
        return None

    def limit_number_value(self, value):
        """
        限制数字的值
        有最大最小值
        "hard_max", "hard_min", "soft_max", "soft_min"
        """
        if rna := self.control_property_rna:
            hard_max = getattr(rna, "hard_max", None)
            hard_min = getattr(rna, "hard_min", None)
            if hard_max is not None and hard_min is not None:
                return min(max(value, hard_min), hard_max)
        return value


class FloatControl:
    float_incremental_value: bpy.props.FloatProperty(default=1, name="Float Incremental Value", precision=2)
    float_value: bpy.props.FloatProperty(name="Float Value", default=1, precision=2)

    def draw_float(self, layout):
        is_set = self.number_value_mode == "SET_VALUE"
        column = layout.column(align=False)
        column.label(text="Float Value")
        column.prop(self, "number_value_mode", expand=True)
        if is_set:
            column.prop(self, "float_value")
        else:
            column.prop(self, "float_incremental_value", expand=True)

    @property
    def float_explanation(self):
        if self.number_value_mode == "SET_VALUE":
            return f"{self.number_explanation}{self.float_value}"
        if self.is_mouse_move_event:
            return f"{self.number_explanation}"
        return f"{self.number_explanation}{round(self.float_incremental_value, 2)}"

    def float_execute(self, ops):
        op = ops.operator_properties
        key = self.control_property
        float_value = op[key] if key in op else self.default_value

        value = round(self.float_incremental_value, 2)
        m = self.number_value_mode
        if m == "ADD":
            value = float_value + value
        elif m == "SUBTRACT":
            value = float_value - value
        elif m == "SET_VALUE":
            value = self.float_value
        op[key] = round(self.limit_number_value(value), 2)


class IntControl:
    int_incremental_value: bpy.props.IntProperty(name="Int Incremental Value", default=1)
    int_value: bpy.props.IntProperty(name="Int Value", options={'HIDDEN', 'SKIP_SAVE'}, default=0)

    def draw_int(self, layout):
        is_set = self.number_value_mode == "SET_VALUE"
        column = layout.column(align=False)
        column.label(text="Int Value")
        column.prop(self, "number_value_mode", expand=True)
        if is_set:
            column.prop(self, "int_value")
        else:
            column.prop(self, "int_incremental_value", expand=True)

    @property
    def int_explanation(self):
        if self.number_value_mode == "SET_VALUE":
            return f"{self.number_explanation}{self.int_value}"
        if self.is_mouse_move_event:
            return f"{self.number_explanation}"
        return f"{self.number_explanation}{self.int_incremental_value}"

    @property
    def is_int(self) -> bool:
        return self.control_property_type == "INT"

    def int_execute(self, ops):
        op = ops.operator_properties
        key = self.control_property
        int_value = op[key] if key in op else self.default_value

        m = self.number_value_mode
        if m == "ADD":
            value = int_value + self.int_incremental_value
        elif m == "SUBTRACT":
            value = int_value - self.int_incremental_value
        elif m == "SET_VALUE":
            value = self.int_value
        op[key] = self.limit_number_value(value)


class BoolControl:
    bool_value_mode: bpy.props.EnumProperty(name="Boolean Value Mode", items=ENUM_BOOL_VALUE_CHANGE_MODE,
                                            default="SWITCH")

    def draw_boolean(self, layout):
        layout.label(text="Boolean Value")
        layout.prop(self, "bool_value_mode", expand=True)

    @property
    def boolean_explanation(self):
        if self.bool_value_mode == "SET_TRUE":
            return pgettext_iface("Set to True")
        elif self.bool_value_mode == "SET_FALSE":
            return pgettext_iface("Set to False")
        elif self.bool_value_mode == "SWITCH":
            return pgettext_iface("Switch")

    def boolean_execute(self, ops):
        bm = self.bool_value_mode
        op = ops.operator_properties
        key = self.control_property
        print(f"\tcall boolean_execute\t{self.bool_value_mode}\t{op}\t{key}")
        if bm == "SET_TRUE":
            op[key] = True
        elif bm == "SET_FALSE":
            op[key] = False
        elif bm == "SWITCH":
            if key in op:
                op[key] = not op.get(key, False)
            else:
                op[key] = True


class EnumControl:
    enum_value_mode: bpy.props.EnumProperty(items=[
        ('SET', 'Direct setting of enumeration values', ''),
        ('CYCLE',
         'Cyclic setting of the enumeration value (if the set value is the same as the current value, the enumeration switches to the previous value)',
         ''),
        ('TOGGLE', 'Toggle setting Enumeration values (toggle between two enumeration values)',
         ''),
    ])

    ___enum_items___ = {}  # 防止脏数据

    @property
    def enum_key(self) -> str:
        return f"{self.parent_element.operator_bl_idname}.{self.control_property}"

    def __load_enum__(self):
        key = self.enum_key
        if self.control_property_type == "ENUM":
            items = from_rna_get_enum_items(self.control_property_rna)
            if items and key not in EnumControl.___enum_items___:
                EnumControl.___enum_items___[key] = items

    def __get_enum__(self, context):
        self.__load_enum__()
        key = self.enum_key
        if key not in EnumControl.___enum_items___:
            self.__load_enum__()
            return [
                ("None", "", ""),
            ]
        return EnumControl.___enum_items___[key]

    def get_enum_name(self, identifier):
        self.__load_enum__()
        key = self.enum_key
        if items := EnumControl.___enum_items___.get(key, None):
            for (i, name, d, icon, index) in items:
                if identifier == i:
                    return pgettext_iface(name)
        return "Unknown"

    enum_value_a: bpy.props.EnumProperty(options={'HIDDEN', 'SKIP_SAVE'}, items=__get_enum__)
    enum_value_b: bpy.props.EnumProperty(options={'HIDDEN', 'SKIP_SAVE'}, items=__get_enum__)
    enum_reverse: bpy.props.BoolProperty(default=False, name="Invert", description="Reverse enumeration order on loop")
    enum_wrap: bpy.props.BoolProperty(default=True, name="Cycle",
                                      description="Automatically jumps if it is the last or first value in the loop")

    @property
    def enum_explanation(self):
        em = self.enum_value_mode
        a = self.get_enum_name(self.enum_value_a)
        b = self.get_enum_name(self.enum_value_b)
        if em == "SET":
            text = pgettext_iface("Set to")
            return f"{text}->{a}"
        elif em == "TOGGLE":
            text = pgettext_iface("Toggle")
            return f"{text}({a}<->{b})"
        elif em == "CYCLE":
            return em.title()
        return em

    # noinspection DuplicatedCode
    def draw_enum(self, layout):
        column = layout.column(align=True)
        column.prop(self, "enum_value_mode", text="Enumeration Value", expand=True)
        if self.enum_value_mode == "TOGGLE":
            row = column.row(align=True)
            a = row.column(align=True)
            a.label(text="Value A")
            a.prop(self, "enum_value_a", expand=True)

            b = row.column(align=True)
            b.label(text="Value B")
            b.prop(self, "enum_value_b", expand=True)
        elif self.enum_value_mode == "SET":
            column.separator()
            column.prop(self, "enum_value_a", expand=True)
        elif self.enum_value_mode == "CYCLE":
            column.separator()
            column.prop(self, "enum_reverse")
            column.prop(self, "enum_wrap")
            column.separator()
            col = column.column(align=True)
            col.enabled = False
            col.prop(self, "enum_value_a", expand=True)

        is_eq = self.enum_value_mode == "TOGGLE" and self.enum_value_a == self.enum_value_b
        if is_eq:
            column.separator()
            cc = column.column(align=True)
            cc.alert = True
            cc.label(text="Value A == Value B")
            cc = cc.column(align=True)
            cc.enabled = False

    def enum_execute(self, ops):
        op = ops.operator_properties
        key = self.control_property
        enum_value = op.get(key, None)

        m = self.enum_value_mode
        if m == "SET":
            op[key] = self.enum_value_a
        elif m == "TOGGLE":
            if enum_value == self.enum_value_a:
                op[key] = self.enum_value_b
            else:
                op[key] = self.enum_value_a
        elif m == "CYCLE":
            op[key] = self.cycle_enum_value(enum_value)

    def cycle_enum_value(self, orig_value):
        enums = list([i[0] for i in self.__get_enum__(None)])

        bpy.ops.wm.context_cycle_enum()
        is_reverse = self.enum_reverse
        is_wrap = self.enum_wrap
        if orig_value is None:
            orig_value = enums[0]
        orig_index = enums.index(orig_value)

        print("cycle_enum_value", orig_value, orig_index, is_reverse, is_wrap, len(enums), enums)
        if is_reverse:
            if orig_index == 0:
                advance_enum = enums[-1] if is_wrap else enums[0]
            else:
                advance_enum = enums[orig_index - 1]
        else:
            if orig_index == len(enums) - 1:
                advance_enum = enums[0] if is_wrap else enums[-1]
            else:
                advance_enum = enums[orig_index + 1]
        return advance_enum


class KeymapEvent:
    event_type: bpy.props.EnumProperty(items=all_event, default="A", name="Event Type")
    event_ctrl: bpy.props.BoolProperty(default=False, name="Ctrl")
    event_alt: bpy.props.BoolProperty(default=False, name="Alt")
    event_shift: bpy.props.BoolProperty(default=False, name="Shift")

    def sync_type_from_temp_kmi(self, kmi):
        if kmi.type != self.event_type:
            self["event_type"] = all_id.index(kmi.type)  # enum被改为了索引

        if kmi.ctrl != self.event_ctrl:
            self["event_ctrl"] = kmi.ctrl
        if kmi.alt != self.event_alt:
            self["event_alt"] = kmi.alt
        if kmi.shift != self.event_shift:
            self["event_shift"] = kmi.shift

    def sync_to_tem_kmi(self):
        temp_kmi = self.temp_kmi
        temp_kmi.type = self.event_type
        temp_kmi.ctrl = self.event_ctrl
        temp_kmi.shift = self.event_shift
        temp_kmi.alt = self.event_alt

    def draw_event_type(self, layout):
        """绘制事件的类型
        用临时kmi
        并且同步到self.event_type"""
        if self.is_mouse_move_event:
            text = pgettext_iface("Incremental")
            value = self.int_incremental_value if self.is_int else self.float_incremental_value
            layout.label(text=f"{text}{value}")
            return
        temp_kmi = self.temp_kmi
        layout.prop(temp_kmi, "type", text="", full_event=True)
        self.sync_type_from_temp_kmi(temp_kmi)

    @property
    def temp_kmi(self):
        """临时事件的快捷键"""
        from ..utils.public_key import get_temp_kmi
        hs = str(hash(self))
        temp_kmi = get_temp_kmi("modal_event_" + hs, {}, {"type": self.event_type, "value": "PRESS"})
        return temp_kmi

    @property
    def is_mouse_move_event(self) -> bool:
        """是否为鼠标移动事件"""
        if self.control_is_number:
            return self.number_value_mode in (
                "MOUSE_CHANGES_HORIZONTAL",
                "MOUSE_CHANGES_VERTICAL",
                "MOUSE_CHANGES_ARBITRARY",
            )
        return False


@cache
def get_event_index(event) -> int:
    try:
        return event.collection.values().index(event)
    except ValueError:
        ...
    return -1


class EventRelationship(
    PublicSortAndRemovePropertyGroup,
):

    @cache_update_lock
    def copy(self):
        """复制元素"""
        from ..utils.property import __set_prop__
        __set_prop__(self.parent_element, 'modal_events', {'0': self.active_event.___dict_data___})

    @property
    def collection(self):
        return self.parent_element.modal_events

    def _get_index_(self) -> int:
        return get_event_index(self)

    def _set_index_(self, value):
        self.parent_element.modal_events_index = value

    index = property(fget=_get_index_, fset=_set_index_, doc='通过当前项的index,来设置索引的index值,以及移动项')

    @property
    def parent_element(self):
        if self not in PublicCache.__element_parent_element_cache__:
            self.init_cache()
            if DEBUG_CACHE:
                print("parent_element key error", self, self not in PublicCache.__element_parent_element_cache__,
                      PublicCache.__element_parent_element_cache__.get(self))
                print("\tw")
                for k, v in PublicCache.__element_parent_element_cache__.items():
                    print("\t", k, v)
        return PublicCache.__element_parent_element_cache__[self]


class ElementModalOperatorEventItem(
    bpy.types.PropertyGroup,
    PublicProperty,
    # PublicCacheFunc,
    # ElementRelationship,

    NumberControl,
    FloatControl,
    IntControl,
    BoolControl,
    EnumControl,

    KeymapEvent,
    EventRelationship,
):
    def update_control_property(self, context):
        """初始化属性
        根据需要控制的属性进行初始化"""
        if tp := self.control_property_type:
            if default := self.default_value:
                if tp == "FLOAT":
                    self.float_incremental_value = default
                    self.float_value = default
                elif tp == "INT":
                    self.int_incremental_value = default
                    self.int_value = default
                elif tp == "BOOL":
                    ...
                elif tp == "ENUM":
                    self.enum_value_a = default
                    self.enum_value_b = default

    control_property: bpy.props.StringProperty(name="Control Property", update=update_control_property)

    def remove_after(self):
        """继承了EventRelationship的类,需要在最后一个"""
        ...

    def remove_before(self):
        if self.is_last and self.index != 0:  # 被删除项是最后一个
            self.index = self.index - 1  # 索引-1,保持始终有一个所选项

    @property
    def control_property_rna(self):
        if func := self.parent_element.operator_func:
            try:
                rna = func.get_rna_type()
                for i in rna.properties:
                    if i.identifier == self.control_property:
                        return i
            except KeyError:  # KeyError: 'get_rna_type("MESH_OT_fill_gridr") not found'
                ...
        return None

    @property
    def property_is_array(self) -> bool:
        if self.control_property_type != "ENUM":
            if rna := self.control_property_rna:
                return getattr(rna, "is_array", False)
        return False

    @property
    def control_property_type(self) -> str:
        if rna := self.control_property_rna:
            return rna.type
        return "Unknown"

    @property
    def property_name(self) -> str:
        if rna := self.control_property_rna:
            return rna.name
        return "Unknown"

    @property
    def control_property_explanation(self) -> str:
        """控制属性解释"""
        if text := getattr(self, f"{self.control_property_type.lower()}_explanation", None):
            return text
        return "Unknown"

    @property
    def check_property_is_validity(self) -> bool:
        """检测属性是否为有效的"""
        pe = self.parent_element
        if pe and pe.__operator_id_name_is_validity__:
            if self.control_property_rna:
                return True
        return False

    def draw_item(self, layout):
        """UIList draw item"""
        row = layout.row(align=True)
        row.alert = not self.check_property_is_validity

        row.label(text=self.control_property, translate=False)
        row.label(text=self.property_name)
        rr = row.row(align=True)
        rr.alert = self.property_is_array
        rr.label(text=self.control_property_type)
        row.label(text=self.control_property_explanation)
        self.draw_event_type(row)

    def draw_modal(self, layout):
        """绘制单项属性"""
        from .element_modal_operator_cure import ElementModalOperatorEventCRUE
        column = layout.column(align=True)

        col = column.column(align=True)
        row = col.row(align=True)
        row.prop(self, "event_type")
        self.draw_event_type(row)
        row = col.row(align=True)
        row.prop(self, "event_ctrl", translate=False)
        row.prop(self, "event_alt", translate=False)
        row.prop(self, "event_shift", translate=False)

        row = column.row(align=True)
        column.label(text=self.property_name)
        column.label(text=self.control_property_type)
        row.prop(self, "control_property")
        row.operator(ElementModalOperatorEventCRUE.SelectControlProperty.bl_idname, icon="RESTRICT_SELECT_OFF", text="")

        if draw_func := getattr(self, f"draw_{self.control_property_type.lower()}", None):
            draw_func(column.box())
        elif self.control_property_type == "":  # 没输入属性
            column.label(text=f"Please enter the control property")
            return
        else:
            column.label(text=f"Unknown {self.control_property}")
        if dir(self.control_property_rna):
            box = None
            for i in dir(self.control_property_rna):
                if i in ("hard_max", "hard_min", "soft_max", "soft_min", "default", "step", "is_array"):
                    if box is None:
                        box = column.box().column(align=True)
                    name = bpy.app.translations.pgettext_iface(i.replace("_", " ").title())
                    row = box.row(align=True)
                    if i == "is_array":
                        row.alert = self.property_is_array
                    row.label(text=name)
                    if self.control_property_type == "ENUM":
                        # 获取有可能会  current value '256' matches no enum in 'EnumProperty', 'snap_elements', 'default'
                        value = getattr(self.control_property_rna, i, None)
                        row.label(text=f"{self.get_enum_name(value)}({value})", translate=False)
                    else:
                        value = getattr(self.control_property_rna, i, None)
                        row.label(text=f"{value}", translate=False)
            if self.debug_property.debug_mode:
                box = column.box()
                for k in dir(self.control_property_rna):
                    i = getattr(self.control_property_rna, k, None)
                    row = box.row(align=True)
                    row.label(text=f"{k} = {i}")

    def execute(self, ops, context, event) -> bool:
        """
        WHEELUPMOUSE
         WHEELDOWNMOUSE
        """
        if self.is_mouse_move_event:
            ...
        else:
            if self.check_event(event):
                if execute_func := getattr(self, f"{self.control_property_type.lower()}_execute", None):
                    print(f"\texecute_func {execute_func} {self.control_property_type.lower()} {self.control_property}")
                    execute_func(ops)
                    return True
        return False

    def check_event(self, event):
        event_type = self.event_type
        event_ctrl = self.event_ctrl
        event_alt = self.event_alt
        event_shift = self.event_shift

        is_press = event.value == 'PRESS'
        is_event = event.type == event_type
        is_ctrl = event.ctrl == event_ctrl
        is_alt = event.alt == event_alt
        is_shift = event.shift == event_shift

        return is_press and is_event and is_ctrl and is_alt and is_shift

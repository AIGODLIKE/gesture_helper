from functools import cache

import bpy

from ..debug import DEBUG_CACHE

all_event = list((e.identifier, e.name, e.description) for e in bpy.types.Event.bl_rna.properties['type'].enum_items)
all_id = list((i[0] for i in all_event))
from ..utils.public_cache import cache_update_lock, PublicCache
from ..utils.public import PublicSortAndRemovePropertyGroup, PublicProperty
from ..utils.enum import from_rna_get_enum_items, ENUM_NUMBER_VALUE_CHANGE_MODE, ENUM_BOOL_VALUE_CHANGE_MODE


class NumberControl:
    number_value_mode: bpy.props.EnumProperty(items=[
        ("ADD", "Add", ""),
        ("SUBTRACT", "Subtract", ""),
        *ENUM_NUMBER_VALUE_CHANGE_MODE
    ])


class FloatControl:
    float_incremental_value: bpy.props.FloatProperty(default=1)

    def draw_float(self, layout):
        layout.label(text="float")
        layout.prop(self, "float_incremental_value")
        layout.prop(self, "number_value_mode")


class IntControl:
    int_incremental_value: bpy.props.IntProperty(default=1)
    int_value: bpy.props.IntProperty(options={'HIDDEN', 'SKIP_SAVE'}, name="Int Value", default=0)

    def draw_int(self, layout):
        layout.label(text="Int Value")
        layout.prop(self, "number_value_mode", expand=True)
        layout.separator()
        if self.number_value_mode == "SET_VALUE":
            layout.prop(self, "int_value")


class BoolControl:
    bool_value_mode: bpy.props.EnumProperty(items=ENUM_BOOL_VALUE_CHANGE_MODE)

    def draw_bool(self, layout):
        layout.label(text="Boolean Value")
        layout.prop(self, "bool_value_mode")


class EnumControl:
    enum_value_mode: bpy.props.EnumProperty(items=[
        ('SET', 'Direct setting of enumeration values', ''),
        ('CYCLE',
         'Cyclic setting of the enumeration value (if the set value is the same as the current value, the enumeration switches to the previous value)',
         ''),
        ('TOGGLE', 'Toggle setting Enumeration values (toggle between two enumeration values)',
         ''),
    ])

    ___enum___ = []  # 防止脏数据

    def __get_enum__(self, context):
        if self.control_property_type == "ENUM":
            items = from_rna_get_enum_items(self.control_property_rna)
            if items:
                if items != self.___enum___:
                    self.___enum___ = items
            return self.___enum___
        return [
            ("None", "", "")
        ]

    enum_value_a: bpy.props.EnumProperty(options={'HIDDEN', 'SKIP_SAVE'}, items=__get_enum__)
    enum_value_b: bpy.props.EnumProperty(options={'HIDDEN', 'SKIP_SAVE'}, items=__get_enum__)
    enum_reverse: bpy.props.BoolProperty(default=False, name="Invert", description="Reverse enumeration order on loop")
    enum_wrap: bpy.props.BoolProperty(default=True, name="Cycle",
                                      description="Automatically jumps if it is the last or first value in the loop")

    # noinspection DuplicatedCode
    def draw_enum(self, layout):
        layout.prop(self, "enum_value_mode", text="Enumeration Value", expand=True)
        if self.enum_value_mode == "TOGGLE":
            row = layout.row(align=True)
            a = row.column(align=True)
            a.label(text="Value A")
            a.prop(self, "enum_value_a", expand=True)

            b = row.column(align=True)
            b.label(text="Value B")
            b.prop(self, "enum_value_b", expand=True)
        elif self.enum_value_mode == "SET":
            layout.prop(self, "enum_value_a", expand=True)
        elif self.enum_value_mode == "CYCLE":
            layout.separator()
            layout.prop(self, "enum_reverse")
            layout.prop(self, "enum_wrap")

        layout.separator()

        cc = layout.column(align=True)
        is_eq = self.enum_value_mode == "TOGGLE" and self.enum_value_a == self.enum_value_b
        if is_eq:
            cc.alert = True
            cc.label(text="Value A == Value B")
            cc = cc.column(align=True)
            cc.enabled = False


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
        temp_kmi = self.temp_kmi
        layout.prop(temp_kmi, "type", text="", full_event=True)
        self.sync_type_from_temp_kmi(temp_kmi)

    @property
    def temp_kmi(self):
        from ..utils.public_key import get_temp_kmi
        hs = str(hash(self))
        temp_kmi = get_temp_kmi("modal_event_" + hs, {}, {"type": self.event_type, "value": "PRESS"})
        return temp_kmi


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
    control_property: bpy.props.StringProperty(name="Control Property")

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

        row.label(text=self.property_name)
        row.label(text=self.control_property_type)
        row.label(text=self.control_property, translate=False)
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
        row.prop(self, "control_property")
        row.operator(ElementModalOperatorEventCRUE.SelectControlProperty.bl_idname, icon="RESTRICT_SELECT_OFF")
        column.label(text=self.property_name)
        column.label(text=self.control_property_type)
        column.label(text=self.control_property)
        column.label(text=self.control_property_explanation)

        if draw_func := getattr(self, f"draw_{self.control_property_type.lower()}", None):
            draw_func(column.box())

        for i in dir(self.control_property_rna):
            if i in ("hard_max", "hard_min", "soft_max", "soft_min"):
                row = column.row(align=True)
                row.label(text=i)
                row.label(text=str(getattr(self.control_property_rna, i, None)))
        if self.debug_property.debug_mode:
            box = column.box()
            for k in dir(self.control_property_rna):
                i = getattr(self.control_property_rna, k, None)
                row = box.row(align=True)
                row.label(text=f"{k} = {i}")

    def execute(self, context, event) -> bool:
        ...

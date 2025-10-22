import bpy

all_event = list((e.identifier, e.name, e.description) for e in bpy.types.Event.bl_rna.properties['type'].enum_items)
all_id = list((i[0] for i in all_event))
from ..utils.public import PublicSortAndRemovePropertyGroup, PublicProperty, PublicCacheFunc
from .element_relationship import Relationship
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

    def draw_int(self, layout):
        layout.label(text="int")
        layout.prop(self, "int_incremental_value")
        layout.prop(self, "number_value_mode")


class BoolControl:
    bool_value_mode: bpy.props.EnumProperty(items=ENUM_BOOL_VALUE_CHANGE_MODE)

    def draw_bool(self, layout):
        layout.label(text="bool")
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
        return []

    enum_value_a: bpy.props.EnumProperty(options={'HIDDEN', 'SKIP_SAVE'}, items=__get_enum__)
    enum_value_b: bpy.props.EnumProperty(options={'HIDDEN', 'SKIP_SAVE'}, items=__get_enum__)
    enum_reverse: bpy.props.BoolProperty(default=False, name="Invert", description="Reverse enumeration order on loop")
    enum_wrap: bpy.props.BoolProperty(default=True, name="Cycle",
                                      description="Automatically jumps if it is the last or first value in the loop")

    def draw_enum(self, layout):
        layout.label(text="enum")
        layout.prop(self, "enum_wrap")
        layout.prop(self, "enum_value_a")
        layout.prop(self, "enum_value_b")
        layout.prop(self, "enum_reverse")


class KeymapEvent:
    event_type: bpy.props.EnumProperty(items=all_event, default="A")
    event_ctrl: bpy.props.BoolProperty(default=False, name="Ctrl")
    event_alt: bpy.props.BoolProperty(default=False, name="Alt")
    event_shift: bpy.props.BoolProperty(default=False, name="Shift")

    def sync_type_from_temp_kmi(self, kmi):
        if kmi.type != self.event_type:
            self["event_type"] = all_id.index(kmi.type)  # enum被改为了索引

        if kmi.ctrl != self.event_ctrl:
            self["ctrl"] = kmi.ctrl
        if kmi.alt != self.event_alt:
            self["alt"] = kmi.alt
        if kmi.shift != self.event_shift:
            self["shift"] = kmi.shift

    def draw_event_type(self, layout):
        """绘制事件的类型
        用临时kmi
        并且同步到self.event_type"""
        from ..utils.public_key import get_temp_kmi
        hs = str(hash(self))
        temp_kmi = get_temp_kmi("modal_event_" + hs, {}, {"type": self.event_type, "value": "PRESS"})
        layout.prop(temp_kmi, "type", text="", full_event=True)
        self.sync_type_from_temp_kmi(temp_kmi)


class ElementModalOperatorEventItem(
    bpy.types.PropertyGroup,

    NumberControl,
    FloatControl,
    IntControl,
    BoolControl,
    EnumControl,

    KeymapEvent,

    Relationship,

    PublicSortAndRemovePropertyGroup,
    PublicProperty,
    PublicCacheFunc
):
    control_property: bpy.props.StringProperty(name="Control Property")

    @property
    def collection(self):
        return self.parent_element.modal_events

    def _get_index_(self) -> int:
        return self.parent_element.modal_events_index

    def _set_index_(self, value):
        self.parent_element.modal_events_index = value

    index = property(fget=_get_index_, fset=_set_index_, doc='通过当前项的index,来设置索引的index值,以及移动项')

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
    def check_property_is_validity(self) -> bool:
        """检测属性是否为有效的"""
        pe = self.parent_element
        if pe and pe.__operator_id_name_is_validity__:
            if self.control_property_rna:
                return True
        return False

    def draw_item(self, layout):
        row = layout.row(align=True)
        row.alert = not self.check_property_is_validity

        row.label(text=self.property_name)
        row.label(text=self.control_property_type)
        row.label(text=self.control_property)
        self.draw_event_type(row)
        self.draw_modal(layout)

    def draw_modal(self, layout):
        column = layout.column(align=True)
        column.label(text="draw_modal")
        column.prop(self, "event_type")
        column.prop(self, "control_property")
        column.label(text=self.property_name)
        column.label(text=self.control_property_type)
        column.label(text=self.control_property)
        if draw_func := getattr(self, f"draw_{self.control_property_type}", None):
            draw_func(column)

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

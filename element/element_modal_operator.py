import bpy

all_event = list((e.identifier, e.name, e.description) for e in bpy.types.Event.bl_rna.properties['type'].enum_items)
all_id = list((i[0] for i in all_event))
from ..utils.public import PublicSortAndRemovePropertyGroup
from .element_relationship import Relationship


class ElementModalOperatorEventItem(bpy.types.PropertyGroup, Relationship, PublicSortAndRemovePropertyGroup):
    event_type: bpy.props.EnumProperty(items=all_event, default="A")
    control_property: bpy.props.StringProperty(name="Control Property")
    value_mode: bpy.props.EnumProperty(items=[
        ("SET_VALUE", "Set Value", ""),
        ("MOUSE_Y", "Mouse Y", ""),
        ("MOUSE_X", "Mouse X", ""),
    ])

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

    def sync_type_from_temp_kmi(self, kmi):
        if kmi.type != self.event_type:
            self["event_type"] = all_id.index(kmi.type)  # enum被改为了索引

    def draw_event_type(self, layout):
        """绘制事件的类型
        用临时kmi
        并且同步到self.event_type"""
        from ..utils.public_key import get_temp_kmi
        hs = str(hash(self))
        temp_kmi = get_temp_kmi("modal_event_" + hs, {}, {"type": self.event_type, "value": "PRESS"})
        layout.prop(temp_kmi, "type", text="", full_event=True)
        self.sync_type_from_temp_kmi(temp_kmi)

    def draw_item(self, layout):
        row = layout.row(align=True)
        row.alert = not self.check_property_is_validity

        row.label(text=self.property_name)
        row.label(text=self.control_property_type)
        row.label(text=self.control_property)
        # row.prop(self, "control_property", text="")
        row.prop(self, "value_mode", text="")
        self.draw_event_type(row)



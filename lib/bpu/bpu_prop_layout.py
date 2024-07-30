import gpu.matrix
from mathutils import Vector

from .bpu_measure import BpuMeasure


class BpuPropLayout(BpuMeasure):

    def __draw_property__(self):
        """https://docs.blender.org/api/master/bpy_types_enum_items/property_type_items.html#rna-enum-property-type-items
        BOOLEAN:Boolean.
        INT:Integer.
        FLOAT:Float.
        STRING:String.
        ENUM:Enumeration.
        POINTER:Pointer.
        COLLECTION:Collection.
        """
        if self.__property_type__ == "BOOLEAN":
            self.___draw_boolean_property___()
        self.__draw_haver_position_debug__()

    def ___draw_boolean_property___(self) -> None:
        """绘制布尔属性"""
        color = (.5, 0, 0, 1)
        h = self.__text_height__
        from .bpu_draw import __box_path__
        if self.__property_value__:
            with gpu.matrix.push_pop():
                gpu.matrix.translate(self.__margin_vector__)
                self.draw_2d_line(
                    __box_path__(h, h),
                    color=color,
                    line_width=self.__normal_line__
                )
                from ...utils.texture import Texture
                self.draw_rounded_rectangle_area(
                    [h / 2, h / 2],
                    color=self.__background_property_haver_color__,
                    width=h,
                    height=h,
                )
                self.draw_image([0, 0], h, h, Texture.get("TICK"))
        else:
            with gpu.matrix.push_pop():
                gpu.matrix.translate(self.__margin_vector__)
                self.draw_2d_line(
                    __box_path__(h, h),
                    color=color,
                    line_width=self.__normal_line__
                )
                if self.is_haver:
                    self.draw_rounded_rectangle_area(
                        [h / 2, h / 2],
                        color=[.3, .3, .3, 1],
                        width=h,
                        height=h)
                else:
                    self.draw_rounded_rectangle_area(
                        [h / 2, h / 2],
                        color=self.__background_property_normal_color__,
                        width=h,
                        height=h)
        with gpu.matrix.push_pop():
            gpu.matrix.translate(Vector([self.__draw_height__, 0]))
            self.__draw_item__()

    def __modify_property_event__(self):
        if self.__property_type__ == "BOOLEAN":
            from ...utils.public import ADDON_NAME
            from ...element import Element
            if type(self.__property_data__) is Element and self.__property_identifier__ == "enabled":
                import bpy
                prop = f"preferences.addons['{ADDON_NAME}'].preferences.active_gesture{self.___element_value___(self.__property_data__)}.enabled"
                bpy.ops.wm.context_set_boolean(data_path=prop, value=not self.__property_value__)
            else:
                if self.__property_value__:
                    ...
                else:
                    ...

    def ___element_value___(self, element):
        p = f".element['{element.name}']"
        if element.parent_element:
            return f"{self.___element_value___(element.parent_element)}{p}"
        return p

import blf
from mathutils import Vector


class BpuDebug:

    @property
    def __is_debug__(self):
        return self.type.is_menu

    def __draw_debug__(self) -> None:
        """绘制debug层"""
        from .bpu_draw import IS_DEBUG_INFO
        if IS_DEBUG_INFO and self.__is_debug__:
            size = 24
            offset = Vector([-500, -200])
            for index, i in enumerate(
                    (
                            f"parent:{self.parent}",
                            str(self.is_haver),
                            str(self.__draw_size__),
                            str(self.offset_position),
                            str(self.__item_position__),
                            str(self.__child_menu_offset_position__),
                            str(self.offset_position + self.__item_position__ + self.__child_menu_offset_position__),
                            str(self.mouse_position),
                    )[::-1]
            ):
                font_id = self.font_id
                blf.size(font_id, size)
                w, h = blf.dimensions(font_id, i)
                offset += Vector((0, h))
                blf.color(font_id, 1, 0, 0, 1)
                blf.position(font_id, offset[0], offset[1], 99)
                blf.draw(font_id, i)
                offset += Vector((0, 20,))

import bpy

from ...utils.public import get_debug, tag_redraw


class BpuRegister:
    __draw_class__ = {}

    @staticmethod
    def refresh_space():
        return list(getattr(bpy.types, i) for i in dir(bpy.types) if 'Space' in i)

    @classmethod
    def space_subclasses(cls):
        cls.refresh_space()
        sub = bpy.types.Space.__subclasses__()
        return sub

    def register_draw(self):
        if not BpuRegister.__draw_class__:
            for cls in self.space_subclasses():
                sub_class = {}
                # bpy.types.Region.bl_rna.properties['type'].enum_items_static
                for identifier in {'WINDOW', }:  # 'UI', 'TOOLS'
                    try:
                        sub_class[identifier] = cls.draw_handler_add(self.gpu_draw, (), identifier, 'POST_PIXEL')
                    except Exception as e:
                        print(e.args)
                BpuRegister.__draw_class__[cls] = sub_class
        tag_redraw()

    @classmethod
    def unregister_draw(cls):
        if get_debug():
            print('unregister_draw')
        for c, debug_class in BpuRegister.__draw_class__.items():
            for key, value in debug_class.items():
                c.draw_handler_remove(value, key)
        BpuRegister.__draw_class__.clear()
        tag_redraw()

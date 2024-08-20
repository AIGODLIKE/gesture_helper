import bpy

from ....utils.public import tag_redraw


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
        i = id(self)
        if i not in self.__draw_class__:
            sub_class = {}
            for cls in self.space_subclasses():
                # bpy.types.Region.bl_rna.properties['type'].enum_items_static
                for identifier in {'WINDOW', }:  # 'UI', 'TOOLS'
                    try:
                        sub_class[(cls, identifier)] = cls.draw_handler_add(
                            self.__gpu_draw__,
                            (),
                            identifier,
                            'POST_PIXEL')
                    except Exception as e:
                        print(e.args)
            self.__draw_class__[i] = sub_class
        tag_redraw()

    def unregister_draw(self):
        # if get_debug():
        #     print(f'unregister_draw\t{id(self)}')
        i = id(self)
        if i in self.__draw_class__:
            for (c, identifier), draw_fun in self.__draw_class__[i].items():
                c.draw_handler_remove(draw_fun,identifier)
            self.__draw_class__.pop(i)
        tag_redraw()

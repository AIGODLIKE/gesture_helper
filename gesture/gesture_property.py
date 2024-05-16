from bpy.props import IntProperty, BoolProperty


class GestureProperty:

    def update_index(self, _):
        try:
            el = self.element.values()[self.index_element]
            if el:
                el.radio = True
        except IndexError:
            ...

    index_element: IntProperty(name='索引', update=update_index)

    enabled: BoolProperty(
        default=True,
        name='启用此手势',
        description="""启用禁用此手势,主要是keymap的更新""",
        update=lambda self, context: self.key_update()
    )

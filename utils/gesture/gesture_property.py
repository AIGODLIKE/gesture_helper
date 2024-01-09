from bpy.props import IntProperty, BoolProperty

from bpy.app.translations import pgettext as _
class GestureProperty:

    def update_index(self, context):
        try:
            el = self.element.values()[self.index_element]
            if el:
                el.radio = True
        except IndexError:
            ...

    index_element: IntProperty(name='index', update=update_index)

    enabled: BoolProperty(
        default=True,
        name=_('Enable this gesture'),
        description=_("""Enable or disable this gesture, primarily for keymap updates"""),
        update=lambda self, context: self.key_update()
    )

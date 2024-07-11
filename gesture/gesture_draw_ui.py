class GestureDrawUI:
    def draw_item(self, layout):
        layout.prop(self, 'enabled', text='')
        layout.separator()
        layout.prop(self, 'name', text='')
        layout.label(text=self.description)

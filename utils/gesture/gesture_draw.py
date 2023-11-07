class GestureDraw:
    def draw_ui(self, layout):
        layout.prop(self, 'enabled', text='')
        layout.separator()
        layout.prop(self, 'name', text='')

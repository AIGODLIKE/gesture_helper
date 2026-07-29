from ...src.lib.overlay_layout import OverlayLayout


class GestureShowTips(OverlayLayout):
    """Draggable hint block initially pinned to the top-left of the 3D View."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.anchor = 'TOP_LEFT_REGION'
        self.root_draggable = True
        self.background = (0.12, 0.04, 0.04, 0.85)
        self.font_size = 18

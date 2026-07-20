from ...src.lib.overlay_layout import OverlayLayout


class GestureShowTips(OverlayLayout):
    """Hint block pinned to the bottom-left corner of the 3D View."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.anchor = 'BOTTOM_LEFT_REGION'
        self.background = (0.12, 0.04, 0.04, 0.85)
        self.font_size = 18

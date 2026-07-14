class BpuColor:
    # Dark flat defaults aligned with gesture draw theme.
    __background_normal_color__ = [0.035, 0.035, 0.038, 1.0]
    __background_active_color__ = [0.02, 0.45, 0.40, 1.0]  # self.active
    __background_haver_color__ = [0.28, 0.18, 0.75, 0.85]
    __background_property_haver_color__ = [0.02, 0.45, 0.40, 0.7]
    __background_property_normal_color__ = [0.05, 0.05, 0.055, 1.0]
    __background_alert_color__ = [0.85, 0.15, 0.15, 1.0]  # self.alert

    __outline_color__ = [0.55, 0.55, 0.58, 0.28]
    __outline_active_color__ = [0.75, 0.75, 0.78, 0.42]
    __outline_width__ = 0.75

    __debug_layout_bound_color__ = [.6, .1, .1, 1]
    __debug_layout_margin_color__ = [.1, .2, 1, 1]

    __debug_item_bound_color__ = [.6, 0, 0, .8]
    __debug_item_margin_color__ = [0, .6, 0, .8]
    __debug_menu_bound_color__ = [.1, .2, 1, 1]
    __debug_menu_margin_color__ = [.5, .5, .5, 1]

    __text_normal_color__ = [0.92, 0.92, 0.94, 1]
    __text_haver_color__ = [1, 1, 1, 1]
    __text_alert_color__ = [1, 0.3, 0.3, 1]

    __separator_color__ = [0.35, 0.35, 0.38, 1]

    __layout_radius__ = 10
    __layout_segments__ = 48

    __debug_line__ = 1
    __separator_line__ = 2
    __normal_line__ = 1

    @property
    def ___text_color___(self) -> list[int]:
        if self.type.is_clickable or self.type.is_operator or self.type.is_prop:
            if self.is_haver:
                return self.__text_haver_color__
        elif self.alert:
            return self.__text_alert_color__
        return self.__text_normal_color__

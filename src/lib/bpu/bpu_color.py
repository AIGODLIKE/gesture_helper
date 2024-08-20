class BpuColor:
    __background_normal_color__ = [.01, .01, .01, 1]
    __background_active_color__ = [0, .5, .7, 1]  # self.active
    __background_haver_color__ = [.5, .5, .5, 1]
    __background_property_haver_color__ = [.1, .2, .5, 1]
    __background_property_normal_color__ = [.1, .1, .1, 1]
    __background_alert_color__ = [1, 0, 0, 1]  # self.alert

    __debug_layout_bound_color__ = [.6, .1, .1, 1]
    __debug_layout_margin_color__ = [.1, .2, 1, 1]

    __debug_item_bound_color__ = [.6, 0, 0, .8]
    __debug_item_margin_color__ = [0, .6, 0, .8]
    __debug_menu_bound_color__ = [.1, .2, 1, 1]
    __debug_menu_margin_color__ = [.5, .5, .5, 1]

    __text_normal_color__ = [.9, .9, .9, 1]
    __text_haver_color__ = [1, 1, 1, 1]
    __text_alert_color__ = [1, 0, 0, 1]

    __separator_color__ = [.4, .4, .4, 1]

    __layout_radius__ = 10
    __layout_segments__ = 40

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

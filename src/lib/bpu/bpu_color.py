from ....utils import theme_defaults


class BpuColor:
    # Dark flat defaults aligned with gesture draw theme (scene-linear).
    __background_normal_color__ = list(theme_defaults.BACKGROUND)
    __background_active_color__ = list(theme_defaults.OPERATOR_ACTIVE)
    __background_haver_color__ = list(theme_defaults.BACKGROUND_HOVER)
    __background_property_haver_color__ = list(theme_defaults.BACKGROUND_PROPERTY_HOVER)
    __background_property_normal_color__ = list(theme_defaults.BACKGROUND_PROPERTY)
    __background_alert_color__ = list(theme_defaults.BACKGROUND_ALERT)

    __outline_color__ = list(theme_defaults.OUTLINE)
    __outline_active_color__ = list(theme_defaults.OUTLINE_ACTIVE)
    __outline_width__ = theme_defaults.OUTLINE_WIDTH

    __debug_layout_bound_color__ = [.6, .1, .1, 1]
    __debug_layout_margin_color__ = [.1, .2, 1, 1]

    __debug_item_bound_color__ = [.6, 0, 0, .8]
    __debug_item_margin_color__ = [0, .6, 0, .8]
    __debug_menu_bound_color__ = [.1, .2, 1, 1]
    __debug_menu_margin_color__ = [.5, .5, .5, 1]

    __text_normal_color__ = list(theme_defaults.TEXT_DEFAULT)
    __text_haver_color__ = list(theme_defaults.TEXT_ACTIVE)
    __text_alert_color__ = list(theme_defaults.TEXT_ALERT)

    __separator_color__ = list(theme_defaults.SEPARATOR)

    __layout_radius__ = 10
    __layout_segments__ = 48

    __debug_line__ = 1
    __separator_line__ = 2
    __normal_line__ = 1

    @property
    def ___text_color___(self) -> list:
        if self.type.is_clickable or self.type.is_operator or self.type.is_prop:
            if self.is_haver:
                return self.__text_haver_color__
        elif self.alert:
            return self.__text_alert_color__
        return self.__text_normal_color__

from bpy.types import PreferencesView
from ..property import get_rna_data


# pie property  # 饼菜单所需属性
class PieProperty:
    PIE_PROPERTY_ITEMS = ['pie_animation_timeout',
                          'pie_tap_timeout',
                          'pie_initial_timeout',
                          'pie_menu_radius',
                          'pie_menu_threshold',
                          'pie_menu_confirm',
                          ]
    PIE_ANIMATION_TIMEOUT_DATA = get_rna_data(
        PreferencesView, 'pie_animation_timeout', fill_copy=True)
    PIE_TAP_TIMEOUT_DATA = get_rna_data(
        PreferencesView, 'pie_tap_timeout', fill_copy=True)
    PIE_INITIAL_TIMEOUT_DATA = get_rna_data(
        PreferencesView, 'pie_initial_timeout', fill_copy=True)
    PIE_MENU_RADIUS_DATA = get_rna_data(
        PreferencesView, 'pie_menu_radius', fill_copy=True)
    PIE_MENU_THRESHOLD_DATA = get_rna_data(
        PreferencesView, 'pie_menu_threshold', fill_copy=True)
    PIE_MENU_CONFIRM_DATA = get_rna_data(
        PreferencesView, 'pie_menu_confirm', fill_copy=True)
    # custom element property   default
    PIE_ANIMATION_TIMEOUT_DATA['default'] = 6
    PIE_TAP_TIMEOUT_DATA['default'] = 20
    PIE_INITIAL_TIMEOUT_DATA['default'] = 0
    PIE_MENU_RADIUS_DATA['default'] = 100
    PIE_MENU_THRESHOLD_DATA['default'] = 20
    PIE_MENU_CONFIRM_DATA['default'] = 60

    PIE_ANIMATION_TIMEOUT_DATA['min'] = PIE_TAP_TIMEOUT_DATA['min'] = PIE_INITIAL_TIMEOUT_DATA['min'] = \
        PIE_MENU_RADIUS_DATA['min'] = PIE_MENU_THRESHOLD_DATA['min'] = PIE_MENU_CONFIRM_DATA['min'] = -1
    PIE_ANIMATION_TIMEOUT_DATA['soft_min'] = PIE_TAP_TIMEOUT_DATA['soft_min'] = PIE_INITIAL_TIMEOUT_DATA['soft_min'] = \
        PIE_MENU_RADIUS_DATA['soft_min'] = PIE_MENU_THRESHOLD_DATA['soft_min'] = PIE_MENU_CONFIRM_DATA['soft_min'] = 0

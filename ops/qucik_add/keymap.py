import bpy


class GestureQuickAddKeymap:
    """注册快捷键"""
    kc = bpy.context.window_manager.keyconfigs.addon  # 获取按键配置addon的
    km = kc.keymaps.new(name='Window', space_type='EMPTY', region_type='WINDOW')
    kmi = None

    @classmethod
    def register(cls):
        from .gesture_preview import GesturePreview
        cls.kmi = cls.km.keymap_items.new(GesturePreview.bl_idname, 'ACCENT_GRAVE', 'PRESS',
                                          ctrl=True, alt=True, shift=True)

    @classmethod
    def unregister(cls):
        cls.km.keymap_items.remove(cls.kmi)

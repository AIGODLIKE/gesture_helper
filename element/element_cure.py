import bpy
from bpy.props import BoolProperty

from .element_property import ElementDirectionProperty
from ..utils.public import PublicProperty, PublicOperator, get_pref
from ..utils.public_cache import cache_update_lock, PublicCacheFunc


class ElementCURE:
    """增删查改"""

    def __init__(self):
        pass

    @cache_update_lock
    def copy(self):
        from ..utils import PropertyGetUtils, PropertySetUtils
        copy_data = PropertyGetUtils.props_data(self.active_element)

        parent = self.parent
        PropertySetUtils.set_prop(parent, 'element', {'0': copy_data})

    @property
    def is_movable(self) -> bool:
        pe = self.parent_element
        if pe:
            if not pe.is_movable:
                return False
        move_from = ElementCURE.MOVE.move_item

        is_ok = move_from and (self not in list(move_from.element))
        move_element = is_ok and move_from != self and self != self.parent_element
        movable = (self.is_child_gesture or self.is_selected_structure) and move_element
        return bool(movable)

    class ElementPoll(PublicProperty, PublicOperator, PublicCacheFunc):

        @classmethod
        def poll(cls, _):
            return cls._pref().active_element is not None

    class ADD(PublicOperator, PublicProperty, ElementDirectionProperty):
        bl_label = '添加手势项'
        bl_idname = 'gesture.element_add'

        add_active_radio: BoolProperty(name="添加元素时是否设置为活动项", default=False,
                                       options={'HIDDEN', 'SKIP_SAVE'})

        @property
        def collection(self):
            r = self.relationship
            ae = self.active_element
            if r == 'SAME' and ae:
                pe = ae.parent_element
                # 如果没有同级则快进到根
                if pe:
                    return pe.element
            elif r == 'CHILD' and ae:
                return ae.element
            return self.active_gesture.element

        @property
        def add_name(self):
            return self.element_type.title() + (" " + self.selected_type.title() if self.is_selected_structure else "")

        def execute(self, _):
            add = self.collection.add()
            add.cache_clear()

            if self.active_element:
                self.active_element.radio = True  # 还是保持默认选择是当前

            add.element_type = self.element_type
            add.selected_type = self.selected_type
            add.__init_element__()
            add.cache_clear()
            add.name = self.add_name

            if self.pref.add_element_property.add_active_radio or self.add_active_radio:
                if self.active_element:
                    self.active_element.show_child = True
                add.radio = True
            return {'FINISHED'}

    class REMOVE(ElementPoll):
        bl_label = '删除手势项'
        bl_idname = 'gesture.element_remove'

        def execute(self, _):
            self.pref.active_element.remove()
            self.cache_clear()
            return {'FINISHED'}

    class MOVE(ElementPoll):
        bl_idname = 'gesture.element_move'
        bl_label = '移动手势项'
        move_item = None

        cancel: BoolProperty(default=False, options={'SKIP_SAVE'})

        @cache_update_lock
        def move(self):
            from ..utils import PropertyGetUtils, PropertySetUtils
            move_to = getattr(bpy.context, 'move_element', None)
            move_from = ElementCURE.MOVE.move_item

            if move_from:
                move_data = PropertyGetUtils.props_data(move_from)
                if move_to:
                    PropertySetUtils.set_prop(move_to, 'element', {'0': move_data})
                else:
                    PropertySetUtils.set_prop(move_from.parent_gesture, 'element', {'0': move_data})
                self.other.is_move_element = False
                move_from.remove()
            self.cache_clear()

        @property
        def other(self):
            return self.pref.other_property

        def execute(self, _):
            other = self.other
            move_from = ElementCURE.MOVE.move_item

            if self.cancel:

                self.cache_clear()
                other.is_move_element = False
                ElementCURE.MOVE.move_item = None
                return {'FINISHED'}
            elif move_from:
                self.move()
                ae = self.active_element
                self.cache_clear()
                if ae:
                    ae.radio = True
                    ae.__check_duplicate_name__()

                self.cache_clear()
                other.is_move_element = False
                ElementCURE.MOVE.move_item = None
                return {'FINISHED'}

            ElementCURE.MOVE.move_item = self.active_element
            other.is_move_element = True
            self.cache_clear()
            return {'FINISHED'}

    class SORT(ElementPoll):
        bl_label = '排序手势项'
        bl_idname = 'gesture.element_sort'

        is_next: BoolProperty()

        def execute(self, _):
            self.active_element.sort(self.is_next)
            self.cache_clear()
            return {'FINISHED'}

    class COPY(ElementPoll):
        bl_idname = 'gesture.element_copy'
        bl_label = '复制手势项'

        def execute(self, _):
            self.active_element.copy()
            self.cache_clear()

            ae = self.active_element
            if ae:
                ae.radio = True
                ae.collection[-1].__check_duplicate_name__()

            self.cache_clear()
            return {'FINISHED'}

    class ScriptEdit(ElementPoll):
        bl_label = '编辑脚本'
        bl_idname = 'gesture.element_operator_script_edit'

        # 获取脚本数据块
        def get_text_data(self) -> bpy.types.Text:
            active = self.active_element
            name = active.name
            text = bpy.data.texts.get(name)
            if text is None:
                text = bpy.data.texts.new(name)
            text.clear()
            text.write(active.operator_script)
            text.gesture_element_hash = str(hash(self.active_element))
            return text

        @staticmethod
        def add_save_key(context):
            keymap = get_text_generic_keymap(context)
            if keymap is not None:
                keymap.keymap_items.new(ElementCURE.ScriptSave.bl_idname, type="S", value="PRESS", ctrl=True)

        def execute(self, context):
            get_text_window(context, self.get_text_data())
            self.add_save_key(context)
            return {'FINISHED'}

    class ScriptSave(ElementPoll):
        bl_label = '保存脚本'
        bl_idname = 'gesture.element_operator_script_save'

        @classmethod
        def poll(cls, context):
            pref = get_pref()
            h = context.space_data.text.gesture_element_hash
            hashOk = h == str(hash(pref.active_element))
            return super().poll(context) and hashOk

        @staticmethod
        def register_ui():
            bpy.types.TEXT_HT_header.append(draw_save_script_button)

        @staticmethod
        def unregister_ui():
            bpy.types.TEXT_HT_header.remove(draw_save_script_button)

        def remove_save_key(self, context):
            keymap = get_text_generic_keymap(context)
            if keymap is not None:
                while True:
                    ops = keymap.keymap_items.find_from_operator(self.bl_idname)
                    if ops is None:
                        break
                    keymap.keymap_items.remove(ops)

        def execute(self, context):
            text = context.space_data.text
            self.active_element.operator_script = text.as_string()
            bpy.data.texts.remove(text)
            self.remove_save_key(context)
            bpy.ops.wm.window_close()
            return {'FINISHED'}


def get_text_generic_keymap(context) -> bpy.types.KeyMapItem | None:
    return get_keymap(context, 'Text Generic')


def get_keymap(context, keymap_name):
    kc = context.window_manager.keyconfigs
    keymaps = kc.user.keymaps
    keymap = keymaps.get(keymap_name)
    if keymap is None:
        um = kc.user.keymaps.get(keymap_name)
        keymap = keymaps.new(keymap_name, space_type=um.space_type, region_type=um.region_type)
    return keymap


def draw_save_script_button(self, context):
    layout = self.layout
    pref = get_pref()
    text = context.space_data.text
    active = pref.active_element

    if getattr(text, "gesture_element_hash", False) == str(hash(active)):
        row = layout.row()
        row.alert = True
        row.operator(ElementCURE.ScriptSave.bl_idname, text=f"保存脚本数据 {active.name} Ctrl + S")


def get_text_window(context: bpy.types.Context, text: bpy.types.Text) -> bpy.types.Window:
    window = get_text_editor_window(context)
    if not window:
        bpy.ops.wm.window_new()
        window = bpy.context.window_manager.windows[-1]
    area = window.screen.areas[-1]
    area.type = "TEXT_EDITOR"
    area.spaces[0].text = text


def get_text_editor_window(context: bpy.types.Context):
    windows = context.window_manager.windows.values()
    for window in windows:
        areas = window.screen.areas.values()
        area = areas[0]
        if len(areas) == 1 and area.type == "TEXT_EDITOR":
            return window

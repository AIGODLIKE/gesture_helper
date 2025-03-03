import bpy
from bpy.app.translations import pgettext
from bpy.props import BoolProperty

from .element_property import ElementDirectionProperty
from ..utils.public import PublicProperty, PublicOperator, get_pref
from ..utils.public_cache import cache_update_lock, PublicCacheFunc


class ElementCURE:
    """增删查改"""

    @cache_update_lock
    def copy(self):
        """复制元素"""
        from ..utils import PropertySetUtils
        PropertySetUtils.set_prop(self.parent, 'element', {'0': self.active_element.___dict_data___})

    @property
    def is_movable(self) -> bool:
        """是可以移动到的项目"""

        move_from = ElementCURE.MOVE.move_item
        if move_from.parent_element == self:
            # 移动到当前项的父级
            return False
        elif self in move_from.element_child_iteration:
            # 移动到的是被移动的子级
            return False

        is_ok = move_from and (self not in list(move_from.element))
        move_element = is_ok and move_from != self and self != self.parent_element
        movable = (self.is_child_gesture or self.is_selected_structure) and move_element
        return bool(movable)

    @property
    def is_can_be_cut(self) -> bool:
        """是可剪切的"""
        return self.is_child_gesture or self.is_selected_structure

    class ElementPoll(PublicProperty, PublicOperator, PublicCacheFunc):

        @classmethod
        def poll(cls, _):
            return cls._pref().active_element is not None

    class ADD(PublicOperator, PublicProperty, ElementDirectionProperty):
        bl_label = 'Add gesture item'
        bl_idname = 'gesture.element_add'

        add_active_radio: BoolProperty(name="Whether or not to set it as an active item when adding an element",
                                       default=False,
                                       options={'HIDDEN', 'SKIP_SAVE'})

        # Some users may experience Gizmo failure in version 4.3 due to attribute updates ,Rewrite Solution
        from ..utils.enum import ENUM_SELECTED_TYPE
        from bpy.props import EnumProperty
        selected_type: EnumProperty(
            name='Select structure type',
            items=ENUM_SELECTED_TYPE,
        )

        @property
        def collection(self):
            r = self.relationship
            ae = self.active_element
            if r == 'SAME' and ae:
                pe = ae.parent_element
                # 如果没有同级则快进到根
                if pe:
                    return pe.element
            elif r == 'CHILD' and ae and ae.is_have_add_child:
                return ae.element
            return self.active_gesture.element

        @property
        def add_name(self):
            return self.element_type.title() + (" " + self.selected_type.title() if self.is_selected_structure else "")

        def execute(self, _):
            add = self.collection.add()
            add.cache_clear()

            if self.active_element:
                add.cache_clear()
                self.active_element.radio = True  # 还是保持默认选择是当前

            add.element_type = self.element_type
            add.selected_type = self.selected_type
            add.__init_element__()
            add.cache_clear()
            add.name = self.add_name

            if self.pref.add_element_property.add_active_radio or self.add_active_radio:
                if self.active_element:
                    self.active_element.show_child = True
                add.cache_clear()
                add.radio = True
            bpy.ops.wm.save_userpref()
            return {'FINISHED'}

    class REMOVE(ElementPoll):
        bl_label = 'Remove gesture item'
        bl_idname = 'gesture.element_remove'

        def invoke(self, context, event):
            from ..utils.adapter import operator_invoke_confirm
            return operator_invoke_confirm(
                self,
                event,
                context,
                title="Confirm To Delete The Element?",
                message=f"{self.active_element.name}",
            )

        def execute(self, _):
            self.pref.active_element.remove()
            self.cache_clear()
            bpy.ops.wm.save_userpref()
            return {'FINISHED'}

    class MOVE(ElementPoll):
        bl_idname = 'gesture.element_move'
        bl_label = 'Move gesture item'
        move_item = None

        cancel_move: BoolProperty(default=False, options={'SKIP_SAVE'})

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
                move_from.remove()
            self.cache_clear()

        @property
        def other(self):
            return self.pref.other_property

        def execute(self, _):
            move_from = ElementCURE.MOVE.move_item

            if self.cancel_move:
                self.cache_clear()
                ElementCURE.MOVE.move_item = None
                return {'FINISHED'}
            elif move_from:
                # 有移动项,直接移动
                self.move()
                ae = self.active_element
                self.cache_clear()
                if ae:
                    ae.radio = True

                self.cache_clear()
                ElementCURE.MOVE.move_item = None
                return {'FINISHED'}

            ElementCURE.MOVE.move_item = self.active_element
            self.cache_clear()
            bpy.ops.wm.save_userpref()
            return {'FINISHED'}

    class SORT(ElementPoll):
        bl_label = 'Sort gesture item'
        bl_idname = 'gesture.element_sort'

        is_next: BoolProperty()

        def execute(self, _):
            self.active_element.sort(self.is_next)
            self.cache_clear()
            bpy.ops.wm.save_userpref()
            return {'FINISHED'}

    class COPY(ElementPoll):
        bl_idname = 'gesture.element_copy'
        bl_label = 'Copy gesture item'

        def execute(self, _):
            self.active_element.copy()
            self.cache_clear()

            ae = self.active_element
            if ae:
                ae.radio = True

            self.cache_clear()
            bpy.ops.wm.save_userpref()
            return {'FINISHED'}

    class CUT(ElementPoll):
        bl_idname = 'gesture.element_cut'
        bl_label = 'Cut gesture item'

        __cut_data__ = None  # 剪切的数据

        cancel_cut: BoolProperty(default=False, options={'SKIP_SAVE'})

        @cache_update_lock
        def cut(self):
            from ..utils import PropertySetUtils
            cut = ElementCURE.CUT.__cut_data__

            # 移动中
            cut_to = getattr(bpy.context, 'cut_element', None)
            if cut_to:
                PropertySetUtils.set_prop(cut_to, 'element', {'0': cut})
            else:
                PropertySetUtils.set_prop(self.active_gesture, 'element', {'0': cut})
            self.cache_clear()

        @classmethod
        def poll(cls, context):
            if cls.__cut_data__ is not None:
                return True
            return super().poll(context)

        def invoke(self, context, event):
            if self.cancel_cut:
                from ..utils.adapter import operator_invoke_confirm
                return operator_invoke_confirm(
                    self,
                    event,
                    context,
                    title="Confirm To Cancel The Cut?",
                    message="Cut Content Will Be Lost",
                )
            return self.execute(context)

        def execute(self, context):
            cut = ElementCURE.CUT.__cut_data__
            if self.cancel_cut:
                self.cache_clear()
                ElementCURE.CUT.__cut_data__ = None
                return {'FINISHED'}
            elif cut:
                self.cut()
                ae = self.active_element
                self.cache_clear()
                if ae:
                    self.cache_clear()
                    ae.radio = True
                self.cache_clear()
                ElementCURE.CUT.__cut_data__ = None
                bpy.ops.wm.save_userpref()
                return {'FINISHED'}

            # 选择一个移动项
            ae = self.pref.active_element
            ElementCURE.CUT.__cut_data__ = ae.___dict_data___
            ae.remove()
            print(ae, self.active_element, ElementCURE.CUT.__cut_data__)
            self.cache_clear()
            return {'FINISHED'}

    class ScriptEdit(ElementPoll):
        bl_idname = 'gesture.element_operator_script_edit'
        bl_label = 'Edit script'

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
        bl_label = 'Save script'
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
            bpy.ops.wm.save_userpref()
            return {'FINISHED'}

    class SwitchShowChild(ElementPoll):
        bl_idname = 'gesture.element_switch_show_child'
        bl_label = 'Switch show child'

        def execute(self, context):
            value = not self.pref.active_element.show_child
            for i in self.pref.active_gesture.element_iteration:
                i.show_child = value
            return {"FINISHED"}


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
        row.operator(ElementCURE.ScriptSave.bl_idname, text=pgettext("Save Script Data %s Ctrl + S") % active.name)


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

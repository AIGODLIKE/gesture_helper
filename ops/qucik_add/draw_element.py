# def draw_element(self, event):
#     try:
#         with self.element_bpu as bpu:
#             bpu.offset_position = self.offset_position + self.offset
#             bpu.mouse_position = self.mouse_position
#             # bpu.font_size = 50
#             bpu.layout_margin = 80
#
#             ag = self.pref.active_gesture
#             if not ag:
#                 bpu.label("请选择一个手势", alert=True)
#             elif not ag.element:
#                 bpu.label("请选择一个元素", alert=True)
#             else:
#                 self.draw_element_child(ag.element, bpu)
#             if bpu.check_event(event):
#                 return True
#     except Exception as e:
#         self.element_bpu.unregister_draw()
#         print(e.args)
#         import traceback
#         traceback.print_exc()
#         traceback.print_stack()
#     return False


# def draw_element_child(self, element, bpu: BpuLayout):
#     for e in reversed(element.values()):
#         if e.show_child:
#             self.draw_element_child(e.element, bpu)
#         bpu.prop(e, "enabled", text=f"{' ' * e.level}{e.name}")

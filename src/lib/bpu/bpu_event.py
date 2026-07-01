import bpy


class BpuEvent:
    def check_event(self, event: bpy.types.Event):
        """Return whether event is on this page."""
        if event.type == "LEFTMOUSE" and event.value == "RELEASE":  # left click
            # print("check_event\t", self.__layout_haver_histories__, self.__active_property__, self.__active_operator__)
            if self.__active_operator__:
                getattr(self.__active_operator__, "running_operator")()
                return True
            elif self.__active_property__:
                self.__active_property__.__modify_property_event__()
        return bool(len(self.parent_top.__layout_haver_histories__))

import bpy


class BpuEvent:
    def check_event(self, event: bpy.types.Event):
        """判断是否有在此页面上"""
        if event.type == "LEFTMOUSE" and event.value == "RELEASE":  # left click
            ao = getattr(self, "__active_operator__", False)
            if ao:
                getattr(ao, "running_operator")()
                return True
            setattr(self, "__active_operator__", None)
        return bool(len(self.__layout_haver__))

import bpy


class BpuEvent:
    def check_event(self, event: bpy.types.Event) -> "BpuLayout":
        """判断是否有在此页面上"""
        if event.type == "LEFTMOUSE" and event.value == "CLICK":  # left click
            ao = getattr(self, "__active_operator__", False)
            if ao:
                getattr(ao, "running_operator")()
            setattr(self, "__active_operator__", None)

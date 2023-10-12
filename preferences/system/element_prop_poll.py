import ast

import bpy

from ...public import PublicBmesh


class ElementPropPoll(PublicBmesh):
    poll_string: str

    @staticmethod
    def _is_enabled_addon(addon_name):
        return addon_name in bpy.context.preferences.addons

    __globals = {"__builtins__": None,
                 'len': len,
                 'is_enabled_addon': _is_enabled_addon,  # 测试是否启用此插件
                 #  'max':max,
                 #  'min':min,
                 }

    # @cache
    @staticmethod
    def _object_bmesh():
        return ElementPropPoll.get_bmesh(bpy.context.object)

    @property
    def _is_select_vert(self) -> bool:
        """反回活动网格是否选中了顶点的布尔值"""
        bm = self._object_bmesh()
        if bm:
            for i in bm.verts:
                if i.select:
                    return True
        return False

    @property
    def _is_select_edges(self) -> bool:
        """反回活动网格是否选中了顶点的布尔值"""
        bm = self._object_bmesh()
        if bm:
            for i in bm.edges:
                if i.select:
                    return True
        return False

    @property
    def _is_select_faces(self) -> bool:
        """反回活动网格是否选中了顶点的布尔值"""
        bm = self._object_bmesh()
        if bm:
            for i in bm.faces:
                if i.select:
                    return True
        return False

    @property
    def poll_args(self):
        """反回poll eval的环境

        Returns:
            _type_: _description_
        """
        context = bpy.context
        data = bpy.data
        o = bpy.context.object
        sel_objs = bpy.context.selected_objects
        use_sel_obj = ((not o) and sel_objs)  # 使用选择的obj最后一个
        obj = sel_objs[-1] if use_sel_obj else o
        mesh = obj.data if obj else None

        return {'bpy': bpy,
                'C': context,
                'D': data,
                'O': obj,
                'mode': context.mode,
                'tool': context.tool_settings,
                'mesh': mesh,
                'is_select_vert': self._is_select_vert,
                'is_select_edges': self._is_select_edges,
                'is_select_faces': self._is_select_faces,
                }

    def _from_poll_string_get_bool(self, poll_string: str) -> bool:
        dump_data = ast.dump(ast.parse(poll_string), indent=2)
        shield = {'Del',
                  'Import',
                  'Lambda',
                  'Return',
                  'Global',
                  'Assert',
                  'ClassDef',
                  'ImportFrom',
                  #   'Module',
                  #   'Expr',
                  #   'Call',
                  }
        is_shield = {i for i in shield if i in dump_data}
        if is_shield:
            print(Exception(f'input poll_string is invalid\t{is_shield} of {poll_string}'))
            return False
        else:
            e = eval(poll_string, self.__globals, self.poll_args)
            return bool(e)

    @classmethod
    def cache_clear_element_prop_poll(cls):
        # cls._object_bmesh.cache_clear()
        ...

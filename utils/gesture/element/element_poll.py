from __future__ import annotations

import ast

import bpy
from bpy.props import StringProperty


class ElementPoll:
    @property
    def poll_bool(self) -> bool:
        """反回当前self的poll

        Returns:
            bool: _description_
        """

        try:
            poll = self._from_poll_string_get_bool(self.poll_string)
            return poll
        except Exception as e:
            print(f'ERROR:\tpoll_bool  {self.poll_string}\t', e.args, self.poll_args)
            return False

    def _update_string(self, context):
        a = self.poll_bool

    poll_string: StringProperty(name='条件',
                                default='True',
                                description="""poll表达式
    {'bpy': bpy,
    'C': bpy.context,
    'D': bpy.data,
    'O': bpy.context.object,
    'mode': bpy.context.mode,
    'tool': bpy.context.tool_settings,
    }
    """,
                                update=_update_string, )

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
        return ...
        # ElementPropPoll.get_bmesh(bpy.context.object)

    @property
    def _is_select_vert(self) -> bool:
        """TODO 反回活动网格是否选中了顶点的布尔值
        每次更新网格时会有卡顿"""
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
        C = bpy.context
        D = bpy.data
        ob = bpy.context.object
        sel_objs = bpy.context.selected_objects
        use_sel_obj = ((not ob) and sel_objs)  # 使用选择的obj最后一个
        O = sel_objs[-1] if use_sel_obj else ob
        mesh = O.data if O else None

        return {'bpy': bpy,
                'C': C,
                'D': D,
                'O': O,
                'mode': C.mode,
                'tool': C.tool_settings,
                'mesh': mesh,
                # 'is_select_vert': self._is_select_vert,
                # 'is_select_edges': self._is_select_edges,
                # 'is_select_faces': self._is_select_faces,
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

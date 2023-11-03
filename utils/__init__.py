import bpy

exclude_items = {'rna_type', 'bl_idname', 'srna'}  # 排除项


def space_layout(layout: 'bpy.types.UILayout', space: int, level: int) -> 'bpy.types.UILayout':
    """
    设置间隔
    """
    if level == 0:
        return layout.column()
    indent = level * space / bpy.context.region.width

    split = layout.split(factor=indent)
    split.column()
    return split.column()


def _get_blender_icon(icon_style):
    """反回图标名称

    Args:
        icon_style (类型或直接输入两个已设置的图标, optional): 图标风格,也可以自已设置图标id. Defaults to 'TRIA' | 'ARROW' | 'TRI' | (str, str).
    Returns:
        (str,str): _description_
    """
    icon_data = {
        'TRI': ('DISCLOSURE_TRI_DOWN', 'DISCLOSURE_TRI_RIGHT'),
        'TRIA': ('TRIA_DOWN', 'TRIA_RIGHT'),
        'SORT': ('SORT_ASC', 'SORT_DESC'),
        'ARROW': ('DOWNARROW_HLT', 'RIGHTARROW'),
        'CHECKBOX': ('CHECKBOX_HLT', 'CHECKBOX_DEHLT'),
        'RESTRICT_SELECT': ('RESTRICT_SELECT_OFF', 'RESTRICT_SELECT_ON'),
    }
    if icon_style in icon_data:
        return icon_data[icon_style]
    else:
        return icon_data['TRI']


def icon_two(bool_prop, style='CHECKBOX', custom_icon: tuple[str, str] = None, ) -> str:
    """输入一个布尔值,反回图标类型str
    Args:
        bool_prop (_type_): _description_
        custom_icon (tuple[str, str], optional): 输入两个自定义的图标名称,True反回前者. Defaults to None.
        style (str, optional): 图标的风格. Defaults to 'CHECKBOX'.
    Returns:
        str: 反回图标str
    """
    icon_true, icon_false = custom_icon if custom_icon else _get_blender_icon(style)
    return icon_true if bool_prop else icon_false


class PropertySetUtils:

    @staticmethod
    def set_collection_data(prop, data):
        """_summary_

        Args:
            prop (_type_): _description_
            data (_type_): _description_
        """
        for i in data:
            pro = prop.add()
            PropertySetUtils.set_property_data(pro, data[i])

    @staticmethod
    def set_prop(prop, path, value):
        pr = getattr(prop, path, None)
        if pr is not None:
            pro = prop.bl_rna.properties[path]
            typ = pro.type
            try:
                if typ == 'POINTER':
                    PropertySetUtils.set_property_data(prop, value)
                elif typ == 'COLLECTION':
                    PropertySetUtils.set_collection_data(pr, value)
                elif typ == 'ENUM' and pro.is_enum_flag:
                    # 可多选枚举
                    setattr(prop, path, set(value))
                else:
                    setattr(prop, path, value)
            except Exception as e:
                print(typ, pro, value, e)

    @staticmethod
    def set_property_data(prop, data: dict):
        """_summary_

        Args:
            prop (_type_): _description_
            data (_type_): _description_
        """
        for k, item in data.items():
            pr = getattr(prop, k, None)
            if pr is not None:
                PropertySetUtils.set_prop(prop, k, item)


class PropertyGetUtils:
    @staticmethod
    def collection_data(prop, exclude=(), reversal=False) -> dict:
        """获取输入集合属性的内容

        Args:
            prop (_type_): _description_

        Returns:
            :param prop:
            :param reversal:
            :param exclude:
        """
        data = {}
        for index, value in enumerate(prop):
            if value not in exclude_items:
                data[index] = PropertyGetUtils.props_data(value, exclude, reversal)
        return data

    @staticmethod
    def props_data(prop, exclude=(), reversal=False) -> dict:
        """获取输入的属性内容
        可多选枚举(ENUM FLAG)将转换为列表 list(用于json写入,json 没有 set类型)
        集合信息将转换为字典 index当索引保存  dict

        Args:
            prop (bl_property): 输入blender的属性内容
            exclude (tuple): 排除内容
            reversal (bool): 反转排除内容,如果为True,则只搜索exclude
        Returns:
            dict: 反回字典式数据,
        """
        data = {}

        for i in prop.bl_rna.properties:
            try:
                id_name = i.identifier
                is_ok = (id_name in exclude) if reversal else (
                        id_name not in exclude)

                is_exclude = id_name not in exclude_items

                if is_exclude and is_ok:
                    typ = i.type

                    pro = getattr(prop, id_name, None)
                    if not pro:
                        continue

                    if typ == 'POINTER':
                        pro = PropertyGetUtils.props_data(pro, exclude, reversal)
                    elif typ == 'COLLECTION':
                        pro = PropertyGetUtils.collection_data(pro, exclude, reversal)
                    elif typ == 'ENUM' and i.is_enum_flag:
                        # 可多选枚举
                        pro = list(pro)
                    data[id_name] = pro
            except Exception as e:
                print(e.args)
                import traceback
                traceback.print_exc()
        return data

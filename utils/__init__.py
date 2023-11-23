import bpy

exclude_items = {'rna_type', 'bl_idname', 'srna'}  # 排除项


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
        if pr is not None or path in prop.bl_rna.properties:
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
            if pr is not None or k in prop.bl_rna.properties:
                PropertySetUtils.set_prop(prop, k, item)

    @staticmethod
    def _for_set_prop(prop, pro, pr):
        for index, j in enumerate(pr):
            try:
                getattr(prop, pro)[index] = j
            except Exception as e:
                print(e.args)

    @staticmethod
    def set_operator_property_to(properties: 'bpy.types.KeyMapItem.properties', property) -> None:
        """注入operator property
        在绘制项时需要使用此方法
        set operator property
        self.operator_property:
        """
        props = property
        for pro in props:
            pr = props[pro]
            if hasattr(properties, pro):
                if type(pr) == tuple:
                    # 阵列参数
                    PropertySetUtils._for_set_prop(properties, pro, pr)
                else:
                    try:
                        setattr(properties, pro, props[pro])
                    except Exception as e:
                        print(e.args)


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

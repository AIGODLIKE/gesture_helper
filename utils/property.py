# version = 1.0.3
# 1.0.3: custom export via ___set_properties___ / ___properties___
# 1.0.2: get_kmi_property exclude 'hyper', 'hyper_ui',
exclude_items = {'rna_type', 'bl_idname', 'srna'}  # Excluded identifiers

import bpy
from mathutils import Euler, Vector, Matrix

from .public_cache import PublicCache


def __set_collection_data__(prop, data):
    """Set collection property values

    Args:
        prop (_type_): _description_
        data (_type_): _description_
    """
    for i in data:
        pro = prop.add()
        set_property(pro, data[i])


def __set_prop__(prop, path, value):
    """Set a single property value."""
    pr = getattr(prop, path, None)
    if pr is not None or path in prop.bl_rna.properties:
        pro = prop.bl_rna.properties[path]
        typ = pro.type
        try:
            if typ == 'POINTER':
                set_property(pr, value)
            elif typ == 'COLLECTION':
                __set_collection_data__(pr, value)
            elif typ == 'BOOL' and path == 'radio' and PublicCache._suppress_radio_update:
                return
            elif typ == 'ENUM' and pro.is_enum_flag:
                # Multi-select enum (ENUM FLAG)
                setattr(prop, path, set(value))
            else:
                setattr(prop, path, value)
        except Exception as e:
            print('ERROR', typ, pro, value, e)
            import traceback
            traceback.print_stack()
            traceback.print_exc()


def set_property(prop, data: dict):
    if func := getattr(prop, "___set_properties___", None):  # Custom property getter/setter hook
        func(data)
    else:
        __set_property__(prop, data)


def __set_property__(prop, data: dict):
    for k, item in data.items():
        pr = getattr(prop, k, None)
        if pr is not None or k in prop.bl_rna.properties:
            __set_prop__(prop, k, item)


def set_property_to_kmi_properties(properties: 'bpy.types.KeyMapItem.properties', props) -> None:
    """Inject operator properties into KMI (use when drawing items)
    set operator property
    self.operator_property:
    """

    def _for_set_prop(prop, pro, pr):
        for index, j in enumerate(pr):
            try:
                getattr(prop, pro)[index] = j
            except Exception as e:
                print(e.args)

    for pro in props:
        pr = props[pro]
        if hasattr(properties, pro):
            if pr is tuple:
                # Array property values
                _for_set_prop(properties, pro, pr)
            else:
                try:
                    setattr(properties, pro, props[pro])
                except Exception as e:
                    print(e.args)


def __collection_data__(prop, exclude=(), reversal=False) -> dict:
    """Get collection property contents

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
            data[index] = get_property(value, exclude, reversal)
    return data


def get_property(prop, exclude=(), reversal=False) -> dict:
    """
    Get property contents for export.
    ENUM FLAG values become lists (JSON has no set type).
    Collections become dicts keyed by index

    Args:
        prop (bl_property): Blender property to read
        exclude (tuple): identifiers to exclude/include
        reversal (bool): if True, only include identifiers in exclude
    Returns:
        dict: exported property data,
    """
    if hasattr(prop, "___properties___"):  # Custom property getter/setter hook
        if res := getattr(prop, "___properties___", None):
            if type(res) == dict:
                return res
    return __get_property__(prop, exclude, reversal)


def __get_property__(prop, exclude=(), reversal=False) -> dict:
    data = {}
    for pr in prop.bl_rna.properties:
        try:
            identifier = pr.identifier
            is_ok = (identifier in exclude) if reversal else (
                    identifier not in exclude)

            is_exclude = identifier not in exclude_items
            if is_exclude and is_ok:
                typ = pr.type

                pro = getattr(prop, identifier, None)
                if pro is None:
                    continue
                if typ == 'POINTER':
                    pro = get_property(pro, exclude, reversal)
                elif typ == 'COLLECTION':
                    pro = __collection_data__(pro, exclude, reversal)
                elif typ == 'ENUM' and pr.is_enum_flag:
                    # Multi-select enum (ENUM FLAG)
                    pro = list(pro)
                elif typ == 'FLOAT' and pr.subtype == 'COLOR':
                    # color
                    pro = pro[:]
                elif isinstance(pro, (Euler, Vector, bpy.types.bpy_prop_array)):
                    pro = pro[:]
                elif isinstance(pro, Matrix):
                    res = ()
                    for j in pro:
                        res += (*tuple(j[:]),)
                    pro = res

                data[identifier] = pro
        except Exception as e:
            print(prop, pr)
            print(e.args)
            import traceback
            traceback.print_exc()
    return data


def get_kmi_property(kmi):
    return dict(
        get_property(
            kmi,
            exclude=(
                'name', 'id', 'show_expanded', 'properties', 'idname', 'map_type', 'active', 'propvalue',
                'shift_ui', 'ctrl_ui', 'alt_ui', 'oskey_ui', 'is_user_modified', 'is_user_defined',
                'hyper', 'hyper_ui',
            )
        )
    )


def get_property_enum_items(cls, prop_name) -> list:
    res = []
    for item in cls.properties[prop_name].enum_items:
        res.append((item.identifier, item.name, item.description))
    return res

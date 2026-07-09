# version = 1.0.3
# 1.0.3: custom export via ___set_properties___ / ___properties___
# 1.0.2: get_kmi_property exclude 'hyper', 'hyper_ui',
exclude_items = {'rna_type', 'bl_idname', 'srna'}  # Excluded identifiers

import bpy
from mathutils import Euler, Vector, Matrix

from .public_cache import PublicCache
from ..utils.debug_util import debug_print


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
            debug_print('ERROR', typ, pro, value, e, key='operator')
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


def collect_operator_property_overrides(operator) -> dict:
    """Collect non-default RNA properties from a context-menu button operator."""
    properties = {}
    for pr in operator.bl_rna.properties:
        identifier = pr.identifier
        if identifier in exclude_items:
            continue
        if pr.type in ("POINTER", "COLLECTION"):
            continue
        if pr.is_hidden:
            continue
        try:
            value = getattr(operator, identifier)
        except (AttributeError, TypeError):
            continue

        if pr.type == 'ENUM' and pr.is_enum_flag:
            value = set(value) if value else set()
            default = set(pr.default) if pr.default else set()
            if value == default:
                continue
            properties[identifier] = value
        elif getattr(pr, 'is_array', False):
            value = tuple(value[:])
            default = tuple(pr.default_array[:])
            if value == default:
                continue
            properties[identifier] = value
        elif isinstance(value, (Euler, Vector, bpy.types.bpy_prop_array)):
            value = tuple(value[:])
            default = tuple(pr.default[:]) if hasattr(pr.default, '__getitem__') else (pr.default,)
            if value == default:
                continue
            properties[identifier] = value
        elif isinstance(value, Matrix):
            value = tuple(tuple(row[:]) for row in value)
            default = tuple(tuple(row[:]) for row in pr.default) if pr.default else ()
            if value == default:
                continue
            properties[identifier] = value
        else:
            default = pr.default
            if pr.type == "ENUM" and default == '':
                default = value
            if default == value:
                continue
            properties[identifier] = value
    return properties


def set_property_to_kmi_properties(properties: 'bpy.types.KeyMapItem.properties', props) -> None:
    """Inject operator properties into KMI (use when drawing items)."""
    if not props or properties is None:
        return
    __set_property__(properties, props)


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
            debug_print(prop, pr, key='operator')
            debug_print(e.args, key='operator')
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


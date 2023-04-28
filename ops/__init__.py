from . import ops

mod_tuple = (
    ops,
)


def register():
    for mod in mod_tuple:
        mod.register()


def unregister():
    for mod in mod_tuple:
        mod.unregister()

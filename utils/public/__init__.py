class Debug:
    register = False


def register_module_factory(module):
    def register_module():
        for mod in module:
            if Debug.register:
                print('register ', mod)
            mod.register()

    def unregister_module():
        for mod in reversed(module):
            if Debug.register:
                print('unregister ', mod)
            mod.unregister()

    return register_module, unregister_module

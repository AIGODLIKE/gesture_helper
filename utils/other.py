def get_element_all_name_set():
    names = set()
    from .public import get_pref
    pref = get_pref()
    for g in pref.gesture:
        for e in g.element_iteration:
            names.add(e.name)
        names.add(g.description)
    return names

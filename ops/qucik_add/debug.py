def __draw__(bpu, event):
    # column = bpu.column()
    column = bpu
    column.label(event.type)
    a = column.operator("mesh.primitive_plane_add", text="Emm 添加")
    a.size = 10

    menu = column.menu("text")
    menu.active = True
    menu.label("fsef开发了可发二十艾萨克发生")
    menu.operator("mesh.primitive_plane_add", "aaaaa爱上发涩发a")
    menu.label("fsef1")
    menu.label("fsef2")
    menu.operator("mesh.primitive_plane_add", "fasefase某某地某某地")

    for i in range(4):
        column.label(f"text {i} sdjrogijsodirgiosjdrg")
    column.separator()

    ops = column.operator("mesh.primitive_plane_add")
    ops.size = 100

    m = menu.menu("sub", "test_id")
    m.active = True
    m.label("sub menu 1")
    m.label("sub menu 2")
    m.label("sub menu A")
    ops = m.operator("mesh.primitive_plane_add", "AAAAA")
    ops = m.operator("mesh.primitive_plane_add", "AAseA")
    ops = m.operator("mesh.primitive_plane_add", "AAAefaefA")

    column.label(event.value)

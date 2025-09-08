import os

"""
1. pip install cairosvg
2. install gtk
https://github.com/tschoonj/GTK-for-Windows-Runtime-Environment-Installer/releases

https://www.modb.pro/db/175191
"""

import cairosvg

size = 256
to_folder_path = os.path.join(os.path.dirname(__file__), "blender")
form_svg_folder = r"D:\Blender\blender\release\datafiles\icons_svg"
# ANIM_DATA.png
# CURVES_DATA.png
# MATERIAL_DATA.png
# OBJECT_DATAMODE.png
# PARTICLE_DATA.png
# RIGHTARROW_THIN.png
# SCRIPTPLUGINS.png
# TEXTURE_DATA.png
# WORLD_DATA.png
for file_name in os.listdir(form_svg_folder):
    file_path = os.path.join(form_svg_folder, file_name)
    if os.path.isfile(file_path) and file_name.endswith(".svg"):
        new_name = file_name.replace(".svg", ".png").upper().replace(".PNG", ".png")
        to_path = os.path.join(to_folder_path, new_name)
        print("SVG to PNG", file_name, "->", new_name)
        cairosvg.svg2png(
            url=file_path,
            write_to=to_path,
            parent_width=size,
            parent_height=size,
            output_width=size,
            output_height=size,
            scale=1
        )

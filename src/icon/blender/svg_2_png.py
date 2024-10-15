import os

"""
1. pip install cairosvg
2. install gtk
https://github.com/tschoonj/GTK-for-Windows-Runtime-Environment-Installer/releases

https://www.modb.pro/db/175191
"""

import cairosvg

size = 64
to_folder_path = os.path.dirname(__file__)
form_svg_folder = r"D:\Blender\blender\release\datafiles\icons_svg"

for file_name in os.listdir(form_svg_folder):
    file_path = os.path.join(form_svg_folder, file_name)
    if os.path.isfile(file_path) and file_name.endswith(".svg"):
        new_name = file_name.replace(".svg", ".png").upper().replace(".PNG", ".png")
        to_path = os.path.join(to_folder_path, new_name)
        print("SVG to PNG", file_name, "->", new_name)
        cairosvg.svg2png(
            url=file_path,
            write_to=to_path,
            output_width=size,
            output_height=size,
            scale=1
        )

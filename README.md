# Gesture Helper

which allows you to quickly use gestures to run the blender operator or change properties.

![image](https://github.com/user-attachments/assets/da8f96e3-129e-462f-93aa-4b71bf16002a)


https://github.com/user-attachments/assets/40e0eeac-7fd7-4a5b-aa2a-21e6b6053ee6

![Preview](src/readme/preview.gif)

Install:
If it is version 4.2, you can drag the plugin directly into Blender.
Conventional methods:
![图片alt](src/readme/install.jpg)

Simple to use:

* Import Preset

  ![Import Preset](src/readme/import_preset.jpg)
    * Maya Axis & Coordinate: Quick Setup Axes and Coordinates
      ![Import Preset](src/readme/preset_c_s_r.gif)
    * Maya Operator: Active object operator, each mode displays different content
      ![Import Preset](src/readme/preset_s_r.gif)
    * Maya Select: Selection gesture
      ![Import Preset](src/readme/preset_c_r.gif)
    * Maya Switch Mode: Use right click to switch mode
      ![Import Preset](src/readme/preset_r.gif)
    * MX Preset:
      ![Import Preset](src/readme/preset_mx.gif)
        * M:Press M to Merge
        * X:Press X to Delete
        * Z:Press Z to Switch View

Gesture:
Keymaps: Select the area where keymap can be triggered    
![Keymaps](src/readme/keymaps.jpg)

Element:  
There are three types

* Child: You can set the direction and expand to child when dragging and dropping gestures.
* Operator: operator, either by using bl_idname, or by using a custom script
    * Fast Add Operator: Operator Right-click to add operator
      ![Add Operator](src/readme/fast_add_operator.gif)
    * Fast Add Property: Property Right-click to add property,Supports int, float, string, and enum.
      ![Add Property](src/readme/fast_add_property.gif)
* Select Structure:Selection structure, requires some logical thinking, can be conditional on the display of child
  or operators
  ![Keymaps](src/readme/selected_structure_set_poll.gif)

* Property:
  Panel Name: N Panel Name
  Author: Export Data Author
  Name Translation: Translation of the name

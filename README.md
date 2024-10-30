# Gesture Helper

which allows you to quickly use gestures to run the blender operator or change properties.

![image](https://github.com/user-attachments/assets/da8f96e3-129e-462f-93aa-4b71bf16002a)


https://github.com/user-attachments/assets/40e0eeac-7fd7-4a5b-aa2a-21e6b6053ee6

![preview](https://github.com/user-attachments/assets/04cbd99a-91de-4818-8cc5-e4bc64dcf69f)

Install:

If it is version 4.2, you can drag the plugin directly into Blender.

Conventional methods:
![install](https://github.com/user-attachments/assets/f6b140ef-1acf-4072-bbae-8747cc23f299)

Simple to use:

* Import Preset

  ![import_preset](https://github.com/user-attachments/assets/2b0dfa04-2470-41ac-ba4a-d6743d4e0d11)
    * Maya Axis & Coordinate: Quick Setup Axes and Coordinates
      ![preset_c_s_r](https://github.com/user-attachments/assets/48d82cdf-e33a-40b3-b591-d89f177e6c5b)
    * Maya Operator: Active object operator, each mode displays different content
      ![preset_s_r](https://github.com/user-attachments/assets/a5a7a20b-28da-49f5-ace8-7d26fcb8d35c)
    * Maya Select: Selection gesture
      ![preset_c_r](https://github.com/user-attachments/assets/46aca90c-2154-4a25-8ca1-c111dd27be3d)
    * Maya Switch Mode: Use right click to switch mode
      ![preset_r](https://github.com/user-attachments/assets/b0e1aa67-c080-430d-9781-b13680479ae6)
    * MX Preset:
      ![preset_mx](https://github.com/user-attachments/assets/962169f0-b489-426e-9b9a-bef89496a07a)
        * M:Press M to Merge
        * X:Press X to Delete
        * Z:Press Z to Switch View

Gesture:

Keymaps: Select the area where keymap can be triggered    
![keymaps](https://github.com/user-attachments/assets/2b89c59b-e951-4eff-8d52-d910f99c4c96)

Element:  
There are three types

* Child:
    You can set the direction and expand to child when dragging and dropping gestures.
  
* Operator:
    operator, either by using bl_idname, or by using a custom script
    * Fast Add Operator: Operator Right-click to add operator
      ![fast_add_operator](https://github.com/user-attachments/assets/f7934c61-cc05-47b6-a22f-f1f8f0c3a764)
    * Fast Add Property: Property Right-click to add property,Supports int, float, string, and enum.
      ![fast_add_property](https://github.com/user-attachments/assets/c1d0474a-f596-4417-a531-9a699a6d68c5)
* Select Structure:Selection structure, requires some logical thinking, can be conditional on the display of child
  or operators
  ![selected_structure_set_poll](https://github.com/user-attachments/assets/5e917a9b-1ae7-445c-984c-a6a540e0d882)

* Property:
  
  Panel Name: N Panel Name
  
  Author: Export Data Author
  
  Name Translation: Translation of the name

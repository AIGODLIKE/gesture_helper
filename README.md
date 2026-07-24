# Gesture Helper

Quickly use gestures to run Blender operators or change properties.

<img width="1355" height="895" alt="image" src="https://github.com/user-attachments/assets/5086f258-922e-4f22-9447-2960c53545ab" />



https://github.com/user-attachments/assets/40e0eeac-7fd7-4a5b-aa2a-21e6b6053ee6

![preview](https://github.com/user-attachments/assets/04cbd99a-91de-4818-8cc5-e4bc64dcf69f)

## Usage

* Import Preset

  ![import_preset](https://github.com/user-attachments/assets/2b0dfa04-2470-41ac-ba4a-d6743d4e0d11)
    * Maya Axis & Coordinate: Quick Setup Axes and Coordinates
      ![preset_c_s_r](https://github.com/user-attachments/assets/48d82cdf-e33a-40b3-b591-d89f177e6c5b)
    * Maya Operator: Context operators for the active object; content changes by mode
      ![preset_s_r](https://github.com/user-attachments/assets/a5a7a20b-28da-49f5-ace8-7d26fcb8d35c)
    * Maya Select: Selection gesture
      ![preset_c_r](https://github.com/user-attachments/assets/46aca90c-2154-4a25-8ca1-c111dd27be3d)
    * Maya Switch Mode: Switch modes with right-click
      ![preset_r](https://github.com/user-attachments/assets/b0e1aa67-c080-430d-9781-b13680479ae6)
    * MX Preset:
      ![preset_mx](https://github.com/user-attachments/assets/962169f0-b489-426e-9b9a-bef89496a07a)
        * M:Press M to Merge
        * X:Press X to Delete
        * Z:Press Z to Switch View

  The Debug section has a separate `Show example presets` option. Those
  opt-in presets cover gesture/menu styles, all radial directions, every
  element and operator context, modal controls, property actions and displays,
  layouts, state icons, and validation states. Every example imports disabled
  so it cannot replace an existing shortcut unexpectedly.

Gesture:

Keymaps: Select the area where keymap can be triggered    
![keymaps](https://github.com/user-attachments/assets/2b89c59b-e951-4eff-8d52-d910f99c4c96)

Element:  
There are eight types: conditional structure, child gesture, operator,
divider, property display, row, column, and box.

* Child:
    You can set the direction and expand to child when dragging and dropping gestures.
  
* Operator:
    Run a Blender operator by `bl_idname`, either directly or through the
    configurable modal-control wrapper.
    * Fast Add Operator: Operator Right-click to add operator
      ![fast_add_operator](https://github.com/user-attachments/assets/f7934c61-cc05-47b6-a22f-f1f8f0c3a764)
    * Fast Add Property: Right-click a property to add boolean, integer,
      float, string, or enum actions, or an interactive property display.
      ![fast_add_property](https://github.com/user-attachments/assets/c1d0474a-f596-4417-a531-9a699a6d68c5)
* Select Structure:Selection structure, requires some logical thinking, can be conditional on the display of child
  or operators
  ![selected_structure_set_poll](https://github.com/user-attachments/assets/5e917a9b-1ae7-445c-984c-a6a540e0d882)

* Dividing Line: Separates groups in layout panels and persistent menus.

* Property: Shows a live boolean, integer, float, or enum value. Numeric
  values support horizontal, vertical, or free drag and mouse-wheel changes.

* Row / Column / Box: Nest elements into aligned, independently scaled layout
  containers with an optional main action.

* Preset metadata:
  
  Panel Name: N Panel Name
  
  Author: Export Data Author
  
  Name Translation: Translation of the name

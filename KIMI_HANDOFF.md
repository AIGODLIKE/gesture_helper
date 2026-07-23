# Gesture Helper Handoff

Updated: 2026-07-23

## Current Branch

- Branch: `feature/gesture-layout-renderer`
- Remote: `origin`
- No local development server or Blender modal process is intentionally left running.

## Implemented In This Working Tree

### Persistence, import/export, and keymaps

- Gesture JSON persistence now writes a temporary file in the destination folder,
  flushes and fsyncs it, validates the JSON payload, then atomically replaces the
  old file. See `utils/gesture_persistence.py`.
- Manual export and automatic gesture backups use the same atomic writer.
- Import immediately saves the imported data and reports a warning if disk writing
  fails, so memory-only imports are not mistaken for durable configuration.
- Import sanitization now validates the basic JSON object structure, defaults old
  gestures to `gesture_type: RADIAL`, and defaults invalid menu styles to `PANEL`.
- New layout, property, and overlay fields have been added to the element export
  whitelist in `ops/export_import.py`.
- Keymap registration selects `wm.gesture_operator` for radial gestures and
  `wm.gesture_menu` for menu gestures. The orphan cleanup list includes both IDs.

### Gesture and menu modes

- Added immutable-at-UI-creation gesture types: `RADIAL` and `MENU`.
- New gesture dialog asks for the type. Existing data defaults to `RADIAL`.
- Added `wm.gesture_menu` with a separate persistent menu runtime. It does not use
  the radial gesture input state machine.
- Menu supports `PANEL`, `COMPACT`, and `BORDERLESS` styles, title/header, close
  button, root order, hover child flyouts, property rows, condition filtering, and
  separator rows.
- Menu closes on Escape, right mouse, close button, or outside left click. A second
  menu in the same window replaces the first one. External modal operators pause
  the menu event handling until they finish.
- `SessionState.clear()` asks the menu runtime to remove active draw handlers before
  addon reload/unregister cleanup.

### Layout, property, and UI work

- Layout containers have alignment (`EXPAND`, `LEFT`, `CENTER`, `RIGHT`), scale,
  advanced settings, a unique main action, native-style separator rows, and layout
  presets. `Switch Layout Type` was left unchanged.
- Layout execution uses its selected main action, otherwise the first runnable leaf
  for compatibility with old layouts.
- Property elements default to `scene.cycles.samples` and fall back to
  `scene.render.resolution_percentage` when Cycles is unavailable.
- Properties support horizontal/vertical/arbitrary drag, reverse direction, value
  visibility/format/precision, boolean on/off labels and icons, and a name-sync
  operator. Quick add separates fixed native values, modal mouse adjustment, and
  gesture-controlled properties.
- `overlay_offset` is stored and exported for radial elements. Automatic radial
  collision avoidance was started but is NOT complete; the stored offset has UI
  support but still needs to be applied consistently to final draw/hit positions.
- GPU status presentation distinguishes disabled, context/poll blocked, missing
  operator, invalid operator arguments, invalid/read-only properties, and bad
  conditional structure. It uses a compact badge plus a severity accent instead of
  color alone.
- Preview input now has `gesture/preview_input.py`, separate from the normal radial
  input processor.
- Theme defaults moved from purple/cyan emphasis to neutral Blender dark gray with
  blue active states and explicit warning/error accents.

## Important Files

- `utils/gesture_persistence.py`: durable config write/load lifecycle.
- `ops/export_import.py`: export whitelist and import migrations.
- `gesture/gesture_keymap.py`, `gesture/addon_keymap.py`: keymap lifecycle.
- `gesture/menu.py`, `ops/menu.py`: persistent menu implementation.
- `gesture/gesture_input.py`, `gesture/preview_input.py`: independent normal and
  preview input policies.
- `element/element_property.py`, `element/element_draw.py`: new layout/property
  RNA fields and editor UI.
- `element/element_layout_gpu.py`, `element/element_gpu_draw.py`,
  `element/element_status.py`: layout draw, status display, hit areas.

## Verification Already Run

- `python -m compileall -q .` passed after the current worktree changes.
- `git diff --check` passed; output only contains CRLF conversion warnings.
- The property implementation was additionally checked against Blender 4.2.1 and
  Blender 5.2.0 for RNA registration, default property setup, drag options,
  boolean display settings, and name-sync registration.

## Recommended Next Steps

1. Run a full Blender 4.2.1 and 5.2.0 register/unregister/reload smoke test with
   both radial and menu gestures. Confirm no residual `wm.gesture_operator` or
   `wm.gesture_menu` keymap items after rename, delete, disable, import, and reload.
2. Exercise the persistent menu in a real `VIEW_3D` area: opening, hover child
   flyout, close/outside click, property interaction, and an invoked external modal
   operator. Verify the draw handler uses `type(context.space_data)`.
3. Finish automatic radial collision avoidance and apply `overlay_offset` to the
   same final coordinates used for drawing and hit boxes. Check long labels and
   direction-9 panels near viewport edges.
4. Visually inspect all layout scale/alignment combinations, nested boxes, and
   status badges in both Blender versions. `gpu.matrix.scale_uniform()` was only
   statically checked in this final pass.
5. Test portable Blender specifically: put the Blender user data beside
   `blender.exe`, create/edit gestures, use File > New, restart Blender, then verify
   the atomic JSON data and fallback path restore the configuration.

## Notes

- The worktree was already dirty before this handoff. Do not use reset/checkout to
  discard changes blindly.
- The user requested a temporary handoff for another model, so this document is a
  current status snapshot rather than release documentation.

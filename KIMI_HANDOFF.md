# Gesture Helper Handoff

Updated: 2026-07-23

## Current State

- Branch: `feature/gesture-layout-renderer`
- Remote: `origin`
- The user's Blender 5.2 process PID `18860` was already running. Do not stop it.
- No development server or Codex-owned interactive Blender process is left running.

## Implemented In This Worktree

### Persistence, import/export, and keymaps

- Gesture JSON persistence writes and validates a temporary file in the destination
  folder, flushes it, then atomically replaces the old file.
- Manual export and automatic backups use the same atomic writer. A successful
  import is saved immediately and reports when only the in-memory update succeeded.
- Manual import is transactional. It validates shortcut JSON before RNA assignment,
  enables strict assignment while applying a batch, suppresses intermediate disk
  saves/keymap rebuilds, and removes every appended gesture on failure.
- New gestures are normalized to unique names before KMI registration, so importing
  an existing preset creates `Name.001` instead of pointing the new shortcut at the
  older gesture with the same name.
- Imported shortcuts are force-validated even when either the gesture or global
  gesture preference is disabled. Failures from older retained shortcuts do not
  incorrectly reject a newly imported valid gesture.
- Startup/disk restore remains lenient but is now transactional: valid gesture data
  is retained, valid KMIs are registered, an individual invalid KMI is skipped and
  logged, and an apply/cache/keymap exception restores the previous live store.
- Legacy AddonPreferences migration uses the same replacement transaction. A
  successful in-memory migration remains active when disk writing fails, while the
  old DNA is retained for a later retry.
- Keymap load failures are immutable records with gesture indices, so rollback and
  validation never retain stale Blender RNA proxies.
- RADIAL gestures register `wm.gesture_operator`; MENU gestures register
  `wm.gesture_menu`. Restart/unregister also removes both IDs and the legacy
  `gesture.operator` ID.
- File > New restores the WindowManager gesture store from disk and rebuilds the
  corresponding shortcuts. Handler registration and unregistration are idempotent.
- New layout, property, menu, and overlay fields are included in export/import.

### Gesture and menu modes

- Gesture type is selected at creation (`RADIAL` or `MENU`) and cannot be switched
  later in the normal UI.
- `wm.gesture_menu` has a separate persistent modal runtime and does not share the
  radial input state machine.
- Menu styles include `PANEL`, `COMPACT`, and `BORDERLESS`, with title/header,
  close button, root ordering, hover flyouts, property rows, condition filtering,
  and separators.
- Escape, right mouse, the close button, or an outside left click closes the menu.
  A second menu replaces the first one in the same window. External modal operators
  temporarily pause menu event handling until they finish.
- Menu handler cleanup is part of session clear/reload/unregister.

### Layout, property, drawing, and preview

- Layout containers support alignment (`EXPAND`, `LEFT`, `CENTER`, `RIGHT`), scale,
  advanced settings, presets, native-style separators, and one main action.
  `Switch Layout Type` was intentionally left unchanged.
- Property elements default to `scene.cycles.samples`, with
  `scene.render.resolution_percentage` as the non-Cycles fallback. They support
  horizontal/vertical/free drag, inversion, formatted values, boolean labels/icons,
  and name synchronization. Quick Add separates fixed-value, modal, and
  gesture-controlled property actions.
- Element list rows use fixed leading/status/expand/icon/select tracks with a
  flexible name column. Missing controls keep placeholders, and only the status
  badge receives error coloring, so rows no longer resize into uneven red blocks.
- `AddLayoutPreset` and `wm.gesture_element_add` now share an unregistered operator
  base instead of registering an Operator parent/child pair. This removes the
  repeated `unable to get Python class for RNA struct` warning in Blender 4.2/5.2.
- The old `Force show` option is now labeled `Always update gesture panels`, with a
  `Keep updating` action in paused panels and a description of its performance cost.
- Automatic radial collision avoidance, manual `overlay_offset`, viewport clamping,
  and final draw/hit-coordinate synchronization are complete. Offset root elements
  use their actual rendered rectangles for selection. Direction 9 blocks the
  underlying angular selection and remains owned by its extension panel.
- Invalid UI states distinguish disabled, context/poll blocked, missing operator,
  invalid operator arguments, invalid/read-only properties, bad conditional data,
  and locked/unavailable items with compact badges and severity accents.
- Preview uses a separate operator/input policy. Cross-window preview context only
  overrides `window`, `area`, and `region`; it does not pass a temporary `screen`.
- Theme defaults use Blender-like neutral grays, blue active states, and explicit
  warning/error accents.

## Important Files

- `utils/gesture_persistence.py`: atomic save and restore lifecycle.
- `ops/export_import.py`: export whitelist, validation, migration, and rollback.
- `gesture/gesture_keymap.py`, `gesture/addon_keymap.py`: shortcut lifecycle.
- `gesture/menu.py`, `ops/menu.py`: persistent menu runtime.
- `gesture/gesture_input.py`, `gesture/preview_input.py`: normal and preview input.
- `utils/radial_collision.py`, `element/extension_hit.py`: placement and hit logic.
- `element/element_gpu_draw.py`, `element/element_status.py`: drawing/status states.
- `tests/`: pure Python tests plus Blender background smoke scripts.

## Verification Run

- `python -m unittest discover -s tests -p 'test_*.py' -v`: 29 tests passed.
- Ruff passed for every changed/new Python file; unrelated legacy lint errors remain
  outside the changed-file check.
- `python -m compileall -q element gesture ops preferences ui utils tests` passed.
- `git diff --check` passed (only Git's CRLF conversion warnings were printed).
- Blender 4.2.1 and 5.2.0 both passed `blender_import_keymap_smoke.py`, including
  strict rollback, invalid enum/modal-event rejection, duplicate-name normalization,
  disabled-item validation, old bad KMI isolation, transactional replacement, and
  lenient startup restore.
- Blender 4.2.1 and 5.2.0 both passed `blender_element_status_smoke.py` against
  real operator RNA.
- Blender 4.2.1 and 5.2.0 both passed `blender_lifecycle_smoke.py`: rename,
  enable/disable, legacy cleanup, File > New restore, delete, unregister, reload,
  KMI cleanup, handler cleanup, plus real `bpy.ops` poll/execute for element add and
  layout presets without RNA warnings.
- Blender 5.2 extension CLI built and validated
  `dist/gesture_helper-2.3.6.zip`. It contains 329 package files and excludes tests,
  smoke data, caches, and this handoff document.
- Earlier GUI checks in both Blender versions passed preview modal and draw-handler
  registration/unregistration.

## Remaining Manual Checks

1. Visually inspect the fixed-width element list, persistent menu hover/flyout/
   property interaction, and every layout scale/alignment combination in real
   3D View themes and DPI settings.
2. Exercise a truly portable installation beside `blender.exe` with several other
   add-ons installed. The isolated lifecycle test covers File > New and disk restore,
   but not every third-party add-on interaction or Windows permission setup.

## Notes

- Do not use reset/checkout to discard the working tree without reviewing it.
- This is a development handoff, not release documentation.
# 2026-07-23 UI drawing handoff

## User feedback / constraints

- Rounded gesture and layout items look jagged or vertically inconsistent.
- Corner radius must only be clamped to `min(width, height) / 2`; it must not
  be clamped by padding/margin.
- Gesture-item padding and layout padding must be independent. Layout padding
  should default smaller.
- Layout scale must have independent X and Y controls.
- During a real gesture, the heavy editor UI must hide. Preview mode may keep
  it editable.
- Do not visually test the Blender UI. The user will test and report results.
- Later: move the example-preset visibility switch under import/export debug,
  add more meaningful example presets, and finish missing Chinese translations.

## Changes already written (not visually tested)

- `utils/public_gpu.py`
  - Removed the global margin-based radius clamp.
  - Radius is now clamped only by half of the actual width/height.
  - Rounded-rectangle arcs now include their end tangent points to make the
    four straight edges and opposite corners symmetric.
- `preferences/draw_property.py`
  - Renamed the existing margin UI to `Gesture item margin`.
  - Added `layout_margin`, default `(5, 3)` versus gesture `(10, 6)`.
  - Removed the obsolete warning that radius is clamped to margin.
- `gesture/draw_frame_context.py`, `element/element_gpu_draw.py`,
  `element/element_layout_gpu.py`
  - Added cached layout X/Y margins and routed layout/flyout measurement to
    them while radial gesture items keep using the original margin.
- `utils/ui_draw_sync.py`
  - A real gesture now takes precedence over the persisted force-update flag.
  - The paused heavy-panel renderer returns blank content instead of showing
    the pause/keep-updating row. Preview remains excluded by
    `is_gesture_modal_active()` as before.
- `element/element_property.py`, `element/element_draw.py`,
  `element/element_layout_gpu.py`
  - Added `layout_scale_x` and `layout_scale_y` controls.
  - Layout measurement and GPU matrix scaling now use both axes.
  - Kept the old `layout_scale` property for preset/backward compatibility.

## Important incomplete work for the next window

1. Review the current diff before editing. The worktree was clean at the start;
   the eight changed source files plus this handoff are from this session.
2. Run code-level checks only (syntax/pytest as appropriate). Do not launch or
   visually inspect Blender UI because the user explicitly wants to test it.
3. Add focused pure-Python tests for rounded-rectangle symmetry and radius
   clamping if the GPU imports can be stubbed cleanly.
4. Check non-uniform nested layout scaling carefully. Hit boxes derive from GPU
   matrix positions, but nested size/alignment behavior has not been exercised.
5. Decide how legacy `layout_scale` should interact with new X/Y properties on
   imported old presets. Current runtime uses X/Y defaults when properties
   exist, so an imported non-default legacy uniform scale may need migration
   into both axes during import.
6. Update export filtering/exclusion for `layout_scale_x` and
   `layout_scale_y`; current export code only knows `layout_scale`.
7. Implement an independent example-preset visibility property near
   `debug_export_import` in `preferences/debug.py`. `utils/preset.py` currently
   hides only `Example Preset` based on the master debug state.
8. Add meaningful examples for layout, property display, and state icons. Do
   not create renamed duplicates merely to increase the count.
9. Audit and complete `src/translate/zh_CN/*.json`, including the newly added
   labels (`Gesture item margin`, `Layout margin`, `Scale X`, `Scale Y`) and the
   property UI strings visible in the user's third screenshot.
10. After code checks, hand the build to the user for Blender visual testing.

## Files currently changed

- `utils/public_gpu.py`
- `preferences/draw_property.py`
- `gesture/draw_frame_context.py`
- `element/element_gpu_draw.py`
- `element/element_layout_gpu.py`
- `utils/ui_draw_sync.py`
- `element/element_property.py`
- `element/element_draw.py`
- `KIMI_HANDOFF.md`

## 2026-07-23 Continuation

- Added `utils/layout_scale.py` for bounded X/Y scale handling and recursive
  migration of legacy uniform `layout_scale` values.
- Export/import now persists `layout_scale_x` and `layout_scale_y`, synthesizes a
  legacy uniform value when possible, and omits stale legacy values for non-uniform
  layouts.
- Added matrix-transformed hit rectangles for radial, layout, and nested flyout
  drawing. Nested non-uniform scales now transform both visual geometry and hit
  areas; extension travel bands use the rendered panel bounds.
- Radius clamping is centralized on actual rectangle dimensions, including the
  full chrome size. Layout X/Y margins now control their corresponding padding
  axes, and the paused heavy-panel tooltip text matches real gesture behavior.
- Added the independent `show_example_presets` preference and four distinct,
  disabled bundled examples for modal control, nested layouts, property displays,
  and boolean state icons. The import list is deterministic and no longer depends
  on the master debug logging switch.
- Completed the new Chinese translations, status templates, menu/layout labels,
  property quick-add text, and preset/example names. Removed obsolete radius and
  paused-panel strings.
- Added pure-Python coverage for layout migration, nested matrix transforms,
  rounded-rectangle symmetry/radius bounds, and example visibility.

## Continuation Verification

- `python -m unittest discover -s tests -p 'test_*.py' -v`: 40 tests passed.
- `python -m compileall -q element gesture ops preferences ui utils tests` passed.
- Ruff passed for every changed/new Python file.
- All 15 preset and `zh_CN` JSON files parse with duplicate-key checks.
- Blender UI was not launched or visually inspected; the remaining visual and
  portable-installation checks are intentionally handed to the user.

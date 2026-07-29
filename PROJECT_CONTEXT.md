# Gesture Helper Project Context

## Purpose

Gesture Helper is a Blender 4.2+ Extension (also loadable as a legacy add-on)
for binding radial gestures and persistent menus to Blender operators, modal
operators, and RNA property edits. The repository is Python-only at runtime,
with bundled JSON presets, translations, and PNG icon assets.

## Architecture

### Startup and registration

- `__init__.py` exposes Blender's legacy `register`/`unregister` API and
  `bl_info`; `blender_manifest.toml` is the Extension package contract.
- `register_mod.py` registers `ui`, `ops`, `preferences`, `props`, and
  translation classes, installs the `WindowManager.gesture_helper` pointer,
  clears stale keymaps/caches, restores persisted gestures, and installs
  load/playback handlers. Unregister cancels timers, modal/draw handlers,
  saves state, removes keymaps and RNA properties, then unregisters modules.
- `utils/rna_register.py` provides reload-tolerant class registration. The
  package build excludes tests, documentation, VCS files, caches, and agent
  files via `[build].paths_exclude_pattern`.

### Runtime data and persistence

- `gesture/__init__.py` defines the RNA model: `GestureStore` contains a
  `CollectionProperty` of `Gesture`; each `Gesture` contains recursive
  `Element` nodes from `element/__init__.py`. Both live on the WindowManager
  with `SKIP_SAVE`, so they are session state rather than `.blend` DNA.
- `utils/gesture_persistence.py` serializes the store to CONFIG JSON using
  atomic temp-file + `os.replace`, validates the written structure, debounces
  structural saves, migrates legacy AddonPreferences data, and rolls back a
  failed restore. `register_mod` snapshots before file load and restores after
  Blender clears the WindowManager store.
- `utils/property.py` is the generic RNA-to-indexed-dict serializer/importer;
  `ops/export_import.py` validates and sanitizes imported JSON. Keymap data is
  strict (scalar shortcut fields and no unknown fields). Bundled source JSON
  duplicate keys are rejected by tests, but runtime JSON readers currently do
  not enforce that rule (see observed issues).

### Input, execution, and drawing flow

1. Blender invokes `ops/gesture.py:GestureOperator` or `ops/menu.py` through
   keymaps managed by `gesture/gesture_keymap.py` and `gesture/addon_keymap.py`.
2. `GestureSession` owns per-modal state, trajectory KD-tree, event snapshot,
   phase/handoff state, property-drag state, proxy identity pool, and timeout
   handles.
3. `gesture/gesture_input.py` normalizes events, thresholds, direction and
   hover state; `gesture/gesture_executor.py` chooses immediate vs release
   execution. `element/element_operator.py` invokes operators and modal
   wrappers; `element/element_property.py` resolves and edits live RNA.
4. `gesture/gesture_draw_gpu.py`, `element/*draw*.py`, and `src/lib` calculate
   GPU geometry and hit boxes. `gesture/menu.py` renders persistent menus;
   `utils/ui_theme.py` owns five coordinated overlay presets (Blender Dark,
   Deep Grey, Minimal Dark, Blender Light, and Maya) plus the user-edited Custom
   state. The same palette drives radial/layout elements, persistent menus,
   preview selectors, and instruction overlays. Pointer interaction is kept
   separate from semantic selection/value state: actionable surfaces have
   distinct normal, hover, pressed, and disabled treatments, selector actions
   activate on release over the original row, and a release after leaving the
   row cancels activation.
   The radial direction cue begins halfway between its center and inner ring,
   then eases its radius, sweep, opacity, and stroke weight into confirmation.
   `ROW`, `COLUMN`, and `BOX` are layout containers and `CHILD_GESTURE` creates
   nested menus. Layout containers keep Blender's two alignment concepts
   separate: `layout_align` defaults on, removes inter-item spacing, makes a
   populated BOX flush with its child surfaces, and treats every drawable
   child run as one rounded group with a single outer border. Nested layout
   containers own a complete four-corner perimeter instead of inheriting
   square middle corners from their parent group.
   `layout_alignment`
   controls horizontal `EXPAND`/`LEFT`/`CENTER`/`RIGHT` distribution.
   Gesture and menu separators share the same thin stroke metric. Separators
   do not restart rounded corners on either side; empty layout containers
   measure to zero, are omitted by their parent, and publish no draw or hit
   area. Layout-row hover changes only the background fill (no
   hover outline); property backgrounds and slider fills receive the same
   color blend so their value fraction remains visible.
   `gesture/runtime_tooltip.py` owns delayed hover fade-in/fade-out state and
   short-lived redraw timers; `element/element_tooltip.py` builds translated
   operator/property metadata and independent status/icon diagnostics. Tooltip
   timers are cancelled on target changes, modal reset/exit, and unregister.
   While a runtime tooltip is visibly displayed, Ctrl+C copies its complete
   content to Blender's clipboard and reports the result. Radial numeric
   directions select only; numeric changes require a wheel event or explicit
   left-mouse drag.
   Read-only radial previews enter `UI_VISIBLE` immediately (without the
   gesture timeout or trajectory overlay); menu previews use the dedicated
   `GestureMenuRuntime` draw handler and a menu-specific area lookup so the
   unified preview's radial GPU base cannot shadow its draw routing. Plain
   Space-drag or left-dragging a menu title converts a centered menu preview
   to a movable anchored preview. The preview selector has a draggable title
   bar with an independent persisted-in-session offset. Read-only gesture,
   menu, and element previews use a 1.2 UI scale multiplier while retaining the
   live overlay palette.
   Radial and menu gesture previews share the compact translated selector and
   viewport instruction HUD; the menu backend initializes, draws, and routes
   selector input through its own handler before menu hit testing. Its compact
   selector keeps the translated Exit Preview action beside Select Gesture in
   the top title row; radial previews retain the static point/line history when
   entering child gestures while still suppressing the live mouse trail. Selector
   hover events do not consume Space-drag navigation.
   Large layout previews cache static measurements, cull off-screen subtrees,
   publish only token-current visible hit rows, and resolve each visible row's
   status, label, icon, and display metrics once per draw.
   Numeric `INT`/`FLOAT` property rows are always painted as three contiguous
   Blender-style blocks: decrement, value, and increment, when Blender's global
   Numeric Input Arrows preference is enabled. The three blocks have
   independent normal, hover, and pressed feedback: edge clicks step, the
   value region scrubs or invokes property editing, and wheel input steps
   hovered values without leaking through a persistent menu to the editor.
   Persistent-menu rows use the panel background in their idle state and meet
   adjacent rows without an inset; internal row corners are square, while only
   the exposed panel perimeter remains rounded. Numeric fields use the complete
   row surface; their three internal part boundaries remain square, while an
   exposed field edge inherits the panel perimeter corners. Edge chevrons scale
   with row height.
   A radial numeric root still uses its complete item bounds,
   including the configured text margin, as that three-part field; it has no
   separate wrapper or inset numeric surface. Read-only numeric rows suppress
   the arrows.
   Persistent-menu enum rows show the translated current value in a dropdown
   control; clicking it opens a Blender-style flyout with radio-marked choices,
   and selecting a choice updates the live RNA value and collapses the flyout.
   Persistent menu boolean rows use Blender-style left checkboxes when their
   per-property State Icons option is enabled, or hover-only feedback when it
   is disabled; nonnumeric rows use type badges.
   Aligned layout separators consume only their visible line height, so they
   no longer introduce hidden vertical spacing. Ordinary bottom-extension rows
   also publish their current-token hit geometry
   before evaluating draw-time hover, so highlight and delayed tooltip state do
   not disappear when each GPU frame rotates the layout token. A flyout with
   one nonnumeric action uses that row as the complete outer surface, so its
   normal, hover, pressed, outline, and hit bounds do not leave a dark inset
   wrapper around the button.
5. `utils/public_cache.py`, `cache_state.py`, `structure_cache_ops.py`, and
   `utils/ui_draw_sync.py` batch invalidation and freeze panel snapshots during
   modal input/playback. Any entry in `bpy.context.window.modal_operators[:]`
   pauses both the N-panel and Preferences with their full layouts disabled;
   the read-only `wm.gesture_preview` and persistent `wm.gesture_menu` lifecycle
   modals are excluded so those panels remain editable.
   Their headers expose a non-persistent, default-off update override for the
   duration of the modal. Registration resets it to false, and preference
   backup/restore explicitly excludes it. `utils/session_state.py` arbitrates
   preview ownership.
6. `gesture/pass_through/*` handles forwarding to Blender's native keymaps when
   a gesture does not consume the event.

### UI, preferences, and assets

- `preferences/` defines AddonPreferences and editor/drawing/debug/backup
  sub-panels; `ui/` defines lists, menus, context-menu integration, and the
  main sidebar panel. Its registered title appends the current `ADDON_VERSION`,
  and modal pause status is the first header item after that title.
  Menu gestures expose a default-on Keep Open toggle beside Menu Style; pinned
  menus pass unrelated editor input through, remain visible after their own
  actions, and close explicitly from the title-bar X (or cancel input).
  Expanded element trees with more than 48 visible descendants use a cached,
  area/root-scoped 32-row page; selection changes reveal their page, while
  explicit page changes are preserved. Layout Gesture Action choices are built
  lazily in a menu instead of as hundreds of controls on every panel draw.
  Gesture preferences include the hover-tooltip delay in milliseconds (300 ms
  by default); runtime tooltip fade timing is fixed and does not persist state.
  `ops/quick_add/` implements context-sensitive creation helpers and previews.
- Ctrl+Alt+Shift on `wm.gesture_add` imports every bundled preset, then
  stably groups only the new entries as example `RADIAL`, example `MENU`,
  normal `RADIAL`, and normal `MENU`; the final reordered list is scheduled
  for persistence.
- `utils/preset.py` discovers `src/preset/*.json`; the five files beginning
  `Example ` are opt-in debug fixtures grouped as essentials, elements/layout,
  property controls, combined menu examples, and validation states. Menu style,
  operator-context, and practical viewport examples share one menu gesture,
  with divider rows between the three child sections. The essentials fixture
  combines the basic radial interaction into the complete direction-slots
  example. The elements/layout fixture
  explicitly demonstrates aligned `EXPAND`, `LEFT`, `CENTER`, and `RIGHT`
  layouts with populated child groups, exposes boolean state icons through its
  `Viewport States` child gesture, and
  includes the practical Subdivide modal control in its bottom extension.
  Property modal modes, quick-add actions, and editable displays share one flat
  menu separated by dividers. Coverage tests derive enum contracts from source and also require
  both states of layout alignment, property drag inversion, property value
  visibility, and boolean state icons. `src/translate/` holds locale JSON and translation
  caches; `src/icons/` holds numbered, color, and Blender-derived PNG icons.

## Module graph

```mermaid
flowchart TD
    Entry[__init__.py] --> Reg[register_mod.py]
    Reg --> RNA[props + gesture model]
    Reg --> UI[ui + preferences]
    Reg --> Ops[ops operators]
    RNA --> Store[WindowManager SKIP_SAVE GestureStore]
    Store --> Persist[utils/gesture_persistence.py]
    Persist --> JSON[CONFIG JSON + rotating backups]
    Ops --> Input[GestureInputProcessor]
    Input --> Session[GestureSession]
    Session --> Exec[GestureExecutor]
    Exec --> Elements[element recursive model]
    Elements --> Blender[bpy operators and live RNA]
    Session --> Draw[GPU overlay / menu hit boxes]
    Theme[utils/ui_theme presets] --> Draw
    Theme --> UI
    Session --> Tooltip[delayed translated runtime tooltips]
    Elements --> Tooltip
    Cache[cache_state + public_cache + ui_draw_sync] --> Session
    Keymap[gesture_keymap + addon_keymap] --> Ops
    Presets[src/preset] --> Persist
    Tests[tests + Blender smoke] --> Reg
    Tests --> Persist
    Tests --> Input
```

## Workflows and verification

- Pure tests: `python -m unittest discover -s tests -p 'test_*.py' -v`.
- Syntax: `python -m compileall -q element gesture ops preferences ui utils tests`.
- Lint: `python -m ruff check .`.
- Blender smoke scripts cover preset coverage, UI-theme RNA application,
  selector press/release cancellation, property data paths, import
  rollback/keymaps, lifecycle/reload, preview (including menu draw routing,
  translation, the visible exit action, single-action flyout surface geometry,
  enum flyouts, three-part numeric-field state/hit boxes, selector/title
  dragging, alignment RNA, and Space-drag), and
  panel behavior. Run them
  with isolated `BLENDER_USER_CONFIG`, `BLENDER_USER_DATAFILES`, and
  `BLENDER_USER_SCRIPTS`, plus `--background --python-exit-code 1`.
- Large-panel profile: set `GH_PANEL_AB_AUTOMATION=1`,
  `GH_PANEL_AB_MODE=ELEMENT_PREVIEW`, and `GH_PANEL_AB_ELEMENT_COUNT=300`, then
  run `tests/blender_panel_profile_ab.py` in foreground Blender. The 300-leaf,
  426-node Blender 5.2 fixture measures about 6.25 ms per Element N-panel draw;
  its centered GPU preview measures about 32.3 ms per draw.
- Release: run Blender `--command extension validate`, then `extension build`,
  inspect ZIP entries, and validate the produced archive again.

## Current risks and observed issues

1. **Runtime JSON accepts duplicate keys:** `ops/export_import.py:479` and
   `utils/gesture_persistence.py:61` use plain `json.load`, so duplicate object
   keys are silently replaced by the last value. Only bundled source files are
   checked with `object_pairs_hook` in tests. This violates the repository's
   strict-JSON constraint and can hide malformed or ambiguous imported data.
2. **Lint failure (reproducible):** `python -m ruff check .` reports `E402`
   at `utils/__init__.py:2` because `import bpy` follows `public_color`.
   This is low-risk behaviorally but blocks a clean lint gate.
3. **Blender-only behavior remains higher risk than unit coverage:** the current
   preview smoke passes in Blender 4.2.1 and 5.2.0, including theme preset
   application/custom detection, normal-hover-pressed selector behavior, menu
   animation, pinned-menu RNA defaults, enum flyouts, selector exit/title
   dragging, and cleanup. Foreground visual placement, multi-window behavior,
   and file-load restoration still require targeted manual checks.
4. **Broad lifecycle surface:** modal timers, GPU draw handlers, playback/load
   handlers, cached RNA proxies, and `SKIP_SAVE` restoration all share cleanup
   paths. Any future change in `register_mod.py`, `gesture_session.py`,
   `gesture_input.py`, or `utils/ui_draw_sync.py` should include a focused
   Blender smoke run and reload/disable verification.
5. **Packaging drift risk:** the CI workflow builds a nested `{id}/` archive
   after Blender's flat build; changes to manifest exclusions or workflow
   layout should be checked by inspecting ZIP entries.
## Constraints

- Support Blender 4.2+ and current 5.x; use version-safe Blender UI icons.
- Preserve bundled example preset shortcuts and nested fixture state exactly.
- JSON is UTF-8; conditional `IF`/`ELIF`/`ELSE` elements must be consecutive.
- Dynamic RNA paths must validate the live owner and fail closed when collection
  identity cannot be preserved.
- Keep the Gesture N-panel Type and menu-style controls on one row, and keep
  Add Element controls at a stable height when `CHILD` is invalid for a leaf.
- Keep the exported preset author signature in `preferences/draw_property.py`
  unchanged; ordinary source UI and manifest text remain English.
- Never include `AGENTS.md`, `PROJECT_CONTEXT.md`, tests, or caches in release
  archives.

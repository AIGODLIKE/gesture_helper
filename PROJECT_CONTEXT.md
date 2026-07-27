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
   `ROW`, `COLUMN`, and `BOX` are layout containers and `CHILD_GESTURE` creates
   nested menus. Layout containers keep Blender's two alignment concepts
   separate: `layout_align` defaults on, removes inter-item spacing, makes a
   populated BOX flush with its child surfaces, and treats every drawable
   child surface as one rounded group with a single outer border.
   `layout_alignment`
   controls horizontal `EXPAND`/`LEFT`/`CENTER`/`RIGHT` distribution.
   Separators do not restart rounded corners on either side; empty layout
   containers measure to zero, are omitted by their parent, and publish no
   draw or hit area. Layout-row hover changes only the background fill (no
   hover outline); property backgrounds and slider fills receive the same
   color blend so their value fraction remains visible.
   `gesture/runtime_tooltip.py` owns delayed hover/fade state and
   short-lived redraw timers; `element/element_tooltip.py` builds translated
   operator/property metadata and independent status/icon diagnostics. Tooltip
   timers are cancelled on target changes, modal reset/exit, and unregister.
   Read-only radial previews enter `UI_VISIBLE` immediately (without the
   gesture timeout or trajectory overlay); menu previews use the dedicated
   `GestureMenuRuntime` draw handler and a menu-specific area lookup so the
   unified preview's radial GPU base cannot shadow its draw routing. Plain
   Space-drag converts a centered menu preview to a movable anchored preview.
   Radial and menu gesture previews share the compact translated selector and
   viewport instruction HUD; the menu backend initializes, draws, and routes
   selector input through its own handler before menu hit testing. Selector
   hover events do not consume Space-drag navigation.
   Large layout previews cache static measurements, cull off-screen subtrees,
   publish only token-current visible hit rows, and resolve each visible row's
   status, label, icon, and display metrics once per draw.
   Ordinary bottom-extension rows also publish their current-token hit geometry
   before evaluating draw-time hover, so highlight and delayed tooltip state do
   not disappear when each GPU frame rotates the layout token.
5. `utils/public_cache.py`, `cache_state.py`, `structure_cache_ops.py`, and
   `utils/ui_draw_sync.py` batch invalidation and freeze panel snapshots during
   modal input/playback. Any entry in `bpy.context.window.modal_operators[:]`
   pauses both the N-panel and Preferences with their full layouts disabled;
   the read-only `wm.gesture_preview` modal is excluded for both gesture and
   element preview scopes so those panels remain editable.
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
  Expanded element trees with more than 48 visible descendants use a cached,
  area/root-scoped 32-row page; selection changes reveal their page, while
  explicit page changes are preserved. Layout Gesture Action choices are built
  lazily in a menu instead of as hundreds of controls on every panel draw.
  Gesture preferences include the hover-tooltip delay in milliseconds (100 ms
  by default); runtime tooltip fade-in is fixed and does not persist state.
  `ops/quick_add/` implements context-sensitive creation helpers and previews.
- `utils/preset.py` discovers `src/preset/*.json`; files beginning `Example `
  are opt-in debug fixtures. `src/translate/` holds locale JSON and translation
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
- Blender smoke scripts cover preset coverage, property data paths, import
  rollback/keymaps, lifecycle/reload, preview (including menu draw routing,
  alignment RNA, and Space-drag), and panel behavior. Run them
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
3. **Blender-only behavior remains higher risk than unit coverage:** real RNA
   status checks and preview lifecycle pass in Blender 4.2.1 and 5.2.0, and the
   4.2.1 full lifecycle smoke passes. Foreground visual placement, multi-window
   behavior, and file-load restoration still require targeted manual checks.
4. **Broad lifecycle surface:** modal timers, GPU draw handlers, playback/load
   handlers, cached RNA proxies, and `SKIP_SAVE` restoration all share cleanup
   paths. Any future change in `register_mod.py`, `gesture_session.py`,
   `gesture_input.py`, or `utils/ui_draw_sync.py` should include a focused
   Blender smoke run and reload/disable verification.
5. **Packaging drift risk:** the CI workflow builds a nested `{id}/` archive
   after Blender's flat build; changes to manifest exclusions or workflow
   layout should be checked by inspecting ZIP entries.
6. **Blender 5.2 lifecycle smoke crash:** the full lifecycle script exits with
   a native `tbbmalloc.dll` access violation and no Python backtrace, while the
   same 5.2 install passes element-status and preview smoke and Blender 4.2.1
   passes all three. Treat 5.2 full-lifecycle coverage as unresolved until the
   allocator crash is isolated; Extension validation/package build were not
   rerun for the tooltip-only change.

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

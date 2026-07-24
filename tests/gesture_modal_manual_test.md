# Gesture Modal Manual Test Record

Use this checklist with Blender already open. Record one run per section.

## Run Metadata

- Code reload completed: yes / no
- Date:
- Blender version:
- OS / GPU:
- Add-on revision:
- Active gesture and invoke key:
- Panel open: `VIEW_3D > N > Gesture`
- Preferences window open: yes / no
- `Update panels during other operators`: on / off

Do not use observations made before the add-on was reloaded as a validation
result. Disable/enable the add-on or restart Blender first.

## A. Frozen Panel Behavior

1. Select a gesture with visible Item and Element panels.
2. Hold the real gesture invoke key without moving the mouse for 2 seconds.
3. Move the mouse slowly, then sweep it quickly across the viewport.
4. Release the invoke key and wait for the panel to recover.

Expected:

- The original panel rows, controls, and height stay in the same positions.
- Controls are visibly disabled/gray while the gesture is held.
- The pause message is in the panel header/title area, not a replacement body row.
- The panel returns to its normal enabled state after release.
- No duplicate panel jump or one-frame collapse is visible.

Record:

- Layout stable: pass / fail
- Gray controls: pass / fail
- Header message: pass / fail
- Recovery after release: pass / fail
- Subjective hitch (0 none, 5 severe): __ / 5
- When the hitch happens (press / still / slow move / fast move / release):
- Notes:

## B. Gesture Event Safety

1. Start a gesture whose radial UI has a child gesture.
2. Enter the child level, move across its extension panel, then return.
3. Confirm an operator and repeat once with cancel (`Esc` or the configured cancel path).
4. Repeat with the invoke key bound to `LMB`, if available.

Expected:

- Hover and child navigation remain responsive.
- The final operator is dispatched exactly once.
- Cancel leaves no zombie modal; the next click works normally.
- No event error, traceback, or stuck gray panel remains.

Record:

- Child enter/exit: pass / fail
- Extension hover: pass / fail
- Confirm once: pass / fail
- Cancel cleanup: pass / fail
- LMB invoke release: pass / fail / not tested
- Notes:

## C. Property Interaction

1. Hover an editable INT or FLOAT property row in the radial UI.
2. Drag by a few pixels that should not change an INT, then drag farther.
3. Use the mouse wheel once with and once without `Shift`.
4. Release, cancel, and confirm in separate runs.

Expected:

- A no-op pixel move does not visibly refresh the overlay.
- A real value change updates the radial state and dependent conditions.
- Wheel input is consumed once and does not trigger a second execute on key release.
- The gesture still exits normally after the drag.

Record:

- No-op drag stable: pass / fail
- Changed drag updates: pass / fail
- Wheel behavior: pass / fail
- Dependent condition refresh: pass / fail / not observable
- Exit after property drag: pass / fail
- Notes:

## D. Other Modal and Preview Regression

1. Start the gesture preview from the panel and edit a gesture while previewing.
2. Run a Blender transform or navigation modal with the Gesture panel visible.
3. Open Preferences in a separate window during a real gesture, if practical.
4. Start Preview, then invoke a real gesture in the same 3D View once. Preview
   should end as the real gesture starts. After release, start Preview again
   and exit it with its normal right-click path.

Expected:

- Preview remains editable and is not treated as a real gesture pause.
- Other modal operators may use the lightweight paused body, without affecting
  the real gesture event stream.
- Preferences controls are gray during a real gesture and recover afterward.
- A real gesture taking the same 3D View as Preview ends Preview cleanly; no
  invisible/stuck preview modal remains after the gesture finishes.

Record:

- Preview remains editable: pass / fail
- Other modal behavior: pass / fail
- Preferences freeze/recovery: pass / fail / not tested
- Preview-to-real-gesture handoff: pass / fail / not tested
- Notes:

## E. Panel-Open Performance Comparison

Keep the same file, viewport, frame range, playback sync setting, and visible
objects for every run. Let playback warm up for 2 seconds, then observe 10
seconds. Repeat each case three times.

1. Close the Gesture N-panel.
2. Open the Gesture N-panel with Item and Element expanded.
3. Repeat step 2 with the Property panel expanded when it contains content.
4. Start a real gesture with the panel open: hold still for 2 seconds, then
   move slowly, move quickly, and release.
5. Use a numeric property drag from the panel, if available: make sub-pixel
   integer motion, then a visible value change, then cancel once.

For one measured run in each playback case, open
`tests/blender_live_panel_profile.py` in Blender's Text Editor and choose
`Text > Reload` once before `Run Script` so Blender is not executing an older
in-memory Text block. The interactive recorder ignores automated smoke-test
environment overrides, waits 3 seconds, then waits until animation is actually
playing and the visible Gesture panel title has drawn before sampling for 10
seconds. Start playback and leave the mouse still until the status-bar recording
message clears. Reports are written to `.tmp/panel-profile/` as matching
`.json`, `.txt`, and `.pstats` files. A usable JSON report must contain
`script_revision = live-panel-profile-v4` and `valid = true`.

Expected:

- Playback with the panel open is materially closer to the closed-panel run.
- Playback does not rebuild Item, Element, or Property lists every frame.
- Gesture and add-on value drags keep the original rows and panel height;
  controls are gray and the pause hint appears in the root Gesture title.
- Drag movement redraws the viewport overlay only. The panel returns once on
  confirm, cancel, or window deactivation.

Record:

| Case | Run 1 | Run 2 | Run 3 | Notes |
| --- | --- | --- | --- | --- |
| Panel closed playback | | | | |
| Panel open playback | | | | |
| Property panel open playback | | | | |
| Gesture still / slow / fast / release | | | | |
| Numeric drag no-op / changed / cancel | | | | |

## Summary

- Overall result: pass / fail
- Most noticeable hitch:
- Reproduction steps for any failure:
- Screenshot or screen recording path:

## Live Observation Log

### Baseline 2026-07-23

- This baseline predates the required code reload and is not a pass/fail result.
- Gesture panel open: persistent hitch is present.
- Gesture panel closed: pending comparison.
- Hitch does not progressively increase with trail length.
- Animation playback with the Gesture panel open still drops frames.
- Interpretation: prioritize repeated Panel/UIList/poll work on UI-region redraw;
  visual trail growth is not the primary reported cause.
- Code reload status: the currently open Blender process does not automatically
  load later file edits; repeat the comparison after add-on disable/enable or a
  Blender restart when the implementation is ready.

### Latest observation 2026-07-24

- The reported hitch is tied to the Gesture panel being open, not to the
  number of gesture elements or the length of the mouse trail.
- Animation playback loses frames while the panel is open.
- Repeating more gesture moves does not progressively make the hitch worse;
  the open panel itself is the stable reproduction condition.
- This is still a pre-reload observation unless the Run Metadata above says
  the add-on was disabled/enabled after the latest source change.

### Live profile 2026-07-24 09:13

- Artifact: `.tmp/panel-profile/panel-profile-20260724-091317.json`.
- Blender 5.2 recorded the expanded Gesture sidebar for 10.05 seconds at a
  width of 485 pixels. The panel was rebuilt about 162 times while visible.
- Playback was not active during this recording (`frame_change_count = 0` and
  `animation_playing = false` at both snapshots), so this run is valid evidence
  for the idle open-panel cost, but not yet a playback frame-rate comparison.
- `GestureItemPanel.draw` accumulated 1.241 seconds. Gesture UI rows were drawn
  3,888 times and Element rows 810 times.
- The largest avoidable hotspot was translation lookup:
  `___translate_dict__("ALL")` rebuilt merged dictionaries 13,284 times and
  accumulated 0.851 seconds. Repeated icon-preview validation accumulated a
  further 0.134 seconds.
- Interpretation: the persistent hitch comes from repeated Python panel work,
  not from gesture-trail growth. Cache translation/icon results by their real
  inputs, then repeat this exact profile with playback actually running.

### Discarded profile 2026-07-24 09:36

- Artifact: `.tmp/panel-profile/panel-profile-20260724-093643.json`.
- This was not a valid user playback sample. It recorded for only 0.5 seconds,
  had `required_playback = false`, captured zero frame changes, and saw the 3D
  View sidebar closed at both ends.
- Those settings identify an isolated smoke configuration or a stale Blender
  Text block, not the interactive recorder defaults. No performance conclusion
  is drawn from this artifact.
- Recorder v2 now keeps interactive runs fixed at a 3-second warm-up and
  10-second playback sample, verifies the visible Gesture panel before starting,
  and writes explicit `valid` / `invalid_reasons` metadata.

### Automated playback A/B 2026-07-24 09:29

- Artifact: `.tmp/panel-profile-ab/panel-profile-ab-20260724-092944.json`.
- Isolated Blender 5.2 played the same 60 FPS animation for five seconds with
  the Gesture panels visible, then for five seconds with the sidebar hidden.
- Visible panel: 300 frame changes, 60.0009 FPS, 17.4847 ms p95, 19.4323 ms max.
- Hidden sidebar: 300 frame changes, 60.0085 FPS, 17.3734 ms p95, 17.9365 ms max.
- Gesture panel Python callbacks during both playback phases: zero. Normal
  playback does not rebuild these panels per frame after the start transition.
- This simple-scene A/B rules out a per-frame add-on callback loop. It does not
  replace the user's complex-scene comparison; repeated non-playback UI redraws
  remain relevant because the 09:13 live profile measured 162 full panel draws.

### Final panel and modal verification 2026-07-24 12:01

- User-triggered artifact after the original path fix:
  `.tmp/panel-profile-ab/panel-profile-ab-20260724-112107.json`.
  The visible panel recorded 60.0078 FPS with a 17.5520 ms p95 and no Gesture
  panel callbacks. The closed-sidebar phase contained one unrelated 234.1765 ms
  spike; it therefore measured 57.3840 FPS and is not evidence of panel cost.
- The measured regression was isolated to the property-bearing Element Add
  operator buttons in the disabled layout. Frozen Add and Preview buttons now
  use property-free operators with no custom poll. Normal editing still uses
  the original operators and behavior.
- Final artifact after restoring the Preview row:
  `.tmp/panel-profile-ab/panel-profile-ab-20260724-120156.json`.
  Visible panel: 60.0011 FPS, 17.4359 ms p95. Closed sidebar: 59.9962 FPS,
  17.3703 ms p95. Visible/closed ratio: 100.0082%. Gesture panel callback
  counts and add-on cProfile rows were empty in both phases.
- Visual artifact: `.tmp/panel-visual-qa/result.json`. Normal, playback,
  explicit value drag, real gesture, and every restored stage kept a
  `280 x 1177` sidebar. The Preview row remains in place and is disabled during
  all three frozen states. The Preview-active, Preview-to-real-gesture freeze,
  and restored stages (`08` through `10`) also keep the same row text and
  position. Pause messages occur only in the root Gesture title. The three
  restored screenshots have the same SHA256 hash.
- Playback semantic snapshots are separate from generic pause-decision cache
  invalidation. Gesture release and explicit numeric-drag start/finish preserve
  every area's playback snapshot. Playback stop, scrub expiry, and add-on
  teardown clear it, so disable/re-enable cannot reuse stale area or RNA state.
- Gesture cancel now treats `ESC`, right-mouse press, and window deactivation as
  one path: restore an active property scrub, clear pending handoff/repair state,
  unregister drawing, cancel UI/timeout callbacks, and release the frozen panel.
- Gesture-to-numeric handoff ignores the old gesture's mouse/key release. Numeric
  confirm/cancel accepts only button press. Restore or draw cleanup failures still
  release explicit freeze ownership, and invalid area/RNA pointers are removed by
  keys captured at registration time.
- Automated verification: 170 unit tests passed; focused modal lifecycle coverage
  includes normal completion followed by Blender `cancel()`, ESC/RMB/deactivation,
  stale releases, `on_event`/immediate exceptions, restore exceptions, draw cleanup
  exceptions, and invalid area/RNA cleanup. Ruff, compileall, and diff-check passed.
  Blender 4.2.1 lifecycle smoke passed. Blender 5.2 foreground visual and playback
  A/B passed; that build's background-only launch crashed twice in `tbbmalloc.dll`
  before reaching add-on assertions, so no plug-in conclusion is drawn from it.

### Build exclusion verification 2026-07-24 12:31

- All automated tests, Blender smoke/profile scripts, manual procedures, and
  `.tmp` profiling/visual artifacts remain in the working repository.
- The manifest build filters exclude `/tests/`, `/.tmp/`, Python caches,
  development metadata, `dist`, generated ZIP files, logs, and conversion tools.
  No runtime source or asset is excluded by these additions.
- Blender 5.2 built
  `.tmp/package-validation-current/gesture_helper-2.3.6.zip` successfully. The
  archive contains 342 entries, zero forbidden development entries, and all six
  checked runtime anchors (`blender_manifest.toml`, `__init__.py`,
  `register_mod.py`, `ui/panel.py`, `utils/ui_draw_sync.py`, and
  `ops/modal_mouse.py`). The source manifest passes Blender 5.2 validation, and
  the built ZIP passes the official extension validator in both Blender 4.2 and
  5.2.
- The user's latest Text Editor run did not create a v4 live-profile artifact;
  `.tmp/panel-profile/` still ends at the 10:00 v2 idle sample. Reload or reopen
  `tests/blender_live_panel_profile.py` from disk before the next complex-scene
  run, and accept it only when `latest-status.json` reports
  `script_revision = live-panel-profile-v4`.

Manual real-event pass after reloading the add-on:

1. Start a gesture, begin a property-row scrub, press `ESC`; the old value and
   enabled panel must return, and releasing the gesture key must do nothing.
2. Repeat with right-mouse press, then repeat while switching focus to another
   window; no gesture overlay or disabled panel may remain after focus returns.
3. Trigger a gesture item that hands off to numeric mouse adjustment. Releasing
   the original gesture button must leave numeric adjustment active. Confirm with
   left-mouse press; repeat and cancel with `ESC` and right-mouse press.
4. During animation playback, compare the expanded Gesture panel with the sidebar
   closed. The layout must keep the Preview row and all child positions while gray,
   and the root title must be the only pause message.

### Optimization after the 09:13 profile

- Merged add-on translation dictionaries are cached once per locale. Name,
  preset, and keymap results use bounded caches keyed by source text, language,
  Blender's interface-translation setting, and the add-on name-translation
  setting. Translation load/register/unregister invalidates every result.
- Valid loaded icon previews are reused for the lifetime of their Blender
  preview collection. Normal panel redraws no longer repeat PNG existence and
  pixel-buffer checks; icon refresh/reload clears the cache.
- Playback, scrubbing, gestures, and add-on-owned value drags keep the full
  disabled layout. Selection and status snapshots are area-scoped. Scrub cache
  expiry clears its semantic snapshot, and queued synchronization also checks
  live playback state before running.
- The live profiler now waits for actual playback instead of silently recording
  an idle run when the countdown is missed.
- Final verification: 125 unit tests passed; Ruff, compileall, and diff-check
  passed. Blender 4.2.1 and 5.2.0 lifecycle smoke tests passed. The live profiler
  produced artifacts successfully in an isolated Blender 5.2 GUI process.

### Performance follow-up 2026-07-24

- The running Blender 5.2 process started at 08:13, after the first playback
  cache changes were written, and its installed extension is a junction to
  this repository. The persistent panel-open slowdown is therefore treated as
  a current-code result, not dismissed as a stale add-on load.
- MENU gestures still used `area.tag_redraw()` for hover/layout changes. That
  path now tags only the owning `WINDOW` region and never falls back to the
  whole area, so it can no longer wake the Gesture sidebar on every hover.
- Active-element lookup now caches the valid "no selected element" result.
  Repeated Panel poll/draw calls no longer rescan a non-empty element tree that
  has no radio-selected row.
- Playback transitions now cancel any foreign-modal recovery timer left alive
  before playback. This removes an unnecessary 0.12-second polling pulse from
  the playback path.
- Numeric-drag header text is set only when the displayed value changes;
  overlay position can still redraw independently on mouse movement.
- Unit tests: 109 passed. Ruff, compileall, and diff-check passed. Blender
  lifecycle smoke passed on 4.2.1 LTS and 5.2.0 LTS.
- `tests/blender_live_panel_profile.py` was validated in an isolated Blender
  5.2 process and produced JSON, text, and pstats artifacts successfully.
- Remaining limitation: during animation playback Blender redraws an open UI
  region in immediate mode. The add-on now skips UILists, status evaluation,
  modal-stack scans, and other heavy body logic, but Blender still invokes the
  registered Panel poll/header/draw callbacks and creates temporary UILayout
  objects. A previous native UILayout cannot be cached and replayed. The next
  measured A/B run must determine whether that native callback floor is the
  remaining visible frame loss.

### Implementation checkpoint 2026-07-23

- Playback pause state is reused across the panel's header/body calls for a
  full playback lifecycle; playback start/stop handlers invalidate it exactly
  at the transition, so the hot path does not read the clock or animation state.
- Normal open-panel drawing coalesces the fallback scan for foreign modal
  operators instead of walking every Blender window at frame rate.
- Playback and add-on-owned gesture/value drags preserve the full disabled
  layout. Foreign-modal child bodies alone use an inert disabled row. No child
  repeats the pause text; the single hint remains in the root Gesture title.
- A real gesture or add-on property drag keeps the existing layout disabled;
  active selection and row status are pinned for the frozen lifecycle.
- Frozen selection is area-scoped and Preferences reuses the owning gesture's
  snapshot. Ending one window's gesture/drag does not clear another window's
  frozen selection.
- Gesture mouse redraws target only `WINDOW` regions. If Blender does not expose
  one, the add-on skips that redraw instead of invalidating the whole area and
  rebuilding the N-panel.
- Window deactivation/system cancel restores an in-progress gesture property
  scrub once before releasing the modal state.
- A real gesture is scoped to its owner `VIEW_3D`; a separate `VIEW_3D` does not
  borrow its session. Preferences remains able to show the global pause state.

For the next valid run, reload the add-on first, then fill section E before
testing long gesture paths. The important comparison is closed-panel playback
versus open-panel playback with the same scene and playback settings. Record
whether the panel-open case is still a persistent frame-rate hit after reload;
that result determines whether the remaining cost is Blender's native UI-region
rebuild or an add-on draw path that still needs a frozen renderer.

# Project Instructions

Read `PROJECT_CONTEXT.md` before reading or searching source code. Use it to
select the smallest relevant scope, then verify important claims against the
current source files and tests; the summary never overrides the source.

Keep `PROJECT_CONTEXT.md` concise and refresh it when architecture, build
behavior, dependencies, workflows, or durable risks change.

This repository is a Blender Extension. Keep agent-only files out of release
packages. When `[build].paths_exclude_pattern` is used, exclude `AGENTS.md`
and `PROJECT_CONTEXT.md`; when `[build].paths` is used, do not add an exclude
table and ensure those files are not listed.

Preserve existing worktree changes. Verify preset changes with JSON duplicate-
key checks, focused unit tests, and isolated Blender smoke tests when they
touch runtime RNA, keymaps, or menu behavior.

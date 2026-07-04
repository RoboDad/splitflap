# Session log

## 2026-05-25 - flap_printer: SVG input + Epilogue flap type

- **Model:** Claude Opus 4.7
- **Commits:** 8685226, 73c6d70, c7f74ae
- **Files touched:**
  - `pvv_tools/flap_printer/svg_loader.py` (new)
  - `pvv_tools/flap_printer/renderer.py` (SVG branch in `_load_source_image`)
  - `pvv_tools/flap_printer/config.py` (`"epilogue"` type resolution)
  - `pvv_tools/requirements.txt` (resvg-py)
  - `pvv_tools/scad/epilogue_flap_single.scad` (new SCAD wrapper)
  - `pvv_tools/generate_epilogue_flap_svgs.py` (new CLI generator)
  - `pvv_tools/assets/epilogue_flaps/flap_00.svg` ... `flap_51.svg`, `index.json`
  - `pvv_tools/test_svg_job.json`, `pvv_tools/test_images/test_svg_01.svg`, `pvv_tools/test_epilogue_job.json` (test fixtures)
  - `pvv_tools/README.md` (SVG docs + Custom Flap Types + new Details section)
  - `.gitignore`

### Goal
Add Epilogue per-character flap rendering to flap_printer. Generalized
into two reusable features: (1) generic SVG input support, (2) a
convenience `"epilogue"` flap type using pre-rendered Epilogue SVGs.

### Changes
- Phase 1: `svg_loader.py` wraps `resvg-py`; renderer branches on `.svg`
  extension; SVGs are rasterized at 2x supersample to a target height,
  then fall through the existing fit/slice pipeline unchanged.
- Phase 2: SCAD wrapper (`epilogue_flap_single.scad`) renders a single
  display face by calling `flap_with_letters(... flap=false ...)` twice
  (top + 180-rotated bottom). Driver script invokes Scott's
  `projection_renderer.Renderer`, post-processes the SVG to (a) set
  viewBox to the canonical `flap_width x (2h+gap)` display face, (b)
  apply etch fill style (black fill, no stroke), (c) special-case the
  space character (no geometry).
- Phase 3: `config.load_config` resolves `type: "epilogue"` + `char`/`index`
  into a `single` SVG source under `pvv_tools/assets/epilogue_flaps/`.
  README updated with SVG input docs, the new type in the custom_flaps
  table, and a new programmer-facing "Details" section covering package
  layout, full pipeline walkthrough, SVG loader internals, Epilogue
  generator internals, the svg.path 6.x pin, and the contract for adding
  new flap types.

### Notes / decisions
- `resvg-py` chosen over CairoSVG (better Windows ergonomics, single
  pip install, no native deps).
- `dpi=96` is required when calling `resvg.svg_to_bytes` for SVGs with
  real-world units (`width="54mm"`); any non-zero value works.
- `svg.path` must be pinned to 6.x (`==6.*`) because Scott's
  `3d/scripts/svg_processor.py` asserts the major version equals 6 at
  import time. Recorded in the README Details section.
- The 52 generated SVGs are committed (not generated on demand) so the
  flap_printer has no OpenSCAD dependency for the epilogue type.
- End-to-end test: `pvv_tools/test_epilogue_job.json` ("HELLO!") rendered
  cleanly through the full pipeline at 360 DPI. L preview confirmed
  geometry.
- Follow-up: the SCAD display-face height (2h+gap-pin) differs from
  flap_printer's `display_height` (2h+gap) by `flap_pin_width` (~1.4 mm).
  Currently the viewBox overrides to flap_printer's expectation, so the
  letters rasterize slightly stretched. Acceptable for now; revisit if
  letters look mis-sized on real prints.

## 2026-05-25 - flap_printer: white-fill prototype + --fill-color option

- **Model:** Claude Opus 4.7
- **Commits:** none (not yet committed)
- **Files touched:**
  - `pvv_tools/generate_epilogue_flap_svgs.py` (added `--fill-color` CLI option)
  - `pvv_tools/assets/epilogue_flaps/flap_*.svg` (regenerated all 52 with `fill=#ffffff`)
  - `pvv_tools/prototype_job.json` (new — 24-module, 12-flap prototype job)
  - `pvv_tools/test_images/placeholders/EP44.svg`..`EP53.svg` (new — 10 placeholders)

### Goal
Set up a prototype print job for the user's 62-flap × 24-module display
(2 corrective Epilogue flaps for EP42/EP43 + 10 custom image placeholders),
then change the Epilogue glyph color from black to white so it prints
correctly on dark flap stock.

### Changes
- Built `prototype_job.json`: slot 0 = EP42 epilogue `"-"` (top-of-dash
  = blank top half, bottom-of-dash flows to next flap's back), slot 1 =
  EP43 epilogue `"\$"` (top-of-dollar on EP43F, bottom-of-dollar pairs
  back via flap_printer's slicing onto EP42B). Slots 2–11 reference
  per-slot placeholder SVGs.
- Generated 10 placeholder SVGs (54×88 mm, black border + `EP{nn}` label
  + `PLACEHOLDER (top/bottom)` subtitle) to make slot ownership obvious
  during test prints.
- Added `--fill-color` argument to `generate_epilogue_flap_svgs.py`
  (default `#ffffff`). After `apply_laser_etch_style()` is called,
  `_postprocess_svg()` iterates `<path>` elements and overrides their
  `fill` attribute. Default is white so the standard regenerated
  Epilogue assets print white text on transparent (correct for dark
  flaps). Pass `--fill-color "#000000"` to revert to black.
- Regenerated all 52 `assets/epilogue_flaps/flap_*.svg` with white fill;
  verified end-to-end via `python -m pvv_tools.flap_printer
  pvv_tools/prototype_job.json` that the `\$` glyph in
  `prototype_output/common/batch_01_front.png` is pure white
  (1593 white opaque pixels, 0 black) in the EP43 pocket.

### Notes / decisions
- `svg_processor.apply_laser_etch_style()` (in `3d/scripts`) is left
  untouched; its black hard-coded fill is overridden post-process inside
  the flap SVG generator, keeping the shared utility unchanged.
- A long debugging detour chasing a "black `\$`" in
  `pvv_tools/prototype_output/` turned out to be a stale output
  directory from a pre-fill-color render. Real output goes to
  `./prototype_output/` (relative to repo root, since the job JSON's
  `output_dir` is just `"prototype_output"`); stale dir removed.
- EP42B / EP53B continuity: EP42B intentionally receives the
  bottom-half of the dollar glyph; EP53B is intrinsically blank because
  the apostrophe glyph has no bottom half — coincidentally matches
  flap_printer's default `last flap back = blank` behaviour, no
  workaround needed.

## 2026-05-25 - flap_printer: stable output_dir + cleanup

- **Model:** Claude Opus 4.7
- **Commits:** 6201fb8
- **Files touched:** pvv_tools/flap_printer/cli.py, pvv_tools/README.md
- Deleted stale dir: pvv_tools/test_output/

### Goal
Avoid confusion from job output landing in different places depending on CWD.

### Changes
- cli.py resolves output_dir against the job file's parent directory when relative.
- README updated to describe the new resolution rule.
- Removed stale pvv_tools/test_output/ (Phase 1 SVG smoke-test artifacts).

### Notes / decisions
- Absolute output_dir values still honored unchanged.
- prototype_job.json now writes to pvv_tools/prototype_output/ regardless of CWD.

## 2026-05-25 - flap_printer canvas_size_mm

- **Model:** Claude Opus 4.7
- **Commits:** (pending)
- **Files touched:** pvv_tools/flap_printer/{config.py,dimensions.py,cli.py}, pvv_tools/README.md, pvv_tools/prototype_job.json

### Goal
Decouple flap_printer output image size from SCAD physical printable area so the rendered canvas can match eufyMake Studio's 335x90 mm mat canvas without altering the physical jig model.

### Changes
- Added optional `output.canvas_size_mm` ([w, h]) to job-file `OutputConfig`.
- Extended `PrintableAreaDimensions` with absolute SCAD mat coordinates (`printable_origin_x/y`, `insert_origin_x/y`).
- When `canvas_size_mm` is set, cli overrides `dims.printable.width/height` only; insert offset stays relative so flap positions don't shift.
- Updated dry-run summary to label the area `Output canvas` when overridden.
- Set `canvas_size_mm: [90, 335]` in `prototype_job.json` and re-rendered: canvas grows to 4748x1276 px (335x90 mm @ 360 DPI), all 4 flaps fit, positions unchanged.

### Notes / decisions
- Initially placed insert at absolute mat coords inside the bigger canvas, which clipped EP47. Corrected: eufy's 335x90 canvas's top-left aligns with the printable-area origin (the same mat zero-point), not mat (0,0); only image size changes.

## 2026-06-02 - flap_printer: invert SCAD/Python architecture

- **Model:** Claude Sonnet 4.6
- **Commits:** 296223a
- **Files touched:**
  - `pvv_cad/PVV_splitflap_mods.scad` (remove jig section; add flap-only FLAP_PRINTER echoes)
  - `pvv_cad/flap_printer_jigs.scad` (new — standalone laser-cut jig generator)
  - `pvv_cad/flap_printer_params.scad` (new — auto-generated by Python; committed initial version)
  - `pvv_tools/flap_printer/config.py` (JigConfig expanded with all jig+mat fields)
  - `pvv_tools/flap_printer/dimensions.py` (from_scad() accepts optional jig_config; fix 330→333 default)
  - `pvv_tools/flap_printer/scad_writer.py` (new — write_flap_printer_params())
  - `pvv_tools/flap_printer/cli.py` (pass jig_config to from_scad(); call scad_writer)
  - `pvv_tools/prototype_job.json` (expanded jig section with all 16 parameters)
  - `pvv_cad/PVV_splitflap_mods.scad.bak` (backup, not committed)

### Goal
Factor flap-printing jig code out of PVV_splitflap_mods.scad into a standalone
flap_printer_jigs.scad, and invert the parameter flow so Python (job JSON) drives
SCAD rather than SCAD driving Python.

### Changes
- All jig+mat geometry variables removed from PVV_splitflap_mods.scad; jig module
  definitions moved to flap_printer_jigs.scad which reads flap_printer_params.scad.
- Python now writes flap_printer_params.scad on every render (scad_writer.py).
- Jig/mat parameters live in job JSON jig section; printable area + insert origin
  no longer come from SCAD echoes — Python reads them directly from config.
- PVV_splitflap_mods.scad retains only flap physical dimension echoes.
- flap_lineup module stays in PVV_splitflap_mods.scad (uses flap 3D modules).
- Fixed bug: PrintableAreaDimensions default height was 330.0, now 333.0.
- Fixed key mismatch: echo now uses flap_notch_height (computed), not flap_notch_height_default.

### Notes / decisions
- Steps 3+4 (SCAD refactor + Python inversion) done simultaneously; they are
  architecturally coupled — can't remove minibed_* from SCAD without also
  removing the echo lines Python read.
- flap_printer_params.scad committed with hardcoded prototype defaults so
  flap_printer_jigs.scad opens in OpenSCAD without requiring a prior Python run.
- minibed_insert_center_x/y aliases removed; code now uses minibed_insert_origin_x/y.
- laser_kerf_compensation / insert_kerf_compensation renamed to laser_kerf / insert_kerf.

## 2026-06-03 - flap_printer: enabled flag + OpenSCAD nightly detection

- **Model:** Claude Sonnet 4.6
- **Commits:** (this session)
- **Files touched:**
  - `pvv_tools/flap_printer/config.py` (added `enabled` field to `CustomFlap`)
  - `pvv_tools/flap_printer/renderer.py` (skip to transparent blank when `enabled=False`)
  - `pvv_tools/flap_printer/scad_parser.py` (prefer nightly OpenSCAD install)
  - `pvv_tools/prototype_job.json` (demo: slot 3 has `"enabled": false`)
  - `pvv_tools/prototype_output/common/batch_01_*.png`, `batch_02_*.png` (regenerated)
  - `pvv_tools/prototype_job_v1.json` (prior job variant saved)

### Goal
1. Add per-flap `enabled` flag so a flap can be blanked (100% transparent output)
   without affecting slot order.
2. Fix OpenSCAD auto-detection to prefer the nightly build over the stable build.

### Changes
- `CustomFlap` gets `enabled: bool = True`; `load_config()` reads `"enabled"` from JSON (defaults true).
- `print_summary()` appends `[DISABLED]` to disabled flap lines.
- `renderer._resolve_flaps_for_module()`: for `single` and `multi-module` types,
  disabled flaps produce a same-size transparent RGBA blank instead of loading/slicing
  the source image. `blank` type unchanged (already transparent).
- `scad_parser._find_openscad()` iterates `["OpenSCAD (Nightly)", "OpenSCAD"]` when
  scanning Program Files; nightly is now preferred so the stable build (which chokes on
  `if (i & 1)` introduced in commit 296223a) is no longer accidentally picked up.

### Notes / decisions
- The stable build (April 2024) does not support bitwise AND (`&`) in `if` conditions;
  the nightly build does. The fix is in the detection order, not the SCAD file.
- Multi-module disabled flaps: range guard runs first (out-of-range modules silently skip
  as before), then enabled check; so a disabled multi-module flap blanks only the
  in-range modules — same behaviour as if it were enabled but the source image were
  fully transparent.
- Large placeholder PNG/HEIC test images added to `test_images/placeholders/` this
  session are not committed (large binary blobs; not referenced by any tracked job file).

## 2026-07-03 - flap_printer: glyph type, emoji type, batch tools

- **Model:** Claude Sonnet 4.6
- **Commits:** 53e8e1b, 2fa78f6, 3e64f0c
- **Files touched:**
  - `pvv_tools/flap_printer/config.py` (glyph type + emoji type)
  - `pvv_tools/generate_epilogue_flap_svgs.py` (default output dir from --font)
  - `pvv_tools/download_emoji.py` (new — Twemoji SVG downloader)
  - `pvv_tools/requirements.txt` (added emoji>=2.0)
  - `pvv_tools/gen_glyphs.bat` (new — batch glyph regeneration)
  - `pvv_tools/gen_emojis.bat` (new — batch emoji download)
  - `pvv_tools/assets/epilogue_flaps/` → `pvv_tools/assets/flap_glyphs/Epilogue/` (git mv)
  - `pvv_tools/assets/flap_glyphs/Roboto/` (new — 52 Roboto glyph SVGs)
  - `pvv_tools/assets/emoji/heart.svg`, `waving-hand-medium-skin-tone.svg` (new)
  - `pvv_tools/README.md` (glyph/emoji types, setup section, generator docs)
  - `.gitignore` (desktop.ini, *.heic, placeholder PNGs)

### Goal
Add multi-font glyph support and color emoji support to flap_printer.
Also improve setup docs and add batch convenience scripts.

### Changes
- New `"glyph"` flap type: `{"type":"glyph","font":"Roboto","char":"A"}` — reads
  from `assets/flap_glyphs/<font>/`. `"epilogue"` remains as backward-compat alias.
- Moved `assets/epilogue_flaps/` → `assets/flap_glyphs/Epilogue/` (history preserved).
- Generator default output dir now auto-computed as `assets/flap_glyphs/<font>/`.
- New `"emoji"` flap type: `{"type":"emoji","name":"heart"}` or `{"type":"emoji","char":"❤️"}`.
  Resolves to `assets/emoji/<name>.svg`; files downloaded by `download_emoji.py`.
- `download_emoji.py`: fetches Twemoji SVGs via jsDelivr CDN, names by CLDR shortname,
  prints job JSON snippet. Added `--codepoints` flag as fallback for batch files where
  literal emoji are mangled by cmd.exe code page.
- `gen_glyphs.bat` / `gen_emojis.bat`: one-line-per-font/emoji batch files;
  activate venv + `chcp 65001` for UTF-8 handling.
- README Quick Start now covers venv creation + both requirements files.
- Fixed variable-shadowing bug: `raw` (demojize result) was overwriting `raw` (parsed JSON).

### Notes / decisions
- Twemoji coverage: Unicode 14.0 / Emoji 14.0 (~3,600 emoji); newer sequences not available.
- Color fonts (Segoe UI Emoji etc.) can't be used in OpenSCAD; emoji path uses pre-built SVGs.
- `chcp 65001` in batch files fixes cmd.exe code page mangling of emoji literals.
- `--codepoints 2764-fe0f` is the reliable fallback when literal chars still corrupt.

## 2026-07-03 - flap_printer: notch_mode, module preview, per-side notch

- **Model:** Claude Sonnet 4.6
- **Commits:** 7ab1064, 500802e, 39fe9f0, 0389ba3, 325dbcf, d481c55
- **Files touched:**
  - `pvv_tools/flap_printer/config.py` (notch_mode, PreviewConfig, _parse_notch_mode)
  - `pvv_tools/flap_printer/slicer.py` (fit_with_notch_mode — symmetric then per-side)
  - `pvv_tools/flap_printer/renderer.py` (refactored _render_custom_flap_images, preview call)
  - `pvv_tools/flap_printer/previewer.py` (new — contact-sheet preview generator)
  - `pvv_tools/README.md` (notch_mode, preview, enabled, type list, source exceptions)
  - `pvv_tools/gen_emojis.bat` (user added 10 more emoji)
  - `pvv_tools/prototype_job.json` (preview section, notch_mode tests)
  - `.gitignore` (prototype_output/ ignored; desktop.ini untracked)

### Goal
Add notch_mode image modifier, a contact-sheet module preview image, and per-side
independent notch control. Also housekeeping (gitignore, README audit).

### Changes
- `notch_mode`: new per-flap/global modifier — `"none"` / `"inset"` / `"squeeze"`.
  Inset fits image to safe content width; squeeze fits full width then squishes.
  Initially symmetric; expanded to per-side list `["left", "right"]` (Option B).
  Internally normalized to `(left, right)` tuple at config load; squeeze wins if sides differ.
- **Module preview**: `preview` config section generates a contact-sheet PNG at a
  separate low DPI (default 96). Each cell shows the physical flap shape (rounded
  outer corners + spool-pin notch cutouts) with artwork composited on top.
  Label below each cell shows both `label` and `slot` index.
- Renderer refactored: extracted `_render_custom_flap_images` helper so preview
  collection (`_collect_preview_entries`) and print pipeline share the same logic.
- README fully audited and fixed (enabled field, source exceptions, type list,
  pipeline steps, notch_mode sections with examples, preview section).
- Repo memory rule written: `flap_printer_readme_rule.md` with per-feature checklist.
- `prototype_output/` removed from git tracking; `desktop.ini` untracked.

### Notes / decisions
- Per-side list form: `["inset", "none"]` = left inset only; backward-compat with string.
- Preview runs a separate render pass at preview DPI (not reusing print-DPI images)
  to keep the code clean; negligible extra time at 96 DPI.
- `vscode_askQuestions` tool auto-dismissed in this session (known VS Code issue in
  agent mode); plain chat Q&A used instead.

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

## 2026-07-04 - flap_printer: bleed refactor, preview clipping, per-flap bleed/offset

- **Model:** Claude Sonnet 4.6
- **Commits:** 74585db, 425f765, 3c5d0a0, fa94e31, 4df5933, 02f2cbc
- **Files touched:**
  - `pvv_tools/flap_printer/slicer.py` (`_flush_edges`, bleed expansion at fit time)
  - `pvv_tools/flap_printer/renderer.py` (bleed threading, `_crop_to_pocket`, `_apply_offset`)
  - `pvv_tools/flap_printer/layout.py` (`generate_batch_image` reads bleed from image size)
  - `pvv_tools/flap_printer/previewer.py` (`_make_flap_mask`, flap-outline clipping)
  - `pvv_tools/flap_printer/config.py` (`CustomFlap.bleed`, `CustomFlap.offset_mm`, `_parse_offset`)
  - `pvv_tools/README.md` (Bleed Margin rewrite, Image Offset section, table rows)
  - `pvv_tools/gen_emojis.bat` (`pushd`/`popd` fix)
  - `pvv_tools/prototype_job.json` (working-state tests)
  - `pvv_tools/assets/emoji/*.svg` (10 new emoji assets)

### Goal
Refactor the bleed pipeline to be per-edge and WYSIWYG; add per-flap `bleed` opt-out
and `offset_mm` positioning; clip preview artwork to the physical flap outline;
document new features.

### Changes
- **Bleed refactor**: Old code uniformly upscaled every image by 2×bleed in
  `layout.py`. New: bleed expansion happens in `slicer.py` at fit time, per-edge,
  only on flush edges (where image fills to the boundary). `layout.py` reads baked-in
  bleed from image dimensions. Ink-save mask (`apply_ink_save_mask`) unchanged — still
  always expands full bleed on all sides.
- **WYSIWYG preview**: Preview render path now renders with bleed then crops back to
  `flap_w × flap_h` via `_crop_to_pocket`, so the preview exactly matches the
  in-pocket appearance.
- **Preview outline clipping**: `previewer.py` gained `_make_flap_mask` (rounded
  corners + notch cutouts); applied via `ImageChops.multiply` on artwork alpha so
  artwork outside the flap shape is hidden in the contact-sheet preview.
- **Per-flap `bleed` field**: `CustomFlap.bleed = True`; when `False`, skips
  bleed edge-expansion for that image (ink-save mask still applies).
- **Per-flap `offset_mm` field**: `[dx_mm, dy_mm]` shift applied to the full display
  image after all fit/notch transforms, before slicing into top/bottom halves.
  Positive X = right, positive Y = down.
- **README**: Bleed Margin section fully rewritten with A/B split (ink-save vs fit
  expansion), flush-edge table, and ASCII diagram. New `## Image Offset` section added.
- `gen_emojis.bat`: replaced `cd /d` with `pushd`/`popd` to preserve CWD.
- 10 new emoji SVGs added to `assets/emoji/`.

### Notes / decisions
- Flush-edge logic: `fill` = always flush; `fit` = AR-dependent (wider image → flush X);
  `stretch` = always flush; `contain` = never flush. Notch sides suppress x-flush.
- `calibration_offset_mm` (global canvas shift) vs `offset_mm` (per-image artwork
  positioning) distinction documented in README.
- Smoke test passed at each stage (`python -m pvv_tools.flap_printer prototype_job.json`).

## 2026-07-04 - flap_printer: inter_cell_gap, AR tolerance fix, multi-module geometry + coverage

- **Model:** Claude Sonnet 4.6
- **Commits:** none (uncommitted)
- **Files touched:**
  - `pvv_tools/flap_printer/config.py` (`inter_cell_gap_mm` in `PreviewConfig`; bleed default by type)
  - `pvv_tools/flap_printer/previewer.py` (border vs inter-cell gap separation; `max(0,...)` fix)
  - `pvv_tools/flap_printer/slicer.py` (`_flush_edges` AR tolerance; `extract_module_column` offset bug fix)
  - `pvv_tools/flap_printer/renderer.py` (slot-grouped resolution; multi-module blank fill; coverage warnings; common-pass fix)
  - `pvv_tools/test_images/skyline.png` (regenerated with correct module guides)
  - `pvv_tools/test_images/triptych.png` (regenerated with correct module guides)
  - `pvv_tools/prototype_job.json` (multi-module test entries)

### Goal
Add `inter_cell_gap_mm` to preview config; fix bleed defaults for SVG-based types;
fix `extract_module_column` geometry bug; add multi-module coverage gap detection
with blank fill-in and a mechanism for users to fill gaps via multiple same-slot entries.

### Changes
- **`inter_cell_gap_mm`**: New `PreviewConfig` field; separate from `cell_padding_mm`
  (outer border). `previewer.py` uses `max(0, ...)` floor so zero gap is valid.
- **Bleed defaults by type**: `single`/`multi-module` default to `bleed=True`;
  `glyph`/`epilogue`/`emoji`/`blank` default to `bleed=False`.  Explicit `"bleed"` in
  JSON still overrides.
- **`_flush_edges` AR tolerance**: Added `_AR_TOL = 1e-3`; exact-AR images now return
  `(True, True)` so bleed expands on both axes instead of one.
- **`extract_module_column` fix**: Removed erroneous `flap_left_in_module = (pitch-width)/2`
  offset.  The composite canvas starts at the left edge of flap 0, not the pitch-slot
  left, so `x_mm = offset * pitch` with no centering offset.
- **Test images regenerated**: `skyline.png` (6-module, 3740×880) and `triptych.png`
  (3-module, 1820×880) re-drawn with correct guide positions (`x = k × pitch`).
- **Slot-grouped resolution** (`_group_flaps_by_slot`): Multiple JSON entries with the
  same `slot` index are tried left-to-right per module; first entry whose `module_range`
  covers the current module wins.  Allows partial-range fill entries (e.g. `"type": "blank",
  "module_range": [0,2]`) alongside a full multi-module entry for a different sub-range.
- **Blank fill for coverage gaps**: When a processed module has no coverage for a
  multi-module slot, a transparent blank is output and `WARNING` is logged.
- **Upfront coverage warning**: `render_job` now warns once per gap slot before rendering
  begins: `Slot N ('label'): modules [x, y] have no coverage — will output blank flap(s)`.
- **Common-pass fix**: `common/` output now uses `module_index=-1`, so multi-module
  entries are correctly excluded from common batches.
- **Preview blank cells**: `_collect_preview_entries` now shows blank cells for uncovered
  modules in multi-module slots (preview grew from 19 → 22 cells for current test job).

### Notes / decisions
- Multiple same-slot entries are ordered by declaration; `module_range` is respected for
  ALL types (not just `multi-module`), allowing `"type": "blank", "module_range": [0,2]`
  as an explicit filler without shadowing adjacent ranges.
- Modules outside ALL multi-module ranges (e.g. 6–23 in the test job) do not appear in
  `_get_modules_to_process` and use `common/` output — no warning, by design.
- `common/` bug pre-existed: previously `module_index=0` was passed for the common pass,
  accidentally including skyline col 0 in `common/`; fixed this session.

## 2026-07-05 - flap_printer: correct front-back jig-flip geometry

- **Model:** Claude Opus 4.8
- **Commits:** none (uncommitted)
- **Files touched:**
  - `pvv_tools/flap_printer/renderer.py` (back-side jig-flip geometry)

### Goal
Fix the front-back flip mode so the back sheet registers correctly after the
physical jig flip (notch/pins and artwork land on the correct side/orientation).
A first attempt (per-image `FLIP_LEFT_RIGHT`) did not fix it.

### Changes
- Removed the speculative per-back-image `FLIP_LEFT_RIGHT` transform.
- Replaced it with a single verified rule: a front-back flip is geometrically
  `reflect_x == rotate180 ∘ reflect_y`, i.e. a left-right flip followed by an
  in-plane 180° rotation. So the back sheet is now ALWAYS built with left-right
  semantics (`reorder` with `"left-right"`, spool-at-top, mask spool-at-top), and
  when the job is in `front-back` mode the fully-composed back image (art + mask +
  labels) is rotated 180° via `Image.ROTATE_180` before registration marks and the
  calibration offset (which stay in true sheet space).
- Removed now-unused imports `FlapSide` and `apply_flip_transform` from renderer.

### Notes / decisions
- Verified empirically with an asymmetric "R" marker (red dot top-left, blue dot
  bottom-right): rendered the same job in both modes, and confirmed pixel-identical
  that `front-back back == ROTATE_180(left-right back)`. Front sheet and left-right
  mode are byte-for-byte unchanged (no regression).
- The ink-save mask notches are drawn symmetrically on both sides, so the notch
  never "swaps" by itself; the real defect was that the back kept the spool at the
  top (spool-at-bottom=False, correct only for left-right) instead of matching the
  front's spool side after a front-back flip. The 180° rotation fixes both the
  spool/pin side and the artwork orientation in one step.
- Full `prototype_job.json` re-rendered clean (29 files, 22-cell preview).
- Left this uncommitted per the session-logging rule (staging left to the user).

## 2026-07-05 - flap_printer_jigs.scad: fix pvv_rounded_square reference + flip_mode default

- **Model:** Claude Sonnet 4.6
- **Commits:** none (uncommitted)
- **Files touched:**
  - `pvv_cad/flap_printer_jigs.scad` (fix unknown-module warning)
  - `pvv_tools/flap_printer/config.py` (fix JSON parse default for flip_mode)
  - `pvv_tools/README.md` (update flip_mode default + description)

### Goal
Fix OpenSCAD warning "Ignoring unknown module 'pvv_rounded_square'" on line 130 of
`flap_printer_jigs.scad`, and fix a stale `flip_mode` default in the README and config.

### Changes
- `flap_printer_jigs.scad`: Both `pvv_rounded_square(..., cr=...)` calls changed to
  `rounded_square(..., r=...)` from Scott's `3d/shapes.scad` (already imported). The
  `pvv_rounded_square` module lives only in `PVV_splitflap_mods.scad` and was never
  in `shapes.scad`; the `use<>` comment was wrong from the refactor.
- `config.py`: `_get(j, 'flip_mode', 'left-right')` → `'front-back'` to match the
  dataclass field default (which had been updated to `"front-back"` in a prior commit
  but the JSON parser fallback was never synced).
- `README.md`: `flip_mode` table row default updated to `"front-back"`; description
  reworded to describe the physical jig motion rather than the image transform.

### Notes / decisions
- `pvv_rounded_square` vs `rounded_square`: both are geometrically equivalent for
  all-4-corners rounding; Scott's version additionally supports a `corners=[]`
  parameter for selective rounding (unused in jigs.scad).
- `PVV_splitflap_mods.scad` has uncommitted top-level call changes
  (`print_plate` / `motor_flange_alignment_jig` toggle) — working state, not staged.

## 2026-07-05 - flap_printer + jig SCAD: unify on printer orientation (remove portrait/landscape)

- **Model:** Claude Fable 5
- **Commits:** none (uncommitted)
- **Files touched:**
  - `pvv_cad/flap_printer_jigs.scad` (rewritten in printer orientation)
  - `pvv_cad/flap_printer_params.scad` (regenerated)
  - `pvv_tools/flap_printer/` `config.py`, `dimensions.py`, `layout.py`,
    `labels.py`, `renderer.py`, `cli.py`, `scad_writer.py`
  - All job JSONs (`prototype_job.json`, `prototype_job_v1.json`,
    `pvv_job_snippets.json`, `example_job.json`, `test_job.json`,
    `test_svg_job.json`, `test_epilogue_job.json`, `PVV_TestFlapSet_01.json`)
  - `pvv_tools/README.md`, `CLAUDE.md`

### Goal
Eliminate the portrait/landscape dual-frame confusion: the OpenSCAD jig was
modeled with its long axis along Y (rotated 90 deg from how it physically sits
on the eufyMake E1 Mini Flatbed).  Refactor so SCAD, the job JSON `jig`
section, and the Python renderer all share ONE frame ("printer orientation"):
long axis along X, mat zero-point / corner-cut corner at bottom-right, exactly
matching the physical top-down view and the output print images.

### Changes
- **SCAD**: `flap_printer_jigs.scad` rewritten — mat 370x97, printable area
  333x88 at (4,5), insert 300x66 at (20.5,16), corner cut at (370,0), six
  pockets in a row along X with `rotate(90) flap_2d()` (spool edge right,
  toward the zero point).  Fingernail relief moved with the geometry (insert
  bottom-right corner).  `minibed_reg_mark_extent_y` -> `_extent_x`.
- **Python**: `output_orientation` config key removed entirely (warning if
  present; second warning if a job's `printable_size_x < y`, i.e. the old
  rotated convention).  Flap content stays composed in the "upright frame";
  the ONE transform to the sheet is a per-flap `Image.ROTATE_90` (CCW) at
  batch-layout time (upright top -> sheet left, spool -> sheet right).  The
  ink-save mask polygon stays in the verified upright frame, drawn once into
  a tile, rotated, and pasted per pocket.  `JigDimensions.insert_size` and
  all pocket spacing now use `flap.height` along X / `flap.width` along Y.
  Labels are drawn via a temporary ROTATE_270 into the upright frame.
  Dead `apply_flip_transform` removed; `reorder_for_jig_flip` loses its
  orientation param (left-right flip reverses columns, front-back reverses
  rows — sheet frame).  `canvas_size_mm` is now sheet-frame `[w, h]` (e.g.
  Camera mode `[335, 90]`), with the insert anchored to the image's left and
  bottom edges to preserve the previously calibrated placement.
- **Job JSONs**: jig sections converted (num_flaps 6x1, printable 333x88 at
  (4,5), insert at (20.5,16)); `output_orientation` dropped everywhere.
- **Docs**: README jig table + orientation preamble, canvas/calibration
  notes, spec table, pipeline walkthrough; CLAUDE.md gained an "Orientation
  convention (critical rule)" section.

### Verification
- Rendered 4 reference variants BEFORE the refactor (default front-back,
  `--flip-mode left-right`, labels+registration-marks, `canvas_size_mm`
  override) and re-rendered AFTER: **all 116 output files byte-identical**
  (script in session scratchpad).  Output images were already in printer
  orientation, so this proves the refactor is a pure internal reframing.
- OpenSCAD top-view renders of old vs new jig confirm the same physical
  geometry rotated 90 deg: corner cut + fingernail relief at bottom-right,
  pocket notches facing right; no OpenSCAD warnings.

### Notes / decisions
- `spool_at_bottom` parameter names kept — they refer to the upright content
  frame (documented in CLAUDE.md); renaming to sheet terms would re-couple
  mask geometry to the sheet frame for no gain.
- The flip-geometry rule (`reflect_x == rotate180 . reflect_y`) is
  frame-independent and unchanged.
- Exact byte-identity required two subtle equivalences, both commented in
  `layout.py`: the odd-pixel side-bleed remainder goes below the pocket, and
  the mask tile pastes 1 px higher because polygon boundary pixels are
  inclusive.  At DPIs where mm->px rounding is non-integer (e.g. 360), new
  vs old placement could in principle differ by <=1 px (0.07 mm) since
  offsets are now rounded in sheet space; at 508 DPI (20 px/mm) everything
  is exact.
- `pvv_plans/flap_printer_plan.md` still uses the old terms — left as-is
  (historical planning record).
- `prototype_job_v1.json` was also converted so it stays runnable.

## 2026-07-05 - flap_printer: multi-module segments (one entry per slot)

- **Model:** Claude Fable 5
- **Commits:** none (uncommitted)
- **Files touched:**
  - `pvv_tools/flap_printer/config.py` (FlapSegment model, parsing, validation)
  - `pvv_tools/flap_printer/renderer.py` (segment resolution; slot grouping removed)
  - `pvv_tools/prototype_job.json` (slot 11 converted to segments)
  - `pvv_tools/test_multimodule_job.json` (new: runnable coverage-gap test job)
  - `pvv_tools/README.md` (custom_flaps table, Multi-Module Segments section)

### Goal
Replace the repeated-slot mechanism for stitched multi-module flaps (several
`custom_flaps` entries sharing one slot, resolved by declaration order) with
an explicit `segments` list on a single entry.  Approved as "Phase 0.5" of
the standard-flatbed plan (pvv_plans work pending user measurements).

### Changes
- New `FlapSegment` dataclass: `module_range`, `source` (or `"blank": true`),
  and per-segment `fit_mode`/`scale`/`crop`/`notch_mode`/`offset_mm`
  overrides.  Fallback chain: segment -> entry -> global transforms.
- Flat multi-module form (`source` + `module_range` on the entry) is
  normalised to a single segment at load time; `cf.module_range` now holds
  the overall span across segments.
- Validation: duplicate slots are a hard error (with a pointer to
  `segments`); overlapping segment ranges error; `module_range`/`segments`
  on non-multi-module types error.  `_get_modules_to_process` enumerates
  per segment, so inter-segment gaps do not pull in uncovered modules.
- Renderer: `_group_flaps_by_slot` removed; `_resolve_flaps_for_module`,
  `_collect_preview_entries`, and the upfront coverage warning now use
  `CustomFlap.segment_for_module`.  Uncovered modules still render blanks
  with the same `-blank` label and warning; explicit blank segments count
  as coverage (no warning).  Dry-run summary prints one line per segment.

### Verification
- Byte-compare harness: rendered prototype_job (slot 11 in old repeated-slot
  form) + a coverage-gap job BEFORE the refactor, re-rendered AFTER (slot 11
  converted to `segments`; gap job in flat form): **38/38 files
  byte-identical**, gap warning unchanged.
- Exercised all new error paths (dup slot, overlapping segments,
  module_range on single, segments+flat mix) and blank-segment warning
  suppression.

### Notes / decisions
- Old repeated-slot form dropped cleanly (duplicate slot = error) rather
  than deprecated — all job files are local and were converted in the same
  change (user decision).
- Preserved edge-case quirk for byte-compat: a disabled multi-module entry
  still contributes a blank flap to the `common/` pass.
- Minor intentional label change: a *disabled* multi-module flap at an
  uncovered module now labels as `<label>` rather than `<label>-blank`
  (content identical; labels-on edge case only).
- The old `{"type": "blank", "module_range": ...}` same-slot filler trick is
  replaced by `"blank": true` segments.

## 2026-07-05 - flap_printer: eufyMake standard flatbed support (multi-row sheets)

- **Model:** Claude Fable 5
- **Commits:** none (uncommitted)
- **Files touched:**
  - `pvv_tools/flap_printer/config.py` (jigs map + active_jig; insert_rows /
    insert_pitch_y_mm; per-jig calibration_offset_mm / canvas_size_mm)
  - `pvv_tools/flap_printer/dimensions.py` (JigDimensions.rows / row_pitch /
    flaps_per_sheet)
  - `pvv_tools/flap_printer/layout.py` (pitch-aware pocket grid in batch
    image + mask; rotate_insert_rows_180)
  - `pvv_tools/flap_printer/labels.py` (pitch-aware pocket grid)
  - `pvv_tools/flap_printer/renderer.py` (_render_sheets global-packing flow;
    _finish_and_save shared finishing)
  - `pvv_tools/flap_printer/cli.py` (--jig flag; per-jig canvas override)
  - `pvv_tools/flap_printer/scad_writer.py` (insert_rows/pitch params; active
    jig noted in the generated header)
  - `pvv_cad/flap_printer_jigs.scad` (generalized for N insert rows: insert
    profiles, flap pockets, and fingernail reliefs loop over rows)
  - `pvv_cad/flap_printer_params.scad` (regenerated; +insert_rows/pitch vars)
  - `pvv_tools/prototype_job.json` (jigs map: minibed + standard; minibed
    calibration moved into its jig def)
  - `pvv_tools/README.md` (jigs docs, Standard Flatbed Sheets section, --jig)

### Goal
Support the eufyMake standard flatbed: printable 333 x 418 mm (Zero Point
mode), origin measured at mat (4, 11).  Same laser-cut insert as the minibed,
5 rows stacked along Y; front-back flips are PER INSERT (each row flipped
individually), not the whole bed.  Must not change minibed output.

### Design
- Job files can hold both jig definitions: `"jigs": {name: {...}}` +
  `"active_jig"`, switchable per run via `--jig NAME`.  Single `"jig"` form
  still accepted.  calibration_offset_mm and canvas_size_mm can live per-jig
  (bed properties), falling back to the output section.
- Row layout (proposed, config-driven): first insert at mat y=25,
  pitch 81 mm -> 5 x 66 mm inserts with 15 mm webs and 14 mm symmetric
  outer margins inside the 418 mm printable depth.
- Multi-row jigs use GLOBAL PACKING: the sheet set is the complete physical
  print job for the whole display, one flap per module x slot.  Covered
  modules use their per-module sequence; uncovered modules use the
  module-agnostic singles sequence (replacing the "print common/ once per
  module" convention, which cannot survive packing).  Print each sheet once.
  sheets_manifest.txt maps sheet/row/pocket -> flap label + module.
- Back sheets: each row built with left-right semantics and (front-back
  mode) rotated 180 deg about ITS OWN row centre (rotate_insert_rows_180) —
  the per-insert flip geometry.  Single-row path keeps the whole-image
  ROTATE_180 (equivalent for a centred single insert; byte-preserved).
- Prototype job on the standard bed: 72 flaps (6 modules x 12) -> 3 sheets,
  one print run each, vs 12 minibed runs.

### Verification
- Minibed: 38/38 output files byte-identical through all new machinery
  (jigs map, per-jig calibration, shared _finish_and_save, pitch-aware grid).
- Standard: rows 1/2 of sheet_01 (front AND back) proven PIXEL-IDENTICAL to
  the verified minibed module_00 batch_01/02 insert bands (calibration
  zeroed for the comparison; X geometry is shared between the beds).
- Investigated residual diffs before zeroing calibration: entirely artifacts
  of _apply_calibration_offset on the mini side (paste-with-self-mask
  attenuates antialiased edge alpha quadratically and zeroes RGB under
  alpha=0).  Pre-existing behaviour, physically irrelevant (<= 0.05 mm edge
  fringe), NOT caused by the new code.  Noted for a possible future fix
  (use Image.transform or offset() instead of paste for the calibration
  shift).

### SCAD (measurements received same session)
- Standard mat outer Y measured at 440 mm; corner cut confirmed lower-right
  (same as mini).  Printable 11..429 -> symmetric 11 mm Y margins.
- flap_printer_jigs.scad generalized: `eufy_minibed_flap_jig_insert_profiles()`
  cuts `minibed_insert_rows` inserts at `minibed_insert_pitch_y`; flap-pocket
  and fingernail-relief loops likewise.  The single-insert cut path
  (bGenInsertOnly=true) is unchanged — the same insert serves both beds.
  To cut the standard outer jig: run the tool with `--jig standard` (writes
  standard params), open jigs.scad, set bGenInsertOnly=false, export SVG.
- Verified via OpenSCAD top-view renders: standard outer jig (370x440,
  corner cut lower-right, 5 cutouts, reliefs, reg marks) and minibed outer
  jig (unchanged with rows=1 params).
- Renamed the `minibed_` variable/module prefix to `flatbed_` throughout
  (params template, jigs.scad incl. `eufy_flatbed_*` modules, and the
  legacy SCAD-echo fallback names in dimensions.py/config.py) — the params
  file describes whichever bed is active, not just the mini.  User's
  snapshot `pvv_cad/flap_printer_params_MINIBED_20260705.scad` left as-is
  (old prefix; regenerate minibed params with a plain run instead of
  swapping it in).
- Committed params file left generated for the STANDARD bed (user request,
  for cutting the standard outer jig); regenerate for the mini with a plain
  run (active_jig = minibed).

### Open items
- Cut the standard outer jig; zero-point calibration print on the standard
  bed (per-jig calibration_offset_mm slot is ready).

## 2026-07-05 - flap_printer: gap-edge bleed (fix bare-stock sliver at the flap gap)

- **Model:** Claude Fable 5
- **Commits:** none at log time (committed/pushed same session)
- **Files touched:**
  - `pvv_tools/flap_printer/slicer.py` (slice_display_image gap_bleed_px)
  - `pvv_tools/flap_printer/renderer.py` (thread gap bleed; _crop_to_pocket)
  - `pvv_tools/flap_printer/layout.py` (gap-aware paste split in
    generate_batch_image)
  - `pvv_tools/README.md` (Bleed Margin behavior C; bleed key; pipeline)

### Goal
Mini-flatbed print test showed thin bars of bare (black) flap stock between
emoji artwork and the gap-side flap edge.  Root cause: the bleed system
expanded content only on OUTER flush edges; the gap-side cut edge of each
half got no bleed for ANY flap type — slice_display_image cropped exactly
at the gap boundary and discarded the gap strip.

### Fix (user-approved plan, unconditional)
- Gap-edge bleed is a pure CROP change, not a fit expansion: the display
  image already contains the artwork's true continuation in the 2 mm gap
  strip.  Each half now keeps min(bleed_mm, gap) = 1 mm of adjacent gap
  rows on its cut edge.  No scaling/repositioning of the glyph whatsoever.
- Applies to ALL flap types unconditionally when bleed_mm > 0 — including
  "bleed": false emoji/glyphs (that flag now gates outer-edge expansion
  only).  The ink-save mask already permitted this overprint (spool-edge
  boundary +bleed, notch voids inset); it needed no change.
- layout.generate_batch_image splits each image's along-X extra size into
  gap bleed (spool side) and outer bleed (display side) via a job-wide
  gap_bleed_px parameter; per-image amounts inferred with min() so blanks
  and legacy-sized images are unaffected.
- Preview stays WYSIWYG: _crop_to_pocket trims the gap rows.

### Verification
- Preview PNGs byte-identical across all variants (gap bleed cropped away).
- Ring check over 4 render variants (front-back, left-right, gap-coverage
  job, standard-bed sheets; fronts AND backs): every changed pixel lies in
  the 1 mm bleed ring around a pocket; pocket interiors pixel-identical.
  (First run flagged false failures on calibrated variants — the checker
  had forgotten the minibed's +1 mm calibration shift, not a code bug.)
- Visual before/after zoom of the heart emoji gap edge: artwork now extends
  through the cut edge into the bleed zone; notch voids respected.

## 2026-07-05 (overnight) - Planning revision + 62-flap firmware started

- **Model:** Claude Fable 5
- **Commits:** none (left uncommitted for morning review)
- **Files touched:**
  - `firmware/src/config.h` ("Flap option 5": PVV 62-flap set behind
    -DPVV_FLAPS_62; standard option 2 untouched otherwise)
  - `platformio.ini` (new [env:chainlink_pvv62] extending chainlink)
  - `pvv_plans/BLE-app-plan.md` (new — Part I-B plan)
  - `pvv_plans/SocialMQTT-plan.md` (roadmap restructure, Part II update,
    critical-review section appended)

### Goal (user request before signing off)
1. Promote extended-flap firmware from Part II to now: display is 62 flaps
   (confirmed by num_flaps=62 in PVV_splitflap_mods.scad); get firmware
   changes started so the custom modules can be seen in action.
2. Add an intermediate milestone: iPhone app driving the display over
   Bluetooth (for demos at work, off any WiFi), with emoji + triptych
   support and decent UX.
3. Critically review the SocialMQTT plan with fresh eyes.

### 62-flap firmware (Part I-A) — done to "builds clean"
- Verified feasibility: step math supports non-integral steps/flap
  (2048/62 ~ 33.03); proto flap_character_set max_size=80 fits 62 (no
  proto regen); QCMD_FLAP(99)+62 < 255; saved-config invalidation on
  num_flaps change is graceful (logged, ignored).
- config.h option 5: standard 52 in standard order + 10 custom flaps at
  indexes 52-61 with lowercase mnemonic codes h/j/n/s/b/k/e/d/c/t
  (avoiding the color-block letters g/p/r/w/y).
- Both `pio run -e chainlink_pvv62` (10.7% RAM / 30.4% flash) and the
  default `chainlink` env build SUCCESS.
- OPEN QUESTION for user: confirm physical spool order matches the table
  (are customs appended after the full standard 52, with the corrective
  '-'/'$' flaps at their standard positions 41/42?).  Labels PVV42..53 on
  the printed flaps left this ambiguous.  Index-based proto control works
  regardless; only character-based text mapping depends on it.
- Flashing note: first 62-flap boot logs "Invalid config - stored
  num_flaps was 52..." and resets saved offsets — re-calibrate after.

### BLE iPhone app (Part I-B) — planned
- New pvv_plans/BLE-app-plan.md.  Key findings: Web Bluetooth does not
  exist on iOS (browser+BLE ruled out); native app REQUIRES a Mac/Xcode
  (decision gate B0); free Apple ID sideloads expire in 7 days.
- Firmware side (B1) is Mac-independent: NimBLE-Arduino 1.4.x (pinned —
  2.x needs newer core than espressif32@3.4), GATT service with
  Text / FlapIndexes / State / Control characteristics, task slotted in
  like MQTT/HTTP.  Bench-testable with nRF Connect before any app exists.
- Fallback if no Mac: ESP32 SoftAP + embedded web app (never touches work
  network; check workplace AP policy).

### SocialMQTT plan critical review — appended to the plan doc
- All plan claims verified against the repo (paths, envs, flags, PubSub
  2.8, WiFiClientSecure.setInsecure availability on core 1.0.6, EMQX
  free-tier quota math).  Plan architecture is sound.
- Real gaps found: Discord Message Content privileged intent missing;
  showString() silently skips unknown chars (bridge sanitize is
  load-bearing; pad to module count); commands must NOT be retained
  (stale-post replay on reboot); lowercase letters are now flap codes so
  sanitize must uppercase BEFORE filtering (plan already did — keep);
  HA discovery publish worth gating; bridge needs bounded queue +
  reconnect backoff.

## 2026-07-06 - 62-flap spool order confirmed; plans updated

- **Model:** Claude Fable 5
- **Commits:** none (holding push per user)
- **Files touched:** `firmware/src/config.h`, `pvv_plans/SocialMQTT-plan.md`,
  `pvv_plans/BLE-app-plan.md`

### Changes
- User confirmed the physical spool order: Scott's standard sequence with
  the 10 custom flaps INSERTED after '$' (index 42):
  indexes 43-52 = heart, joy, wink, smile, sob, kiss, heart_eyes,
  art_1 (woodgathering), panorama (skyline), art_2 (triptych); Scott's
  apostrophe..w continue at 53-61.  The printed labels PVV42..53 turn out
  to be 1-BASED spool positions (PVV44 = heart = index 43).
- config.h "Flap option 5" table reordered accordingly (TODO removed);
  `pio run -e chainlink_pvv62` rebuilds SUCCESS.
- BLE plan: decision gate resolved — user has an iMac (Xcode install
  needed); native SwiftUI path is GO; added phase B2a (Xcode +
  Hello-World provisioning de-risk).  Panel indexes corrected to 51/52.
- SocialMQTT roadmap: code-map indexes corrected to 43-52.

## 2026-07-06 - Make-folder project audit (readmes + master directory)

- **Model:** Claude Fable 5
- **Commits:** none (no repo source changes)
- **Files touched:** none inside this repo; audit artifacts written OUTSIDE
  the repo (see below)

### Changes
- Audited all 40 project folders under `C:\Users\phgev\Documents\Make`
  (8 parallel agents): purpose, tech, usage, GitHub presence (RoboDad),
  and backup freshness vs `\CHICKENCOOP\Public\Make`.
- Wrote a `readme.md` into every project folder (37 new; `readme_audit2026.md`
  in Chalkbot, DragonChonk, SVG2GCODE which had READMEs). No existing files
  modified or deleted anywhere.
- Generated master directory: `C:\Users\phgev\Documents\Make\MakeProjects_audit2026.html`
  (searchable/filterable HTML5, 40 cards, GitHub + backup badges).
- Note for this repo: `Make\Splitflap\readme.md` (new, OUTSIDE the git repo)
  describes the whole Splitflap workspace incl. non-git folders
  (MX1508_Driver, PVV_CAD, pre-fork backup) — NAS backup of those is
  ~4 months stale (2026-03-05).
- Key audit findings: 34 of 40 projects not on GitHub; 24 with no NAS
  backup at all, incl. HomeMovieMigration (12.5 GB family video, no copy
  anywhere) and Blockwall (3.3 GB); PipBoy NAS copy is MORE complete than
  local; local `Laser` folder empty while NAS copy is the active primary.

## 2026-07-06 - "Fire When Ready, Gridley" TRS-80 recreation

- **Model:** Claude Fable 5
- **Commits:** none
- **Files touched:** none inside this repo (final state) — created briefly
  as `pvv_misc/castle_shot/`, then moved OUTSIDE the repo to its own Make
  project: `C:\Users\phgev\Documents\Make\FireWhenReadyGridley\`
  (`castle_shot.bas`, `castle_shot.html`, `README.md`)

### Changes
- Located the original "CASTLE SHOT" listing ("Fire When Ready, Gridley"
  section, pp. 212-214) in D. Lien's *User's Manual for Level 1* (1977) via
  the archive.org scan; transcribed it from the page images (OCR text layer
  was unreliable — corrected Z=74, FOR X=1 TO 18, 1800 NEXT Z, 1810 PRINT
  AT 0 against the scans).
- Built a self-contained HTML5 remake (`castle_shot.html`): simulated 64x16
  cell / 128x48 pixel Model I screen incl. text-cell vs graphics-cell
  SET/RESET semantics (shell punches holes through the fort; KAPOW! erased
  by RESETs), statement-paced execution (~300 stmt/s at 1x, slider to MAX),
  5x7 pixel font, CRT bezel/scanline styling, initials input, rerun prompt.
- Verified headless via Node smoke test (25 assertions on end-state screen
  model): all pass.
- Per user request, relocated the whole folder out of this repo to
  `Make\FireWhenReadyGridley` (standalone project); `pvv_misc/` removed.

# Flap Printer — UV Print Layout Generator

Generates print-ready images for UV printing custom splitflap flaps on a
Eufy E1 printer, using a laser-cut flap jig.

## Quick Start

All commands must be run from the **repo root** directory
(`splitflap/`), because Python needs to find the `pvv_tools/` package.

### First-time setup (one-off)

Create a virtual environment and install all dependencies:

```powershell
cd c:\Users\phgev\Documents\Make\Splitflap\Firmware\splitflap

# Create the venv (once per machine)
python -m venv .venv

# Activate it (required every new terminal session)
.venv\Scripts\Activate.ps1          # PowerShell
# or: .venv\Scripts\activate.bat   # Command Prompt / batch files

# Install dependencies
pip install -r pvv_tools\requirements.txt      # flap_printer packages
pip install -r 3d\scripts\requirements.txt     # needed by the glyph generator
```

The `.venv` folder is gitignored — everyone who clones the repo does this once.
Re-run the `pip install` lines any time `requirements.txt` changes.

### Running the tool

```powershell
# Make sure the venv is active first (see above)

# Dry run — validate config and show summary
python -m pvv_tools.flap_printer pvv_tools/example_job.json --dry-run

# Generate print images
python -m pvv_tools.flap_printer pvv_tools/example_job.json --output-dir output/
```

### What does `python -m pvv_tools.flap_printer` mean?

- `python -m` tells Python to run a **package** by its dotted module path
  (not a file path).
- `pvv_tools.flap_printer` means "the `flap_printer` sub-package inside the
  `pvv_tools` package" — the dot is Python's package separator (like `/` in
  file paths).
- Python resolves this to `pvv_tools/flap_printer/__main__.py`.
- It only works if Python can find `pvv_tools/` on its search path, which
  happens automatically when you `cd` to the repo root. Alternatively, set
  the `PYTHONPATH` environment variable:

  ```powershell
  $env:PYTHONPATH = "c:\Users\phgev\Documents\Make\Splitflap\Firmware\splitflap"
  python -m pvv_tools.flap_printer pvv_tools/example_job.json --dry-run
  ```

## Usage

```
python -m pvv_tools.flap_printer JOB_FILE [options]

positional arguments:
  job_file              Path to JSON job config file

options:
  --dpi INT             Override output DPI (default: from config or 360)
  --output-dir PATH     Override output directory
  --modules M [M ...]   Process specific modules only
  --no-labels           Disable EP labels
  --no-mask             Disable ink-saving mask
  --flip-mode MODE      left-right | front-back (default: left-right)
  --print-size W H      Override output size in mm
  --dry-run             Validate config, print summary
  --verbose, -v         Verbose logging
  --openscad PATH       Path to OpenSCAD executable (auto-detected if omitted)
  --scad-mods PATH      Override path to PVV_splitflap_mods.scad
```

---

## Job Config (JSON)

See `example_job.json` for a complete example. The config has five sections:

### `display` — Display geometry

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `num_modules` | int | `48` | Total modules in the display |
| `module_pitch_mm` | float | `64.0` | Center-to-center distance between modules (mm) |
| `inter_module_gap_mm` | float | `10.0` | Gap between adjacent module frames (mm) |

### `jig` — Print jig settings

All jig coordinates are in **printer orientation** — exactly as the jig sits
on the eufyMake E1 Mini Flatbed, viewed from above.  The mat's long axis runs
along X (left/right), and the mat zero-point corner (the one with the
diagonal corner cut) is at the bottom-right.  The OpenSCAD model
(`pvv_cad/flap_printer_jigs.scad`), the output print images, and the physical
flatbed all share this one frame.  Flap pockets sit rotated 90° in the jig —
spool/notch edge facing right, toward the zero point — in a single row along
X, so a pocket's X extent is `flap_height` and its Y extent is `flap_width`.

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `type` | string | `"minibed"` | Jig type (currently only `"minibed"` supported) |
| `flip_mode` | string | `"front-back"` | How the jig is physically flipped to load the back: `"front-back"` (pancake flip — rotate about the long X axis) or `"left-right"` (side flip — rotate about the short Y axis) |
| `num_flaps_x` | int | `6` | Number of flap pocket columns in the jig insert (along the long X axis) |
| `num_flaps_y` | int | `1` | Number of flap pocket rows in the jig insert |
| `gap_x_mm` | float | `6.0` | Horizontal gap between flap pockets (mm) |
| `gap_y_mm` | float | `6.0` | Vertical gap between flap pockets (mm) |
| `margin_x_mm` | float | `6.0` | Horizontal margin around the pocket grid inside the insert (mm) |
| `margin_y_mm` | float | `6.0` | Vertical margin around the pocket grid inside the insert (mm) |
| `printable_size_x_mm` | float | `333.0` | Width of the printer's printable area along the long X axis (mm). Used as the default canvas width and to anchor insert position. |
| `printable_size_y_mm` | float | `88.0` | Depth of the printer's printable area along the short Y axis (mm). Used as the default canvas height. |
| `printable_origin_x_mm` | float | `4.0` | X position of printable area's lower-left corner in mat absolute coordinates (mm) |
| `printable_origin_y_mm` | float | `5.0` | Y position of printable area's lower-left corner in mat absolute coordinates (mm) |
| `insert_origin_x_mm` | float | `20.5` | X position of insert's lower-left corner in mat absolute coordinates (mm) |
| `insert_origin_y_mm` | float | `16.0` | Y position of insert's lower-left corner in mat absolute coordinates (mm) |
| `laser_kerf_mm` | float | `0.04` | Inward offset applied to each flap pocket when cutting the insert (tightens fit) |
| `insert_kerf_mm` | float | `0.04` | Outward offset applied to the insert outline when cutting the outer jig (compensates laser kerf) |
| `mat_size_x_mm` | float | `370.0` | eufyMake minibed mat outer length along X (mm) — hardware constant, rarely changed |
| `mat_size_y_mm` | float | `97.0` | eufyMake minibed mat outer depth along Y (mm) — hardware constant, rarely changed |
| `mat_corner_radius_mm` | float | `7.5` | Mat outer corner radius (mm) |
| `mat_corner_cut_mm` | float | `22.0` | Mat diagonal corner cut length (mm) at the mat origin corner |
| `reg_mark_size_mm` | float | `6.0` | L-shaped registration mark arm length (mm) — written to `flap_printer_params.scad` for use by the laser-cut outer jig |
| `reg_mark_stroke_mm` | float | `1.0` | Registration mark stroke width (mm) |

> **Note:** All jig and mat parameters are written to `pvv_cad/flap_printer_params.scad`
> on every render. Open `pvv_cad/flap_printer_jigs.scad` in OpenSCAD to generate the
> laser-cut SVG files for the insert and outer jig.

### `output` — Output file settings

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `dpi` | int | `360` | Output resolution in dots per inch |
| `format` | string | `"png"` | Output image format |
| `bleed_mm` | float | `1.0` | Bleed expansion and ink-save mask margin beyond the flap pocket edge (mm). See [Bleed Margin](#bleed-margin). |
| `ink_save_mask` | bool | `true` | Zero alpha outside flap pockets to save ink |
| `labels` | bool | `true` | Render EP slot labels in the gap areas |
| `label_font_size_pt` | int | `6` | Label font size in points |
| `output_dir` | string | `"output"` | Output directory (relative paths are resolved against the job file's directory, not CWD) |
| `canvas_size_mm` | `[w, h]` | _unset_ | Optional output image canvas size in mm. When set, the rendered image is sized to these dimensions without changing physical jig geometry. The insert stays anchored to the image's left and bottom edges (extra canvas area is added at the top and right), so all flap positions keep their calibrated placement. Omit to use the jig section's `printable_size_x/y_mm` (default 333 × 88 mm, matches eufyMake **Zero Point** alignment mode). See note below on eufyMake alignment modes. |
| `registration_marks` | bool | `false` | Draw 5 mm L-shaped registration marks in the 4 corners of the output image to aid alignment debugging. The bottom-right mark is rendered green to indicate the eufyMake Zero-Point origin; the other three are white. |
| `registration_mark_line_width_mm` | float | `1.0` | Line width (mm) of the registration mark arms. Marks thinner than ~0.5 mm tend not to print reliably on the eufyMake. |
| `calibration_offset_mm` | `[dx, dy]` | `[0, 0]` | Global mat-calibration offset (mm) applied to every drawn element in the final output image (flap art, ink-save mask, labels, and registration marks all shift together). Use this to compensate for a systematic offset between the printer's zero-point and the physical jig (e.g. eufyMake Zero-Point calibration being off by a couple of mm). Positive `dx` shifts content toward +X (along the long axis, away from the zero point); positive `dy` shifts toward +Y (downward in the image). Content shifted past the image edge is clipped. |

> **eufyMake alignment modes & canvas size.** The eufyMake Studio app has two
> alignment modes with *different* working canvas sizes:
>
> | Mode | Canvas size | Origin reference |
> |------|-------------|------------------|
> | **Camera** | 335 × 90 mm | Camera-detected mat position |
> | **Zero Point** | 333 × 88 mm | Mat zero-point (lower-right corner of imported image) |
>
> The jig `printable_size_*` constants (333 × 88) match **Zero Point**
> mode exactly, so the default (no `canvas_size_mm` override) is correct when
> using the alignment jig in Zero Point mode. Importing a 335 × 90 image into
> Zero Point mode will appear ≈2 mm offset because the origin reference doesn't
> match the image canvas. If you intend to use Camera mode, set
> `canvas_size_mm: [335, 90]`.

### `preview` — Module preview contact sheet

Optional section. When `enabled` is `true`, a contact-sheet PNG is written
to the same output directory as the print images (e.g. `output/preview.png`).
Each cell shows one flap slot rendered as it would appear on the physical
display: two flap halves separated by the real gap, with the physical flap
shape drawn in `flap_color` and the artwork alpha-composited on top.

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `enabled` | bool | `false` | Generate the preview image |
| `columns` | int | `12` | Number of cells per row in the grid |
| `cell_padding_mm` | float | `3.0` | Gap between cells and around the grid border (mm) |
| `flap_color` | `[R, G, B]` | `[20, 20, 20]` | Physical flap stock colour |
| `background_color` | `[R, G, B]` | `[245, 245, 245]` | Overall canvas background colour |
| `label_color` | `[R, G, B]` | `[60, 60, 60]` | Label text colour |
| `label_font_size_pt` | int | `7` | Label font size in points |
| `dpi` | int | `96` | Preview image resolution (screen DPI, independent of print DPI) |
| `filename` | string | `"preview.png"` | Output filename (written into the root output directory) |

The label below each cell shows both the `label` field and the `slot` index
(e.g. `PVV42 · #0`). Multi-module flaps show one cell per module with the
module index appended (e.g. `EP47 M5 · #2`).

Example minimal config to add to any job:

```json
"preview": {
  "enabled": true,
  "columns": 12
}
```

### `global_transforms` — Default image transforms

Applied to all input images unless overridden per-flap.

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `scale` | [float, float] | `[1.0, 1.0]` | Scale multiplier `[sx, sy]` applied after crop |
| `crop_percent` | [L, T, R, B] | `null` | Percentage to trim from each edge: `[left%, top%, right%, bottom%]` |
| `fit_mode` | string | `"fit"` | How images are fit to the target flap area (see [Fit Modes](#fit-modes)) |
| `notch_mode` | string or `[left, right]` | `"none"` | Notch-clearance modifier (see [Notch Modes](#notch-modes)) |

### `custom_flaps` — Flap definitions

An array of objects, one per custom flap. Required fields: `slot`, `source`.

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `slot` | int | *required* | 0-based index in the custom flap sequence |
| `label` | string | `"EP{slot+42}"` | Display label (e.g. `"EP42"`) |
| `source` | string | *required* (except `blank`, `glyph`, `emoji`, `epilogue`) | Image path (PNG/JPEG/SVG), relative to the JSON config file's directory |
| `type` | string | `"single"` | `"single"`, `"multi-module"`, `"blank"`, `"glyph"`, `"emoji"`, or `"epilogue"` (see [Custom Flap Types](#custom-flap-types)) |
| `module_range` | [int, int] | `null` | Required for `multi-module`: inclusive range `[start, end]` |
| `index` | int | `null` | Required for `epilogue` if `char` is not given; 0-based index into the standard 52-flap character set |
| `char` | string | `null` | Required for `epilogue` if `index` is not given; single character from the standard 52-flap set |
| `scale` | [float, float] | `null` | Per-image scale override `[sx, sy]`; `null` = use global |
| `crop` | [L, T, R, B] | `null` | Per-image crop override `[left%, top%, right%, bottom%]`; `null` = use global |
| `fit_mode` | string | `null` | Per-image fit mode override; `null` = use global default |
| `notch_mode` | string or `[left, right]` | `null` | Per-image notch-clearance override; `null` = use global default |
| `offset_mm` | `[dx, dy]` | `null` | Shift image content by `[dx_mm, dy_mm]` within the pocket, applied after all fit/notch transforms and before the ink-save mask. Positive X shifts right, positive Y shifts down. Content pushed past the pocket edge is clipped by the ink-save mask. Useful for fine-tuning the position of an image within its flap without recompositing the source artwork. |
| `bleed` | bool | `true` | When `false`, skips bleed edge-expansion for this image (the ink-save mask still applies). Useful for images with transparent backgrounds at their edges that don't need the misalignment buffer. |
| `enabled` | bool | `true` | When `false`, output for this flap is fully transparent; the slot position is preserved in the layout. Useful for temporarily disabling a slot without removing it from the config. |

---

## Image Offset (`offset_mm`)

The per-flap `offset_mm: [dx_mm, dy_mm]` field shifts the fitted image content
within the pocket after all fit, notch, and bleed transformations have been
applied, but before the ink-save mask clips the result.

```json
{"slot": 3, "type": "emoji", "name": "heart", "offset_mm": [0, -2.5]}
```

**Coordinate system** (matches the print output image):
- **Positive X** → shifts content **right**
- **Negative X** → shifts content **left**
- **Positive Y** → shifts content **down**
- **Negative Y** → shifts content **up**

The offset is applied to the full display image (both halves together) before
the top/bottom split. This means a vertical offset moves the character up or
down relative to the gap line — e.g. `[0, -3]` raises the whole character 3 mm,
so more of the top half's area has content and the bottom half loses content
at its lower edge.

Content pushed outside the `pocket + bleed_mm` boundary is clipped by the
ink-save mask, same as bleed overflow. The preview image shows the offset
applied, so what you see in `preview.png` matches the final printed flap.

**Contrast with `calibration_offset_mm`** (in the `output` section):
that field shifts the *entire output canvas* — flap art, ink-save mask, labels,
and registration marks all move together — to compensate for a systematic
printer-vs-jig registration error. `offset_mm` moves only the artwork for one
specific flap entry, leaving all other flaps and the mask shape unchanged.

**When to use it:** fine-tuning image placement within a pocket when the
source artwork has uneven whitespace, or when an emoji's visual centre of mass
reads as off-centre after fitting. Prefer adjusting source artwork instead when
doing so is straightforward.

---

## Fit Modes

Controls how each input image is mapped to the target flap area
(54 × 88 mm for single-module images). Set globally in `global_transforms.fit_mode`
and/or per-image via `fit_mode` on individual `custom_flaps` entries.

| Mode | Behavior |
|------|----------|
| **`fit`** (default) | Uniform scale to fit *within* target. Transparent letterbox padding, centered. Aspect ratio preserved; no cropping. |
| **`fill`** | Uniform scale to *cover* the entire target. Center-crop any overflow. Aspect ratio preserved; edges may be lost. |
| **`stretch`** | Non-uniform resize to exact target dimensions. May distort if aspect ratio differs from 54:88. |
| **`contain`** | No scaling at all. Image is centered on the target canvas as-is. Useful for pre-sized artwork at the correct DPI. |

**Recommended workflow:** Start with `"fit"` (default) to see how your artwork
maps onto the flaps. Switch to `"fill"` if you prefer edge-to-edge coverage
and don't mind losing some border. Use `"stretch"` only if the image is already
at the correct aspect ratio and you want pixel-exact mapping.

---

## Notch Modes

Flaps have a notch cutout (default depth `3.2 mm`) on each side at the spool
pin location. If an image fills the full `54 mm` width, the edges of the image
will be hidden behind the notch walls. `notch_mode` controls how the image is
adjusted to account for this.

Set globally in `global_transforms.notch_mode` and/or per-image via `notch_mode`
on individual `custom_flaps` entries. The effective safe width is
`flap_width - 2 × notch_depth` (default: 54 - 2×3.2 = **47.6 mm**).

### Symmetric (string) form

A plain string applies the same mode to both sides:

| Mode | Behavior |
|------|-----------|
| **`"none"`** (default) | No adjustment. Image fills the full 54 mm canvas. Use for text/character glyphs that already stay clear of the notch zone. |
| **`"inset"`** | Image is fit into the **safe-width** canvas (47.6 mm), then centered on the full 54 mm canvas with transparent bands at the sides. Best for emoji/icons where you want the full image visible. |
| **`"squeeze"`** | Image is fit to the full 54 mm canvas as normal, then **non-uniformly scaled** to the safe width. Height is unchanged; the image is slightly narrower. Best when you want edge-to-edge coverage and a small aspect-ratio change is acceptable. |

### Per-side (list) form

Pass a two-element list `[left_mode, right_mode]` to control each notch independently.
Each element is one of `"none"`, `"inset"`, or `"squeeze"`.

```json
// Both sides — equivalent to the string form above:
{"notch_mode": "inset"}
{"notch_mode": ["inset", "inset"]}

// Left side only (right notch is unobstructed):
{"notch_mode": ["inset", "none"]}

// Right side only:
{"notch_mode": ["none", "squeeze"]}

// Different depths on each side — squeeze wins for the fitting step:
{"notch_mode": ["inset", "squeeze"]}
```

When sides have different modes, **`"squeeze"` takes precedence** for the
image-fitting step: the image is always fit to full width first and then
scaled to the content area, regardless of which side requested it.

The `left_inset` and `right_inset` gaps are computed independently:

| JSON value | Content width | `paste_x` |
|---|---|---|
| `"inset"` / `["inset","inset"]` | 47.6 mm | 3.2 mm (centered) |
| `["inset", "none"]` | 50.8 mm | 3.2 mm (left gap only) |
| `["none", "inset"]` | 50.8 mm | 0 mm (right gap only) |
| `["squeeze","none"]` | 50.8 mm | 3.2 mm |

**Choosing a mode:** Use `"inset"` for icons and emoji — content is untouched
but the sides will not be visible past the notch. Use `"squeeze"` when the
slight horizontal compression is preferable to visible letterbox bands.
Use the list form when an image only approaches one notch.

---

## Image Pipeline

The full transformation chain from input image to output print file:

1. **Load** — Source image opened as RGBA (any pixel size)
2. **Crop** — Per-image `crop` or fallback to `global_transforms.crop_percent`
3. **Scale** — Per-image `scale` or fallback to `global_transforms.scale`
4. **Fit + Notch** — Image fit to target dimensions using `fit_mode`; then
   `notch_mode` adjusts the result to clear the spool-pin notch cutouts
   - Single: target = `flap_width` × `display_height` (54 × 88 mm)
   - Multi-module: target = full span width × `display_height`
5. **Slice** — Split into top half (43mm) and bottom half (43mm); 2mm gap discarded
6. **Map to flap sides** — Front of flap K = top(K), back of flap K = bottom(K+1)
7. **Batch** — Group into jig-sized batches (6 flaps per batch)
8. **Layout** — Place on printable-area canvas (88 × 330mm) with insert
   offset. Images that have been bleed-expanded in step 4 are pasted offset
   by their bleed amount so the pocket area aligns with its grid position
   and the overflow extends into the bleed zone (see
   [Bleed Margin](#bleed-margin) below).
9. **Flip** — Back-side flaps reordered to their post-jig-flip grid positions
   (individual flap content is **not** mirrored)
10. **Mask** — Ink-save mask zeros alpha outside flap pockets (+ bleed)
11. **Labels** — EP labels rendered in gap margins
12. **Save** — PNG with embedded DPI metadata
13. **Preview** — If `preview.enabled`, a contact-sheet grid is written to the
    root output directory at `preview.dpi` (default 96 DPI, independent of
    print DPI).

### Input Images

Each input represents a **full display character** as a viewer would see it:

```
┌──────────────┐
│  top half    │ ← 43mm (flap_height)
│              │
├──────────────┤ ← 2mm gap (discarded)
│  bottom half │ ← 43mm (flap_height)
│              │
└──────────────┘
     54mm
    (flap_width)
```

Total height = 2 × 43 + 2 = 88mm. Any pixel dimensions are accepted; the
image is fit to the physical target size using the active `fit_mode`.

### Flap Side Mapping

- **Flap K front** = top half of image K
- **Flap K back** = bottom half of image K+1
- **Last flap back** = blank (transparent)

### Custom Flap Types

- **`single`**: One image per flap. Same output for all modules. Source may
  be a raster (PNG/JPEG) or an `.svg` file (see [SVG Inputs](#svg-inputs)).
- **`multi-module`**: Image spans multiple modules (e.g., triptych).
  Requires `module_range: [start, end]` (inclusive). The tool extracts
  the correct column for each module automatically. Raster or SVG.
- **`blank`**: Fully transparent top/bottom halves. No source required.
- **`glyph`**: Resolves to a pre-rendered per-character SVG from
  `assets/flap_glyphs/<font>/`. Specify the font with `font` (default
  `"Epilogue"`), and the character via either `char` or `index` (0–51).
  No `source` field needed. Example:

  ```json
  {"slot": 0, "type": "glyph", "font": "Epilogue", "char": "H"},
  {"slot": 1, "type": "glyph", "font": "Roboto",   "char": "H"}
  ```

  Assets must exist under `assets/flap_glyphs/<font>/` — run the
  [glyph generator](#glyph-generator-generate_epilogue_flap_svgspy) first
  for any font other than Epilogue (which ships pre-rendered). The SVG
  files can be hand-edited (e.g. to change fill color) after generation.
- **`epilogue`**: Backward-compatible alias for `{"type": "glyph", "font": "Epilogue"}`.
  The `font` field is ignored; Epilogue is always used. Existing job files
  using `"type": "epilogue"` continue to work without changes.

  The bundled Epilogue assets are pre-rendered with a **white** (`#ffffff`)
  fill for dark flap stock. Re-run the generator with `--fill-color` to
  change the color — see
  [Glyph generator](#glyph-generator-generate_epilogue_flap_svgspy).
- **`emoji`**: Resolves to a Twemoji SVG from `assets/emoji/`. Download SVGs
  first with `pvv_tools/download_emoji.py`, then optionally hand-edit the SVG
  (colors, stroke weights) before committing. Specify the emoji with `name`
  (the filename stem) or `char` (auto-resolved to CLDR name at load time).
  Example:

  ```json
  {"slot": 3, "type": "emoji", "name": "waving-hand-medium-skin-tone"},
  {"slot": 4, "type": "emoji", "char": "❤️"}
  ```

  Source: Twemoji (Twitter/X), CC-BY 4.0 — covers Unicode 14.0 / ~3,600 emoji.
  See [Emoji downloader](#emoji-downloader-download_emojipypy).

### SVG Inputs

Any `single` or `multi-module` source whose path ends in `.svg` is
rasterized via `resvg-py` before entering the image pipeline.  SVGs are
treated identically to raster inputs once loaded:

- The SVG's full viewBox is interpreted as the full display face
  (`flap_width` x `display_height` for `single`; full span width x
  `display_height` for `multi-module`).
- Rasterization uses 2x supersampling by default for clean edges, then
  is resampled down by the standard `fit_mode` pipeline.
- Unit-bearing SVGs (`width="54mm"` etc.) are supported; resvg honours
  the embedded units.

### Bleed Margin

The `bleed_mm` setting (default `1.0`) controls two related but distinct
behaviors:

#### A — Ink-save mask expansion

The ink-save mask (step 10) always clips alpha to the flap outline
expanded outward by `bleed_mm` on all sides. This prevents ink from being
wasted on the jig body, with a small buffer around the cut line.

#### B — Per-edge image content expansion (misalignment tolerance)

The 3D-printed jig introduces small mechanical tolerances. If an image that
is supposed to fill to the flap edge stops exactly at the pocket boundary,
even a 0.5 mm mis-cut could expose a thin strip of bare flap stock.

To prevent this, the fit target is expanded outward by `bleed_mm` on **flush
edges** — edges where the image content is supposed to fill all the way to the
boundary. The image is then fit to the expanded target and naturally overflows
the pocket by `bleed_mm` on those sides. Non-flush edges (where the image has
letterbox bars or transparent padding) are **not** expanded, since bare stock
was always expected there.

```
flush edge (fill / width-constrained fit):

         bleed
       ◄───────►
  ┌───────────────────────┐
  │  ╔═════════════════╗  │  ← pocket boundary
  │  ║ image overflows ║  │
  │  ╚═════════════════╝  │  ← bleed content extends beyond pocket
  └───────────────────────┘
    ▲ ink-save mask clips here

non-flush edge (fit with letterbox bars on that axis): no expansion
```

**Flush-edge rules by fit mode:**

| Fit mode | flush x (left/right) | flush y (top/bottom) |
|----------|----------------------|----------------------|
| `fill` | always (unless `notch_mode=inset`) | always |
| `fit` — image wider than pocket ratio | yes | no (bars top/bottom) |
| `fit` — image taller than pocket ratio | no (bars left/right) | yes |
| `stretch` | always | always |
| `contain` | never | never |

Notch modes affect x-flush: with `notch_mode=inset`, the notch sides are
transparent clearance zones and are never treated as flush. With
`notch_mode=none` or `squeeze`, the x-flush determination follows the
fit-mode rule above.

To disable bleed expansion for a specific image (e.g., an emoji on a
transparent background that doesn't need the buffer), set `"bleed": false`
on that `custom_flaps` entry. The ink-save mask (behavior A) still applies.

At 508 DPI with 1 mm bleed, the expansion is ~20 px per flush edge
(≈ 3.7 % on a 54 mm-wide pocket, ≈ 4.7 % on a 43 mm-tall half).

---

## Dimensions

Physical dimensions are resolved using a three-tier chain:

1. **OpenSCAD echo** — Runs `PVV_splitflap_mods.scad` (which includes
   `flap_dimensions.scad`) and parses tagged `FLAP_PRINTER:` echo output.
   This is the authoritative source for **flap physical dimensions**. Results are cached in
   `.flap_printer_dims.json` next to the `.scad` file (mtime-based invalidation).
2. **Job config `jig` section** — Jig and mat parameters come directly from the
   `jig` section of the job JSON (see above). These are no longer read from SCAD.
3. **Hardcoded defaults** — Last-resort values baked into `dimensions.py`.

### `dimensions` — Optional flap dimension overrides

Useful when OpenSCAD is not installed. Jig/mat parameters belong in the `jig` section, not here.

| Key | Type | SCAD Variable | Default |
|-----|------|---------------|---------|
| `flap_width` | float | `flap_width` | `54.0` |
| `flap_height` | float | `flap_height` | `43.0` |
| `flap_gap` | float | `flap_gap` | `2.0` |
| `flap_corner_radius` | float | `flap_corner_radius` | `3.1` |
| `flap_notch_height` | float | `flap_notch_height` | `15.0` |
| `flap_notch_depth` | float | `flap_notch_depth` | `3.2` |
| `flap_pin_width` | float | `flap_pin_width` | `1.4` |

All fields are optional. Omit the entire section to rely solely on OpenSCAD + hardcoded defaults.

### Reference Values

| Parameter | Value |
|-----------|-------|
| Flap size | 54 × 43 mm |
| Flap gap | 2.0 mm |
| Display char height | 88.0 mm |
| Printable area (minibed) | 333 × 88 mm |
| Jig insert | 300 × 66 mm (centered in printable area) |
| Insert offset | 16.5 × 11 mm |
| Flaps per batch | 6 (6 cols × 1 row) |
| Default DPI | 360 |

## Output

```
output/
├── common/           # For single-type flaps (same for all modules)
│   ├── batch_01_front.png
│   ├── batch_01_back.png
│   ├── batch_02_front.png
│   ├── batch_02_back.png
│   ├── batch_03_front.png
│   └── batch_03_back.png
└── module_10/        # For multi-module flaps (per-module slices)
    ├── batch_01_front.png
    └── batch_01_back.png
```

Output images are sized to the full printable area (333 × 88 mm, in the same
printer orientation as the jig) with the jig insert content centered at the
computed offset, surrounded by transparent pixels. This enables **Zero Point
Alignment** in eufymake studio.

PNGs include DPI metadata so image editors show correct physical size.

## Dependencies

- **Pillow** ≥ 10.0 (MIT-like license)
- **resvg-py** ≥ 0.3 (MPL-2.0) — used to rasterize SVG sources

---

## Details

Programmer-facing notes on internals.  Read this if you intend to modify
the pipeline; the sections above are sufficient for ordinary use.

### Package layout

```
pvv_tools/
  flap_printer/         # Main package; entry point is __main__.py
    cli.py              # Argparse + top-level orchestration
    config.py           # JSON loader + dataclasses + validation
    dimensions.py       # FlapDimensions / JigDimensions / DisplayDimensions
    scad_parser.py      # OpenSCAD subprocess + echo-output parsing + cache
    svg_loader.py       # is_svg() + load_svg() (resvg-py wrapper)
    slicer.py           # apply_transforms, fit_to_target, fit_with_notch_mode,
                        # slice_display_image, extract_module_column
    layout.py           # FlapSide, batch grouping, jig flip, ink-save mask
    labels.py           # EP label rendering
    previewer.py        # contact-sheet preview grid generator
    renderer.py         # Pipeline orchestrator (load -> slice -> layout -> save -> preview)
  scad/
    epilogue_flap_single.scad   # SCAD wrapper used by the glyph generator
  assets/
    flap_glyphs/
      Epilogue/                 # Pre-rendered flap_NN.svg + index.json
      <OtherFont>/              # Generated on demand, committed after review
    emoji/                      # Downloaded Twemoji SVGs, hand-editable
  generate_epilogue_flap_svgs.py  # CLI that generates assets/flap_glyphs/<font>/
  download_emoji.py               # CLI that downloads assets/emoji/<name>.svg
  example_job.json
```

### Pipeline walkthrough (raster + SVG)

1. **Config load** (`config.load_config`) parses JSON, resolves `source`
   paths relative to the config file's directory, validates `fit_mode` /
   `flip_mode`, and expands `epilogue` shorthand into `single` + an
   absolute path under `assets/flap_glyphs/<font>/`.
2. **Dimension resolution** (`dimensions.AllDimensions.resolve`) tries
   OpenSCAD first (via `scad_parser.run_openscad`, which spawns OpenSCAD
   with `PVV_splitflap_mods.scad`, parses `FLAP_PRINTER: key=value` echoes,
   and caches to `.flap_printer_dims.json` keyed by SCAD mtime), then
   falls back to `dimensions` overrides in the config, then hardcoded
   defaults.
3. **Per-module flap resolution** (`renderer._resolve_flaps_for_module`)
   iterates `custom_flaps` and, for each entry:
   1. Calls `_load_source_image(flap_cfg, target_h)` which dispatches on
      file extension: SVG -> `svg_loader.load_svg`, otherwise PIL `open`.
   2. Applies per-image or global `scale` / `crop` (`slicer.apply_transforms`).
   3. Fits to the display-face target via `slicer.fit_with_notch_mode` (which
      calls `slicer.fit_to_target` internally).  When `bleed_mm > 0` and
      `bleed: true` for the flap, the target rect is expanded outward by
      `bleed_mm` on flush edges before fitting, so the returned image
      overflows the pocket on those sides with real content.
   4. Slices into top/bottom halves with `slicer.slice_display_image`
      (top `flap_height` mm + any top bleed, skip `flap_gap` mm, then
      `flap_height` mm + any bottom bleed).
   5. For `multi-module`, the full multi-flap image is fit to the
      combined span first (`module_pitch * num_span - inter_module_gap`),
      then `slicer.extract_module_column` cuts out this module's column,
      which is then re-fit to a single flap before slicing.
4. **Flap-side mapping** (`layout.map_images_to_flap_sides`): Flap K's
   front is `top(K)`, its back is `bottom(K+1)`; the last back is blank.
5. **Batch grouping** + **layout** (`layout.generate_batch_image`):
   slots are grouped into jig-sized batches (`jig_num_x * jig_num_y`).
   Each slot's upright flap image is rotated 90° CCW (pockets sit rotated
   in the jig: top edge → left, spool edge → right) and pasted onto a
   transparent `printable_width x printable_height` canvas.  The paste
   position is offset by the image's bleed amount (derived from
   `image.size` vs pocket size) so the pocket area aligns with its grid
   coordinates and bleed content extends beyond. Front batches offset
   leftward (outer display edge), back batches offset rightward.
6. **Jig flip** (`layout.reorder_for_jig_flip`):
   When the operator flips the laser-cut jig (left-right or front-back)
   to print the back side, the flaps remain physically in place but their
   grid coordinates change. This step reorders only the *grid mapping*
   (no per-image mirroring) so the back-side composite aligns with the
   flipped jig.
7. **Ink-save mask** (`layout.apply_ink_save_mask`): zeros alpha
   everywhere outside `pocket + bleed_mm` to avoid printing on the jig.
8. **Labels** (`labels.render_labels`): EP labels in the gap rows.
9. **Save**: PNG with embedded DPI metadata (`info['dpi']`) so editors
   show physical mm.

### SVG loader (`svg_loader.py`)

Thin wrapper around `resvg_py.svg_to_bytes`:

- `is_svg(path)` is a `.svg` suffix check (case-insensitive).
- `load_svg(svg_path, target_height_px, supersample=2.0)` calls resvg with
  `svg_path=`, computes width preserving the SVG aspect ratio at
  `supersample * target_height_px`, and sets `dpi=96` (any non-zero value)
  so resvg correctly interprets real-world units like `width="54mm"`.
- Returns a PIL `Image` (RGBA).  The downstream pipeline owns all further
  resizing, so the supersampled raster only exists transiently.
- `resvg_py` is imported lazily so installs that never use SVG inputs do
  not pay the import cost.

### Glyph generator (`generate_epilogue_flap_svgs.py`)

This script renders `assets/flap_glyphs/<font>/flap_NN.svg` for any font
preset defined in `3d/flap_fonts.scad`. It is **not**
run by the flap_printer at runtime — the SVGs are committed to the repo.
Run it manually after editing the SCAD wrapper or switching fonts.

Basic usage:

```bash
# Epilogue (already committed; re-run to change fill color)
python pvv_tools/generate_epilogue_flap_svgs.py --font Epilogue

# Any other preset from 3d/flap_fonts.scad
python pvv_tools/generate_epilogue_flap_svgs.py --font Roboto
python pvv_tools/generate_epilogue_flap_svgs.py --font Bangers --fill-color "#000000"
```

Output is written to `pvv_tools/assets/flap_glyphs/<font>/`. After
reviewing the SVGs (and optionally hand-editing fill colors or adjusting
geometry), commit the directory to make it available to job configs via
`{"type": "glyph", "font": "<font>", ...}`.

### Emoji downloader (`download_emoji.py`)

Downloads a single Twemoji SVG for use as an `"emoji"` flap type.

```powershell
# Download by emoji character (name auto-derived from CLDR)
python pvv_tools/download_emoji.py "👋🏽"
# → assets/emoji/waving-hand-medium-skin-tone.svg

# Override the name
python pvv_tools/download_emoji.py "❤️" --name heart
# → assets/emoji/heart.svg
```

The script prints the job JSON snippet to use:
```
Job JSON (by name — explicit, edit-safe):
  {"type": "emoji", "name": "waving-hand-medium-skin-tone"}

Job JSON (by char — auto-resolves name at load time):
  {"type": "emoji", "char": "👋🏽"}
```

After downloading, open the SVG in any editor to adjust colors or style,
then commit `pvv_tools/assets/emoji/` to make it available to job configs.

Source: [Twemoji](https://github.com/twitter/twemoji) (Twitter/X), CC-BY 4.0.
Covers Unicode 14.0 / Emoji 14.0 (~3,600 emoji). Browse at
[twemoji-cheatsheet.vercel.app](https://twemoji-cheatsheet.vercel.app/) or
[emojipedia.org](https://emojipedia.org) (select the Twemoji style).

For each of the 52 characters it:

1. Adds Scott Bezek's `3d/scripts/` to `sys.path` and imports
   `projection_renderer.Renderer` and `svg_processor.SvgProcessor`.
2. Invokes the renderer on `pvv_tools/scad/epilogue_flap_single.scad`
   with `flap_index=N` (the character's index in the standard 52-flap
   list, mirroring `3d/flap_characters.scad`).
3. The SCAD wrapper calls `flap_with_letters(... flap=false ...)` twice
   — once for the front (top) letter at `flap_index` and once for the
   back (bottom) letter at `flap_index - 1`, translated and rotated 180°
   to sit below the top.  `flap=false` suppresses the flap outline, so
   only the letter geometry is exported.  The wrapper also `echo()`s
   `flap_width`, `flap_height`, `flap_gap`, `flap_pin_width`; the driver
   captures these via `openscad.extract_values`.
4. Post-processes the SVG (`_postprocess_svg`):
   - Overrides `viewBox` / `width` / `height` so the SVG covers exactly
     `flap_width x (2*flap_height + flap_gap)` mm — the canonical display
     face the flap_printer expects.
   - Applies `apply_laser_etch_style()` (`fill=#000000`, `stroke=none`)
     so the letters render as solid ink rather than thin cut outlines.
   - Overrides the `fill` attribute on every `<path>` with the value of
     `--fill-color` (default `#ffffff`).  This runs after
     `apply_laser_etch_style()` so the shared utility in
     `3d/scripts/svg_processor.py` is left untouched.  Pass
     `--fill-color "#000000"` to regenerate black-on-transparent assets
     for printing on light flap stock.
   - Calls `remove_redundant_lines()` to collapse duplicate coincident
     edges left over from the cut-style export.
5. Special-cases the space character (index 0): OpenSCAD produces no
   geometry, so the driver emits an empty SVG with the correct viewBox
   via `_write_empty_svg`.
6. Also writes `index.json` recording the font, character list, and
   `index_to_char` mapping for downstream tooling.

#### svg.path version pinning

Scott's `svg_processor.py` asserts `int(version('svg.path').split('.')[0]) == 6`.
Newer versions (7.x) break this assertion at import time, so the project
pins `svg.path==6.*` in `pvv_tools/requirements.txt`.

### Adding a new flap type

The minimal contract for a custom flap type is: at the end of
`config.load_config`, `flap.source_path` must point to a loadable raster
or SVG (or `flap.type == 'blank'` for transparency).  Anything more
elaborate — a generator that runs at config-load time, a procedural source,
etc. — should be added in `config.load_config` and lower itself to
`single` / `multi-module` semantics before validation continues.  This
keeps `renderer.py` unaware of higher-level flap types.

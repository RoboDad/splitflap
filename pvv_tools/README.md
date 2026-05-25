# Flap Printer — UV Print Layout Generator

Generates print-ready images for UV printing custom splitflap flaps on a
Eufy E1 printer, using a laser-cut flap jig.

## Quick Start

All commands must be run from the **repo root** directory
(`splitflap/`), because Python needs to find the `pvv_tools/` package.

```bash
cd c:\Users\phgev\Documents\Make\Splitflap\Firmware\splitflap

# Install dependencies (once)
pip install -r requirements.txt

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

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `type` | string | `"minibed"` | Jig type (currently only `"minibed"` supported) |
| `flip_mode` | string | `"left-right"` | How back images are flipped: `"left-right"` (mirror horizontal) or `"front-back"` |
| `output_orientation` | string | `"landscape"` | Output image orientation: `"landscape"` or `"portrait"` |

### `output` — Output file settings

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `dpi` | int | `360` | Output resolution in dots per inch |
| `format` | string | `"png"` | Output image format |
| `bleed_mm` | float | `1.0` | Ink-save mask bleed beyond flap pocket edges (mm) |
| `ink_save_mask` | bool | `true` | Zero alpha outside flap pockets to save ink |
| `labels` | bool | `true` | Render EP slot labels in the gap areas |
| `label_font_size_pt` | int | `6` | Label font size in points |
| `output_dir` | string | `"output"` | Output directory (relative to CWD) |

### `global_transforms` — Default image transforms

Applied to all input images unless overridden per-flap.

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `scale` | [float, float] | `[1.0, 1.0]` | Scale multiplier `[sx, sy]` applied after crop |
| `crop_percent` | [L, T, R, B] | `null` | Percentage to trim from each edge: `[left%, top%, right%, bottom%]` |
| `fit_mode` | string | `"fit"` | How images are fit to the target flap area (see [Fit Modes](#fit-modes)) |

### `custom_flaps` — Flap definitions

An array of objects, one per custom flap. Required fields: `slot`, `source`.

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `slot` | int | *required* | 0-based index in the custom flap sequence |
| `label` | string | `"EP{slot+42}"` | Display label (e.g. `"EP42"`) |
| `source` | string | *required* | Image path, relative to the JSON config file's directory |
| `type` | string | `"single"` | `"single"` (one module) or `"multi-module"` (spans multiple) |
| `module_range` | [int, int] | `null` | Required for `multi-module`: inclusive range `[start, end]` |
| `scale` | [float, float] | `null` | Per-image scale override `[sx, sy]`; `null` = use global |
| `crop` | [L, T, R, B] | `null` | Per-image crop override `[left%, top%, right%, bottom%]`; `null` = use global |
| `fit_mode` | string | `null` | Per-image fit mode override; `null` = use global default |

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

## Image Pipeline

The full transformation chain from input image to output print file:

1. **Load** — Source image opened as RGBA (any pixel size)
2. **Crop** — Per-image `crop` or fallback to `global_transforms.crop_percent`
3. **Scale** — Per-image `scale` or fallback to `global_transforms.scale`
4. **Fit** — Image fit to target dimensions using the selected `fit_mode`
   - Single: target = `flap_width` × `display_height` (54 × 88 mm)
   - Multi-module: target = full span width × `display_height`
5. **Slice** — Split into top half (43mm) and bottom half (43mm); 2mm gap discarded
6. **Map to flap sides** — Front of flap K = top(K), back of flap K = bottom(K+1)
7. **Batch** — Group into jig-sized batches (6 flaps per batch)
8. **Layout + Bleed Expansion** — Place on printable-area canvas (88 × 330mm)
   with insert offset.  Each flap image is upscaled by 2 × `bleed_mm` in each
   dimension and pasted centred on its pocket position so that the bleed zone
   contains real image content rather than transparency (see
   [Bleed Margin](#bleed-margin) below).
9. **Flip** — Back-side flaps reordered to their post-jig-flip grid positions
   (individual flap content is **not** mirrored)
10. **Mask** — Ink-save mask zeros alpha outside flap pockets (+ bleed)
11. **Labels** — EP labels rendered in gap margins
12. **Save** — PNG with embedded DPI metadata

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

- **`single`**: One image per flap. Same output for all modules.
- **`multi-module`**: Image spans multiple modules (e.g., triptych).
  Requires `module_range: [start, end]` (inclusive). The tool extracts
  the correct column for each module automatically.

### Bleed Margin

The `bleed_mm` setting (default `1.0`) controls a border of extra image
content around each flap pocket.  It serves two purposes:

1. **Ink saving** — The ink-save mask (step 10) zeros alpha outside of
   `pocket + bleed`, so no ink is wasted on areas that will never be
   visible on the finished flap.
2. **Misalignment tolerance** — The 3D-printed jig introduces small
   mechanical tolerances. If the flap image ended exactly at the pocket
   edge, any sub-mm shift would expose bare flap stock alongside the
   image. The bleed expansion fills this border with real image content.

How it works:

```
          bleed
        ◄───────►
   ┌─────────────────────┐
   │ ╔═════════════════╗ │  ← pocket boundary
   │ ║                 ║ │
   │ ║   flap image    ║ │  ← image upscaled to pocket + 2×bleed
   │ ║                 ║ │
   │ ╚═════════════════╝ │
   └─────────────────────┘
     ▲ ink-save mask clips here (pocket + bleed)
```

At 360 DPI with a 1 mm bleed, each flap image is enlarged by ~28 px per
side (≈ 3.7 % upscale on a 766 px-wide pocket). This is visually
imperceptible but ensures the bleed zone is always filled.

---

## Dimensions

Physical dimensions are resolved using a three-tier chain:

1. **OpenSCAD echo** — Runs `PVV_splitflap_mods.scad` (which includes
   `flap_dimensions.scad`) and parses tagged `FLAP_PRINTER:` echo output.
   This is the authoritative source. Results are cached in
   `.flap_printer_dims.json` next to the `.scad` file (mtime-based invalidation).
2. **Job config overrides** — Optional `dimensions` section in the JSON config
   (see below). Useful when OpenSCAD is not installed.
3. **Hardcoded defaults** — Last-resort values baked into `dimensions.py`.

### `dimensions` — Optional dimension overrides

| Key | Type | SCAD Variable | Default |
|-----|------|---------------|---------|
| `flap_width` | float | `flap_width` | `54.0` |
| `flap_height` | float | `flap_height` | `43.0` |
| `flap_gap` | float | `flap_gap` | `2.0` |
| `flap_corner_radius` | float | `flap_corner_radius` | `3.1` |
| `flap_notch_height` | float | `flap_notch_height_default` | `15.0` |
| `flap_notch_depth` | float | `flap_notch_depth` | `3.2` |
| `flap_pin_width` | float | `flap_pin_width` | `1.4` |
| `jig_num_x` | int | `minibed_flap_jig_num_flaps_x` | `1` |
| `jig_num_y` | int | `minibed_flap_jig_num_flaps_y` | `6` |
| `jig_gap_x` | float | `minibed_flap_jig_gap_x` | `6.0` |
| `jig_gap_y` | float | `minibed_flap_jig_gap_y` | `6.0` |
| `jig_margin_x` | float | `minibed_flap_jig_margin_x` | `6.0` |
| `jig_margin_y` | float | `minibed_flap_jig_margin_y` | `6.0` |
| `printable_width` | float | `minibed_printable_size_x` | `88.0` |
| `printable_height` | float | `minibed_printable_size_y` | `333.0` |

All fields are optional. Omit the entire section to rely solely on OpenSCAD + hardcoded defaults.

### Reference Values

| Parameter | Value |
|-----------|-------|
| Flap size | 54 × 43 mm |
| Flap gap | 2.0 mm |
| Display char height | 88.0 mm |
| Printable area (minibed) | 88 × 333 mm |
| Jig insert | 66 × 300 mm (centered in printable area) |
| Insert offset | 11 × 16.5 mm |
| Flaps per batch | 6 (1 col × 6 rows) |
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

Output images are sized to the full printable area (330 × 88 mm in landscape)
with the jig insert content centered at the computed offset, surrounded by
transparent pixels. This enables **Zero Point Alignment** in eufymake studio.

PNGs include DPI metadata so image editors show correct physical size.

## Dependencies

- **Pillow** ≥ 10.0 (MIT-like license)

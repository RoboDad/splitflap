# Plan: Flap Printer — UV Print Layout Generator for Custom Splitflap Flaps

## TL;DR
Build a Python CLI tool (`pvv_tools/flap_printer/`) that takes custom display images, slices them into flap top/bottom halves, and produces correctly-laid-out print images (front + back) for the Eufy E1 UV printer jig. Supports multi-module triptychs, configurable DPI/jig dimensions, ink-saving masks, and EP labels. Config via JSON job file. Designed for future GUI extension.

## Context & Key Dimensions

### Flap System
- Standard: 52 flaps per module, characters: ` ABCDEFGHIJKLMNOPQRSTUVWXYZg0123456789r.?-$'#yp,!@&w`
- Custom: 64 flaps (50 standard + 14 custom replacing EP42/EP43 which carry `$`)
- flap_width = 54mm, flap_height = 43mm, flap_gap = 2.4mm
- Full display character height = 43 + 43 + 2.4 = 88.4mm
- Mapping: flap K front = top half of character K, flap K back = bottom half of character K+1
- Inter-module gap = 10mm, module pitch = 64mm

### Eufy Minibed Jig (from PVV_splitflap_mods.scad)
- Insert: 66mm × 300mm (1 flap wide × 6 tall)
- Flap pockets: 54mm × 43mm, gaps: 6mm, margins: 6mm
- Output image rotated 90° → 300mm wide × 66mm tall (landscape)

### Decisions
- Config format: JSON job file
- Default DPI: 360 (E1 standard sufficient for proofing, 720/1440 available)
- Flip mode: left-to-right default (option for front-to-back)
- Input images: full display characters (tool splits top/bottom)
- Multi-module: config describes full display, output is per-module per-batch
- Parameter sharing: Python regex-parses .scad files directly
- Labels: configurable per flap in job file (EP naming)
- Bleed: 1mm default for ink-saving mask
- Output format: PNG (alpha transparency)
- License: all deps must be permissive (PIL/Pillow = MIT-like)

---

## Steps

### Phase 1 — Project Scaffolding

**1.1** Create directory structure:
```
pvv_tools/
├── flap_printer/
│   ├── __init__.py
│   ├── cli.py            # CLI entry point (argparse)
│   ├── config.py         # JSON config schema + loader + validator
│   ├── scad_parser.py    # Regex parser for .scad variable assignments
│   ├── dimensions.py     # Flap/jig dimension constants loaded from .scad
│   ├── slicer.py         # Image splitting (top/bottom, multi-module column extraction)
│   ├── layout.py         # Batch grid layout (front/back, flip transform, mask)
│   ├── labels.py         # EP label rendering in margins
│   └── renderer.py       # Orchestrator: config → slicer → layout → output files
├── requirements.txt      # Pillow
├── example_job.json      # Annotated example config
└── README.md
```

**1.2** Single external dependency: `Pillow>=10.0` (MIT-like license)

### Phase 2 — Dimension Extraction (scad_parser.py, dimensions.py)

**2.1** `scad_parser.py`: regex parser for `.scad` files.
- Parse lines matching `^\s*(\w+)\s*=\s*(.+?)\s*;`
- Handle numeric literals (int/float), string literals, simple expressions referencing already-parsed variables
- Return dict of name→value
- Parse `flap_dimensions.scad` for: `flap_width`, `flap_height`, `flap_thickness`, `flap_corner_radius`, `flap_notch_height`, `flap_notch_depth`, `flap_pin_width`
- Parse `PVV_splitflap_mods.scad` for: `minibed_flap_jig_*` variables, `flap_gap`, `num_flaps`

**2.2** `dimensions.py`: dataclass holding all resolved dimensions.
- `FlapDimensions`: width, height, gap, corner_radius, notch_height, notch_depth, pin_width, display_height (= height*2 + gap)
- `JigDimensions`: num_x, num_y, gap_x, gap_y, margin_x, margin_y, insert_width, insert_height
- `DisplayDimensions`: module_pitch (64mm), inter_module_gap (10mm), module_width (54mm)
- Factory method that loads from .scad file paths with fallback defaults

### Phase 3 — Config Schema (config.py)

**3.1** JSON job file schema:
```json
{
  "display": {
    "num_modules": 48,
    "module_pitch_mm": 64,
    "inter_module_gap_mm": 10
  },
  "jig": {
    "type": "minibed",
    "flip_mode": "left-right",
    "output_orientation": "landscape"
  },
  "output": {
    "dpi": 360,
    "format": "png",
    "bleed_mm": 1.0,
    "ink_save_mask": true,
    "labels": true,
    "label_font_size_pt": 6,
    "output_dir": "output/"
  },
  "global_transforms": {
    "scale": [1.0, 1.0],
    "crop_percent": null
  },
  "custom_flaps": [
    {
      "slot": 0,
      "label": "EP42",
      "source": "images/sunset.png",
      "type": "single",
      "scale": null,
      "crop": null
    },
    {
      "slot": 3,
      "label": "EP45",
      "source": "images/triptych_cityscape.png",
      "type": "multi-module",
      "module_range": [10, 12],
      "scale": null,
      "crop": null
    }
  ]
}
```

**3.2** Loader + validator: parse JSON, validate required fields, resolve file paths relative to config file location, type-check, provide defaults.

### Phase 4 — Image Slicer (slicer.py)

**4.1** `slice_display_image(image, flap_dims) → (top_half, bottom_half)`:
- Input: RGBA image representing full display character (88.4mm tall)
- Split at midpoint accounting for flap_gap (2.4mm → remove center gap strip)
- Top half: upper 43mm portion → flap front content
- Bottom half: lower 43mm portion → flap back content (of preceding flap)
- All dimensions scaled by image DPI

**4.2** `extract_module_column(image, module_index, module_range, display_dims) → column_image`:
- For multi-module images: extract the column for a specific module
- Column width = 54mm, position = module_offset * 64mm from left edge
- Preserves the image content at that module position (no inter-module gap removal)

**4.3** `apply_transforms(image, scale, crop) → image`:
- Apply optional scale and crop transforms (from config or global)
- Scale: resize image by (sx, sy) factor
- Crop: percentage-based crop (left%, top%, right%, bottom%)

### Phase 5 — Batch Layout (layout.py)

**5.1** `FlapSide` dataclass: image (RGBA), label (str), slot_index (int), side ("front"/"back")

**5.2** `map_images_to_flap_sides(slot_images, labels) → list[FlapSide]`:
- For N custom slots: produces N front sides + N back sides
- Front of slot K = top half of image K
- Back of slot K = bottom half of image K+1
- Last slot back = blank (transparent)

**5.3** `generate_batch_image(flap_sides, jig_dims, dpi, orientation) → RGBA image`:
- Arrange up to 6 flap side images on the jig grid
- Jig grid: 1 wide × 6 tall (SCAD orientation), then rotate 90° for landscape output
- Each flap positioned at (margin + k * space, margin) with proper scale (mm → pixels at DPI)
- Background: transparent (alpha=0)

**5.4** `apply_flip_transform(front_image, flip_mode) → back_image_template`:
- "left-right": mirror entire image horizontally
- "front-back": mirror entire image vertically

**5.5** `apply_ink_save_mask(image, flap_shape, bleed_mm, dpi) → masked_image`:
- Flap shape: rounded rectangle with notch cutouts (from flap_dimensions.scad)
- Expand shape by `bleed_mm` (offset outward)
- Set alpha=0 outside the expanded flap shapes
- Saves ink on non-flap areas of the print

### Phase 6 — Label Rendering (labels.py)

**6.1** `render_labels(image, flap_sides, jig_dims, dpi, font_size_pt) → image`:
- Draw EP labels (e.g., "EP42", "EP43") in the margin areas between flaps
- Use Pillow's ImageDraw + built-in font (or bundled TTF if available)
- Labels positioned in the 6mm gap between flap pockets
- Labels are for debugging/identification only (outside flap area)

### Phase 7 — Renderer / Orchestrator (renderer.py)

**7.1** `render_job(config) → list[output_files]`:
- For each module in the display:
  - Resolve which custom slots have content for this module (single images + triptych slices)
  - Slice each resolved image → top/bottom halves
  - Map to flap front/back sides
  - Group into batches of 6 (ceil(14/6) = 3 batches per module)
  - For each batch:
    - Generate front image
    - Generate back image (with flip transform applied)
    - Apply ink-saving mask (if enabled)
    - Add labels (if enabled)
    - Save as `{output_dir}/module_{M:02d}/batch_{B:02d}_front.png` and `..._back.png`
- Return list of all generated file paths

**7.2** Optimization: for modules with identical custom content (non-triptych), detect duplicates and output once with a note.

### Phase 8 — CLI Entry Point (cli.py)

**8.1** argparse interface:
```
python -m pvv_tools.flap_printer JOB_FILE
  --dpi INT              Override output DPI (default: from config or 360)
  --output-dir PATH      Override output directory
  --modules M [M ...]    Only process specific modules (default: all)
  --no-labels            Disable EP labels
  --no-mask              Disable ink-saving mask
  --flip-mode MODE       Override flip mode (left-right | front-back)
  --print-size W H       Override output size in mm (default: from jig dims)
  --dry-run              Validate config and print summary without generating images
  --verbose              Verbose logging
```

**8.2** CLI overrides take precedence over JSON config values.

---

## Relevant Files

### Files to CREATE
- `pvv_tools/flap_printer/__init__.py` — package init
- `pvv_tools/flap_printer/cli.py` — argparse CLI entry point
- `pvv_tools/flap_printer/config.py` — JSON config schema + loader
- `pvv_tools/flap_printer/scad_parser.py` — .scad variable parser
- `pvv_tools/flap_printer/dimensions.py` — dimension dataclasses
- `pvv_tools/flap_printer/slicer.py` — image slicing (top/bottom, multi-module)
- `pvv_tools/flap_printer/layout.py` — batch grid layout + flip + mask
- `pvv_tools/flap_printer/labels.py` — EP label rendering
- `pvv_tools/flap_printer/renderer.py` — orchestrator
- `pvv_tools/requirements.txt` — Pillow>=10.0
- `pvv_tools/example_job.json` — annotated example config
- `pvv_tools/README.md` — usage docs

### Files to READ (not modify)
- `3d/flap_dimensions.scad` — flap_width=54, flap_height=43, flap_gap calc, notch dims
- `3d/flap.scad` — `flap_2d()` module for flap outline shape, `get_letter_for_front/back()` mapping logic
- `3d/flap_characters.scad` — `character_list` for reference
- `pvv_cad/PVV_splitflap_mods.scad` — `minibed_flap_jig_*` dimensions, `flap_gap`, jig layout

### Reference code patterns
- `3d/scripts/openscad.py` — `extract_values()` regex pattern for parsing echo output (similar approach for scad_parser)
- `3d/scripts/generate_fonts.py` — existing flap layout generation (reference for font/bleed/spacing patterns)

---

## Verification

1. **Unit test: scad_parser** — parse `flap_dimensions.scad`, assert `flap_width==54`, `flap_height==43`
2. **Unit test: slicer** — create a test image (88.4mm tall at 360 DPI), slice, verify top/bottom heights match 43mm each (gap removed)
3. **Unit test: layout** — generate a 6-flap batch image, verify output dimensions match 300mm × 66mm at 360 DPI (4252 × 935 px)
4. **Unit test: flip** — verify left-right flip produces horizontally mirrored image
5. **Integration test: dry-run** — `python -m pvv_tools.flap_printer example_job.json --dry-run` validates config and prints summary
6. **Visual test: single image** — process one custom display image, inspect output front/back PNGs for correct split/positioning
7. **Visual test: triptych** — process a 3-module triptych, verify per-module columns extract correctly and align at module boundaries
8. **Visual test: labels** — confirm EP labels appear in margins, not overlapping flap content
9. **Measurement test** — open output PNG in image editor, verify physical dimensions at stated DPI match jig measurements

---

## Decisions

- **EP42/EP43 omission**: confirmed by Scott; $ character flaps removed, 14 custom flaps inserted in their position
- **Flip mode default**: left-to-right (operator flips jig along vertical axis); back image = front image mirrored horizontally
- **No OpenSCAD runtime dependency**: Python parses .scad files statically (no need to invoke OpenSCAD)
- **Pillow only external dep**: MIT-compatible license, sufficient for all image processing needs
- **Future GUI**: clean separation of core engine (slicer, layout, renderer) from CLI; renderer returns in-memory images that a GUI could display
- **Vertical keepout zone**: NOT applied to custom images by default (artistic content may intentionally use that area). Configurable as optional mask.
- **Excluded from scope**: firmware character set changes, spool sequencing logic, standard EP01-EP52 re-rendering, OpenSCAD 3D rendering

## Further Considerations

1. **Large jig support**: The Eufy E1 standard flatbed is larger than the minibed. The tool should accept jig dimensions as config (already planned — `jig` section in JSON). When scaling up, the user changes jig type or overrides dimensions.
2. **Color management**: UV printers may need specific color profiles (CMYK vs RGB). Currently outputting RGBA. If needed, ICC profile support could be added as a post-processing step.
3. **Flap outline accuracy**: The ink-saving mask uses a simplified flap shape (rounded rect + notches). If higher fidelity is needed, an SVG trace of `flap_2d()` could be imported. Starting with computed shape should be sufficient.

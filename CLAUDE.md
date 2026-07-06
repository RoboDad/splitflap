# Splitflap — Claude Code Project Context

## What this repo is

DIY ESP32-based split-flap display project (open source, by scottbez1).
This workspace extends the upstream project with custom tooling under `pvv_*` directories.

## Repo layout

| Path | Purpose |
|---|---|
| `firmware/` | ESP32 firmware (PlatformIO / Arduino framework) |
| `pvv_tools/flap_printer/` | **Primary active work** — Python UV-print layout generator |
| `pvv_cad/` | OpenSCAD files for custom laser-cut jigs and parts |
| `3d/` | Upstream OpenSCAD model files |
| `electronics/` | KiCad PCB designs |
| `proto/` | Protobuf definitions (`splitflap.proto`) |
| `software/` | Python host software (chainlink controller etc.) |
| `docs/` | Documentation and `SESSION_LOG.md` |
| `pvv_plans/` | Planning documents (Markdown) |
| `.venv/` | Python virtual environment (gitignored) |

## Python environment

**Always run Python commands from the repo root** (`splitflap/`).

```powershell
# Activate venv (required each new terminal)
.venv\Scripts\Activate.ps1

# Install / refresh dependencies
pip install -r pvv_tools\requirements.txt
pip install -r 3d\scripts\requirements.txt
```

The `.venv` folder is gitignored; recreate with `python -m venv .venv` if missing.

## Key commands

```powershell
# Flap printer — dry run (validate config)
python -m pvv_tools.flap_printer pvv_tools/prototype_job.json --dry-run

# Flap printer — generate output
python -m pvv_tools.flap_printer pvv_tools/prototype_job.json

# Flap printer — flip modes
python -m pvv_tools.flap_printer pvv_tools/prototype_job.json --flip-mode left-right
python -m pvv_tools.flap_printer pvv_tools/prototype_job.json --flip-mode front-back

# Firmware build (PlatformIO, default target = chainlink)
pio run
pio run -t upload
```

## Active development: pvv_tools/flap_printer

The flap printer generates print-ready images for UV printing custom flaps on a Eufy E1 printer using a laser-cut jig.

### Orientation convention (critical rule)

There is exactly ONE shared frame — **printer orientation** — used by the
OpenSCAD jig model (`pvv_cad/flap_printer_jigs.scad`), the generated params
file, the job JSON `jig` section, and the output print images:

- The jig/mat long axis runs along **X** (370 mm), matching how the jig
  physically sits on the eufyMake E1 Mini Flatbed, viewed from above.
- The mat zero-point corner (diagonal corner cut) is at the **bottom-right**
  (= lower-right of the imported image in eufyMake Studio Zero Point mode;
  the green registration mark).
- Flap pockets sit **rotated 90°** in the jig (single row along X, spool/notch
  edge facing right, toward the zero point), so a pocket's X extent is
  `flap_height` (43) and its Y extent is `flap_width` (54).

Flap *content* (images, slicing, preview) is composed in the **upright frame**
(character upright).  The only transform between frames is a single 90° CCW
rotation (`Image.ROTATE_90`) applied per-flap at batch-layout time in
`layout.py`: upright top edge → sheet left, upright spool edge → sheet right.
The terms "portrait"/"landscape" are obsolete — do not reintroduce them.

### Flip geometry (critical rule)

A **front-back** flip is geometrically equivalent to a **left-right** flip **+ in-plane 180° rotation**:

```
reflect_x == rotate180 ∘ reflect_y
```

In `renderer.py`, the back sheet is *always* built with left-right semantics.
When `flip == "front-back"`, the finished back image is `Image.ROTATE_180` **before** registration marks and calibration offset are applied (those stay in sheet space).

- Front sheet: `spool_at_bottom=True` (upright frame; spool edge faces right on the sheet)
- Left-right back: `spool_at_bottom=False` (spool edge faces left on the sheet)
- Front-back back: left-right back rotated 180° (spool ends up on the correct side)

`spool_at_bottom` always refers to the upright content frame (see Orientation
convention above), not the sheet.

Ink-save mask notches are drawn symmetrically on both sides — if the notch looks wrong on a back sheet, the real cause is spool orientation, not the mask geometry.

### README update rule

Any change to `pvv_tools/flap_printer/` that adds or modifies a **user-facing feature** MUST include a `pvv_tools/README.md` update in the same commit. Checklist:

- New config key → add row to the relevant table
- New flap type → add bullet under **Custom Flap Types**
- New mode constant → add a dedicated `## X Modes` section
- Pipeline change → update the numbered list under **Image Pipeline**
- New CLI option → update the usage block

## Firmware notes

- PlatformIO project; `platformio.ini` is at the repo root.
- `default_envs = chainlink` (ESP32-based Chainlink Driver board).
- Source in `firmware/src/`, libs in `firmware/lib/`, includes in `firmware/include/`.
- Protobuf generated files live in `proto/`; regenerate with `proto/generate_protobuf.py`.

## CAD notes

- `pvv_cad/PVV_splitflap_mods.scad` — custom mod overrides for the upstream 3d model.
- `pvv_cad/flap_printer_jigs.scad` / `flap_printer_params.scad` — laser-cut jig definitions.
- OpenSCAD is required; path can be passed via `--openscad` flag or auto-detected.

## Session log

All sessions that modify files must append an entry to `docs/SESSION_LOG.md`.

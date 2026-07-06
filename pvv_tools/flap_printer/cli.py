"""CLI entry point for the flap printer tool."""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from .config import load_config, print_summary
from .dimensions import AllDimensions
from .renderer import render_job
from .scad_writer import write_flap_printer_params


def _find_repo_root() -> Path:
    """Walk up from this file to find the repo root (contains 3d/ and pvv_cad/)."""
    p = Path(__file__).resolve()
    for parent in [p] + list(p.parents):
        if (parent / '3d').is_dir() and (parent / 'pvv_cad').is_dir():
            return parent
    return Path('.')


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog='flap_printer',
        description='Generate UV print layout images for custom splitflap flaps.',
    )
    parser.add_argument('job_file', type=str, help='Path to JSON job config file')
    parser.add_argument('--dpi', type=int, default=None, help='Override output DPI (default: from config or 360)')
    parser.add_argument('--output-dir', type=str, default=None, help='Override output directory')
    parser.add_argument('--modules', type=int, nargs='+', default=None, help='Process specific modules only')
    parser.add_argument('--no-labels', action='store_true', help='Disable EP labels')
    parser.add_argument('--no-mask', action='store_true', help='Disable ink-saving mask')
    parser.add_argument('--registration-marks', dest='registration_marks', action='store_true', default=None,
                        help='Draw corner registration marks on output images (overrides config)')
    parser.add_argument('--no-registration-marks', dest='registration_marks', action='store_false',
                        help='Disable corner registration marks (overrides config)')
    parser.add_argument('--flip-mode', choices=['left-right', 'front-back'], default=None, help='Override flip mode')
    parser.add_argument('--print-size', type=float, nargs=2, metavar=('W', 'H'), default=None,
                        help='Override output size in mm (width height)')
    parser.add_argument('--dry-run', action='store_true', help='Validate config and print summary without generating images')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose logging')
    parser.add_argument('--openscad', type=str, default=None,
                        help='Path to OpenSCAD executable (auto-detected if omitted)')
    parser.add_argument('--scad-mods', type=str, default=None,
                        help='Path to PVV_splitflap_mods.scad (auto-detected from repo)')

    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format='%(levelname)s: %(message)s',
    )

    # Load config
    try:
        config = load_config(args.job_file)
    except (FileNotFoundError, ValueError, KeyError) as e:
        logging.error("Config error: %s", e)
        return 1

    # Load dimensions: OpenSCAD → config overrides → hardcoded defaults
    # Jig + printable area dims come from job config (architectural inversion);
    # only flap physical dims are still resolved via OpenSCAD echo.
    repo_root = _find_repo_root()
    mods_path = args.scad_mods or (repo_root / 'pvv_cad' / 'PVV_splitflap_mods.scad')
    dims = AllDimensions.from_scad(
        mods_path=mods_path,
        openscad_path=args.openscad,
        overrides=config.dimensions.as_dict(),
        jig_config=config.jig,
    )

    # Write flap_printer_params.scad so flap_printer_jigs.scad has current values
    params_path = repo_root / 'pvv_cad' / 'flap_printer_params.scad'
    try:
        write_flap_printer_params(params_path, dims, config.jig)
        logging.info("Wrote %s", params_path)
    except OSError as e:
        logging.warning("Could not write flap_printer_params.scad: %s", e)

    # Override display dimensions from config if they differ from defaults
    if config.display.module_pitch_mm != dims.display.module_pitch:
        dims.display = dims.display.__class__(
            module_pitch=config.display.module_pitch_mm,
            inter_module_gap=config.display.inter_module_gap_mm,
            module_width=dims.flap.width,
        )

    # Apply output.canvas_size_mm override (e.g. match eufyMake Studio's
    # Camera-mode mat canvas: [335, 90]).  The insert stays anchored to the
    # image's left and bottom edges — extra canvas size is added at the top
    # and right — so flap content keeps its calibrated physical placement
    # while the output image grows to match the eufyMake working canvas.
    if config.output.canvas_size_mm is not None:
        cw, ch = config.output.canvas_size_mm
        dims.printable = dims.printable.__class__(
            width=cw,
            height=ch,
            insert_offset_x=dims.printable.insert_offset_x,
            insert_offset_y=dims.printable.insert_offset_y + (ch - dims.printable.height),
            printable_origin_x=dims.printable.printable_origin_x,
            printable_origin_y=dims.printable.printable_origin_y,
            insert_origin_x=dims.printable.insert_origin_x,
            insert_origin_y=dims.printable.insert_origin_y,
        )

    # Dry run: just print summary
    if args.dry_run:
        print("=== Flap Printer — Dry Run ===")
        print()
        print("Config:")
        print_summary(config)
        print()
        print("Dimensions:")
        print(f"  Flap: {dims.flap.width}×{dims.flap.height}mm, gap={dims.flap.gap}mm, "
              f"display_height={dims.flap.display_height}mm")
        insert = dims.jig.insert_size(dims.flap)
        print(f"  Jig insert: {insert[0]:.1f}×{insert[1]:.1f}mm ({dims.jig.flaps_per_batch} flaps/batch)")
        pa = dims.printable
        canvas_overridden = config.output.canvas_size_mm is not None
        label = "Output canvas" if canvas_overridden else "Printable area"
        print(f"  {label}: {pa.width}×{pa.height}mm")
        print(f"  Insert offset: ({pa.insert_offset_x:.1f}, {pa.insert_offset_y:.1f})mm")
        print(f"  Module pitch: {dims.display.module_pitch}mm, gap: {dims.display.inter_module_gap}mm")
        print()

        dpi = args.dpi or config.output.dpi
        import math
        num_batches = math.ceil(len(config.custom_flaps) / dims.jig.flaps_per_batch)
        print(f"Output: {dpi} DPI, {num_batches} batch(es) × 2 sides = {num_batches * 2} images")
        from .dimensions import mm_to_px
        print(f"  Canvas size: {mm_to_px(pa.width, dpi)}×{mm_to_px(pa.height, dpi)} px "
              f"({pa.width:.1f}×{pa.height:.1f} mm)")
        print(f"  Insert area: {insert[0]:.1f}×{insert[1]:.1f}mm at offset "
              f"({pa.insert_offset_x:.1f}, {pa.insert_offset_y:.1f})mm")
        print()
        print("Validation: OK")
        return 0

    # Resolve output_dir relative to the job file's directory (not CWD)
    # so output always lands in a predictable place regardless of where
    # the command is invoked from.
    job_dir = Path(args.job_file).resolve().parent
    raw_out = args.output_dir or config.output.output_dir
    out_path = Path(raw_out)
    if not out_path.is_absolute():
        out_path = (job_dir / out_path).resolve()

    # Render
    try:
        generated = render_job(
            config=config,
            dims=dims,
            dpi=args.dpi,
            output_dir=str(out_path),
            module_filter=args.modules,
            enable_labels=False if args.no_labels else None,
            enable_mask=False if args.no_mask else None,
            enable_registration_marks=args.registration_marks,
            flip_mode=args.flip_mode,
        )
    except Exception as e:
        logging.error("Render failed: %s", e, exc_info=args.verbose)
        return 1

    print(f"\nGenerated {len(generated)} file(s):")
    for p in generated:
        print(f"  {p}")
    return 0


if __name__ == '__main__':
    sys.exit(main())

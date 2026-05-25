"""CLI entry point for the flap printer tool."""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from .config import load_config, print_summary
from .dimensions import AllDimensions
from .renderer import render_job


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
    repo_root = _find_repo_root()
    mods_path = args.scad_mods or (repo_root / 'pvv_cad' / 'PVV_splitflap_mods.scad')
    dims = AllDimensions.from_scad(
        mods_path=mods_path,
        openscad_path=args.openscad,
        overrides=config.dimensions.as_dict(),
    )

    # Override display dimensions from config if they differ from defaults
    if config.display.module_pitch_mm != dims.display.module_pitch:
        dims.display = dims.display.__class__(
            module_pitch=config.display.module_pitch_mm,
            inter_module_gap=config.display.inter_module_gap_mm,
            module_width=dims.flap.width,
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
        print(f"  Printable area: {pa.width}×{pa.height}mm")
        print(f"  Insert offset: ({pa.insert_offset_x:.1f}, {pa.insert_offset_y:.1f})mm")
        print(f"  Module pitch: {dims.display.module_pitch}mm, gap: {dims.display.inter_module_gap}mm")
        print()

        dpi = args.dpi or config.output.dpi
        import math
        num_batches = math.ceil(len(config.custom_flaps) / dims.jig.flaps_per_batch)
        print(f"Output: {dpi} DPI, {num_batches} batch(es) × 2 sides = {num_batches * 2} images")
        orient = config.jig.output_orientation
        if orient == "landscape":
            out_w, out_h = pa.height, pa.width
        else:
            out_w, out_h = pa.width, pa.height
        from .dimensions import mm_to_px
        print(f"  Canvas size: {mm_to_px(out_w, dpi)}×{mm_to_px(out_h, dpi)} px "
              f"({out_w:.1f}×{out_h:.1f} mm)")
        print(f"  Insert area: {insert[0]:.1f}×{insert[1]:.1f}mm at offset "
              f"({pa.insert_offset_x:.1f}, {pa.insert_offset_y:.1f})mm")
        print()
        print("Validation: OK")
        return 0

    # Render
    try:
        generated = render_job(
            config=config,
            dims=dims,
            dpi=args.dpi,
            output_dir=args.output_dir,
            module_filter=args.modules,
            enable_labels=False if args.no_labels else None,
            enable_mask=False if args.no_mask else None,
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

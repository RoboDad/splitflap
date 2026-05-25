"""Orchestrator: load config, resolve images, slice, layout, and save batch outputs."""

from __future__ import annotations

import logging
import math
from pathlib import Path
from typing import Optional

from PIL import Image

from .config import JobConfig, CustomFlap
from .dimensions import AllDimensions, FlapDimensions, JigDimensions, DisplayDimensions, mm_to_px
from .slicer import slice_display_image, extract_module_column, apply_transforms, fit_to_target
from .layout import FlapSide, map_images_to_flap_sides, generate_batch_image, apply_flip_transform, apply_ink_save_mask, reorder_for_jig_flip
from .labels import render_labels
from . import svg_loader

logger = logging.getLogger(__name__)


def _load_source_image(flap_cfg: CustomFlap, target_height_px: int) -> Image.Image:
    """Load and validate a source image (raster or SVG).

    ``target_height_px`` is the eventual display-image height in pixels;
    it is used only by the SVG path to pick a high-quality render size.
    Raster images are loaded at their native resolution and resampled by
    the downstream pipeline as usual.
    """
    if flap_cfg.source_path is None or not flap_cfg.source_path.exists():
        raise FileNotFoundError(f"Source image not found: {flap_cfg.source} "
                                f"(resolved to {flap_cfg.source_path})")
    if svg_loader.is_svg(flap_cfg.source_path):
        return svg_loader.load_svg(flap_cfg.source_path, target_height_px)
    img = Image.open(flap_cfg.source_path).convert('RGBA')
    return img


def _resolve_flaps_for_module(
    config: JobConfig,
    module_index: int,
    dims: AllDimensions,
    dpi: float,
) -> list[tuple[Image.Image, Image.Image, str]]:
    """Resolve and slice all custom flap images for a given module.

    Returns a list of (top_half, bottom_half, label) tuples, one per
    custom flap slot that has content for this module.
    """
    results = []

    for cf in config.custom_flaps:
        if cf.type == "blank":
            # Blank flap: fully transparent top and bottom halves
            flap_w = mm_to_px(dims.flap.width, dpi)
            flap_h = mm_to_px(dims.flap.height, dpi)
            blank = Image.new('RGBA', (flap_w, flap_h), (0, 0, 0, 0))
            results.append((blank, blank, cf.label))

        elif cf.type == "single":
            # Single-module images apply to every module identically
            target_w = mm_to_px(dims.flap.width, dpi)
            target_h = mm_to_px(dims.flap.display_height, dpi)
            img = _load_source_image(cf, target_h)

            # Apply per-image transforms, falling back to globals
            scale = cf.scale or (config.global_transforms.scale
                                 if config.global_transforms.scale != (1.0, 1.0) else None)
            crop = cf.crop or config.global_transforms.crop_percent
            img = apply_transforms(img, scale=scale, crop=crop)

            # Fit to expected display image size: flap_width × display_height
            fit = cf.fit_mode or config.global_transforms.fit_mode
            img = fit_to_target(img, target_w, target_h, fit)

            top, bottom = slice_display_image(img, dims.flap, dpi)
            results.append((top, bottom, cf.label))

        elif cf.type == "multi-module":
            if cf.module_range is None:
                continue
            start_mod, end_mod = cf.module_range
            if not (start_mod <= module_index <= end_mod):
                continue  # This image doesn't cover this module

            target_h = mm_to_px(dims.flap.display_height, dpi)
            img = _load_source_image(cf, target_h)

            # Apply per-image transforms
            scale = cf.scale or (config.global_transforms.scale
                                 if config.global_transforms.scale != (1.0, 1.0) else None)
            crop = cf.crop or config.global_transforms.crop_percent
            img = apply_transforms(img, scale=scale, crop=crop)

            # Fit image to expected multi-module span
            num_span = end_mod - start_mod + 1
            total_width_mm = num_span * dims.display.module_pitch - dims.display.inter_module_gap
            target_w = mm_to_px(total_width_mm, dpi)
            fit = cf.fit_mode or config.global_transforms.fit_mode
            img = fit_to_target(img, target_w, target_h, fit)

            # Extract this module's column
            column = extract_module_column(img, module_index, cf.module_range, dims.display, dpi)

            # Fit column to exact flap dimensions
            flap_w = mm_to_px(dims.flap.width, dpi)
            flap_display_h = mm_to_px(dims.flap.display_height, dpi)
            column = fit_to_target(column, flap_w, flap_display_h, fit)

            top, bottom = slice_display_image(column, dims.flap, dpi)
            results.append((top, bottom, cf.label))

    return results


def _get_modules_to_process(config: JobConfig, module_filter: Optional[list[int]]) -> list[int]:
    """Determine which modules need custom flap output."""
    if module_filter is not None:
        return module_filter

    modules = set()
    for cf in config.custom_flaps:
        if cf.type == "single":
            # Single images produce the same output for all modules;
            # output once as "common"
            modules.add(-1)  # sentinel for common/shared
        elif cf.type == "multi-module" and cf.module_range:
            for m in range(cf.module_range[0], cf.module_range[1] + 1):
                modules.add(m)

    return sorted(modules)


def render_job(
    config: JobConfig,
    dims: AllDimensions,
    dpi: Optional[int] = None,
    output_dir: Optional[str] = None,
    module_filter: Optional[list[int]] = None,
    enable_labels: Optional[bool] = None,
    enable_mask: Optional[bool] = None,
    flip_mode: Optional[str] = None,
    orientation: Optional[str] = None,
) -> list[Path]:
    """Main render pipeline: process all modules and write batch images.

    Returns list of paths to generated files.
    """
    dpi = dpi or config.output.dpi
    out_dir = Path(output_dir or config.output.output_dir)
    labels_on = enable_labels if enable_labels is not None else config.output.labels
    mask_on = enable_mask if enable_mask is not None else config.output.ink_save_mask
    flip = flip_mode or config.jig.flip_mode
    orient = orientation or config.jig.output_orientation

    modules = _get_modules_to_process(config, module_filter)
    generated: list[Path] = []

    for mod_idx in modules:
        if mod_idx == -1:
            mod_label = "common"
            # For common/single flaps, process without module context
            flap_data = _resolve_flaps_for_module(config, 0, dims, dpi)
        else:
            mod_label = f"module_{mod_idx:02d}"
            flap_data = _resolve_flaps_for_module(config, mod_idx, dims, dpi)

        if not flap_data:
            logger.info("No custom flaps for %s, skipping", mod_label)
            continue

        slot_images = [(top, bottom) for top, bottom, _ in flap_data]
        labels = [label for _, _, label in flap_data]

        fronts, backs = map_images_to_flap_sides(slot_images, labels)

        # Batch into groups of jig.flaps_per_batch
        batch_size = dims.jig.flaps_per_batch
        num_batches = math.ceil(len(fronts) / batch_size)

        mod_dir = out_dir / mod_label
        mod_dir.mkdir(parents=True, exist_ok=True)

        for b in range(num_batches):
            start = b * batch_size
            end = min(start + batch_size, len(fronts))

            front_batch = fronts[start:end]
            back_batch = backs[start:end]

            # Generate front image
            bleed = config.output.bleed_mm
            front_img = generate_batch_image(front_batch, dims.flap, dims.jig, dims.printable, dpi, orient,
                                             bleed_mm=bleed)

            # Reorder back-side flaps to their post-jig-flip grid positions.
            # This reverses the flap order (correct for physical jig flip)
            # without mirroring individual flap content.
            reordered_back = reorder_for_jig_flip(back_batch, dims.jig, flip, orient)
            back_img = generate_batch_image(reordered_back, dims.flap, dims.jig, dims.printable, dpi, orient,
                                            bleed_mm=bleed)

            # Apply ink-saving mask
            if mask_on:
                front_img = apply_ink_save_mask(front_img, dims.flap, dims.jig, dims.printable, dpi,
                                                config.output.bleed_mm, orient, spool_at_bottom=True)
                back_img = apply_ink_save_mask(back_img, dims.flap, dims.jig, dims.printable, dpi,
                                               config.output.bleed_mm, orient, spool_at_bottom=False)

            # Add labels
            if labels_on:
                front_img = render_labels(front_img, front_batch, dims.flap, dims.jig, dims.printable, dpi,
                                          config.output.label_font_size_pt, orient)
                back_img = render_labels(back_img, reordered_back, dims.flap, dims.jig, dims.printable, dpi,
                                         config.output.label_font_size_pt, orient)

            # Set DPI metadata
            dpi_info = (dpi, dpi)

            # Save
            fmt = config.output.format.lower()
            front_path = mod_dir / f"batch_{b + 1:02d}_front.{fmt}"
            back_path = mod_dir / f"batch_{b + 1:02d}_back.{fmt}"

            front_img.save(str(front_path), dpi=dpi_info)
            back_img.save(str(back_path), dpi=dpi_info)

            generated.extend([front_path, back_path])
            logger.info("Wrote %s, %s", front_path, back_path)

    return generated

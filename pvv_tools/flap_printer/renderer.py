"""Orchestrator: load config, resolve images, slice, layout, and save batch outputs."""

from __future__ import annotations

import logging
import math
from pathlib import Path
from typing import Optional

from PIL import Image

from .config import JobConfig, CustomFlap
from .dimensions import AllDimensions, FlapDimensions, JigDimensions, DisplayDimensions, mm_to_px
from .slicer import slice_display_image, extract_module_column, apply_transforms, fit_to_target, fit_with_notch_mode
from .layout import FlapSide, map_images_to_flap_sides, generate_batch_image, apply_flip_transform, apply_ink_save_mask, reorder_for_jig_flip
from .labels import render_labels
from . import svg_loader

logger = logging.getLogger(__name__)


def _apply_calibration_offset(img: Image.Image, dx_px: int, dy_px: int) -> Image.Image:
    """Translate ``img`` by (dx_px, dy_px) on a fresh transparent canvas of
    the same size.  Content shifted past the image edge is clipped.  Used
    to apply a global mat-calibration offset to the final composited image.
    """
    if dx_px == 0 and dy_px == 0:
        return img
    shifted = Image.new('RGBA', img.size, (0, 0, 0, 0))
    shifted.paste(img, (dx_px, dy_px), img)
    return shifted


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


def _render_custom_flap_images(
    cf: CustomFlap,
    config: JobConfig,
    module_index: int,
    dims: AllDimensions,
    dpi: float,
    bleed_px: int = 0,
) -> Optional[tuple[Image.Image, Image.Image]]:
    """Render one CustomFlap to (top_half, bottom_half) at the given DPI.

    When *bleed_px* > 0, images are expanded into the bleed zone on flush
    edges so the batch layout can paste them offset by the bleed amount.
    The physical pocket area is centred within the returned images.

    Returns None if the flap does not apply to *module_index* (multi-module
    flaps whose range excludes the requested module).
    Returns (blank, blank) for blank or disabled flaps.
    """
    flap_w = mm_to_px(dims.flap.width, dpi)
    flap_h = mm_to_px(dims.flap.height, dpi)
    blank = Image.new('RGBA', (flap_w, flap_h), (0, 0, 0, 0))

    if cf.type == "blank" or not cf.enabled:
        return blank, blank

    if cf.type == "single":
        target_w = mm_to_px(dims.flap.width, dpi)
        target_h = mm_to_px(dims.flap.display_height, dpi)
        img = _load_source_image(cf, target_h)
        scale = cf.scale or (config.global_transforms.scale
                             if config.global_transforms.scale != (1.0, 1.0) else None)
        crop = cf.crop or config.global_transforms.crop_percent
        img = apply_transforms(img, scale=scale, crop=crop)
        fit = cf.fit_mode or config.global_transforms.fit_mode
        notch = cf.notch_mode or config.global_transforms.notch_mode
        notch_inset_px = mm_to_px(dims.flap.notch_depth, dpi)
        img = fit_with_notch_mode(img, target_w, target_h, fit, notch[0], notch[1], notch_inset_px, bleed_px)
        bleed_y = max(0, (img.height - mm_to_px(dims.flap.display_height, dpi)) // 2)
        return slice_display_image(img, dims.flap, dpi, bleed_y=bleed_y)

    if cf.type == "multi-module":
        if cf.module_range is None:
            return None
        start_mod, end_mod = cf.module_range
        if not (start_mod <= module_index <= end_mod):
            return None
        target_h = mm_to_px(dims.flap.display_height, dpi)
        img = _load_source_image(cf, target_h)
        scale = cf.scale or (config.global_transforms.scale
                             if config.global_transforms.scale != (1.0, 1.0) else None)
        crop = cf.crop or config.global_transforms.crop_percent
        img = apply_transforms(img, scale=scale, crop=crop)
        num_span = end_mod - start_mod + 1
        total_width_mm = num_span * dims.display.module_pitch - dims.display.inter_module_gap
        target_w = mm_to_px(total_width_mm, dpi)
        fit = cf.fit_mode or config.global_transforms.fit_mode
        notch = cf.notch_mode or config.global_transforms.notch_mode
        notch_inset_px = mm_to_px(dims.flap.notch_depth, dpi)
        img = fit_to_target(img, target_w, target_h, fit)
        column = extract_module_column(img, module_index, cf.module_range, dims.display, dpi)
        flap_w_px = mm_to_px(dims.flap.width, dpi)
        flap_display_h = mm_to_px(dims.flap.display_height, dpi)
        column = fit_with_notch_mode(column, flap_w_px, flap_display_h, fit, notch[0], notch[1], notch_inset_px, bleed_px)
        bleed_y = max(0, (column.height - mm_to_px(dims.flap.display_height, dpi)) // 2)
        return slice_display_image(column, dims.flap, dpi, bleed_y=bleed_y)

    return None  # unknown type


def _resolve_flaps_for_module(
    config: JobConfig,
    module_index: int,
    dims: AllDimensions,
    dpi: float,
    bleed_px: int = 0,
) -> list[tuple[Image.Image, Image.Image, str]]:
    """Resolve and slice all custom flap images for a given module.

    Returns a list of (top_half, bottom_half, label) tuples, one per
    custom flap slot that has content for this module.
    """
    results = []
    for cf in config.custom_flaps:
        pair = _render_custom_flap_images(cf, config, module_index, dims, dpi, bleed_px)
        if pair is not None:
            results.append((*pair, cf.label))
    return results


def _crop_to_pocket(
    img: Image.Image,
    flap_w: int,
    flap_h: int,
    is_top: bool,
) -> Image.Image:
    """Crop a (possibly bleed-expanded) half-flap image to the physical pocket area.

    For top halves the outer bleed is at the top of the image; for bottom
    halves it is at the bottom.  Returns img unchanged when there is no bleed.
    """
    bx = max(0, (img.width - flap_w) // 2)
    by = max(0, img.height - flap_h)
    if bx == 0 and by == 0:
        return img
    if is_top:
        # Bleed at outer top → visible pocket area occupies the bottom flap_h rows
        return img.crop((bx, by, bx + flap_w, img.height))
    else:
        # Bleed at outer bottom → visible pocket area occupies the top flap_h rows
        return img.crop((bx, 0, bx + flap_w, flap_h))


def _collect_preview_entries(
    config: JobConfig,
    dims: AllDimensions,
    dpi: float,
) -> list[tuple[Image.Image, Image.Image, str]]:
    """Collect (top_half, bottom_half, label) for every unique displayable slot.

    Images are rendered with bleed and then cropped to the physical pocket
    area, so the preview is WYSIWYG: it shows exactly the content that will
    be visible on the physical flap after cutting.

    Single / glyph / emoji / blank flaps appear once.
    Multi-module flaps appear once per module in their range.
    Labels include both the flap label and the slot index (user preference).
    """
    flap_w = mm_to_px(dims.flap.width, dpi)
    flap_h = mm_to_px(dims.flap.height, dpi)
    bleed_px = mm_to_px(config.output.bleed_mm, dpi)

    entries = []
    for cf in config.custom_flaps:
        if cf.type == "multi-module" and cf.module_range:
            start, end = cf.module_range
            for m in range(start, end + 1):
                pair = _render_custom_flap_images(cf, config, m, dims, dpi, bleed_px)
                if pair is not None:
                    top = _crop_to_pocket(pair[0], flap_w, flap_h, is_top=True)
                    bottom = _crop_to_pocket(pair[1], flap_w, flap_h, is_top=False)
                    label = f"{cf.label} M{m} · #{cf.slot}"
                    entries.append((top, bottom, label))
        else:
            pair = _render_custom_flap_images(cf, config, 0, dims, dpi, bleed_px)
            if pair is not None:
                top = _crop_to_pocket(pair[0], flap_w, flap_h, is_top=True)
                bottom = _crop_to_pocket(pair[1], flap_w, flap_h, is_top=False)
                label = f"{cf.label} · #{cf.slot}"
                entries.append((top, bottom, label))
    return entries


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
    enable_registration_marks: Optional[bool] = None,
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
    reg_on = enable_registration_marks if enable_registration_marks is not None else config.output.registration_marks
    flip = flip_mode or config.jig.flip_mode
    orient = orientation or config.jig.output_orientation

    modules = _get_modules_to_process(config, module_filter)
    generated: list[Path] = []
    bleed_px = mm_to_px(config.output.bleed_mm, dpi)

    for mod_idx in modules:
        if mod_idx == -1:
            mod_label = "common"
            # For common/single flaps, process without module context
            flap_data = _resolve_flaps_for_module(config, 0, dims, dpi, bleed_px)
        else:
            mod_label = f"module_{mod_idx:02d}"
            flap_data = _resolve_flaps_for_module(config, mod_idx, dims, dpi, bleed_px)

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
            front_img = generate_batch_image(front_batch, dims.flap, dims.jig, dims.printable, dpi, orient,
                                             spool_at_bottom=True)

            # Reorder back-side flaps to their post-jig-flip grid positions.
            # This reverses the flap order (correct for physical jig flip)
            # without mirroring individual flap content.
            reordered_back = reorder_for_jig_flip(back_batch, dims.jig, flip, orient)
            back_img = generate_batch_image(reordered_back, dims.flap, dims.jig, dims.printable, dpi, orient,
                                            spool_at_bottom=False)

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

            # Corner registration marks (after mask + labels so they aren't clipped)
            if reg_on:
                from .layout import draw_registration_marks
                lw = config.output.registration_mark_line_width_mm
                front_img = draw_registration_marks(front_img, dpi, line_width_mm=lw)
                back_img = draw_registration_marks(back_img, dpi, line_width_mm=lw)

            # Global calibration offset (applied last so it moves *everything*
            # — flap art, ink-save mask, labels, and registration marks —
            # together).  Compensates for systematic printer-vs-jig offsets
            # such as eufyMake Zero-Point calibration error.
            cal_dx_mm, cal_dy_mm = config.output.calibration_offset_mm
            if cal_dx_mm != 0.0 or cal_dy_mm != 0.0:
                cal_dx_px = round(cal_dx_mm * dpi / 25.4)
                cal_dy_px = round(cal_dy_mm * dpi / 25.4)
                front_img = _apply_calibration_offset(front_img, cal_dx_px, cal_dy_px)
                back_img = _apply_calibration_offset(back_img, cal_dx_px, cal_dy_px)

            # Set DPI metadata.
            # Compute the *effective* DPI from the actual saved pixel count
            # and the intended physical size in mm, so that downstream tools
            # (eufyMake Studio, etc.) read the image back at exactly the
            # target mm dimensions instead of off-by-pixel-rounding values
            # (e.g. 90 mm @ 360 DPI → 1276 px, which naively reads back as
            # 90.022 mm).  Per-axis because the actual pixel rounding can
            # differ on each axis.  Orientation may swap width/height.
            img_w_px, img_h_px = front_img.size
            if orient == "landscape":
                target_mm_w, target_mm_h = dims.printable.height, dims.printable.width
            else:
                target_mm_w, target_mm_h = dims.printable.width, dims.printable.height
            eff_dpi_x = img_w_px * 25.4 / target_mm_w
            eff_dpi_y = img_h_px * 25.4 / target_mm_h
            dpi_info = (eff_dpi_x, eff_dpi_y)

            # Save
            fmt = config.output.format.lower()
            front_path = mod_dir / f"batch_{b + 1:02d}_front.{fmt}"
            back_path = mod_dir / f"batch_{b + 1:02d}_back.{fmt}"

            front_img.save(str(front_path), dpi=dpi_info)
            back_img.save(str(back_path), dpi=dpi_info)

            generated.extend([front_path, back_path])
            logger.info("Wrote %s, %s", front_path, back_path)

    # Generate preview if enabled (uses a separate lower DPI for screen output)
    if config.preview.enabled:
        from .previewer import generate_preview
        preview_dpi = float(config.preview.dpi)
        logger.info("Generating preview at %g DPI", preview_dpi)
        preview_entries = _collect_preview_entries(config, dims, preview_dpi)
        out_dir.mkdir(parents=True, exist_ok=True)
        preview_path = generate_preview(preview_entries, config, dims, out_dir)
        if preview_path:
            generated.append(preview_path)

    return generated

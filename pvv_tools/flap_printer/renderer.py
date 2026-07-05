"""Orchestrator: load config, resolve images, slice, layout, and save batch outputs."""

from __future__ import annotations

import logging
import math
from pathlib import Path
from typing import Optional

from PIL import Image

try:
    from pillow_heif import register_heif_opener
    register_heif_opener()
except ImportError:
    pass  # HEIC/HEIF support unavailable; install pillow-heif to enable it

from .config import JobConfig, CustomFlap
from .dimensions import AllDimensions, FlapDimensions, JigDimensions, DisplayDimensions, mm_to_px
from .slicer import slice_display_image, extract_module_column, apply_transforms, fit_to_target, fit_with_notch_mode
from .layout import map_images_to_flap_sides, generate_batch_image, apply_ink_save_mask, reorder_for_jig_flip
from .labels import render_labels
from . import svg_loader

logger = logging.getLogger(__name__)


def _group_flaps_by_slot(flaps: list[CustomFlap]) -> dict[int, list[CustomFlap]]:
    """Group CustomFlap entries by slot, preserving declaration order within each group.

    Multiple entries with the same slot index represent alternative coverage
    for the same physical flap position (e.g. two multi-module ranges that
    together span different module subsets).  The renderer resolves them
    left-to-right: the first entry whose module_range covers the current
    module wins.
    """
    groups: dict[int, list[CustomFlap]] = {}
    for cf in flaps:
        groups.setdefault(cf.slot, []).append(cf)
    return groups


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

    # Per-flap bleed override: bleed=False suppresses edge expansion for this image
    effective_bleed_px = bleed_px if cf.bleed else 0

    def _apply_offset(img: Image.Image) -> Image.Image:
        """Shift image content by cf.offset_mm within a canvas of the same size."""
        if cf.offset_mm is None or (cf.offset_mm[0] == 0.0 and cf.offset_mm[1] == 0.0):
            return img
        dx_px = round(cf.offset_mm[0] * dpi / 25.4)
        dy_px = round(cf.offset_mm[1] * dpi / 25.4)
        canvas = Image.new('RGBA', img.size, (0, 0, 0, 0))
        canvas.paste(img, (dx_px, dy_px), img)
        return canvas

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
        img = fit_with_notch_mode(img, target_w, target_h, fit, notch[0], notch[1], notch_inset_px, effective_bleed_px)
        img = _apply_offset(img)
        bleed_y = max(0, (img.height - mm_to_px(dims.flap.display_height, dpi)) // 2)
        return slice_display_image(img, dims.flap, dpi, bleed_y=bleed_y)

    if cf.type == "multi-module":
        if cf.module_range is None:
            return None
        if module_index < 0:
            # Common/sentinel pass — multi-module content is module-specific; skip.
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
        column = fit_with_notch_mode(column, flap_w_px, flap_display_h, fit, notch[0], notch[1], notch_inset_px, effective_bleed_px)
        column = _apply_offset(column)
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

    Returns a list of (top_half, bottom_half, label) tuples, one per slot
    that has content for this module.

    Multiple entries with the same slot are tried in declaration order;
    the first entry whose module_range covers *module_index* wins.
    module_range is respected for all entry types, not just multi-module:
    this allows a ``{"type": "blank", "module_range": [0, 2]}`` entry to
    fill in a partial range without overriding adjacent ranges in the same
    slot.

    When module_index >= 0 (a real module pass, not the common/sentinel pass)
    and a slot has at least one multi-module entry but none of them cover
    *module_index*, a blank is inserted and a warning is logged.
    """
    flap_w = mm_to_px(dims.flap.width, dpi)
    flap_h = mm_to_px(dims.flap.height, dpi)
    blank = Image.new('RGBA', (flap_w, flap_h), (0, 0, 0, 0))

    slot_groups = _group_flaps_by_slot(config.custom_flaps)
    results = []

    for slot in sorted(slot_groups.keys()):
        entries = slot_groups[slot]
        pair = None
        winning_label = None

        for cf in entries:
            # Respect module_range for all types: if an entry explicitly declares
            # a range, skip it when the current module is outside that range.
            if cf.module_range is not None and module_index >= 0:
                start, end = cf.module_range
                if not (start <= module_index <= end):
                    continue
            candidate = _render_custom_flap_images(cf, config, module_index, dims, dpi, bleed_px)
            if candidate is not None:
                pair = candidate
                winning_label = cf.label
                break

        if pair is None:
            has_multimodule = any(e.type == 'multi-module' for e in entries)
            if has_multimodule and module_index >= 0:
                # All entries for this multi-module slot lack coverage here —
                # insert a blank.  (Upfront warning already logged by render_job.)
                pair = (blank.copy(), blank.copy())
                winning_label = f"{entries[0].label}-blank"
            # else: non-multi-module slot that skipped all entries (shouldn't
            # normally happen); omit silently to preserve prior behaviour.

        if pair is not None:
            results.append((*pair, winning_label))

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
    """Collect (top_half, bottom_half, label) for every displayable slot × module.

    Images are rendered with bleed and then cropped to the physical pocket
    area, so the preview is WYSIWYG.

    Slot grouping rules:
    - Non-multi-module slots appear once (first entry in the group).
    - Multi-module slot groups enumerate every module that is processed for
      the job (from ``_get_modules_to_process``).  Modules that have no
      coverage within that slot group are shown as a labelled blank so the
      user can see the gap.
    """
    flap_w = mm_to_px(dims.flap.width, dpi)
    flap_h = mm_to_px(dims.flap.height, dpi)
    bleed_px = mm_to_px(config.output.bleed_mm, dpi)
    blank = Image.new('RGBA', (flap_w, flap_h), (0, 0, 0, 0))

    # Modules that will be rendered (>= 0 only; -1 sentinel excluded)
    processed_modules = sorted(m for m in _get_modules_to_process(config, None) if m >= 0)

    slot_groups = _group_flaps_by_slot(config.custom_flaps)
    entries = []

    for slot in sorted(slot_groups.keys()):
        slot_entries = slot_groups[slot]
        has_multimodule = any(e.type == 'multi-module' for e in slot_entries)

        if has_multimodule:
            for m in processed_modules:
                pair = None
                winning_label = None
                for cf in slot_entries:
                    if cf.module_range is not None:
                        start, end = cf.module_range
                        if not (start <= m <= end):
                            continue
                    candidate = _render_custom_flap_images(cf, config, m, dims, dpi, bleed_px)
                    if candidate is not None:
                        pair = candidate
                        winning_label = f"{cf.label} M{m} · #{slot}"
                        break
                if pair is None:
                    pair = (blank.copy(), blank.copy())
                    winning_label = f"BLANK M{m} · #{slot}"
                top = _crop_to_pocket(pair[0], flap_w, flap_h, is_top=True)
                bottom = _crop_to_pocket(pair[1], flap_w, flap_h, is_top=False)
                entries.append((top, bottom, winning_label))
        else:
            # Non-multi-module slot: use first entry, render module-agnostic
            cf = slot_entries[0]
            pair = _render_custom_flap_images(cf, config, -1, dims, dpi, bleed_px)
            if pair is not None:
                top = _crop_to_pocket(pair[0], flap_w, flap_h, is_top=True)
                bottom = _crop_to_pocket(pair[1], flap_w, flap_h, is_top=False)
                entries.append((top, bottom, f"{cf.label} · #{slot}"))

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

    # Warn upfront about multi-module slots that have coverage gaps for the
    # modules this job will process.
    slot_groups = _group_flaps_by_slot(config.custom_flaps)
    processed_module_set = {m for m in modules if m >= 0}
    for slot, entries in sorted(slot_groups.items()):
        if not any(e.type == 'multi-module' for e in entries):
            continue
        uncovered = []
        for m in sorted(processed_module_set):
            covered = any(
                e.type == 'multi-module' and e.module_range is not None
                and e.module_range[0] <= m <= e.module_range[1]
                for e in entries
            )
            if not covered:
                uncovered.append(m)
        if uncovered:
            logger.warning(
                "Slot %d ('%s'): modules %s have no coverage — will output blank flap(s)",
                slot, entries[0].label, uncovered,
            )

    for mod_idx in modules:
        if mod_idx == -1:
            mod_label = "common"
            # Pass module_index=-1 so multi-module entries are skipped;
            # common/ contains only module-agnostic (single/glyph/blank) content.
            flap_data = _resolve_flaps_for_module(config, -1, dims, dpi, bleed_px)
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

            # --- Back-side jig-flip geometry -------------------------------
            # A front-back (pancake) flip is geometrically identical to a
            # left-right flip followed by an in-plane 180° rotation:
            #     reflect_x  ==  rotate180 ∘ reflect_y
            # So the back sheet that registers correctly under a front-back
            # flip is exactly the left-right back sheet rotated 180°.
            # We therefore always BUILD the back using left-right semantics
            # (reorder + spool-at-top), then rotate the finished back image
            # 180° when the job is in front-back mode.  This keeps a single,
            # verified code path for both flip modes and guarantees the flap
            # frame (pins/notches/rounded corners) and content stay aligned
            # after the physical flip.
            back_build_flip = "left-right"

            # Generate front image
            front_img = generate_batch_image(front_batch, dims.flap, dims.jig, dims.printable, dpi, orient,
                                             spool_at_bottom=True)

            # Reorder back-side flaps to their post-jig-flip grid positions.
            reordered_back = reorder_for_jig_flip(back_batch, dims.jig, back_build_flip, orient)
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

            # Front-back flip == left-right flip + 180° in-plane rotation.
            # Rotate the fully-composed (art + mask + labels) back sheet 180°
            # so it registers under a front-back jig flip.  Done before
            # registration marks and calibration offset so those stay in
            # true sheet space.
            if flip == "front-back":
                back_img = back_img.transpose(Image.ROTATE_180)

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

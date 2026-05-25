"""Batch grid layout: arrange flap side images on the jig, apply flip
transforms, and generate ink-saving masks.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Optional

from PIL import Image, ImageDraw

from .dimensions import FlapDimensions, JigDimensions, PrintableAreaDimensions, mm_to_px


@dataclass
class FlapSide:
    """One printable side of one flap."""
    image: Image.Image          # RGBA, sized to flap_width × flap_height in pixels
    label: str                  # e.g. "EP42"
    slot_index: int             # 0-based index in the custom flap sequence
    side: str                   # "front" or "back"


def map_images_to_flap_sides(
    slot_images: list[tuple[Image.Image, Image.Image]],
    labels: list[str],
) -> tuple[list[FlapSide], list[FlapSide]]:
    """Map sliced (top, bottom) image pairs to front and back FlapSide lists.

    slot_images: list of (top_half, bottom_half) for each custom flap slot.
    labels: list of EP labels, same length as slot_images.

    Mapping rule:
      - Front of slot K = top_half of slot K's image
      - Back of slot K  = bottom_half of slot (K+1)'s image
      - Back of last slot = blank (transparent)

    Returns (fronts, backs) — parallel lists of FlapSide.
    """
    n = len(slot_images)
    fronts: list[FlapSide] = []
    backs: list[FlapSide] = []

    for k in range(n):
        top_half, _ = slot_images[k]
        fronts.append(FlapSide(
            image=top_half,
            label=labels[k],
            slot_index=k,
            side="front",
        ))

        if k + 1 < n:
            _, bottom_half = slot_images[k + 1]
        else:
            # Last slot back is blank
            bottom_half = Image.new('RGBA', top_half.size, (0, 0, 0, 0))

        backs.append(FlapSide(
            image=bottom_half,
            label=labels[k],
            slot_index=k,
            side="back",
        ))

    return fronts, backs


def generate_batch_image(
    flap_sides: list[FlapSide],
    flap: FlapDimensions,
    jig: JigDimensions,
    printable: PrintableAreaDimensions,
    dpi: float,
    orientation: str = "landscape",
    bleed_mm: float = 0.0,
) -> Image.Image:
    """Arrange up to jig.flaps_per_batch flap images on a printable-area-sized canvas.

    The canvas matches the full printable area of the printer bed.  The jig
    insert is positioned at (insert_offset_x, insert_offset_y) within that
    area, and the flap grid is positioned within the insert using margins.

    When *bleed_mm* > 0, each flap image is upscaled by 2×bleed in each
    dimension and pasted centered on its pocket position (offset by −bleed).
    This fills the bleed zone with real image content so that sub-mm jig
    misalignment doesn't expose bare flap stock.  The ink-save mask (applied
    later) clips to exactly pocket + bleed.

    If orientation is "landscape", the final image is rotated 90° CCW.

    Returns an RGBA image at the correct physical size for the given DPI.
    """
    canvas_w = mm_to_px(printable.width, dpi)
    canvas_h = mm_to_px(printable.height, dpi)

    canvas = Image.new('RGBA', (canvas_w, canvas_h), (0, 0, 0, 0))

    # Insert origin within the printable area
    insert_x_px = mm_to_px(printable.insert_offset_x, dpi)
    insert_y_px = mm_to_px(printable.insert_offset_y, dpi)

    flap_w_px = mm_to_px(flap.width, dpi)
    flap_h_px = mm_to_px(flap.height, dpi)
    bleed_px = mm_to_px(bleed_mm, dpi) if bleed_mm > 0 else 0
    margin_x_px = mm_to_px(jig.margin_x, dpi)
    margin_y_px = mm_to_px(jig.margin_y, dpi)
    space_x_px = mm_to_px(flap.width + jig.gap_x, dpi)
    space_y_px = mm_to_px(flap.height + jig.gap_y, dpi)

    # Target size: pocket + 2×bleed on each axis
    target_w = flap_w_px + 2 * bleed_px
    target_h = flap_h_px + 2 * bleed_px

    for i, fs in enumerate(flap_sides[:jig.flaps_per_batch]):
        col = i % jig.num_x
        row = i // jig.num_x

        pocket_x = insert_x_px + margin_x_px + col * space_x_px
        pocket_y = insert_y_px + margin_y_px + row * space_y_px

        # Resize to pocket + bleed, paste offset by −bleed so image is
        # centred on the pocket
        resized = fs.image.resize((target_w, target_h), Image.LANCZOS)
        canvas.paste(resized, (pocket_x - bleed_px, pocket_y - bleed_px), resized)

    if orientation == "landscape":
        canvas = canvas.transpose(Image.ROTATE_90)

    return canvas


def apply_flip_transform(image: Image.Image, flip_mode: str) -> Image.Image:
    """Flip an image to produce the back-side print layout.

    "left-right": mirror horizontally (operator flips jig left-to-right).
    "front-back": mirror vertically (operator flips jig front-to-back).
    """
    if flip_mode == "left-right":
        return image.transpose(Image.FLIP_LEFT_RIGHT)
    elif flip_mode == "front-back":
        return image.transpose(Image.FLIP_TOP_BOTTOM)
    else:
        raise ValueError(f"Unknown flip_mode: {flip_mode!r}")


def reorder_for_jig_flip(
    flap_sides: list[FlapSide],
    jig: 'JigDimensions',
    flip_mode: str,
    orientation: str = "landscape",
) -> list[FlapSide]:
    """Reorder flap sides to their post-jig-flip grid positions.

    Unlike apply_flip_transform (which mirrors the entire canvas and thus
    mirrors individual flap content), this places each flap at its
    physically-correct post-flip position while preserving the original
    content orientation.

    For landscape + left-right flip: portrait rows are reversed.
    For landscape + front-back flip: portrait columns are reversed.
    (Portrait mode is the inverse.)
    """
    if not flap_sides:
        return flap_sides

    total = jig.num_x * jig.num_y

    # Decide which grid axis to reverse
    reverse_rows = (
        (flip_mode == "left-right" and orientation == "landscape") or
        (flip_mode == "front-back" and orientation == "portrait")
    )
    reverse_cols = (
        (flip_mode == "left-right" and orientation == "portrait") or
        (flip_mode == "front-back" and orientation == "landscape")
    )

    result: list[Optional[FlapSide]] = [None] * total

    for i, fs in enumerate(flap_sides):
        col = i % jig.num_x
        row = i // jig.num_x

        new_row = (jig.num_y - 1 - row) if reverse_rows else row
        new_col = (jig.num_x - 1 - col) if reverse_cols else col

        new_i = new_row * jig.num_x + new_col
        if new_i < total:
            result[new_i] = fs

    # Fill empty slots with blank FlapSide entries
    sample_size = flap_sides[0].image.size
    filled: list[FlapSide] = []
    for entry in result:
        if entry is not None:
            filled.append(entry)
        else:
            blank = Image.new('RGBA', sample_size, (0, 0, 0, 0))
            filled.append(FlapSide(
                image=blank, label="", slot_index=-1, side="back",
            ))

    return filled


def _arc_points(cx: float, cy: float, r: float,
                start_deg: float, end_deg: float,
                steps: int = 12) -> list[tuple[int, int]]:
    """Generate points along a circular arc."""
    pts: list[tuple[int, int]] = []
    for i in range(steps + 1):
        angle = math.radians(start_deg + (end_deg - start_deg) * i / steps)
        pts.append((round(cx + r * math.cos(angle)), round(cy + r * math.sin(angle))))
    return pts


def _flap_mask_polygon(
    x: int, y: int, w: int, h: int,
    corner_r: int, notch_d: int, notch_h: int, pin_w: int,
    bleed: int, spool_at_bottom: bool,
) -> list[tuple[int, int]]:
    """Build a mask polygon: flap profile expanded outward by *bleed*.

    Outer edges expand by bleed, convex corner radii grow by bleed,
    and notch voids shrink by bleed on each edge (so the mask extends
    slightly into the notch area, providing bleed coverage along the
    notch boundaries).
    """
    b = bleed
    r = corner_r + b

    # Expanded outer bounds
    xL = x - b
    xR = x + w + b
    yT = y - b
    yB = y + h + b

    # Check if notch is large enough to remain after shrinking by bleed
    skip_notch = (notch_d <= b) or (notch_h <= 2 * b)

    pts: list[tuple[int, int]] = []

    if spool_at_bottom:
        # --- TOP edge: rounded corners (free/display edge) ---
        pts += _arc_points(xL + r, yT + r, r, 180, 270)
        pts.append((xR - r, yT))
        pts += _arc_points(xR - r, yT + r, r, 270, 360)

        if skip_notch:
            # Straight right edge to bottom
            pts.append((xR, yB))
        else:
            # Right side with notch near BOTTOM (spool edge)
            nv_top = y + h - pin_w - notch_h + b   # notch void top (shrunk down)
            nv_bot = y + h - pin_w - b              # notch void bottom (shrunk up)
            ni_r = x + w - notch_d + b              # right notch inner wall (shrunk right)

            pts.append((xR, nv_top))
            pts.append((ni_r, nv_top))
            pts.append((ni_r, nv_bot))
            pts.append((xR, nv_bot))
            pts.append((xR, yB))

        # --- BOTTOM edge: straight (spool edge) ---
        pts.append((xL, yB))

        if skip_notch:
            pass  # Left edge goes straight up to arc
        else:
            # Left side with notch near BOTTOM
            nv_top = y + h - pin_w - notch_h + b
            nv_bot = y + h - pin_w - b
            ni_l = x + notch_d - b                  # left notch inner wall (shrunk left)

            pts.append((xL, nv_bot))
            pts.append((ni_l, nv_bot))
            pts.append((ni_l, nv_top))
            pts.append((xL, nv_top))
    else:
        # --- TOP edge: straight (spool edge) ---
        pts.append((xL, yT))
        pts.append((xR, yT))

        if skip_notch:
            pts.append((xR, yB - r))
        else:
            # Right side with notch near TOP (spool edge)
            nv_top = y + pin_w + b                  # notch void top (shrunk down)
            nv_bot = y + pin_w + notch_h - b        # notch void bottom (shrunk up)
            ni_r = x + w - notch_d + b

            pts.append((xR, nv_top))
            pts.append((ni_r, nv_top))
            pts.append((ni_r, nv_bot))
            pts.append((xR, nv_bot))
            pts.append((xR, yB - r))

        # --- BOTTOM edge: rounded corners (free/display edge) ---
        pts += _arc_points(xR - r, yB - r, r, 0, 90)
        pts.append((xL + r, yB))
        pts += _arc_points(xL + r, yB - r, r, 90, 180)

        if not skip_notch:
            # Left side with notch near TOP
            nv_top = y + pin_w + b
            nv_bot = y + pin_w + notch_h - b
            ni_l = x + notch_d - b

            pts.append((xL, nv_bot))
            pts.append((ni_l, nv_bot))
            pts.append((ni_l, nv_top))
            pts.append((xL, nv_top))

    return pts


def _draw_flap_mask(
    draw: ImageDraw.ImageDraw,
    x: int, y: int,
    flap_w: int, flap_h: int,
    corner_r: int,
    notch_depth: int,
    notch_height: int,
    pin_w: int,
    bleed: int,
    spool_at_bottom: bool,
) -> None:
    """Draw one flap mask shape as a filled white polygon.

    The mask matches the actual flap profile (with notches and correct
    corner radii) expanded outward by *bleed*.
    """
    pts = _flap_mask_polygon(
        x, y, flap_w, flap_h,
        corner_r, notch_depth, notch_height, pin_w,
        bleed, spool_at_bottom,
    )
    draw.polygon(pts, fill=255)


def apply_ink_save_mask(
    image: Image.Image,
    flap: FlapDimensions,
    jig: JigDimensions,
    printable: PrintableAreaDimensions,
    dpi: float,
    bleed_mm: float = 1.0,
    orientation: str = "landscape",
    spool_at_bottom: bool = True,
) -> Image.Image:
    """Zero out alpha outside the flap pocket areas (expanded by bleed).

    This saves ink by only printing within the flap outlines + margin.
    The mask is drawn on a printable-area-sized canvas at the insert offset.

    *spool_at_bottom* controls which end of each pocket gets the notch:
    True for front batches (top halves), False for back batches (bottom halves).
    """
    mask_w = mm_to_px(printable.width, dpi)
    mask_h = mm_to_px(printable.height, dpi)

    mask = Image.new('L', (mask_w, mask_h), 0)
    draw = ImageDraw.Draw(mask)

    insert_x_px = mm_to_px(printable.insert_offset_x, dpi)
    insert_y_px = mm_to_px(printable.insert_offset_y, dpi)

    flap_w_px = mm_to_px(flap.width, dpi)
    flap_h_px = mm_to_px(flap.height, dpi)
    margin_x_px = mm_to_px(jig.margin_x, dpi)
    margin_y_px = mm_to_px(jig.margin_y, dpi)
    space_x_px = mm_to_px(flap.width + jig.gap_x, dpi)
    space_y_px = mm_to_px(flap.height + jig.gap_y, dpi)
    corner_r_px = mm_to_px(flap.corner_radius, dpi)
    notch_d_px = mm_to_px(flap.notch_depth, dpi)
    notch_h_px = mm_to_px(flap.notch_height, dpi)
    pin_w_px = mm_to_px(flap.pin_width, dpi)
    bleed_px = mm_to_px(bleed_mm, dpi)

    for row in range(jig.num_y):
        for col in range(jig.num_x):
            x = insert_x_px + margin_x_px + col * space_x_px
            y = insert_y_px + margin_y_px + row * space_y_px
            _draw_flap_mask(
                draw, x, y, flap_w_px, flap_h_px,
                corner_r_px, notch_d_px, notch_h_px, pin_w_px, bleed_px,
                spool_at_bottom,
            )

    if orientation == "landscape":
        mask = mask.transpose(Image.ROTATE_90)

    # Apply mask: zero alpha outside flap shapes
    result = image.copy()
    r, g, b, a = result.split()
    # Combine existing alpha with the flap mask
    from PIL import ImageChops
    a = ImageChops.multiply(a, mask)
    result = Image.merge('RGBA', (r, g, b, a))
    return result

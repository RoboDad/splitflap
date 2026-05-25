"""Image slicing: split display images into flap top/bottom halves,
extract module columns from multi-module images, and apply transforms.
"""

from __future__ import annotations

from PIL import Image

from .dimensions import FlapDimensions, DisplayDimensions, mm_to_px


def slice_display_image(
    image: Image.Image,
    flap: FlapDimensions,
    dpi: float,
) -> tuple[Image.Image, Image.Image]:
    """Split a full-character display image into top and bottom halves.

    The input image represents one full character as a viewer would see it:
    top-half (43mm) + gap (2.4mm) + bottom-half (43mm) = 88.4mm total.

    Returns (top_half, bottom_half) as RGBA images.
    The gap strip in the centre is discarded.
    """
    image = image.convert('RGBA')

    top_px = mm_to_px(flap.height, dpi)
    gap_px = mm_to_px(flap.gap, dpi)
    # bottom starts after top + gap
    bottom_start = top_px + gap_px

    w = image.width

    top_half = image.crop((0, 0, w, top_px))
    bottom_half = image.crop((0, bottom_start, w, bottom_start + top_px))

    return top_half, bottom_half


def extract_module_column(
    image: Image.Image,
    module_index: int,
    module_range: tuple[int, int],
    display: DisplayDimensions,
    dpi: float,
) -> Image.Image:
    """Extract a single module's column from a multi-module image.

    The input image spans modules module_range[0] through module_range[1]
    (inclusive), including the inter-module gaps.  module_index is the
    absolute module position to extract.

    Returns the column as an RGBA image with width = flap_width in pixels.
    """
    image = image.convert('RGBA')

    start_module = module_range[0]
    offset_modules = module_index - start_module

    # Position of this module's flap within the wide image:
    # Each module occupies module_pitch except the last (which is just module_width).
    # Module N's left edge = N * module_pitch from the start of the range.
    # The flap area is centred within the module pitch.
    flap_left_in_module = (display.module_pitch - display.module_width) / 2.0
    x_mm = offset_modules * display.module_pitch + flap_left_in_module

    x_px = mm_to_px(x_mm, dpi)
    w_px = mm_to_px(display.module_width, dpi)

    column = image.crop((x_px, 0, x_px + w_px, image.height))
    return column


def apply_transforms(
    image: Image.Image,
    scale: tuple[float, float] | None = None,
    crop: tuple[float, float, float, float] | None = None,
) -> Image.Image:
    """Apply optional scale and crop transforms.

    scale: (sx, sy) — multiply image dimensions by these factors.
    crop: (left%, top%, right%, bottom%) — crop percentages from each edge.
    """
    image = image.convert('RGBA')

    if crop is not None:
        left_pct, top_pct, right_pct, bottom_pct = crop
        w, h = image.size
        left = round(w * left_pct / 100)
        top = round(h * top_pct / 100)
        right = w - round(w * right_pct / 100)
        bottom = h - round(h * bottom_pct / 100)
        image = image.crop((left, top, right, bottom))

    if scale is not None:
        sx, sy = scale
        new_w = max(1, round(image.width * sx))
        new_h = max(1, round(image.height * sy))
        image = image.resize((new_w, new_h), Image.LANCZOS)

    return image


def fit_to_target(
    image: Image.Image,
    target_w: int,
    target_h: int,
    mode: str = 'fit',
) -> Image.Image:
    """Resize image to target dimensions using the specified fit mode.

    Modes:
      fit     — uniform scale to fit within target; transparent letterbox, centered.
      fill    — uniform scale to fill target; center-crop overflow.
      stretch — non-uniform resize to exact target (may distort).
      contain — no scaling; center on target canvas, clip if larger.
    """
    image = image.convert('RGBA')

    if mode == 'stretch':
        return image.resize((target_w, target_h), Image.LANCZOS)

    if mode == 'fit':
        # Scale uniformly so the image fits entirely within the target
        ratio = min(target_w / image.width, target_h / image.height)
        new_w = max(1, round(image.width * ratio))
        new_h = max(1, round(image.height * ratio))
        scaled = image.resize((new_w, new_h), Image.LANCZOS)
        canvas = Image.new('RGBA', (target_w, target_h), (0, 0, 0, 0))
        paste_x = (target_w - new_w) // 2
        paste_y = (target_h - new_h) // 2
        canvas.paste(scaled, (paste_x, paste_y), scaled)
        return canvas

    if mode == 'fill':
        # Scale uniformly so the image covers the entire target, then center-crop
        ratio = max(target_w / image.width, target_h / image.height)
        new_w = max(1, round(image.width * ratio))
        new_h = max(1, round(image.height * ratio))
        scaled = image.resize((new_w, new_h), Image.LANCZOS)
        crop_x = (new_w - target_w) // 2
        crop_y = (new_h - target_h) // 2
        return scaled.crop((crop_x, crop_y, crop_x + target_w, crop_y + target_h))

    if mode == 'contain':
        # No scaling — center the image on the target canvas as-is
        canvas = Image.new('RGBA', (target_w, target_h), (0, 0, 0, 0))
        paste_x = (target_w - image.width) // 2
        paste_y = (target_h - image.height) // 2
        canvas.paste(image, (paste_x, paste_y), image)
        return canvas

    raise ValueError(f"Unknown fit_mode: {mode!r}")

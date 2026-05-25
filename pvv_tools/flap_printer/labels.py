"""Render EP labels in the margin areas between flap pockets."""

from __future__ import annotations

from PIL import Image, ImageDraw, ImageFont

from .dimensions import FlapDimensions, JigDimensions, PrintableAreaDimensions, mm_to_px
from .layout import FlapSide


def render_labels(
    image: Image.Image,
    flap_sides: list[FlapSide],
    flap: FlapDimensions,
    jig: JigDimensions,
    printable: PrintableAreaDimensions,
    dpi: float,
    font_size_pt: int = 6,
    orientation: str = "landscape",
    flip_mode: str | None = None,
) -> Image.Image:
    """Draw EP labels in the margin/gap areas of a batch image.

    Labels are drawn in portrait orientation (matching jig SCAD coords),
    then the image is rotated to match the requested orientation.

    When *flip_mode* is set (for back-side images), labels are drawn at the
    post-flip grid positions so they align with the flipped image content.
    """
    # Work in portrait orientation for positioning
    if orientation == "landscape":
        work = image.transpose(Image.ROTATE_270)
    else:
        work = image.copy()

    draw = ImageDraw.Draw(work)

    # Font: try to use a reasonable default
    font_size_px = mm_to_px(font_size_pt * 0.3528, dpi)  # pt → mm → px
    font_size_px = max(8, font_size_px)
    try:
        font = ImageFont.truetype("arial.ttf", font_size_px)
    except (OSError, IOError):
        font = ImageFont.load_default()

    margin_x_px = mm_to_px(jig.margin_x, dpi)
    margin_y_px = mm_to_px(jig.margin_y, dpi)
    insert_x_px = mm_to_px(printable.insert_offset_x, dpi)
    insert_y_px = mm_to_px(printable.insert_offset_y, dpi)
    space_y_px = mm_to_px(flap.height + jig.gap_y, dpi)
    flap_h_px = mm_to_px(flap.height, dpi)

    label_color = (200, 200, 200, 255)  # light grey, visible on transparent bg

    for i, fs in enumerate(flap_sides[:jig.flaps_per_batch]):
        if not fs.label:
            continue

        # Compute the original (pre-flip) grid cell for item i
        col = i % jig.num_x
        row = i // jig.num_x

        # When a flip has been applied to the canvas, remap to the
        # post-flip grid position so the label lands on the correct image.
        if flip_mode is not None:
            if (flip_mode == "left-right" and orientation == "landscape") or \
               (flip_mode == "front-back" and orientation == "portrait"):
                row = jig.num_y - 1 - row
            elif (flip_mode == "left-right" and orientation == "portrait") or \
                 (flip_mode == "front-back" and orientation == "landscape"):
                col = jig.num_x - 1 - col

        y_flap_bottom = insert_y_px + margin_y_px + row * space_y_px + flap_h_px
        # Label in the gap below the flap
        label_x = insert_x_px + margin_x_px + 2
        label_y = y_flap_bottom + 1

        draw.text((label_x, label_y), fs.label, fill=label_color, font=font)

        # Also draw side indicator
        side_text = "F" if fs.side == "front" else "B"
        bbox = draw.textbbox((0, 0), fs.label, font=font)
        text_w = bbox[2] - bbox[0]
        draw.text((label_x + text_w + 4, label_y), side_text,
                  fill=(150, 150, 255, 255) if fs.side == "front" else (255, 150, 150, 255),
                  font=font)

    # Rotate back if needed
    if orientation == "landscape":
        work = work.transpose(Image.ROTATE_90)

    return work

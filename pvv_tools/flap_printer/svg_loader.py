"""SVG input support: rasterize SVG source files into PIL images.

Uses resvg-py (a Rust-backed SVG renderer) so there are no native system
library dependencies on Windows.

Vector input flows through the same downstream pipeline as raster input
(``apply_transforms`` → ``fit_to_target`` → ``slice_display_image``).  We
rasterize at a configurable supersample factor so the final fit/slice
downsample preserves edge quality.
"""

from __future__ import annotations

import io
import logging
from pathlib import Path

from PIL import Image

logger = logging.getLogger(__name__)

# resvg-py is required only when SVG inputs are used.  Import lazily so a
# missing dependency only matters for jobs that actually reference .svg
# files.
_resvg = None


def _get_resvg():
    global _resvg
    if _resvg is None:
        try:
            import resvg_py  # type: ignore
        except ImportError as e:
            raise ImportError(
                "SVG input requires resvg-py.  Install with: pip install resvg-py"
            ) from e
        _resvg = resvg_py
    return _resvg


def is_svg(path: str | Path) -> bool:
    """Return True if path has a .svg extension (case-insensitive)."""
    return str(path).lower().endswith('.svg')


def load_svg(svg_path: str | Path, target_height_px: int, supersample: float = 2.0) -> Image.Image:
    """Rasterize an SVG file to a PIL RGBA Image.

    The SVG is rendered at ``target_height_px * supersample`` pixels of
    height, preserving the aspect ratio implied by the SVG's viewBox or
    width/height attributes.  Downstream ``fit_to_target`` will then
    downsample to the exact target size, which yields better edge quality
    than rendering at 1×.

    A non-zero ``dpi`` is passed to resvg so SVG width/height attributes
    expressed in real-world units (``mm``, ``in``) are interpreted
    correctly.
    """
    resvg = _get_resvg()
    svg_path = Path(svg_path)
    if not svg_path.exists():
        raise FileNotFoundError(f"SVG source not found: {svg_path}")

    render_h = max(1, int(round(target_height_px * supersample)))
    png_bytes = resvg.svg_to_bytes(
        svg_path=str(svg_path),
        height=render_h,
        dpi=96,  # any non-zero value enables mm/in unit handling
    )
    img = Image.open(io.BytesIO(png_bytes)).convert('RGBA')
    logger.debug("Loaded SVG %s at %dx%d (supersample=%.1f)",
                 svg_path.name, img.width, img.height, supersample)
    return img

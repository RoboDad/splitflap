"""Dimension dataclasses for flap, jig, and display geometry.

Values are resolved using a two-tier chain:
  1. OpenSCAD subprocess (parses tagged echo output from PVV_splitflap_mods.scad)
  2. Job-config dimension overrides (JSON fallbacks)
  3. Hardcoded defaults (last resort)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from .scad_parser import run_openscad

logger = logging.getLogger(__name__)


def mm_to_px(mm: float, dpi: float) -> int:
    """Convert millimetres to pixels at the given DPI."""
    return round(mm / 25.4 * dpi)


def px_to_mm(px: int, dpi: float) -> float:
    """Convert pixels to millimetres at the given DPI."""
    return px * 25.4 / dpi


@dataclass(frozen=True)
class FlapDimensions:
    width: float = 54.0           # mm
    height: float = 43.0          # mm
    gap: float = 2.0              # mm — vertical gap between stacked flaps
    corner_radius: float = 3.1    # mm
    notch_height: float = 15.0    # mm
    notch_depth: float = 3.2      # mm
    pin_width: float = 1.4        # mm

    @property
    def display_height(self) -> float:
        """Full visible height of one character: top-half + gap + bottom-half."""
        return self.height * 2 + self.gap


@dataclass(frozen=True)
class JigDimensions:
    num_x: int = 1
    num_y: int = 6
    gap_x: float = 6.0            # mm between flap pockets horizontally
    gap_y: float = 6.0            # mm between flap pockets vertically
    margin_x: float = 6.0         # mm margin around grid
    margin_y: float = 6.0         # mm margin around grid

    @property
    def flaps_per_batch(self) -> int:
        return self.num_x * self.num_y

    def insert_size(self, flap: FlapDimensions) -> tuple[float, float]:
        """Return (width_mm, height_mm) of the jig insert in SCAD orientation (portrait)."""
        space_x = flap.width + self.gap_x
        space_y = flap.height + self.gap_y
        w = space_x * self.num_x - self.gap_x + 2 * self.margin_x
        h = space_y * self.num_y - self.gap_y + 2 * self.margin_y
        return (w, h)


@dataclass(frozen=True)
class PrintableAreaDimensions:
    """Printable area of the printer bed, and the insert's position within it."""
    width: float = 88.0           # mm — minibed_printable_size_x
    height: float = 330.0         # mm — minibed_printable_size_y
    insert_offset_x: float = 11.0 # mm — offset from printable left edge to insert left edge
    insert_offset_y: float = 15.0 # mm — offset from printable bottom edge to insert bottom edge


@dataclass(frozen=True)
class DisplayDimensions:
    module_pitch: float = 64.0    # mm centre-to-centre
    inter_module_gap: float = 10.0  # mm gap between adjacent flap edges
    module_width: float = 54.0    # mm (= flap_width)


@dataclass
class AllDimensions:
    flap: FlapDimensions = field(default_factory=FlapDimensions)
    jig: JigDimensions = field(default_factory=JigDimensions)
    printable: PrintableAreaDimensions = field(default_factory=PrintableAreaDimensions)
    display: DisplayDimensions = field(default_factory=DisplayDimensions)

    @staticmethod
    def from_scad(
        mods_path: Optional[str | Path] = None,
        openscad_path: Optional[str] = None,
        overrides: Optional[dict[str, float]] = None,
    ) -> AllDimensions:
        """Load dimensions with two-tier fallback: OpenSCAD → overrides → hardcoded.

        Args:
            mods_path: Path to PVV_splitflap_mods.scad (includes flap_dimensions.scad
                       via include<>, so one OpenSCAD run resolves all variables).
            openscad_path: Path to the OpenSCAD executable, or None to auto-detect.
            overrides: Optional dict of dimension fallbacks from the job config
                       (DimensionOverrides.as_dict()).  Values here fill in any
                       gaps left when OpenSCAD is unavailable.
        """
        # Tier 1: OpenSCAD echo extraction
        scad_vals: dict[str, float] = {}
        if mods_path and Path(mods_path).exists():
            result, from_cache = run_openscad(mods_path, openscad_path=openscad_path)
            if result:
                scad_vals = result
                if from_cache:
                    logger.info("Got %d dimensions from cache", len(scad_vals))
                else:
                    logger.info("Got %d dimensions from OpenSCAD", len(scad_vals))
            else:
                logger.info("OpenSCAD unavailable or failed, using fallbacks")

        # Tier 2: merge overrides underneath (scad wins)
        ov = overrides or {}

        def _get(key: str, default: float) -> float:
            """Resolve: scad_vals → overrides → hardcoded default."""
            if key in scad_vals:
                return scad_vals[key]
            if key in ov:
                return ov[key]
            return default

        flap = FlapDimensions(
            width=_get('flap_width', 54.0),
            height=_get('flap_height', 43.0),
            gap=_get('flap_gap', 2.0),
            corner_radius=_get('flap_corner_radius', 3.1),
            notch_height=_get('flap_notch_height', 15.0),
            notch_depth=_get('flap_notch_depth', 3.2),
            pin_width=_get('flap_pin_width', 1.4),
        )

        jig = JigDimensions(
            num_x=int(_get('minibed_flap_jig_num_flaps_x', 1)),
            num_y=int(_get('minibed_flap_jig_num_flaps_y', 6)),
            gap_x=_get('minibed_flap_jig_gap_x', 6.0),
            gap_y=_get('minibed_flap_jig_gap_y', 6.0),
            margin_x=_get('minibed_flap_jig_margin_x', 6.0),
            margin_y=_get('minibed_flap_jig_margin_y', 6.0),
        )

        # Compute insert offset within printable area
        insert_w, insert_h = jig.insert_size(flap)
        printable_w = _get('minibed_printable_size_x', 88.0)
        printable_h = _get('minibed_printable_size_y', 330.0)
        insert_offset_x = (printable_w - insert_w) / 2.0
        insert_offset_y = (printable_h - insert_h) / 2.0

        printable = PrintableAreaDimensions(
            width=printable_w,
            height=printable_h,
            insert_offset_x=insert_offset_x,
            insert_offset_y=insert_offset_y,
        )

        display = DisplayDimensions(
            module_width=flap.width,
        )

        return AllDimensions(flap=flap, jig=jig, printable=printable, display=display)

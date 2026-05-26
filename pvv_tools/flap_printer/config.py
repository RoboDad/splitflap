"""JSON job-file loader, validator, and config dataclasses."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# Location of the pre-rendered Epilogue per-character flap SVGs (see
# pvv_tools/generate_epilogue_flap_svgs.py).  These are bundled with the
# repository and resolved relative to this package's parent directory so
# the "epilogue" flap type works regardless of the job config's location.
_EPILOGUE_ASSETS_DIR = Path(__file__).resolve().parent.parent / 'assets' / 'epilogue_flaps'

# Must stay in sync with 3d/flap_characters.scad and the CHARACTER_LIST
# in pvv_tools/generate_epilogue_flap_svgs.py.
_EPILOGUE_CHARACTER_LIST = " ABCDEFGHIJKLMNOPQRSTUVWXYZg0123456789r.?-$'#yp,!@&w"

# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------

@dataclass
class DisplayConfig:
    num_modules: int = 48
    module_pitch_mm: float = 64.0
    inter_module_gap_mm: float = 10.0


@dataclass
class JigConfig:
    type: str = "minibed"
    flip_mode: str = "left-right"       # "left-right" | "front-back"
    output_orientation: str = "landscape"  # "landscape" | "portrait"


@dataclass
class OutputConfig:
    dpi: int = 360
    format: str = "png"
    bleed_mm: float = 1.0
    ink_save_mask: bool = True
    labels: bool = True
    label_font_size_pt: int = 6
    output_dir: str = "output"
    # Optional (width_mm, height_mm) override for the output image canvas.
    # When set, the canvas is treated as the eufyMake Studio mat working canvas
    # (origin = mat zero-point), and the jig insert is placed at absolute mat
    # coordinates from SCAD (minibed_insert_origin_x/y).  Use this to match
    # eufyMake Studio's reported canvas size (e.g. [90, 335]) without
    # touching the physical jig dimensions.  Leave unset to use the SCAD
    # printable-area size.
    canvas_size_mm: Optional[tuple[float, float]] = None
    # If true, draw thin L-shaped registration marks at the four corners of
    # the output image (bottom-right is green = eufyMake origin, others white).
    # Useful for visually verifying jig-vs-print alignment.
    registration_marks: bool = False
    # Line width (mm) for registration marks.  Larger values are more visible
    # on the print and more reliable on lower-resolution print heads.
    registration_mark_line_width_mm: float = 1.0
    # Global (dx_mm, dy_mm) shift applied to every drawn element in the
    # final output image (flap art, ink-save mask, labels, and registration
    # marks all shift together).  Use this to compensate for a systematic
    # offset between the printer's zero-point and the physical jig (e.g.
    # the eufyMake Zero-Point calibration being off by a couple of mm).
    # Positive dx moves content toward +X in the output image (in landscape
    # orientation this is the long axis); positive dy moves content toward +Y.
    # Content shifted past the image edge is clipped.
    calibration_offset_mm: tuple[float, float] = (0.0, 0.0)


VALID_FIT_MODES = ('fit', 'fill', 'stretch', 'contain')


@dataclass
class GlobalTransforms:
    scale: tuple[float, float] = (1.0, 1.0)
    crop_percent: Optional[tuple[float, float, float, float]] = None  # (left%, top%, right%, bottom%)
    fit_mode: str = 'fit'  # 'fit' | 'fill' | 'stretch' | 'contain'


@dataclass
class CustomFlap:
    slot: int                           # 0-based index within the custom flap sequence
    label: str                          # e.g. "EP42"
    source: Optional[str] = None        # image file path (resolved relative to config dir); None for blank
    type: str = "single"                # "single" | "multi-module" | "blank"
    module_range: Optional[tuple[int, int]] = None  # inclusive [start, end] for multi-module
    scale: Optional[tuple[float, float]] = None
    crop: Optional[tuple[float, float, float, float]] = None  # (left%, top%, right%, bottom%)
    fit_mode: Optional[str] = None  # per-image override; None = use global default

    # Resolved at load time
    source_path: Optional[Path] = None


@dataclass
class DimensionOverrides:
    """Optional dimension fallbacks loaded from the job config.

    These values are used when OpenSCAD is not available to extract
    dimensions from the .scad source files.  Any field left as None
    will fall through to the hardcoded defaults in dimensions.py.
    """
    flap_width: Optional[float] = None
    flap_height: Optional[float] = None
    flap_gap: Optional[float] = None
    flap_corner_radius: Optional[float] = None
    flap_notch_height: Optional[float] = None
    flap_notch_depth: Optional[float] = None
    flap_pin_width: Optional[float] = None
    jig_num_x: Optional[int] = None
    jig_num_y: Optional[int] = None
    jig_gap_x: Optional[float] = None
    jig_gap_y: Optional[float] = None
    jig_margin_x: Optional[float] = None
    jig_margin_y: Optional[float] = None
    printable_width: Optional[float] = None
    printable_height: Optional[float] = None

    # Map from config-friendly names to SCAD echo tag names
    _KEY_MAP = {
        'flap_width': 'flap_width',
        'flap_height': 'flap_height',
        'flap_gap': 'flap_gap',
        'flap_corner_radius': 'flap_corner_radius',
        'flap_notch_height': 'flap_notch_height_default',
        'flap_notch_depth': 'flap_notch_depth',
        'flap_pin_width': 'flap_pin_width',
        'jig_num_x': 'minibed_flap_jig_num_flaps_x',
        'jig_num_y': 'minibed_flap_jig_num_flaps_y',
        'jig_gap_x': 'minibed_flap_jig_gap_x',
        'jig_gap_y': 'minibed_flap_jig_gap_y',
        'jig_margin_x': 'minibed_flap_jig_margin_x',
        'jig_margin_y': 'minibed_flap_jig_margin_y',
        'printable_width': 'minibed_printable_size_x',
        'printable_height': 'minibed_printable_size_y',
    }

    def as_dict(self) -> dict[str, float]:
        """Return non-None values keyed by SCAD echo tag names."""
        result = {}
        for config_key, scad_key in self._KEY_MAP.items():
            val = getattr(self, config_key)
            if val is not None:
                result[scad_key] = val
        return result


@dataclass
class JobConfig:
    display: DisplayConfig = field(default_factory=DisplayConfig)
    jig: JigConfig = field(default_factory=JigConfig)
    output: OutputConfig = field(default_factory=OutputConfig)
    global_transforms: GlobalTransforms = field(default_factory=GlobalTransforms)
    custom_flaps: list[CustomFlap] = field(default_factory=list)
    dimensions: DimensionOverrides = field(default_factory=DimensionOverrides)

    # Metadata
    config_dir: Path = field(default_factory=lambda: Path('.'))

# ---------------------------------------------------------------------------
# Loader
# ---------------------------------------------------------------------------

def _get(d: dict, key: str, default=None):
    """Get a value from a dict, returning default if missing or None."""
    val = d.get(key)
    return val if val is not None else default


def _parse_offset(raw) -> tuple[float, float]:
    """Parse a [dx, dy] offset list/tuple into a (float, float) tuple."""
    if raw is None:
        return (0.0, 0.0)
    if len(raw) != 2:
        raise ValueError("output.calibration_offset_mm must be [dx_mm, dy_mm]")
    return (float(raw[0]), float(raw[1]))


def load_config(path: str | Path) -> JobConfig:
    """Load and validate a JSON job config file."""
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")

    with open(path, 'r', encoding='utf-8') as f:
        raw = json.load(f)

    config_dir = path.parent.resolve()

    # Display section
    d = raw.get('display', {})
    display = DisplayConfig(
        num_modules=_get(d, 'num_modules', 48),
        module_pitch_mm=_get(d, 'module_pitch_mm', 64.0),
        inter_module_gap_mm=_get(d, 'inter_module_gap_mm', 10.0),
    )

    # Jig section
    j = raw.get('jig', {})
    jig = JigConfig(
        type=_get(j, 'type', 'minibed'),
        flip_mode=_get(j, 'flip_mode', 'left-right'),
        output_orientation=_get(j, 'output_orientation', 'landscape'),
    )
    if jig.flip_mode not in ('left-right', 'front-back'):
        raise ValueError(f"Invalid flip_mode: {jig.flip_mode!r} (expected 'left-right' or 'front-back')")

    # Output section
    o = raw.get('output', {})
    canvas_raw = _get(o, 'canvas_size_mm', None)
    if canvas_raw is not None:
        if len(canvas_raw) != 2:
            raise ValueError("output.canvas_size_mm must be [width_mm, height_mm]")
        canvas_size = (float(canvas_raw[0]), float(canvas_raw[1]))
    else:
        canvas_size = None
    output = OutputConfig(
        dpi=_get(o, 'dpi', 360),
        format=_get(o, 'format', 'png'),
        bleed_mm=_get(o, 'bleed_mm', 1.0),
        ink_save_mask=_get(o, 'ink_save_mask', True),
        labels=_get(o, 'labels', True),
        label_font_size_pt=_get(o, 'label_font_size_pt', 6),
        output_dir=_get(o, 'output_dir', 'output'),
        canvas_size_mm=canvas_size,
        registration_marks=_get(o, 'registration_marks', False),
        registration_mark_line_width_mm=_get(o, 'registration_mark_line_width_mm', 1.0),
        calibration_offset_mm=_parse_offset(_get(o, 'calibration_offset_mm', [0.0, 0.0])),
    )

    # Global transforms
    gt = raw.get('global_transforms', {})
    scale_raw = _get(gt, 'scale', [1.0, 1.0])
    crop_raw = _get(gt, 'crop_percent', None)
    global_transforms = GlobalTransforms(
        scale=tuple(scale_raw) if scale_raw else (1.0, 1.0),
        crop_percent=tuple(crop_raw) if crop_raw else None,
        fit_mode=_get(gt, 'fit_mode', 'fit'),
    )
    if global_transforms.fit_mode not in VALID_FIT_MODES:
        raise ValueError(f"Invalid global fit_mode: {global_transforms.fit_mode!r} (expected one of {VALID_FIT_MODES})")

    # Custom flaps
    custom_flaps = []
    for i, cf in enumerate(raw.get('custom_flaps', [])):
        if 'slot' not in cf:
            raise ValueError(f"custom_flaps[{i}]: 'slot' is required")

        flap_type = cf.get('type', 'single')

        # The "epilogue" type is a convenience shorthand for "single" with
        # one of the pre-rendered Epilogue per-character SVGs from
        # pvv_tools/assets/epilogue_flaps/.  We resolve it here and then
        # behave exactly like a "single" SVG from this point on.
        if flap_type == 'epilogue':
            ep_index = cf.get('index')
            ep_char = cf.get('char')
            if (ep_index is None) == (ep_char is None):
                raise ValueError(
                    f"custom_flaps[{i}]: type 'epilogue' requires exactly one "
                    f"of 'index' (0-{len(_EPILOGUE_CHARACTER_LIST) - 1}) or 'char'")
            if ep_char is not None:
                if len(ep_char) != 1 or ep_char not in _EPILOGUE_CHARACTER_LIST:
                    raise ValueError(
                        f"custom_flaps[{i}]: 'char' {ep_char!r} is not in the "
                        f"Epilogue character set {_EPILOGUE_CHARACTER_LIST!r}")
                ep_index = _EPILOGUE_CHARACTER_LIST.index(ep_char)
            if not (0 <= ep_index < len(_EPILOGUE_CHARACTER_LIST)):
                raise ValueError(
                    f"custom_flaps[{i}]: 'index' {ep_index} out of range "
                    f"[0, {len(_EPILOGUE_CHARACTER_LIST) - 1}]")
            cf['source'] = str(_EPILOGUE_ASSETS_DIR / f'flap_{ep_index:02d}.svg')
            flap_type = 'single'
            if 'label' not in cf:
                ep_char_resolved = _EPILOGUE_CHARACTER_LIST[ep_index]
                cf['label'] = f"EP-{ep_char_resolved!r}" if ep_char_resolved.strip() else "EP-SP"

        # 'source' is required for non-blank types
        source_str: Optional[str] = cf.get('source')
        source_path: Optional[Path] = None
        if flap_type == 'blank':
            if source_str is not None:
                logger.warning("custom_flaps[%d]: 'source' ignored for blank type", i)
                source_str = None
        else:
            if source_str is None:
                raise ValueError(f"custom_flaps[{i}]: 'source' is required for type '{flap_type}'")
            source_path = Path(source_str)
            if not source_path.is_absolute():
                source_path = config_dir / source_path

        mr = cf.get('module_range')
        scale = cf.get('scale')
        crop = cf.get('crop')

        flap = CustomFlap(
            slot=cf['slot'],
            label=cf.get('label', f"EP{cf['slot'] + 42:02d}"),
            source=source_str,
            type=flap_type,
            module_range=tuple(mr) if mr else None,
            scale=tuple(scale) if scale else None,
            crop=tuple(crop) if crop else None,
            fit_mode=cf.get('fit_mode', None),
            source_path=source_path,
        )

        if flap.fit_mode is not None and flap.fit_mode not in VALID_FIT_MODES:
            raise ValueError(f"custom_flaps[{i}]: invalid fit_mode {flap.fit_mode!r} (expected one of {VALID_FIT_MODES})")

        if flap.type == 'multi-module' and flap.module_range is None:
            raise ValueError(f"custom_flaps[{i}]: 'module_range' is required for multi-module type")

        custom_flaps.append(flap)

    # Dimension overrides (optional fallbacks when OpenSCAD is unavailable)
    dim = raw.get('dimensions', {})
    dimensions = DimensionOverrides(
        flap_width=dim.get('flap_width'),
        flap_height=dim.get('flap_height'),
        flap_gap=dim.get('flap_gap'),
        flap_corner_radius=dim.get('flap_corner_radius'),
        flap_notch_height=dim.get('flap_notch_height'),
        flap_notch_depth=dim.get('flap_notch_depth'),
        flap_pin_width=dim.get('flap_pin_width'),
        jig_num_x=int(dim['jig_num_x']) if dim.get('jig_num_x') is not None else None,
        jig_num_y=int(dim['jig_num_y']) if dim.get('jig_num_y') is not None else None,
        jig_gap_x=dim.get('jig_gap_x'),
        jig_gap_y=dim.get('jig_gap_y'),
        jig_margin_x=dim.get('jig_margin_x'),
        jig_margin_y=dim.get('jig_margin_y'),
        printable_width=dim.get('printable_width'),
        printable_height=dim.get('printable_height'),
    )

    config = JobConfig(
        display=display,
        jig=jig,
        output=output,
        global_transforms=global_transforms,
        custom_flaps=custom_flaps,
        dimensions=dimensions,
        config_dir=config_dir,
    )

    logger.info("Loaded config: %d custom flaps, %d modules, %d DPI",
                len(custom_flaps), display.num_modules, output.dpi)
    return config


def print_summary(config: JobConfig) -> None:
    """Print a human-readable summary of the job config."""
    print(f"  Display: {config.display.num_modules} modules, "
          f"pitch={config.display.module_pitch_mm}mm, "
          f"gap={config.display.inter_module_gap_mm}mm")
    print(f"  Jig: {config.jig.type}, flip={config.jig.flip_mode}, "
          f"orient={config.jig.output_orientation}")
    print(f"  Output: {config.output.dpi} DPI, format={config.output.format}, "
          f"bleed={config.output.bleed_mm}mm, mask={config.output.ink_save_mask}, "
          f"labels={config.output.labels}")
    print(f"  Output dir: {config.output.output_dir}")
    print(f"  Fit mode: {config.global_transforms.fit_mode} (global default)")
    print(f"  Custom flaps: {len(config.custom_flaps)}")
    for cf in config.custom_flaps:
        mod_info = f", modules {cf.module_range[0]}-{cf.module_range[1]}" if cf.module_range else ""
        if cf.type == "blank":
            exists = "blank"
        elif cf.source_path and cf.source_path.exists():
            exists = "OK"
        else:
            exists = "MISSING"
        fit_info = f", fit={cf.fit_mode}" if cf.fit_mode else ""
        print(f"    [{cf.label}] slot={cf.slot}, type={cf.type}{mod_info}{fit_info}, "
              f"source={cf.source} ({exists})")

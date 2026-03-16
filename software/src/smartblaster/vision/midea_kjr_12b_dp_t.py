"""Midea KJR-12B-DP-T display parser implementation.

This parser uses fixed normalized ROIs and 7-segment decoding for the first
supported thermostat display layout.
"""

from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
import math
from typing import TypeVar

from PIL import Image, ImageDraw, ImageStat

from smartblaster.vision.models import (
    DisplayMode,
    FanSpeedLevel,
    ThermostatDisplayState,
)


@dataclass(frozen=True)
class Rect:
    x: float
    y: float
    w: float
    h: float


MODE_ROIS: dict[DisplayMode, Rect] = {
    DisplayMode.AUTO: Rect(0.17, 0.4082, 0.09476, 0.0918),
    DisplayMode.COOL: Rect(0.26476, 0.4082, 0.09476, 0.0918),
    DisplayMode.DRY: Rect(0.35952, 0.4082, 0.09476, 0.0918),
    DisplayMode.HEAT: Rect(0.45428, 0.4082, 0.09476, 0.0918),
    DisplayMode.FAN_ONLY: Rect(0.54904, 0.4082, 0.13596, 0.0918),
}

POWER_ON_ROI = Rect(0.765, 0.36, 0.075, 0.14)
FOLLOW_ME_ROI = Rect(0.69, 0.37, 0.075, 0.13)
TIMER_SET_ROI = Rect(0.17, 0.6255, 0.06, 0.1055)
TIMER_ON_ROI = Rect(0.23, 0.6255, 0.06, 0.1055)
TIMER_OFF_ROI = Rect(0.29, 0.6255, 0.06, 0.1055)
# Undocumented display glyph to the left of the setpoint digits.
# Vertical bounds: top aligned with digit top, bottom aligned to timer top.
SET_TEMP_ROI = Rect(0.17, 0.52, 0.18, 0.1055)
# Backward-compatibility alias for older ad-hoc overlay scripts.
SET_TEMPP_ROI = SET_TEMP_ROI
LOCK_ROI = Rect(0.543, 0.52, 0.06, 0.13)

FAN_ROIS: dict[FanSpeedLevel, Rect] = {
    FanSpeedLevel.LOW: Rect(0.615, 0.621, 0.072667, 0.11),
    FanSpeedLevel.MEDIUM: Rect(0.687667, 0.621, 0.072667, 0.11),
    FanSpeedLevel.HIGH: Rect(0.760334, 0.621, 0.072667, 0.11),
}

# Temperature unit is installer-configured and not displayed on this thermostat.
# Keep these legacy constants as zero-size placeholders for tooling compatibility.
UNIT_C_ROI = Rect(0.0, 0.0, 0.0, 0.0)
UNIT_F_ROI = Rect(0.0, 0.0, 0.0, 0.0)

DIGIT_1_ROI = Rect(0.35, 0.52, 0.09, 0.211)
DIGIT_2_ROI = Rect(0.45, 0.52, 0.09, 0.211)


SEGMENT_TO_DIGIT: dict[frozenset[str], int] = {
    frozenset({"a", "b", "c", "d", "e", "f"}): 0,
    frozenset({"b", "c"}): 1,
    frozenset({"a", "b", "g", "e", "d"}): 2,
    frozenset({"a", "b", "c", "d", "g"}): 3,
    frozenset({"f", "g", "b", "c"}): 4,
    frozenset({"a", "f", "g", "c", "d"}): 5,
    frozenset({"a", "f", "g", "e", "c", "d"}): 6,
    frozenset({"a", "b", "c"}): 7,
    frozenset({"a", "b", "c", "d", "e", "f", "g"}): 8,
    frozenset({"a", "b", "c", "d", "f", "g"}): 9,
}


def _segment_rects() -> dict[str, Rect]:
    # Segment rectangles relative to one digit ROI.
    return {
        "a": Rect(0.20, 0.05, 0.60, 0.12),
        "b": Rect(0.74, 0.16, 0.16, 0.30),
        "c": Rect(0.74, 0.54, 0.16, 0.30),
        "d": Rect(0.20, 0.83, 0.60, 0.12),
        "e": Rect(0.10, 0.54, 0.16, 0.30),
        "f": Rect(0.10, 0.16, 0.16, 0.30),
        "g": Rect(0.20, 0.45, 0.60, 0.12),
    }


SEGMENT_RECTS = _segment_rects()
TKey = TypeVar("TKey")

MODE_SLOT_MIN_SCORE = 0.025
MODE_SLOT_MIN_MARGIN = 0.004
FAN_SLOT_MIN_SCORE = 0.03
FAN_SLOT_MIN_MARGIN = 0.004
INDICATOR_MIN_SCORE = 0.025
POWER_ACTIVITY_MIN_SCORE = 0.25
NORMALIZED_WIDTH = 640
NORMALIZED_HEIGHT = 360

# Mode text is painted on the glass (static). Score only the active-glyph area.
MODE_FOCUS_X = 0.10
MODE_FOCUS_W = 0.55
MODE_FOCUS_Y = 0.40
MODE_FOCUS_H = 0.55

# Temperature digits are blur/noise sensitive. Evaluate a small set of
# ROI shifts/scales and use local-threshold probabilistic segment scoring.
#
# NOTE: Candidate y-offsets intentionally bias upward by about one digit height.
# This is based on overlay validation where initial boxes were aligned too low.
TEMP_LOCAL_PERCENTILE = 0.22
TEMP_SEGMENT_OFF_WEIGHT = 0.70
TEMP_SEARCH_PAD_X = 0.08
TEMP_SEARCH_PAD_Y = 0.12
TEMP_ROI_CANDIDATES: tuple[tuple[float, float, float, float], ...] = (
    # Up-shifted candidates (visual feedback driven)
    (0.00, -0.21, 1.00, 1.00),
    (0.00, -0.20, 1.00, 0.90),
    (0.02, -0.21, 0.95, 1.00),
    (-0.01, -0.22, 1.05, 1.05),
    # Additional right-shifted candidates from sample-driven score search.
    (0.08, -0.21, 1.00, 1.00),
    (0.08, -0.21, 0.95, 1.00),
    (0.07, -0.21, 1.05, 1.00),
    # Baseline candidates retained during transition to avoid abrupt regressions.
    (0.00, 0.00, 1.00, 1.00),
    (0.15, 0.01, 1.00, 0.70),
    (0.15, 0.01, 0.80, 0.70),
    (0.16, 0.18, 0.80, 1.30),
)

# Reference display position as fractions of the full camera frame.
# Derived from sample_001.jpg (the calibration image) via _estimate_display_bounds.
# These describe where the thermostat LCD sits at the nominal camera mount.
REFERENCE_DISPLAY_CX = 0.491
REFERENCE_DISPLAY_CY = 0.484
REFERENCE_DISPLAY_W_FRAC = 0.824
REFERENCE_DISPLAY_H_FRAC = 0.727
REFERENCE_DISPLAY_ASPECT_MIN = 1.4
REFERENCE_DISPLAY_ASPECT_MAX = 2.6


class MideaKjr12bDpTParser:
    model_id = "midea_kjr_12b_dp_t"

    def __init__(self, *, normalize_display: bool = True) -> None:
        # Normalize each capture to a canonical LCD crop before ROI decoding.
        self._normalize_display = normalize_display

    def parse(self, frame: bytes) -> ThermostatDisplayState:
        image = Image.open(BytesIO(frame)).convert("L")
        if self._normalize_display:
            image = _normalize_display_region(image)
        threshold = _calibrated_threshold(image)

        mode_scores = {
            mode: _slot_presence_score(image, _focus_subroi(roi, MODE_FOCUS_X, MODE_FOCUS_Y, MODE_FOCUS_W, MODE_FOCUS_H), threshold)
            for mode, roi in MODE_ROIS.items()
        }
        mode, mode_conf = _pick_winning_slot(
            mode_scores,
            min_score=MODE_SLOT_MIN_SCORE,
            min_margin=MODE_SLOT_MIN_MARGIN,
        )

        power_dark_score = _slot_presence_score(image, POWER_ON_ROI, threshold)
        power_activity_score = _slot_activity_score(image, POWER_ON_ROI, threshold)
        power_on_score = max(power_dark_score, power_activity_score)
        follow_me_score = _slot_presence_score(image, FOLLOW_ME_ROI, threshold)
        timer_set_score = _slot_presence_score(image, TIMER_SET_ROI, threshold)
        timer_on_score = _slot_presence_score(image, TIMER_ON_ROI, threshold)
        timer_off_score = _slot_presence_score(image, TIMER_OFF_ROI, threshold)
        set_temp_score = _slot_presence_score(image, SET_TEMP_ROI, threshold)
        lock_score = _slot_presence_score(image, LOCK_ROI, threshold)

        power_on_dark, power_dark_conf = _indicator_presence(power_dark_score, min_score=INDICATOR_MIN_SCORE)
        power_on_activity, power_activity_conf = _indicator_presence(
            power_activity_score,
            min_score=POWER_ACTIVITY_MIN_SCORE,
        )
        power_on = power_on_dark or power_on_activity
        power_conf = max(power_dark_conf, power_activity_conf)
        follow_me, follow_me_conf = _indicator_presence(follow_me_score, min_score=INDICATOR_MIN_SCORE)
        timer_set_raw, timer_set_conf = _indicator_presence(timer_set_score, min_score=INDICATOR_MIN_SCORE)
        timer_on, timer_on_conf = _indicator_presence(timer_on_score, min_score=INDICATOR_MIN_SCORE)
        timer_off, timer_off_conf = _indicator_presence(timer_off_score, min_score=INDICATOR_MIN_SCORE)
        # On this thermostat, timer_set often co-appears with timer_on/off icons.
        timer_set = timer_set_raw or timer_on or timer_off
        if timer_set:
            timer_set_conf = max(timer_set_conf, timer_on_conf, timer_off_conf)
        set_temp_raw, set_temp_raw_conf = _indicator_presence(set_temp_score, min_score=INDICATOR_MIN_SCORE)
        # WORKAROUND (intentional temporary behavior):
        # The set_temp glyph is too low-contrast/noisy in field images to be
        # reliable. For now, set_temp is derived from follow_me semantics.
        #
        # TODO: Replace this with direct set_temp OCR/icon detection once a
        # stable, dedicated detector is implemented and validated.
        set_temp = follow_me
        set_temp_conf = follow_me_conf if set_temp else max(0.0, min(set_temp_raw_conf, 0.35))
        lock_enabled, _ = _indicator_presence(lock_score, min_score=INDICATOR_MIN_SCORE)

        fan_scores = {level: _slot_presence_score(image, roi, threshold) for level, roi in FAN_ROIS.items()}
        fan_speed, fan_conf = _pick_winning_slot(
            fan_scores,
            min_score=FAN_SLOT_MIN_SCORE,
            min_margin=FAN_SLOT_MIN_MARGIN,
        )
        if fan_speed is None:
            fan_speed = FanSpeedLevel.OFF
            fan_conf = 0.75

        # Temperature unit is not OCR-derived for this model.
        temperature_unit = None
        unit_conf = 0.0

        if self._normalize_display:
            set_temperature, temp_conf = _decode_temperature(image, threshold, mode)
        else:
            # Preserve deterministic behaviour for synthetic/unit-test frames.
            tens = _decode_digit(image, DIGIT_1_ROI, threshold)
            ones = _decode_digit(image, DIGIT_2_ROI, threshold)
            set_temperature = None
            temp_conf = 0.0
            if tens is not None and ones is not None:
                set_temperature = float((tens * 10) + ones)
                temp_conf = 0.9

        resolved_mode = mode if mode is not None else DisplayMode.UNKNOWN
        unreadable_fields: list[str] = []
        if mode is None:
            unreadable_fields.append("mode")
        if set_temperature is None:
            unreadable_fields.append("set_temperature")
        raw_indicators = {
            **{f"mode_{m.value}": (mode_scores[m] >= MODE_SLOT_MIN_SCORE) for m in MODE_ROIS},
            "power_on": power_on,
            "follow_me": follow_me,
            "timer_set": timer_set,
            "timer_on": timer_on,
            "timer_off": timer_off,
            "set_temp": set_temp,
            "set_temp_raw": set_temp_raw,
            "lock": lock_enabled,
            "fan_low": fan_scores[FanSpeedLevel.LOW] >= FAN_SLOT_MIN_SCORE,
            "fan_medium": fan_scores[FanSpeedLevel.MEDIUM] >= FAN_SLOT_MIN_SCORE,
            "fan_high": fan_scores[FanSpeedLevel.HIGH] >= FAN_SLOT_MIN_SCORE,
        }

        return ThermostatDisplayState(
            model_id=self.model_id,
            power_on=power_on,
            mode=resolved_mode,
            set_temperature=set_temperature,
            temperature_unit=temperature_unit,
            fan_speed=fan_speed,
            timer_set=timer_set,
            timer_on_enabled=timer_on,
            timer_off_enabled=timer_off,
            follow_me_enabled=follow_me,
            lock_enabled=lock_enabled,
            raw_indicators=raw_indicators,
            confidence_by_field={
                "mode": mode_conf,
                "fan_speed": fan_conf,
                "set_temperature": temp_conf,
                "temperature_unit": unit_conf,
                "power_on": power_conf,
                "timer_set": timer_set_conf,
                "follow_me": follow_me_conf,
                "set_temp": set_temp_conf,
            },
            unreadable_fields=tuple(unreadable_fields),
        )

    def debug_overlays(self, frame: bytes) -> dict[str, Image.Image]:
        """Render parser debug overlays for visual alignment validation.

        Returns images keyed by view name:
        - original_bounds: source image with detected boundary box.
        - rois_selected: parser ROI boxes on the chosen normalized candidate.
        - rois_bounds: parser ROI boxes on bounds-aligned candidate (if produced).
        - rois_identity: parser ROI boxes on plain resize fallback.
        """
        source = Image.open(BytesIO(frame)).convert("L")

        # Original image: show detected bounds and which candidate was selected.
        bounds_view = source.convert("RGB")
        bounds = _estimate_display_bounds(source)
        if bounds is not None:
            _draw_box(bounds_view, bounds, color=(255, 215, 0))

        candidates = _normalization_candidates(source)
        selected_name, selected = _select_best_normalized_candidate(candidates)

        overlays: dict[str, Image.Image] = {
            "original_bounds": bounds_view,
            "rois_selected": _draw_rois_view(selected),
            "rois_identity": _draw_rois_view(candidates["identity"]),
            "digits_global_segments": _draw_digit_segments_view(selected, threshold=_calibrated_threshold(selected), local=False),
            "digits_local_segments": _draw_digit_segments_view(selected, threshold=0, local=True),
            "temp_candidates": _draw_temperature_candidates_view(selected),
        }

        if "bounds" in candidates:
            overlays["rois_bounds"] = _draw_rois_view(candidates["bounds"])

        return overlays


def _debug_roi_entries() -> list[tuple[str, Rect]]:
    entries: list[tuple[str, Rect]] = []
    entries.extend((f"mode_{mode.value}", roi) for mode, roi in MODE_ROIS.items())
    entries.extend(
        [
            ("power_on", POWER_ON_ROI),
            ("follow_me", FOLLOW_ME_ROI),
            ("timer_set", TIMER_SET_ROI),
            ("timer_on", TIMER_ON_ROI),
            ("timer_off", TIMER_OFF_ROI),
            ("set_temp", SET_TEMP_ROI),
            ("lock", LOCK_ROI),
            ("digit_1", DIGIT_1_ROI),
            ("digit_2", DIGIT_2_ROI),
        ]
    )
    entries.extend((f"fan_{level.value}", roi) for level, roi in FAN_ROIS.items())
    return entries


def _draw_all_rois(image: Image.Image, entries: list[tuple[str, Rect]], color: tuple[int, int, int]) -> None:
    draw = ImageDraw.Draw(image)
    width, height = image.size
    for _, roi in entries:
        x0, y0, x1, y1 = _to_box_size(width, height, roi)
        draw.rectangle((x0, y0, x1, y1), outline=color, width=2)


def _draw_rois_view(image: Image.Image) -> Image.Image:
    out = image.convert("RGB")
    _draw_all_rois(out, _debug_roi_entries(), color=(0, 255, 0))
    return out


def _draw_box(image: Image.Image, box: tuple[int, int, int, int], color: tuple[int, int, int]) -> None:
    draw = ImageDraw.Draw(image)
    x0, y0, x1, y1 = box
    draw.rectangle((x0, y0, x1, y1), outline=color, width=3)


def _draw_digit_segments_view(image: Image.Image, *, threshold: int, local: bool) -> Image.Image:
    out = image.convert("RGB")
    draw = ImageDraw.Draw(out)

    for digit_name, digit_roi in (("d1", DIGIT_1_ROI), ("d2", DIGIT_2_ROI)):
        x0, y0, x1, y1 = _to_box(out.convert("L"), digit_roi)
        draw.rectangle((x0, y0, x1, y1), outline=(0, 255, 0), width=2)

        seg_threshold = threshold
        if local:
            seg_threshold = _crop_percentile(image.crop(_to_box(image, digit_roi)), 0.22)

        for seg_name, rel in SEGMENT_RECTS.items():
            abs_roi = Rect(
                x=digit_roi.x + (digit_roi.w * rel.x),
                y=digit_roi.y + (digit_roi.h * rel.y),
                w=digit_roi.w * rel.w,
                h=digit_roi.h * rel.h,
            )
            ratio = _roi_dark_ratio(image, abs_roi, seg_threshold)
            # Red intensity indicates segment darkness ratio.
            red = int(max(0.0, min(1.0, ratio)) * 255)
            color = (red, 40, 40)
            sx0, sy0, sx1, sy1 = _to_box(image, abs_roi)
            draw.rectangle((sx0, sy0, sx1, sy1), outline=color, width=2)

        # Label each digit box for quick visual checks in overlay exports.
        draw.text((x0 + 2, max(0, y0 - 14)), digit_name, fill=(255, 255, 0))

    return out


def _draw_temperature_candidates_view(image: Image.Image) -> Image.Image:
    out = image.convert("RGB")
    draw = ImageDraw.Draw(out)

    palette = [
        (255, 0, 0),
        (255, 165, 0),
        (255, 255, 0),
        (0, 255, 255),
    ]

    y_text = 4
    static_pairs = [
        (
            _offset_scale_roi(DIGIT_1_ROI, dx, dy, sw, sh),
            _offset_scale_roi(DIGIT_2_ROI, dx, dy, sw, sh),
        )
        for dx, dy, sw, sh in TEMP_ROI_CANDIDATES
    ]

    candidate_pairs: list[tuple[str, Rect, Rect]] = []
    for idx, (r1, r2) in enumerate(static_pairs):
        if _roi_is_valid(r1) and _roi_is_valid(r2):
            candidate_pairs.append((f"c{idx}", r1, r2))

    anchor_pair, anchor_quality = _estimate_temperature_digit_rois(image)
    if anchor_pair is not None and anchor_quality > 0.0:
        candidate_pairs.append(("a0", anchor_pair[0], anchor_pair[1]))

    for i, (label_prefix, r1, r2) in enumerate(candidate_pairs):
        color = palette[i % len(palette)]

        d1, s1, _ = _decode_digit_probabilistic(image, r1)
        d2, s2, _ = _decode_digit_probabilistic(image, r2)
        temp = (d1 * 10) + d2

        x0, y0, x1, y1 = _to_box(image, r1)
        draw.rectangle((x0, y0, x1, y1), outline=color, width=2)
        x0, y0, x1, y1 = _to_box(image, r2)
        draw.rectangle((x0, y0, x1, y1), outline=color, width=2)

        label = f"{label_prefix}: {temp} ({s1:.2f},{s2:.2f})"
        draw.text((4, y_text), label, fill=color)
        y_text += 14

    return out


def _draw_anchor(image: Image.Image, cx: float, cy: float, color: tuple[int, int, int]) -> None:
    draw = ImageDraw.Draw(image)
    x = int(cx)
    y = int(cy)
    r = 6
    draw.ellipse((x - r, y - r, x + r, y + r), outline=color, width=2)
    draw.line((x - 10, y, x + 10, y), fill=color, width=2)
    draw.line((x, y - 10, x, y + 10), fill=color, width=2)


def _dark_threshold(image: Image.Image) -> int:
    mean = float(ImageStat.Stat(image).mean[0])
    # LCD "ink" is darker than background.
    return max(20, min(220, int(mean - 18)))


def _calibrated_threshold(image: Image.Image) -> int:
    """Estimate threshold from persistent label/anchor regions.

    Uses robust percentiles from high-contrast, always-present label areas to
    adapt to exposure and white balance shifts across installations.
    """
    samples: list[int] = []

    # Label anchors that are expected to remain visible across modes.
    label_rois = [
        MODE_ROIS[DisplayMode.AUTO],
        MODE_ROIS[DisplayMode.COOL],
        MODE_ROIS[DisplayMode.DRY],
        MODE_ROIS[DisplayMode.HEAT],
        MODE_ROIS[DisplayMode.FAN_ONLY],
        TIMER_SET_ROI,
        TIMER_ON_ROI,
        TIMER_OFF_ROI,
        SET_TEMP_ROI,
    ]

    for roi in label_rois:
        crop = image.crop(_to_box(image, roi))
        hist = crop.histogram()
        for value, count in enumerate(hist):
            if count <= 0:
                continue
            samples.extend([value] * min(count, 6))

    if len(samples) < 100:
        return _dark_threshold(image)

    p20 = _percentile(samples, 0.20)
    p80 = _percentile(samples, 0.80)
    if p80 <= p20:
        return _dark_threshold(image)

    threshold = int(p20 + (0.33 * (p80 - p20)))
    return max(20, min(220, threshold))


def _normalize_display_region(image: Image.Image) -> Image.Image:
    """Choose the best-scoring normalized candidate for robust alignment."""
    candidates = _normalization_candidates(image)
    _, selected = _select_best_normalized_candidate(candidates)
    return selected


def _normalization_candidates(image: Image.Image) -> dict[str, Image.Image]:
    candidates: dict[str, Image.Image] = {
        "identity": _to_normalized_canvas(image),
    }

    # Landmark-based normalization was removed: the cooling-slot and power-button
    # anchors detected wrong physical features across varied camera distances,
    # causing rotation/distortion rather than alignment.

    bounds_norm = _normalize_from_bounds(image)
    if bounds_norm is not None:
        candidates["bounds"] = bounds_norm

    return candidates


def _select_best_normalized_candidate(candidates: dict[str, Image.Image]) -> tuple[str, Image.Image]:
    if not candidates:
        raise ValueError("normalization candidates cannot be empty")

    best_name = ""
    best_image: Image.Image | None = None
    best_score = -1.0
    for name, candidate in candidates.items():
        score = _alignment_quality_score(candidate)
        if score > best_score:
            best_name = name
            best_image = candidate
            best_score = score

    if best_image is None:
        fallback_name, fallback_img = next(iter(candidates.items()))
        return (fallback_name, fallback_img)
    return (best_name, best_image)


def _normalize_from_bounds(image: Image.Image) -> Image.Image | None:
    """Align image using detected display bounds via a full-frame scale+translate.

    Unlike crop+resize, this preserves the coordinate system that the ROI
    fractions were calibrated in (full camera frame).  The transform maps the
    detected display centre/width to the reference display position, so after
    normalisation the ROI fractions land on the same display elements as they
    do on the calibration image (sample_001).
    """
    bounds = _estimate_display_bounds(image)
    if bounds is None:
        return None

    bx0, by0, bx1, by1 = bounds
    cur_w = bx1 - bx0
    cur_h = by1 - by0
    if cur_w <= 10 or cur_h <= 10:
        return None

    W, H = image.size

    # Reject bounds that capture the whole unit body instead of just the LCD.
    cur_aspect = cur_w / cur_h
    if not (REFERENCE_DISPLAY_ASPECT_MIN <= cur_aspect <= REFERENCE_DISPLAY_ASPECT_MAX):
        return None

    cur_cx_frac = (bx0 + bx1) / (2.0 * W)
    cur_cy_frac = (by0 + by1) / (2.0 * H)
    cur_w_frac = cur_w / W
    cur_h_frac = cur_h / H

    # Fit both width and height of detected LCD bounds to the reference LCD box.
    scale_x = REFERENCE_DISPLAY_W_FRAC / cur_w_frac
    scale_y = REFERENCE_DISPLAY_H_FRAC / cur_h_frac
    if not (0.35 <= scale_x <= 3.5 and 0.35 <= scale_y <= 3.5):
        return None

    # Translation: map detected display centre to reference display centre.
    tx_frac = REFERENCE_DISPLAY_CX - scale_x * cur_cx_frac
    ty_frac = REFERENCE_DISPLAY_CY - scale_y * cur_cy_frac

    out_w, out_h = NORMALIZED_WIDTH, NORMALIZED_HEIGHT

    # PIL inverse affine (src coords from dst coords):
    #   forward:  dst_px = (scale_x * out_w / W) * src_px  +  tx_frac * out_w
    #             dst_py = (scale_y * out_h / H) * src_py  +  ty_frac * out_h
    #   inverse:  src_px = W / (scale_x * out_w) * dst_px  -  tx_frac * W / scale_x
    #             src_py = H / (scale_y * out_h) * dst_py  -  ty_frac * H / scale_y
    a = W / (scale_x * out_w)
    c = -tx_frac * W / scale_x
    e = H / (scale_y * out_h)
    f = -ty_frac * H / scale_y

    return image.transform(
        (out_w, out_h),
        Image.Transform.AFFINE,
        data=(a, 0.0, c, 0.0, e, f),
        resample=Image.Resampling.BILINEAR,
    )


def _to_normalized_canvas(image: Image.Image) -> Image.Image:
    if image.size == (NORMALIZED_WIDTH, NORMALIZED_HEIGHT):
        return image
    return image.resize((NORMALIZED_WIDTH, NORMALIZED_HEIGHT), Image.Resampling.BILINEAR)


def _alignment_quality_score(image: Image.Image) -> float:
    """Estimate normalized alignment quality using persistent display labels."""
    threshold = _calibrated_threshold(image)
    rois = [
        MODE_ROIS[DisplayMode.AUTO],
        MODE_ROIS[DisplayMode.COOL],
        MODE_ROIS[DisplayMode.DRY],
        MODE_ROIS[DisplayMode.HEAT],
        MODE_ROIS[DisplayMode.FAN_ONLY],
        TIMER_SET_ROI,
        TIMER_ON_ROI,
        TIMER_OFF_ROI,
        SET_TEMP_ROI,
    ]

    score = 0.0
    for roi in rois:
        score += _slot_presence_score(image, roi, threshold)

    # Favor candidates where row labels are spread across expected x positions.
    mode_row_variation = _row_score_variation(
        image,
        [MODE_ROIS[DisplayMode.AUTO], MODE_ROIS[DisplayMode.COOL], MODE_ROIS[DisplayMode.DRY], MODE_ROIS[DisplayMode.HEAT]],
        threshold,
    )
    score += (mode_row_variation * 2.5)

    # Penalize candidates with a strongly tilted mode-label row.
    tilt = _mode_row_tilt(image)
    score -= min(1.0, tilt * 3.0)
    return score


def _row_score_variation(image: Image.Image, rois: list[Rect], threshold: int) -> float:
    vals = [_slot_presence_score(image, roi, threshold) for roi in rois]
    if not vals:
        return 0.0
    mean = sum(vals) / len(vals)
    variance = sum((v - mean) ** 2 for v in vals) / len(vals)
    return math.sqrt(max(0.0, variance))


def _mode_row_tilt(image: Image.Image) -> float:
    """Return absolute slope dy/dx for fitted mode row anchors (0 is ideal)."""
    width, height = image.size
    centers = [
        (0.22 * width, 0.45 * height),
        (0.31 * width, 0.45 * height),
        (0.40 * width, 0.45 * height),
        (0.49 * width, 0.45 * height),
        (0.60 * width, 0.45 * height),
    ]

    hits: list[tuple[float, float]] = []
    for ex, ey in centers:
        hit = _detect_dark_label_anchor(
            image=image,
            center_x=ex,
            center_y=ey,
            half_w=0.07 * width,
            half_h=0.05 * height,
        )
        if hit is None:
            continue
        hx, hy, cov = hit
        if cov < 0.01:
            continue
        hits.append((hx, hy))

    if len(hits) < 3:
        return 0.0

    xs = [p[0] for p in hits]
    ys = [p[1] for p in hits]
    x_mean = sum(xs) / len(xs)
    y_mean = sum(ys) / len(ys)
    var_x = 0.0
    cov_xy = 0.0
    for x, y in zip(xs, ys):
        dx = x - x_mean
        dy = y - y_mean
        var_x += dx * dx
        cov_xy += dx * dy
    if var_x <= 1e-6:
        return 0.0
    slope = cov_xy / var_x
    return abs(slope)


def _scaled_box(
    box: tuple[int, int, int, int],
    width: int,
    height: int,
    *,
    scale: float,
) -> tuple[int, int, int, int]:
    x0, y0, x1, y1 = box
    cx = (x0 + x1) / 2.0
    cy = (y0 + y1) / 2.0
    half_w = ((x1 - x0) * scale) / 2.0
    half_h = ((y1 - y0) * scale) / 2.0

    nx0 = int(max(0, min(width - 1, cx - half_w)))
    ny0 = int(max(0, min(height - 1, cy - half_h)))
    nx1 = int(max(nx0 + 1, min(width, cx + half_w)))
    ny1 = int(max(ny0 + 1, min(height, cy + half_h)))
    return (nx0, ny0, nx1, ny1)

    bounds = _estimate_display_bounds(image)
    if bounds is None:
        return image

    x0, y0, x1, y1 = bounds
    if x1 <= x0 + 10 or y1 <= y0 + 10:
        return image

    crop = image.crop((x0, y0, x1, y1)).resize((640, 360), Image.Resampling.BILINEAR)
    refined = _refine_normalized_alignment(crop)
    return refined if refined is not None else crop


def _refine_normalized_alignment(image: Image.Image) -> Image.Image | None:
    """Second-pass alignment in canonical space using multiple text anchors.

    This pass estimates small per-frame scale/translation drift after coarse
    normalization and applies a lightweight affine correction.
    """
    width, height = image.size
    if width < 200 or height < 120:
        return None

    # Anchor centers are expected label locations in normalized space.
    # We use multiple labels across the display width to estimate drift.
    anchors = [
        (0.22 * width, 0.45 * height),  # AUTO label region
        (0.31 * width, 0.45 * height),  # COOL label region
        (0.40 * width, 0.45 * height),  # DRY label region
        (0.49 * width, 0.45 * height),  # HEAT label region
        (0.60 * width, 0.45 * height),  # FAN ONLY label region
        (0.22 * width, 0.67 * height),  # timer/set-temp text region
    ]

    detected: list[tuple[float, float]] = []
    expected: list[tuple[float, float]] = []
    for ex, ey in anchors:
        hit = _detect_dark_label_anchor(
            image=image,
            center_x=ex,
            center_y=ey,
            half_w=0.07 * width,
            half_h=0.05 * height,
        )
        if hit is None:
            continue
        hx, hy, coverage = hit
        if coverage < 0.01:
            continue
        detected.append((hx, hy))
        expected.append((ex, ey))

    if len(detected) < 3:
        return None

    sx, tx = _fit_scale_shift([p[0] for p in detected], [p[0] for p in expected])
    sy, ty = _fit_scale_shift([p[1] for p in detected], [p[1] for p in expected])
    if sx is None or sy is None or tx is None or ty is None:
        return None

    # Guard rails: only apply small, near-isotropic refinements.
    # Strong anisotropy in this pass creates visible skew/distortion.
    if not (0.90 <= sx <= 1.10 and 0.90 <= sy <= 1.10):
        return None
    if abs(sx - sy) > 0.06:
        return None
    if abs(tx) > (0.12 * width) or abs(ty) > (0.12 * height):
        return None

    s = (sx + sy) / 2.0
    if s <= 1e-6:
        return None

    # dst = [s 0 tx; 0 s ty] * src
    # PIL needs inverse mapping src = A * dst + b
    a = 1.0 / s
    b = 0.0
    c = -tx / s
    d = 0.0
    e = 1.0 / s
    f = -ty / s
    return image.transform(
        (width, height),
        Image.Transform.AFFINE,
        data=(a, b, c, d, e, f),
        resample=Image.Resampling.BILINEAR,
    )


def _detect_dark_label_anchor(
    *,
    image: Image.Image,
    center_x: float,
    center_y: float,
    half_w: float,
    half_h: float,
) -> tuple[float, float, float] | None:
    width, height = image.size
    x0 = max(0, min(width - 1, int(center_x - half_w)))
    x1 = max(x0 + 1, min(width, int(center_x + half_w)))
    y0 = max(0, min(height - 1, int(center_y - half_h)))
    y1 = max(y0 + 1, min(height, int(center_y + half_h)))
    if x1 <= x0 or y1 <= y0:
        return None

    crop = image.crop((x0, y0, x1, y1))
    threshold = _crop_percentile(crop, 0.18)

    px = crop.load()
    sx = 0.0
    sy = 0.0
    sw = 0.0
    selected = 0
    for yy in range(crop.size[1]):
        for xx in range(crop.size[0]):
            v = int(px[xx, yy])
            if v > threshold:
                continue
            w = float((threshold - v) + 1)
            sx += (xx * w)
            sy += (yy * w)
            sw += w
            selected += 1

    if sw <= 0.0:
        return None
    area = max(1, crop.size[0] * crop.size[1])
    cx = x0 + (sx / sw)
    cy = y0 + (sy / sw)
    return (cx, cy, selected / area)


def _fit_scale_shift(src: list[float], dst: list[float]) -> tuple[float | None, float | None]:
    if len(src) != len(dst) or len(src) < 2:
        return (None, None)

    src_mean = sum(src) / len(src)
    dst_mean = sum(dst) / len(dst)
    var = 0.0
    cov = 0.0
    for x, y in zip(src, dst):
        dx = x - src_mean
        dy = y - dst_mean
        var += dx * dx
        cov += dx * dy
    if var <= 1e-6:
        return (None, None)

    scale = cov / var
    shift = dst_mean - (scale * src_mean)
    return (scale, shift)


def _normalize_from_landmarks(image: Image.Image) -> Image.Image | None:
    """Normalize using two semantic anchors: cooling slots and power button."""
    anchors = _detect_landmark_anchors(image)
    if anchors is None:
        return None

    (sx0, sy0), (sx1, sy1) = anchors
    src_dx = sx1 - sx0
    src_dy = sy1 - sy0
    src_dist = math.hypot(src_dx, src_dy)
    if src_dist < 40.0:
        return None

    out_w, out_h = NORMALIZED_WIDTH, NORMALIZED_HEIGHT
    dst_slots = (0.22 * out_w, 0.20 * out_h)
    dst_power = (0.74 * out_w, 0.08 * out_h)
    dst_dx = dst_power[0] - dst_slots[0]
    dst_dy = dst_power[1] - dst_slots[1]
    dst_dist = math.hypot(dst_dx, dst_dy)
    if dst_dist <= 1.0:
        return None

    scale = dst_dist / src_dist
    if scale < 0.35 or scale > 3.5:
        return None

    theta = math.atan2(dst_dy, dst_dx) - math.atan2(src_dy, src_dx)
    # Landmark geometry is noisy across captures; avoid large corrective rolls.
    max_theta = math.radians(2.5)
    theta = max(-max_theta, min(max_theta, theta))
    c = math.cos(theta)
    s = math.sin(theta)

    # Forward transform: dst = scale * R * src + t
    tx = dst_slots[0] - (scale * ((c * sx0) - (s * sy0)))
    ty = dst_slots[1] - (scale * ((s * sx0) + (c * sy0)))

    # PIL wants inverse mapping: src = A * dst + b
    a = c / scale
    b = s / scale
    cc = (-(c * tx) - (s * ty)) / scale
    d = -s / scale
    e = c / scale
    f = ((s * tx) - (c * ty)) / scale

    return image.transform(
        (out_w, out_h),
        Image.Transform.AFFINE,
        data=(a, b, cc, d, e, f),
        resample=Image.Resampling.BILINEAR,
    )


def _detect_landmark_anchors(image: Image.Image) -> tuple[tuple[float, float], tuple[float, float]] | None:
    # Top-left cooling slots are very dark against white plastic.
    slots = _weighted_centroid_in_window(
        image=image,
        x_bounds=(0.03, 0.38),
        y_bounds=(0.03, 0.35),
        mode="dark",
        percentile=0.08,
    )
    # Top-right power button is a bright oval in the LCD border area.
    power = _weighted_centroid_in_window(
        image=image,
        x_bounds=(0.62, 0.98),
        y_bounds=(0.03, 0.35),
        mode="bright",
        percentile=0.92,
    )

    if slots is None or power is None:
        return None

    (sx, sy, s_cov) = slots
    (px, py, p_cov) = power
    if s_cov < 0.04 or p_cov < 0.04:
        return None
    if px <= sx:
        return None
    if abs(py - sy) > (0.30 * image.size[1]):
        return None

    return ((sx, sy), (px, py))


def _weighted_centroid_in_window(
    *,
    image: Image.Image,
    x_bounds: tuple[float, float],
    y_bounds: tuple[float, float],
    mode: str,
    percentile: float,
) -> tuple[float, float, float] | None:
    width, height = image.size
    x0 = max(0, min(width - 1, int(width * x_bounds[0])))
    x1 = max(x0 + 1, min(width, int(width * x_bounds[1])))
    y0 = max(0, min(height - 1, int(height * y_bounds[0])))
    y1 = max(y0 + 1, min(height, int(height * y_bounds[1])))
    if x1 <= x0 or y1 <= y0:
        return None

    pixels = image.load()
    values: list[int] = []
    for y in range(y0, y1):
        for x in range(x0, x1):
            values.append(int(pixels[x, y]))
    if not values:
        return None

    threshold = _percentile(values, percentile)
    sx = 0.0
    sy = 0.0
    sw = 0.0
    selected = 0

    for y in range(y0, y1):
        for x in range(x0, x1):
            v = int(pixels[x, y])
            if mode == "dark":
                if v > threshold:
                    continue
                weight = float((threshold - v) + 1)
            else:
                if v < threshold:
                    continue
                weight = float((v - threshold) + 1)

            sx += (x * weight)
            sy += (y * weight)
            sw += weight
            selected += 1

    if sw <= 0.0:
        return None

    area = max(1, (x1 - x0) * (y1 - y0))
    coverage = selected / area
    return (sx / sw, sy / sw, coverage)


def _percentile(values: list[int], p: float) -> int:
    if not values:
        return 0
    ordered = sorted(values)
    idx = int(max(0.0, min(1.0, p)) * (len(ordered) - 1))
    return int(ordered[idx])


def _estimate_display_bounds(image: Image.Image) -> tuple[int, int, int, int] | None:
    width, height = image.size
    if width < 80 or height < 80:
        return None

    pixels = image.load()

    # Vertical edge-energy projection (left/right display borders).
    # Limit to the upper region to avoid lower-door and body groove edges.
    y_lo = int(height * 0.02)
    y_hi = int(height * 0.72)
    vx = [0.0] * width
    for x in range(1, width):
        s = 0.0
        for y in range(y_lo, y_hi):
            s += abs(float(pixels[x, y]) - float(pixels[x - 1, y]))
        vx[x] = s

    # Horizontal edge-energy projection (top/bottom display borders).
    # Limit to central x-range so side shadows and case edges contribute less.
    x_lo = int(width * 0.08)
    x_hi = int(width * 0.92)
    hy = [0.0] * height
    for y in range(1, height):
        s = 0.0
        for x in range(x_lo, x_hi):
            s += abs(float(pixels[x, y]) - float(pixels[x, y - 1]))
        hy[y] = s

    vx_s = _smooth_projection(vx, radius=3)
    hy_s = _smooth_projection(hy, radius=3)

    left_band = range(int(width * 0.04), int(width * 0.45))
    right_band = range(int(width * 0.55), int(width * 0.96))
    top_band = range(int(height * 0.03), int(height * 0.45))
    bottom_band = range(int(height * 0.42), int(height * 0.88))

    if not left_band or not right_band or not top_band or not bottom_band:
        return None

    left = max(left_band, key=lambda i: vx_s[i])
    right = max(right_band, key=lambda i: vx_s[i])
    top = max(top_band, key=lambda i: hy_s[i])
    bottom = max(bottom_band, key=lambda i: hy_s[i])

    box_w = right - left
    box_h = bottom - top
    if box_w < int(width * 0.30) or box_h < int(height * 0.25):
        return None

    aspect = box_w / max(1, box_h)
    if aspect < REFERENCE_DISPLAY_ASPECT_MIN or aspect > REFERENCE_DISPLAY_ASPECT_MAX:
        return None

    v_med = _median(vx_s)
    h_med = _median(hy_s)
    if v_med <= 0.0 or h_med <= 0.0:
        return None

    # Require edge peaks to be meaningfully above background projection noise.
    if vx_s[left] < (v_med * 2.0) or vx_s[right] < (v_med * 2.0):
        return None
    if hy_s[top] < (h_med * 2.0) or hy_s[bottom] < (h_med * 2.0):
        return None

    pad_x = int(width * 0.015)
    pad_y = int(height * 0.015)
    x0 = max(0, left - pad_x)
    y0 = max(0, top - pad_y)
    x1 = min(width, right + pad_x)
    y1 = min(height, bottom + pad_y)
    return (x0, y0, x1, y1)


def _smooth_projection(values: list[float], radius: int) -> list[float]:
    if radius <= 0:
        return values[:]
    out = [0.0] * len(values)
    for i in range(len(values)):
        lo = max(0, i - radius)
        hi = min(len(values), i + radius + 1)
        window = values[lo:hi]
        out[i] = sum(window) / max(1, len(window))
    return out


def _median(values: list[float]) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    n = len(ordered)
    mid = n // 2
    if n % 2 == 1:
        return float(ordered[mid])
    return float((ordered[mid - 1] + ordered[mid]) / 2.0)


def _to_box(image: Image.Image, roi: Rect) -> tuple[int, int, int, int]:
    width, height = image.size
    return _to_box_size(width, height, roi)


def _focus_subroi(roi: Rect, x_frac: float, y_frac: float, w_frac: float, h_frac: float) -> Rect:
    x = roi.x + (roi.w * x_frac)
    y = roi.y + (roi.h * y_frac)
    w = roi.w * w_frac
    h = roi.h * h_frac
    return Rect(x=x, y=y, w=w, h=h)


def _offset_scale_roi(roi: Rect, dx: float, dy: float, sw: float, sh: float) -> Rect:
    return Rect(
        x=roi.x + dx,
        y=roi.y + dy,
        w=roi.w * sw,
        h=roi.h * sh,
    )


def _to_box_size(width: int, height: int, roi: Rect) -> tuple[int, int, int, int]:
    x0 = int(max(0, min(width - 1, roi.x * width)))
    y0 = int(max(0, min(height - 1, roi.y * height)))
    x1 = int(max(x0 + 1, min(width, (roi.x + roi.w) * width)))
    y1 = int(max(y0 + 1, min(height, (roi.y + roi.h) * height)))
    return (x0, y0, x1, y1)


def _roi_dark_ratio(image: Image.Image, roi: Rect, threshold: int) -> float:
    crop = image.crop(_to_box(image, roi))
    hist = crop.histogram()
    dark = sum(hist[: threshold + 1])
    total = max(1, crop.size[0] * crop.size[1])
    return dark / total


def _expand_roi(roi: Rect, *, pad_x_factor: float, pad_y_factor: float) -> Rect:
    px = roi.w * pad_x_factor
    py = roi.h * pad_y_factor
    x = max(0.0, roi.x - px)
    y = max(0.0, roi.y - py)
    w = min(1.0 - x, roi.w + (2.0 * px))
    h = min(1.0 - y, roi.h + (2.0 * py))
    return Rect(x=x, y=y, w=w, h=h)


def _hist_dark_ratio(hist: list[int], threshold: int) -> float:
    total = sum(hist)
    if total <= 0:
        return 0.0
    dark = sum(hist[: threshold + 1])
    return dark / total


def _hist_mean(hist: list[int]) -> float:
    total = sum(hist)
    if total <= 0:
        return 0.0
    weighted = 0
    for value, count in enumerate(hist):
        weighted += (value * count)
    return weighted / total


def _slot_presence_score(image: Image.Image, roi: Rect, threshold: int) -> float:
    inner_crop = image.crop(_to_box(image, roi))
    inner_hist = inner_crop.histogram()
    inner_dark = _hist_dark_ratio(inner_hist, threshold)
    inner_mean = _hist_mean(inner_hist)

    ring_roi = _expand_roi(roi, pad_x_factor=0.30, pad_y_factor=0.35)
    ring_crop = image.crop(_to_box(image, ring_roi))
    outer_hist = ring_crop.histogram()

    # Ring histogram = expanded region histogram minus inner ROI histogram.
    ring_hist = [max(0, outer_hist[i] - inner_hist[i]) for i in range(256)]
    if sum(ring_hist) <= 0:
        return inner_dark

    ring_dark = _hist_dark_ratio(ring_hist, threshold)
    ring_mean = _hist_mean(ring_hist)

    dark_contrast = max(0.0, inner_dark - ring_dark)
    luminance_contrast = max(0.0, (ring_mean - inner_mean) / 255.0)

    # Prefer local contrast over absolute darkness to avoid all-slots-active.
    score = (dark_contrast * 1.8) + (luminance_contrast * 0.9) + (inner_dark * 0.1)
    return max(0.0, min(1.0, score))


def _slot_activity_score(image: Image.Image, roi: Rect, threshold: int) -> float:
    """Polarity-agnostic icon activity score (dark or bright glyph)."""
    inner_crop = image.crop(_to_box(image, roi))
    inner_hist = inner_crop.histogram()
    inner_dark = _hist_dark_ratio(inner_hist, threshold)
    inner_mean = _hist_mean(inner_hist)

    ring_roi = _expand_roi(roi, pad_x_factor=0.30, pad_y_factor=0.35)
    ring_crop = image.crop(_to_box(image, ring_roi))
    outer_hist = ring_crop.histogram()
    ring_hist = [max(0, outer_hist[i] - inner_hist[i]) for i in range(256)]
    if sum(ring_hist) <= 0:
        return 0.0

    ring_dark = _hist_dark_ratio(ring_hist, threshold)
    ring_mean = _hist_mean(ring_hist)

    dark_delta = abs(inner_dark - ring_dark)
    luminance_delta = abs(inner_mean - ring_mean) / 255.0
    score = (dark_delta * 1.2) + (luminance_delta * 1.4)
    return max(0.0, min(1.0, score))


def _pick_winning_slot(
    scores: dict[TKey, float],
    *,
    min_score: float,
    min_margin: float,
) -> tuple[TKey | None, float]:
    if not scores:
        return (None, 0.0)
    best_key = max(scores, key=scores.get)
    best_score = scores[best_key]
    if best_score < min_score:
        # Low confidence when no slot clears the presence floor.
        conf = 0.0 if min_score <= 0.0 else min(0.2, max(0.0, best_score / min_score) * 0.2)
        return (None, conf)

    ordered = sorted(scores.values(), reverse=True)
    second = ordered[1] if len(ordered) > 1 else 0.0
    margin = best_score - second
    if margin < min_margin:
        # Ambiguous winner: keep confidence intentionally low.
        conf = 0.0 if min_margin <= 0.0 else min(0.25, max(0.0, margin / min_margin) * 0.25)
        return (None, conf)

    confidence = min(1.0, max(0.0, (margin - min_margin) * 18.0))
    return (best_key, confidence)


def _indicator_presence(score: float, *, min_score: float) -> tuple[bool, float]:
    present = score >= min_score
    distance = (score - min_score) if present else (min_score - score)
    confidence = min(1.0, max(0.0, distance * 20.0))
    return (present, confidence)


def _decode_temperature(
    image: Image.Image,
    threshold: int,
    mode: DisplayMode | None,
) -> tuple[float | None, float]:
    best_temp: int | None = None
    best_score = -1e9
    second_score = -1e9

    roi_pairs: list[tuple[Rect, Rect, float]] = []
    for dx, dy, sw, sh in TEMP_ROI_CANDIDATES:
        tens_roi = _offset_scale_roi(DIGIT_1_ROI, dx, dy, sw, sh)
        ones_roi = _offset_scale_roi(DIGIT_2_ROI, dx, dy, sw, sh)
        if _roi_is_valid(tens_roi) and _roi_is_valid(ones_roi):
            roi_pairs.append((tens_roi, ones_roi, 0.0))

    anchor_pair, anchor_quality = _estimate_temperature_digit_rois(image)
    if anchor_pair is not None and anchor_quality > 0.0:
        roi_pairs.append((anchor_pair[0], anchor_pair[1], 0.25 * anchor_quality))

    for tens_roi, ones_roi, bonus in roi_pairs:

        tens, tens_score, tens_margin = _decode_digit_probabilistic(image, tens_roi)
        ones, ones_score, ones_margin = _decode_digit_probabilistic(image, ones_roi)

        temp = (tens * 10) + ones
        # Prioritize crisp segment matches.
        score = tens_score + ones_score + (0.25 * (tens_margin + ones_margin))
        score += bonus
        if 10 <= temp <= 35:
            score += 0.10
        # In COOL mode, heavily prefer realistic Celsius setpoints.
        if mode == DisplayMode.COOL:
            if 16 <= temp <= 32:
                score += 0.35
            else:
                score -= 0.45

        if score > best_score:
            second_score = best_score
            best_score = score
            best_temp = temp
        elif score > second_score:
            second_score = score

    if best_temp is None:
        # Fallback to legacy decoder path if candidate search produced no ROI.
        tens = _decode_digit(image, DIGIT_1_ROI, threshold)
        ones = _decode_digit(image, DIGIT_2_ROI, threshold)
        if tens is None or ones is None:
            return (None, 0.0)
        return (float((tens * 10) + ones), 0.35)

    if second_score <= -1e8:
        conf = 0.5
    else:
        conf = min(1.0, max(0.0, (best_score - second_score) * 2.0))
    return (float(best_temp), conf)


def _estimate_temperature_digit_rois(image: Image.Image) -> tuple[tuple[Rect, Rect] | None, float]:
    """Estimate two digit ROIs from dark-ink activity in the temp display band."""
    width, height = image.size
    x0 = int(max(0, (DIGIT_1_ROI.x - TEMP_SEARCH_PAD_X) * width))
    x1 = int(min(width, (DIGIT_2_ROI.x + DIGIT_2_ROI.w + TEMP_SEARCH_PAD_X) * width))
    y0 = int(max(0, (DIGIT_1_ROI.y - TEMP_SEARCH_PAD_Y) * height))
    y1 = int(min(height, (DIGIT_1_ROI.y + DIGIT_1_ROI.h + TEMP_SEARCH_PAD_Y) * height))
    if x1 <= x0 + 12 or y1 <= y0 + 12:
        return (None, 0.0)

    band = image.crop((x0, y0, x1, y1))
    th = _crop_percentile(band, TEMP_LOCAL_PERCENTILE)
    px = band.load()
    bw, bh = band.size

    col_activity = [0.0] * bw
    for xx in range(bw):
        s = 0.0
        for yy in range(bh):
            if int(px[xx, yy]) <= th:
                s += 1.0
        col_activity[xx] = s / max(1.0, bh)

    col_s = _smooth_projection(col_activity, radius=4)
    p1 = _argmax(col_s)
    if p1 is None:
        return (None, 0.0)

    # Suppress neighborhood around first peak then find second peak.
    suppress = max(3, int(0.08 * bw))
    masked = col_s[:]
    for i in range(max(0, p1 - suppress), min(bw, p1 + suppress + 1)):
        masked[i] = -1.0
    p2 = _argmax(masked)
    if p2 is None:
        return (None, 0.0)

    lx, rx = (p1, p2) if p1 < p2 else (p2, p1)
    peak_dist = max(1, rx - lx)
    digit_w_px = max(8.0, 0.9 * peak_dist)

    # Row activity around both peaks to estimate shared digit row top/bottom.
    xw0 = max(0, int(lx - (0.55 * digit_w_px)))
    xw1 = min(bw, int(rx + (0.55 * digit_w_px)))
    row_activity = [0.0] * bh
    span_w = max(1, xw1 - xw0)
    for yy in range(bh):
        s = 0.0
        for xx in range(xw0, xw1):
            if int(px[xx, yy]) <= th:
                s += 1.0
        row_activity[yy] = s / span_w

    row_s = _smooth_projection(row_activity, radius=3)
    ymax = max(row_s) if row_s else 0.0
    if ymax <= 0.0:
        return (None, 0.0)
    cut = 0.45 * ymax
    ys = [i for i, v in enumerate(row_s) if v >= cut]
    if not ys:
        return (None, 0.0)
    yt = max(0, min(ys))
    yb = min(bh - 1, max(ys))
    digit_h_px = max(10.0, float(yb - yt + 1))

    # Convert pixel coordinates in band back to normalized image coordinates.
    def to_roi(cx_px: float) -> Rect:
        cx = (x0 + cx_px) / width
        y = (y0 + yt) / height
        w = digit_w_px / width
        h = digit_h_px / height
        x = cx - (w / 2.0)
        return Rect(x=x, y=y, w=w, h=h)

    r1 = to_roi(float(lx))
    r2 = to_roi(float(rx))
    if not _roi_is_valid(r1) or not _roi_is_valid(r2):
        return (None, 0.0)

    # Reject anchors that drift too far from the expected 2-digit display row.
    overlap = (_rect_overlap_fraction(r1, DIGIT_1_ROI) + _rect_overlap_fraction(r2, DIGIT_2_ROI)) / 2.0
    if overlap < 0.25:
        return (None, 0.0)

    # Quality based on peak prominence and row confidence.
    baseline = 0.0
    if col_s:
        sorted_col = sorted(col_s)
        mid = len(sorted_col) // 2
        if len(sorted_col) % 2:
            baseline = sorted_col[mid]
        else:
            baseline = (sorted_col[mid - 1] + sorted_col[mid]) / 2.0
    p1v = col_s[p1]
    p2v = col_s[p2]
    prominence = max(0.0, ((p1v - baseline) + (p2v - baseline)) / 2.0)
    quality = max(0.0, min(1.0, ((prominence * 2.0) + (ymax * 0.8)) * min(1.0, overlap / 0.6)))
    return ((r1, r2), quality)


def _argmax(values: list[float]) -> int | None:
    if not values:
        return None
    best_i = 0
    best_v = values[0]
    for i in range(1, len(values)):
        if values[i] > best_v:
            best_v = values[i]
            best_i = i
    return best_i


def _rect_overlap_fraction(a: Rect, b: Rect) -> float:
    ax0 = a.x
    ay0 = a.y
    ax1 = a.x + a.w
    ay1 = a.y + a.h
    bx0 = b.x
    by0 = b.y
    bx1 = b.x + b.w
    by1 = b.y + b.h

    ix0 = max(ax0, bx0)
    iy0 = max(ay0, by0)
    ix1 = min(ax1, bx1)
    iy1 = min(ay1, by1)
    if ix1 <= ix0 or iy1 <= iy0:
        return 0.0

    inter = (ix1 - ix0) * (iy1 - iy0)
    amin = min(max(1e-9, a.w * a.h), max(1e-9, b.w * b.h))
    return max(0.0, min(1.0, inter / amin))


def _decode_digit_probabilistic(image: Image.Image, digit_roi: Rect) -> tuple[int, float, float]:
    crop = image.crop(_to_box(image, digit_roi))
    threshold = _crop_percentile(crop, TEMP_LOCAL_PERCENTILE)

    ratios: dict[str, float] = {}
    for segment_name, rel in SEGMENT_RECTS.items():
        abs_roi = Rect(
            x=digit_roi.x + (digit_roi.w * rel.x),
            y=digit_roi.y + (digit_roi.h * rel.y),
            w=digit_roi.w * rel.w,
            h=digit_roi.h * rel.h,
        )
        ratios[segment_name] = _roi_dark_ratio(image, abs_roi, threshold)

    best_digit = 0
    best_score = -1e9
    second_score = -1e9
    for digit, segments_on in _digit_segment_map().items():
        on_mean = sum(ratios[s] for s in segments_on) / max(1, len(segments_on))
        segments_off = set(SEGMENT_RECTS.keys()) - segments_on
        off_mean = 0.0
        if segments_off:
            off_mean = sum(ratios[s] for s in segments_off) / len(segments_off)
        score = on_mean - (TEMP_SEGMENT_OFF_WEIGHT * off_mean)

        if score > best_score:
            second_score = best_score
            best_score = score
            best_digit = digit
        elif score > second_score:
            second_score = score

    margin = max(0.0, best_score - second_score)
    return (best_digit, best_score, margin)


def _roi_is_valid(roi: Rect) -> bool:
    if roi.w <= 0.0 or roi.h <= 0.0:
        return False
    if roi.x < 0.0 or roi.y < 0.0:
        return False
    if (roi.x + roi.w) > 1.0 or (roi.y + roi.h) > 1.0:
        return False
    return True


def _decode_digit(image: Image.Image, digit_roi: Rect, threshold: int) -> int | None:
    segment_hits: set[str] = set()
    for segment_name, rel in SEGMENT_RECTS.items():
        abs_roi = Rect(
            x=digit_roi.x + (digit_roi.w * rel.x),
            y=digit_roi.y + (digit_roi.h * rel.y),
            w=digit_roi.w * rel.w,
            h=digit_roi.h * rel.h,
        )
        # Require ≥35% of the segment ROI to be dark.  A partial overlap from a
        # neighbouring indicator (e.g. the °C symbol overlapping the right edge
        # of DIGIT_2) only darkens ~22% of the affected segment, so raising the
        # threshold from 0.20 to 0.35 prevents false segment hits while still
        # reliably detecting fully-illuminated segments (typically 80%+ dark).
        if _roi_dark_ratio(image, abs_roi, threshold) >= 0.35:
            segment_hits.add(segment_name)

    if segment_hits:
        exact = SEGMENT_TO_DIGIT.get(frozenset(segment_hits))
        if exact is not None:
            return exact

    # Fallback: template match in normalized digit space for blur/exposure drift.
    return _decode_digit_template(image, digit_roi)


def _decode_digit_template(image: Image.Image, digit_roi: Rect) -> int | None:
    crop = image.crop(_to_box(image, digit_roi)).resize((40, 72), Image.Resampling.BILINEAR)
    threshold = _crop_percentile(crop, 0.33)

    mask: list[int] = []
    px = crop.load()
    for y in range(crop.size[1]):
        for x in range(crop.size[0]):
            mask.append(1 if int(px[x, y]) <= threshold else 0)

    best_digit: int | None = None
    best_score = -1.0
    second = -1.0
    for digit, template in _digit_templates().items():
        score = _binary_iou(mask, template)
        if score > best_score:
            second = best_score
            best_score = score
            best_digit = digit
        elif score > second:
            second = score

    # Require a minimally plausible match with some separation.
    if best_digit is None:
        return None
    if best_score < 0.18:
        return None
    if (best_score - second) < 0.01:
        return None
    return best_digit


def _digit_templates() -> dict[int, list[int]]:
    if hasattr(_digit_templates, "_cache"):
        return getattr(_digit_templates, "_cache")

    out: dict[int, list[int]] = {}
    width, height = 40, 72
    for digit, segments in _digit_segment_map().items():
        img = Image.new("L", (width, height), 255)
        draw = ImageDraw.Draw(img)
        for seg in segments:
            rel = SEGMENT_RECTS[seg]
            x0 = int(rel.x * width)
            y0 = int(rel.y * height)
            x1 = int((rel.x + rel.w) * width)
            y1 = int((rel.y + rel.h) * height)
            draw.rectangle((x0, y0, x1, y1), fill=0)

        px = img.load()
        bits: list[int] = []
        for y in range(height):
            for x in range(width):
                bits.append(1 if int(px[x, y]) < 128 else 0)
        out[digit] = bits

    setattr(_digit_templates, "_cache", out)
    return out


def _digit_segment_map() -> dict[int, set[str]]:
    return {
        0: {"a", "b", "c", "d", "e", "f"},
        1: {"b", "c"},
        2: {"a", "b", "d", "e", "g"},
        3: {"a", "b", "c", "d", "g"},
        4: {"b", "c", "f", "g"},
        5: {"a", "c", "d", "f", "g"},
        6: {"a", "c", "d", "e", "f", "g"},
        7: {"a", "b", "c"},
        8: {"a", "b", "c", "d", "e", "f", "g"},
        9: {"a", "b", "c", "d", "f", "g"},
    }


def _crop_percentile(crop: Image.Image, p: float) -> int:
    hist = crop.histogram()
    total = sum(hist)
    if total <= 0:
        return 127
    target = int(total * max(0.0, min(1.0, p)))
    c = 0
    for i, v in enumerate(hist):
        c += v
        if c >= target:
            return i
    return 255


def _binary_iou(a: list[int], b: list[int]) -> float:
    if len(a) != len(b) or not a:
        return 0.0
    inter = 0
    union = 0
    for x, y in zip(a, b):
        if x == 1 or y == 1:
            union += 1
            if x == 1 and y == 1:
                inter += 1
    if union == 0:
        return 0.0
    return inter / union

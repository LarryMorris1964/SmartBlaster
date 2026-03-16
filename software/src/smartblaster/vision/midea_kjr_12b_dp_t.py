"""Midea KJR-12B-DP-T display parser implementation.

This parser uses fixed normalized ROIs and 7-segment decoding for the first
supported thermostat display layout.
"""

from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
import math
from typing import TypeVar

from PIL import Image, ImageStat

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


class MideaKjr12bDpTParser:
    model_id = "midea_kjr_12b_dp_t"

    def __init__(self, *, normalize_display: bool = True) -> None:
        # Normalize each capture to a canonical LCD crop before ROI decoding.
        self._normalize_display = normalize_display

    def parse(self, frame: bytes) -> ThermostatDisplayState:
        image = Image.open(BytesIO(frame)).convert("L")
        if self._normalize_display:
            image = _normalize_display_region(image)
        threshold = _dark_threshold(image)

        mode_scores = {mode: _roi_dark_ratio(image, roi, threshold) for mode, roi in MODE_ROIS.items()}
        mode, mode_conf = _pick_best(mode_scores, min_score=0.025)

        power_on_score = _roi_dark_ratio(image, POWER_ON_ROI, threshold)
        follow_me_score = _roi_dark_ratio(image, FOLLOW_ME_ROI, threshold)
        timer_set_score = _roi_dark_ratio(image, TIMER_SET_ROI, threshold)
        timer_on_score = _roi_dark_ratio(image, TIMER_ON_ROI, threshold)
        timer_off_score = _roi_dark_ratio(image, TIMER_OFF_ROI, threshold)
        set_temp_score = _roi_dark_ratio(image, SET_TEMP_ROI, threshold)
        lock_score = _roi_dark_ratio(image, LOCK_ROI, threshold)

        fan_scores = {level: _roi_dark_ratio(image, roi, threshold) for level, roi in FAN_ROIS.items()}
        fan_speed, fan_conf = _pick_best(fan_scores, min_score=0.03)
        if fan_speed is None:
            fan_speed = FanSpeedLevel.OFF
            fan_conf = 0.75

        # Temperature unit is not OCR-derived for this model.
        temperature_unit = None
        unit_conf = 0.0

        tens = _decode_digit(image, DIGIT_1_ROI, threshold)
        ones = _decode_digit(image, DIGIT_2_ROI, threshold)
        set_temperature: float | None = None
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
            **{f"mode_{m.value}": (mode_scores[m] >= 0.025) for m in MODE_ROIS},
            "power_on": power_on_score >= 0.025,
            "follow_me": follow_me_score >= 0.025,
            "timer_set": timer_set_score >= 0.025,
            "timer_on": timer_on_score >= 0.025,
            "timer_off": timer_off_score >= 0.025,
            "set_temp": set_temp_score >= 0.025,
            "lock": lock_score >= 0.025,
            "fan_low": fan_scores[FanSpeedLevel.LOW] >= 0.03,
            "fan_medium": fan_scores[FanSpeedLevel.MEDIUM] >= 0.03,
            "fan_high": fan_scores[FanSpeedLevel.HIGH] >= 0.03,
        }

        return ThermostatDisplayState(
            model_id=self.model_id,
            power_on=(power_on_score >= 0.025),
            mode=resolved_mode,
            set_temperature=set_temperature,
            temperature_unit=temperature_unit,
            fan_speed=fan_speed,
            timer_set=(timer_set_score >= 0.025),
            timer_on_enabled=(timer_on_score >= 0.025),
            timer_off_enabled=(timer_off_score >= 0.025),
            follow_me_enabled=(follow_me_score >= 0.025),
            lock_enabled=(lock_score >= 0.025),
            raw_indicators=raw_indicators,
            confidence_by_field={
                "mode": mode_conf,
                "fan_speed": fan_conf,
                "set_temperature": temp_conf,
                "temperature_unit": unit_conf,
                "power_on": min(1.0, power_on_score * 8),
                "timer_set": min(1.0, timer_set_score * 8),
                "follow_me": min(1.0, follow_me_score * 8),
                "set_temp": min(1.0, set_temp_score * 8),
            },
            unreadable_fields=tuple(unreadable_fields),
        )


def _dark_threshold(image: Image.Image) -> int:
    mean = float(ImageStat.Stat(image).mean[0])
    # LCD "ink" is darker than background.
    return max(20, min(220, int(mean - 18)))


def _normalize_display_region(image: Image.Image) -> Image.Image:
    """Crop to detected LCD region and resize to a stable working size.

    Falls back to the original image if boundary detection is low-confidence.
    """
    aligned = _normalize_from_landmarks(image)
    if aligned is not None:
        return aligned

    bounds = _estimate_display_bounds(image)
    if bounds is None:
        return image

    x0, y0, x1, y1 = bounds
    if x1 <= x0 + 10 or y1 <= y0 + 10:
        return image

    crop = image.crop((x0, y0, x1, y1))
    return crop.resize((640, 360), Image.Resampling.BILINEAR)


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

    out_w, out_h = 640, 360
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
    if s_cov < 0.03 or p_cov < 0.03:
        return None
    if px <= sx:
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

    # Vertical edge-energy projection (detect left/right display border).
    vx = [0.0] * width
    for x in range(1, width):
        s = 0.0
        for y in range(height):
            s += abs(float(pixels[x, y]) - float(pixels[x - 1, y]))
        vx[x] = s

    # Horizontal edge-energy projection (detect top/bottom display border).
    hy = [0.0] * height
    for y in range(1, height):
        s = 0.0
        for x in range(width):
            s += abs(float(pixels[x, y]) - float(pixels[x, y - 1]))
        hy[y] = s

    vx_s = _smooth_projection(vx, radius=3)
    hy_s = _smooth_projection(hy, radius=3)

    left_band = range(int(width * 0.05), int(width * 0.45))
    right_band = range(int(width * 0.55), int(width * 0.95))
    top_band = range(int(height * 0.05), int(height * 0.45))
    bottom_band = range(int(height * 0.55), int(height * 0.95))

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

    v_med = _median(vx_s)
    h_med = _median(hy_s)
    if v_med <= 0.0 or h_med <= 0.0:
        return None

    # Require edge peaks to be meaningfully above background projection noise.
    if vx_s[left] < (v_med * 2.0) or vx_s[right] < (v_med * 2.0):
        return None
    if hy_s[top] < (h_med * 2.0) or hy_s[bottom] < (h_med * 2.0):
        return None

    pad_x = int(width * 0.02)
    pad_y = int(height * 0.02)
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


def _pick_best(scores: dict[TKey, float], *, min_score: float) -> tuple[TKey | None, float]:
    if not scores:
        return (None, 0.0)
    best_key = max(scores, key=scores.get)
    best_score = scores[best_key]
    if best_score < min_score:
        return (None, best_score)

    ordered = sorted(scores.values(), reverse=True)
    second = ordered[1] if len(ordered) > 1 else 0.0
    confidence = min(1.0, max(0.0, best_score - second) * 8.0)
    return (best_key, confidence)


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

    if not segment_hits:
        return None
    return SEGMENT_TO_DIGIT.get(frozenset(segment_hits))

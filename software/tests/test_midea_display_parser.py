from __future__ import annotations

from io import BytesIO

from PIL import Image, ImageDraw

from smartblaster.vision.midea_kjr_12b_dp_t import (
    DIGIT_1_ROI,
    DIGIT_2_ROI,
    FAN_ROIS,
    FOLLOW_ME_ROI,
    LOCK_ROI,
    MODE_ROIS,
    MideaKjr12bDpTParser,
    POWER_ON_ROI,
    SEGMENT_RECTS,
    TIMER_OFF_ROI,
    TIMER_ON_ROI,
    TIMER_SET_ROI,
)
from smartblaster.vision.models import DisplayMode, FanSpeedLevel


DIGIT_TO_SEGMENTS = {
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


def _to_box(width: int, height: int, roi) -> tuple[int, int, int, int]:
    x0 = int(roi.x * width)
    y0 = int(roi.y * height)
    x1 = int((roi.x + roi.w) * width)
    y1 = int((roi.y + roi.h) * height)
    return (x0, y0, x1, y1)


def _draw_roi(draw: ImageDraw.ImageDraw, width: int, height: int, roi) -> None:
    draw.rectangle(_to_box(width, height, roi), fill=0)


def _draw_digit(draw: ImageDraw.ImageDraw, width: int, height: int, digit_roi, value: int) -> None:
    for seg in DIGIT_TO_SEGMENTS[value]:
        rel = SEGMENT_RECTS[seg]
        abs_roi = type(digit_roi)(
            x=digit_roi.x + (digit_roi.w * rel.x),
            y=digit_roi.y + (digit_roi.h * rel.y),
            w=digit_roi.w * rel.w,
            h=digit_roi.h * rel.h,
        )
        _draw_roi(draw, width, height, abs_roi)


def _render_frame(*, mode: DisplayMode, temp: int, fan: FanSpeedLevel, timer: bool, follow_me: bool, power_on: bool, lock: bool = False) -> bytes:
    width, height = 1000, 500
    image = Image.new("L", (width, height), 240)
    draw = ImageDraw.Draw(image)

    _draw_roi(draw, width, height, MODE_ROIS[mode])

    if power_on:
        _draw_roi(draw, width, height, POWER_ON_ROI)
    if follow_me:
        _draw_roi(draw, width, height, FOLLOW_ME_ROI)
    if timer:
        _draw_roi(draw, width, height, TIMER_SET_ROI)
        _draw_roi(draw, width, height, TIMER_ON_ROI)
    if lock:
        _draw_roi(draw, width, height, LOCK_ROI)

    if fan in FAN_ROIS:
        _draw_roi(draw, width, height, FAN_ROIS[fan])

    tens = temp // 10
    ones = temp % 10
    _draw_digit(draw, width, height, DIGIT_1_ROI, tens)
    _draw_digit(draw, width, height, DIGIT_2_ROI, ones)

    buf = BytesIO()
    image.save(buf, format="JPEG")
    return buf.getvalue()


def test_midea_parser_extracts_mode_temp_unit_fan_timer_followme_and_power() -> None:
    parser = MideaKjr12bDpTParser(normalize_display=False)
    frame = _render_frame(
        mode=DisplayMode.COOL,
        temp=24,
        fan=FanSpeedLevel.HIGH,
        timer=True,
        follow_me=True,
        power_on=True,
        lock=True,
    )

    state = parser.parse(frame)

    assert state.mode == DisplayMode.COOL
    assert state.set_temperature == 24.0
    assert state.temperature_unit is None
    assert state.fan_speed == FanSpeedLevel.HIGH
    assert state.timer_set is True
    assert state.follow_me_enabled is True
    assert state.power_on is True
    assert state.lock_enabled is True


def test_midea_parser_reports_fan_off_when_no_fan_indicator() -> None:
    parser = MideaKjr12bDpTParser(normalize_display=False)
    frame = _render_frame(
        mode=DisplayMode.HEAT,
        temp=75,
        fan=FanSpeedLevel.UNKNOWN,
        timer=False,
        follow_me=False,
        power_on=True,
    )

    state = parser.parse(frame)

    assert state.mode == DisplayMode.HEAT
    assert state.set_temperature == 75.0
    assert state.temperature_unit is None
    assert state.fan_speed == FanSpeedLevel.OFF
    assert state.timer_set is False
    assert state.follow_me_enabled is False

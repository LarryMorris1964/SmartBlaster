"""SmartBlaster CLI for sending Midea commands to the ESP32 bridge."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys
import uuid
from typing import TextIO

from smartblaster.hardware.camera import CameraService
from smartblaster.ir.command import MideaFan, MideaIrCommand, MideaMode, MideaPreset, MideaSwing
from smartblaster.ir.transport import Esp32IrBridgeClient
from smartblaster.services.thermostat_status import ThermostatStatusService
from smartblaster.vision.dataset import validate_labels_manifest
from smartblaster.vision.evaluation import evaluate_dataset
from smartblaster.vision.registry import create_parser_for_model


def create_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="smartblaster-cli", description="Send SmartBlaster IR commands")
    parser.add_argument("--serial-port", default="COM3", help="Serial port (e.g. COM3, /dev/ttyUSB0)")
    parser.add_argument("--baud", type=int, default=115200, help="Serial baud rate")

    sub = parser.add_subparsers(dest="command", required=True)

    set_cmd = sub.add_parser("set", help="Send HVAC state command")
    set_cmd.add_argument("--mode", choices=[m.value for m in MideaMode], required=True)
    set_cmd.add_argument("--temp", type=float, dest="temperature_c")
    set_cmd.add_argument("--fan", choices=[f.value for f in MideaFan], default=MideaFan.AUTO.value)
    set_cmd.add_argument("--swing", choices=[s.value for s in MideaSwing], default=MideaSwing.OFF.value)
    set_cmd.add_argument("--preset", choices=[p.value for p in MideaPreset], default=MideaPreset.NONE.value)
    set_cmd.add_argument("--follow-me", type=float, dest="follow_me_c")
    set_cmd.add_argument("--beeper", action="store_true")

    sub.add_parser("off", help="Power off HVAC")

    status_cmd = sub.add_parser("status", help="Capture and parse thermostat display status")
    status_cmd.add_argument("--model-id", default="midea_kjr_12b_dp_t")
    status_cmd.add_argument("--history-file", default="data/thermostat_status_history.log")
    status_cmd.add_argument("--diagnostic-save-images", action="store_true")
    status_cmd.add_argument("--diagnostic-image-dir", default="data/status_images")

    eval_cmd = sub.add_parser("vision-eval", help="Evaluate parser on labeled image dataset")
    eval_cmd.add_argument("--model-id", default="midea_kjr_12b_dp_t")
    eval_cmd.add_argument("--images-dir", required=True)
    eval_cmd.add_argument("--labels-file", required=True, help="JSONL labels manifest")
    eval_cmd.add_argument("--output-report", default="data/vision_eval_report.json")

    validate_cmd = sub.add_parser("vision-validate-labels", help="Validate JSONL labels manifest")
    validate_cmd.add_argument("--labels-file", required=True, help="JSONL labels manifest")
    validate_cmd.add_argument("--images-dir", help="Optional image directory to check filename existence")

    debug_cmd = sub.add_parser("vision-debug-overlays", help="Render vision debug overlays for input images")
    debug_cmd.add_argument("--model-id", default="midea_kjr_12b_dp_t")
    debug_cmd.add_argument("--images-dir", required=True)
    debug_cmd.add_argument("--output-dir", required=True)
    debug_cmd.add_argument(
        "--include-auxiliary-images",
        action="store_true",
        help="Include helper/overlay source files such as *_rois.jpg",
    )

    return parser


def build_command_from_args(args: argparse.Namespace) -> MideaIrCommand:
    if args.command == "off":
        return MideaIrCommand(mode=MideaMode.OFF)

    return MideaIrCommand(
        mode=MideaMode(args.mode),
        temperature_c=args.temperature_c,
        fan=MideaFan(args.fan),
        swing=MideaSwing(args.swing),
        preset=MideaPreset(args.preset),
        follow_me_c=args.follow_me_c,
        beeper=args.beeper,
    )


def _open_serial_as_text(port: str, baud: int) -> TextIO:
    try:
        import serial  # type: ignore
    except ImportError as ex:
        raise RuntimeError("pyserial is required for CLI serial transport") from ex

    ser = serial.Serial(port=port, baudrate=baud, timeout=0.1)
    return ser  # pyserial object provides read/write/flush/readline compatible APIs


def main(argv: list[str] | None = None) -> int:
    parser = create_parser()
    args = parser.parse_args(argv)

    if args.command == "status":
        return _handle_status_command(args)
    if args.command == "vision-eval":
        return _handle_vision_eval_command(args)
    if args.command == "vision-validate-labels":
        return _handle_vision_validate_labels_command(args)
    if args.command == "vision-debug-overlays":
        return _handle_vision_debug_overlays_command(args)

    command = build_command_from_args(args)

    request_id = str(uuid.uuid4())
    stream = _open_serial_as_text(args.serial_port, args.baud)
    client = Esp32IrBridgeClient(stream)

    ack = client.send_command(command, request_id=request_id)
    if not ack.get("ok", False):
        print(f"FAILED: {ack}")
        return 2

    print(f"OK request_id={request_id}")
    return 0


def _handle_status_command(args: argparse.Namespace) -> int:
    parser = create_parser_for_model(args.model_id)
    camera = CameraService()
    service = ThermostatStatusService(
        camera=camera,
        parser=parser,
        history_file=Path(args.history_file),
        diagnostic_save_images=bool(args.diagnostic_save_images),
        diagnostic_image_dir=Path(args.diagnostic_image_dir),
    )
    state = service.request_status()
    print(
        "STATUS "
        f"mode={state.mode.value} "
        f"power_on={state.power_on} "
        f"temp={state.set_temperature} "
        f"unit={(state.temperature_unit.value if state.temperature_unit else None)} "
        f"fan={state.fan_speed.value} "
        f"timer_set={state.timer_set} "
        f"follow_me={state.follow_me_enabled}"
    )
    return 0


def _handle_vision_eval_command(args: argparse.Namespace) -> int:
    parser = create_parser_for_model(args.model_id)
    summary = evaluate_dataset(
        parser=parser,
        images_dir=Path(args.images_dir),
        labels_file=Path(args.labels_file),
        output_report=Path(args.output_report),
    )
    print(
        "VISION_EVAL "
        f"images={summary['images']} "
        f"all_correct_images={summary['all_correct_images']} "
        f"report={args.output_report}"
    )
    return 0


def _handle_vision_validate_labels_command(args: argparse.Namespace) -> int:
    labels_file = Path(args.labels_file)
    images_dir = Path(args.images_dir) if args.images_dir else None
    issues = validate_labels_manifest(labels_file, images_dir=images_dir)

    if issues:
        print("VISION_LABELS_INVALID")
        for issue in issues:
            print(f"- {issue}")
        return 2

    print(f"VISION_LABELS_OK labels={args.labels_file}")
    return 0


def _handle_vision_debug_overlays_command(args: argparse.Namespace) -> int:
    parser = create_parser_for_model(args.model_id)
    if not hasattr(parser, "debug_overlays"):
        print(f"VISION_DEBUG_UNSUPPORTED model_id={args.model_id}")
        return 2

    images_dir = Path(args.images_dir)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    image_paths = sorted(
        p
        for p in images_dir.iterdir()
        if p.is_file()
        and p.suffix.lower() in {".jpg", ".jpeg", ".png", ".bmp"}
        and (args.include_auxiliary_images or not p.stem.lower().endswith("_rois"))
    )
    if not image_paths:
        print(f"VISION_DEBUG_NO_IMAGES images_dir={images_dir}")
        return 2

    exported = 0
    view_counts: list[int] = []
    for path in image_paths:
        frame = path.read_bytes()
        overlays = parser.debug_overlays(frame)
        view_counts.append(len(overlays))
        stem = path.stem
        for view_name, image in overlays.items():
            output_path = output_dir / f"{stem}.{view_name}.png"
            image.save(output_path)
            exported += 1

    min_views = min(view_counts)
    max_views = max(view_counts)
    views_text = str(min_views) if min_views == max_views else f"{min_views}-{max_views}"

    print(
        "VISION_DEBUG_OVERLAYS "
        f"images={len(image_paths)} "
        f"views_per_image={views_text} "
        f"exported={exported} "
        f"output_dir={output_dir}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

from smartblaster.cli import build_command_from_args, create_parser
from smartblaster.ir.command import MideaMode


def test_cli_off_command_builds_off_mode() -> None:
    parser = create_parser()
    args = parser.parse_args(["off"])
    cmd = build_command_from_args(args)
    assert cmd.mode == MideaMode.OFF


def test_cli_set_command_builds_payload_fields() -> None:
    parser = create_parser()
    args = parser.parse_args([
        "set",
        "--mode",
        "cool",
        "--temp",
        "24",
        "--fan",
        "medium",
        "--swing",
        "vertical",
        "--preset",
        "boost",
        "--follow-me",
        "23",
        "--beeper",
    ])
    cmd = build_command_from_args(args)
    payload = cmd.to_payload()

    assert payload["mode"] == "cool"
    assert payload["temperature_c"] == 24
    assert payload["fan"] == "medium"
    assert payload["swing"] == "vertical"
    assert payload["preset"] == "boost"
    assert payload["follow_me_c"] == 23
    assert payload["beeper"] is True


def test_cli_status_command_parses_options() -> None:
    parser = create_parser()
    args = parser.parse_args(
        [
            "status",
            "--model-id",
            "midea_kjr_12b_dp_t",
            "--history-file",
            "data/history.log",
            "--diagnostic-save-images",
            "--diagnostic-image-dir",
            "data/images",
        ]
    )
    assert args.command == "status"
    assert args.model_id == "midea_kjr_12b_dp_t"
    assert args.history_file == "data/history.log"
    assert args.diagnostic_save_images is True
    assert args.diagnostic_image_dir == "data/images"


def test_cli_vision_eval_command_parses_options() -> None:
    parser = create_parser()
    args = parser.parse_args(
        [
            "vision-eval",
            "--model-id",
            "midea_kjr_12b_dp_t",
            "--images-dir",
            "data/samples/midea",
            "--labels-file",
            "data/samples/midea/labels.jsonl",
            "--output-report",
            "data/vision_report.json",
        ]
    )
    assert args.command == "vision-eval"
    assert args.model_id == "midea_kjr_12b_dp_t"
    assert args.images_dir == "data/samples/midea"
    assert args.labels_file == "data/samples/midea/labels.jsonl"
    assert args.output_report == "data/vision_report.json"


def test_cli_vision_validate_labels_command_parses_options() -> None:
    parser = create_parser()
    args = parser.parse_args(
        [
            "vision-validate-labels",
            "--labels-file",
            "data/samples/midea/labels.jsonl",
            "--images-dir",
            "data/samples/midea",
        ]
    )
    assert args.command == "vision-validate-labels"
    assert args.labels_file == "data/samples/midea/labels.jsonl"
    assert args.images_dir == "data/samples/midea"


def test_cli_vision_debug_overlays_command_parses_options() -> None:
    parser = create_parser()
    args = parser.parse_args(
        [
            "vision-debug-overlays",
            "--model-id",
            "midea_kjr_12b_dp_t",
            "--images-dir",
            "data/samples/midea",
            "--output-dir",
            "data/debug_overlays",
        ]
    )
    assert args.command == "vision-debug-overlays"
    assert args.model_id == "midea_kjr_12b_dp_t"
    assert args.images_dir == "data/samples/midea"
    assert args.output_dir == "data/debug_overlays"
    assert args.include_auxiliary_images is False

    args_with_aux = parser.parse_args(
        [
            "vision-debug-overlays",
            "--images-dir",
            "data/samples/midea",
            "--output-dir",
            "data/debug_overlays",
            "--include-auxiliary-images",
        ]
    )
    assert args_with_aux.include_auxiliary_images is True

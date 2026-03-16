# Vision Dataset Evaluation

You can validate parser quality offline using labeled JPEGs (no live HVAC required).

## Why this helps

- Works with sample images at any resolution.
- Lets you build a growing regression suite from real thermostat photos.
- Enables repeatable testing in CI without hardware.

## Label manifest format (JSONL)

Each line:

```json
{"filename":"img_001.jpg","expected":{"mode":"cool","set_temperature":24.0,"temperature_unit":"C","fan_speed":"high","timer_set":true,"follow_me_enabled":false,"power_on":true}}
```

Fields are optional per image. Include only fields you know are correct.

## Run evaluation

```bash
smartblaster-cli vision-eval \
  --model-id midea_kjr_12b_dp_t \
  --images-dir data/samples/midea \
  --labels-file data/samples/midea/labels.jsonl \
  --output-report data/vision_eval_report.json
```

The report includes per-field accuracy and per-image mismatches.

## Render alignment overlays

Use this when tuning landmark normalization and ROI placement:

```bash
smartblaster-cli vision-debug-overlays \
  --model-id midea_kjr_12b_dp_t \
  --images-dir data/samples/midea \
  --output-dir data/debug_overlays
```

For each input image, this writes:

- stem.landmarks_original.png: original image with detected landmark anchors and boundary estimate.
- stem.rois_selected.png: parser ROI boxes on the chosen normalized candidate.
- stem.rois_landmarks.png: parser ROI boxes on landmark-based normalization (when available).
- stem.rois_bounds.png: parser ROI boxes on boundary-based normalization (when available).
- stem.rois_identity.png: parser ROI boxes on plain resize fallback (when selected differs).

By default, helper files ending in _rois are skipped. Add --include-auxiliary-images to include them.

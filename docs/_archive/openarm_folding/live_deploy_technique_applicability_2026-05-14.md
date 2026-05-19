# OpenArm Folding Live Deploy Technique Applicability

Date: 2026-05-14

Baseline source:
- https://huggingface.co/spaces/lerobot/robot-folding
- https://lerobot-robot-folding.hf.space/
- https://huggingface.co/docs/lerobot/rtc

## Immediate deploy path

The next rollout should use a live closed-loop path, not repeated snapshot/scp
chunks. The robot-folding recipe explicitly depends on continuous chunked
execution with RTC and action interpolation.

Implemented for the live path:
- A6000 `/predict_live` with inline state/images, no snapshot directory.
- Full `[1, 30, 16]` absolute action chunk response.
- Metadata gates for `robot_config_id`, `checkpoint_id`, `action_normalization_id`,
  `joint_order`, `action_units`, and `is_absolute_action`.
- RTC inputs: previous leftover absolute chunk, inference delay estimate, and
  `execution_horizon=20`.
- Relative-action RTC re-anchoring on A6000 before `predict_action_chunk`.
- Syhlabtop long-lived RealSense and CAN sessions.
- Guarded `_mit_control_batch()` action execution only.
- Default policy cadence `30 Hz` and interpolation multiplier `3`.
- Optional evaluation frame sampling for post-run review.

## Technique applicability

| Technique | Deploy now? | Applicability |
| --- | --- | --- |
| RTC | Yes | Required for continuous chunk transitions and high inference latency. Use `execution_horizon=20`. |
| Action interpolation | Yes | Required for recipe-aligned smooth execution. Default multiplier is `3`. |
| Relative actions | Already applied | Training/checkpoint-side requirement. Server returns absolute actions after postprocessor. RTC leftover is re-anchored to relative/model space. |
| Full 16D bimanual + grippers | Yes | Required to avoid OOD state from one-arm-only execution. Guarded limits/clipping still apply. |
| 3 camera live observation | Yes | Required. Base + two wrist views are policy inputs. |
| 30 FPS camera/control baseline | Yes where hardware supports it | Live client defaults to 30 FPS. If RealSense profile is unstable, lower FPS is allowed but logged as a recipe deviation. |
| 50 FPS recording | Not now | The Space notes it as a future improvement. It is useful for new data collection, not a hard blocker for this checkpoint. |
| SARM/RABC | Not live-runtime | Training/data-curation technique. Keep checkpoint metadata, but do not add as a runtime gate. |
| DAgger/HIL corrections | After first failure analysis | Use after live rollout identifies repeatable failure modes. Not required before first continuous rollout. |
| Evaluation video | Yes, lightweight now | At minimum record sampled frames and structured logs. Full synchronized video recording can be added after live stability is verified. |
| +5 cm upper arm / larger jaws | Hardware track | Important recipe fidelity item. Record installed/not-installed status, but do not block software live-loop bring-up if the operator accepts reduced fidelity. |

## Current recommendation

Proceed directly with an approved online closed-loop session. Do not collect a
30-second observation block and then replay it. Vision/state must keep updating
while actions are being executed.

1. Start A6000 live server.
2. Generate the session envelope from `/health` metadata, not from a no-execute
   proposal chunk.
3. Operator approves that live session envelope.
4. Start syhlabtop with `--execute`.
5. The client immediately runs the online loop:
   live camera/state read -> `/predict_live` -> action queue merge -> guarded
   MIT execution -> next live camera/state read.

The `--execute` session duration is wall-clock online rollout duration. A
30-second session means 30 seconds of continuously refreshed observations and
actions, not 30 seconds of pre-captured observations followed by replay.

Do not add intermediate no-execute gates inside the live session. Do not add
heavy recalibration or old 20-degree mismatch diagnostics as a live hard gate.
The remaining hard gates should be metadata integrity, finite actions, joint
limits after allowed saturation, command path integrity, motor communication, and
operator stop.

Safety measurements during the live session are monitor-only. Delta caps,
readback errors, camera age, queue depth, clipping counts, and saturation counts
are logged for the operator, but they do not pause/block the online rollout.
The runtime safety gates are the operator's visual review, held power cutoff, and
explicit stop. Software still blocks command-integrity failures such as malformed
or non-finite actions, metadata mismatch, forbidden command paths, invalid joint
targets after allowed saturation, and actuator communication exceptions.

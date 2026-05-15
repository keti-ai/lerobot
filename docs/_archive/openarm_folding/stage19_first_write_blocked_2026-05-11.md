# Stage 19 First Write Blocked

Date: 2026-05-11
Scope: guarded first actuator write attempt from the Stage 18 right-arm writer.

## Result

The operator provided the required confirmation phrase:

```text
SEND_RIGHT_ARM_JOINTS_ONCE_20260511
```

The writer was invoked with:

```text
--execute
--power-held
--confirm SEND_RIGHT_ARM_JOINTS_ONCE_20260511
```

The write was blocked before torque enable and before MIT batch command because
fresh current readback no longer matched the Stage 17 packet closely enough.

Final blocked log:

```text
/home/syhlabtop/openarm_folding_20260511/shadow_reviews/snapshot_20260511_154554_stage18_execute_blocked.json
sha256: 4aefc44e4b7dd74583bbebd63a57d1e6dbece9ecb294edfc7c7ca54589999d28
```

Safety state:

```text
send_allowed: false
motion_allowed: false
actuator_commands_sent: false
post_write_readback_deg: null
post_hold_readback_deg: null
final_readback_deg: null
```

## Blocked Rows

| Motor | Fresh deg | Target deg | Delta deg | Drift deg | Status |
| --- | ---: | ---: | ---: | ---: | --- |
| `joint_1` | 1.104 | -3.126 | -4.229 | 2.229 | blocked |
| `joint_2` | -1.344 | -2.295 | -0.951 | -1.049 | blocked |
| `joint_3` | 14.611 | 11.540 | -3.071 | 1.071 | blocked |
| `joint_4` | -4.229 | 0.000 | 4.229 | -4.590 | blocked |
| `joint_7` | -3.792 | 7.978 | 11.770 | -9.770 | blocked |

Rows still within limits:

```text
joint_5  delta=-1.082 drift=-0.918
joint_6  delta=-1.825 drift=-0.175
```

## Decision

The Stage 17 packet is stale and must not be used for actuator write.

Do not retry this packet. The next step is to restart the offline single-step
loop from current hardware state:

1. capture a new no-send snapshot;
2. transfer it to A6000/NAS;
3. run A6000 offline action review;
4. rebuild Stage 15 dry-run, Stage 16 preflight, and Stage 17 packet;
5. only then consider a new Stage 18 dry-run and Stage 19 operator-gated write.

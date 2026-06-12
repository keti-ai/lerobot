# Copyright 2026 The HuggingFace Inc. team. All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Online per-joint trajectory generation toward (possibly moving) VLA setpoints.

A VLA policy emits joint-position setpoints at a low rate (e.g. 30 Hz action
chunks). Streaming those setpoints directly to the motors — even linearly
interpolated — produces velocity discontinuities at every setpoint switch.
This module tracks the latest setpoint with a velocity/acceleration-limited
profile so a high-rate command thread (e.g. 100-250 Hz) can stream smooth
joint commands regardless of when setpoints change.

Profiles:
- ``trapezoidal``: acceleration-limited tracking. Per tick the desired velocity
  follows the time-optimal law ``v_des = sign(err) * min(v_max, sqrt(2*a_max*|err|))``
  (guarantees decel-to-stop at the target without overshoot) and the actual
  velocity slews toward it bounded by ``a_max``.
- ``scurve``: adds a jerk bound. Acceleration itself slews toward the
  acceleration demanded by the trapezoidal law, bounded by ``j_max``, yielding
  C2-continuous (jerk-limited) commands.

Both are *online* trackers: the target may move every call, which matches the
asynchronous arrival of VLA action chunks.
"""

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class JointProfileLimits:
    """Per-joint kinematic limits, in degrees-based units (deg/s, deg/s^2, deg/s^3)."""

    v_max: float
    a_max: float
    j_max: float = 1e9  # effectively unlimited unless the scurve profile is used

    def __post_init__(self):
        if self.v_max <= 0 or self.a_max <= 0 or self.j_max <= 0:
            raise ValueError(f"Profile limits must be positive, got {self}")


class OnlineTrajectoryGenerator:
    """Tracks moving joint setpoints with velocity/acceleration(/jerk)-limited profiles.

    Usage:
        gen = OnlineTrajectoryGenerator(names, limits, profile="trapezoidal")
        gen.reset(initial_positions)        # e.g. robot present positions
        gen.set_target(latest_vla_action)   # whenever a new setpoint arrives
        cmd = gen.step(dt)                  # every control tick (1/rate)
    """

    PROFILES = ("trapezoidal", "scurve")

    def __init__(
        self,
        names: list[str],
        limits: dict[str, JointProfileLimits] | JointProfileLimits,
        profile: str = "trapezoidal",
    ):
        if profile not in self.PROFILES:
            raise ValueError(f"Unknown profile '{profile}'. Options: {self.PROFILES}")
        self.names = list(names)
        self.profile = profile
        n = len(self.names)

        if isinstance(limits, JointProfileLimits):
            per_joint = [limits] * n
        else:
            per_joint = [self._resolve_limits(name, limits) for name in self.names]
        self.v_max = np.array([lim.v_max for lim in per_joint], dtype=np.float64)
        self.a_max = np.array([lim.a_max for lim in per_joint], dtype=np.float64)
        self.j_max = np.array([lim.j_max for lim in per_joint], dtype=np.float64)

        self.pos = np.zeros(n, dtype=np.float64)
        self.vel = np.zeros(n, dtype=np.float64)
        self.acc = np.zeros(n, dtype=np.float64)
        self.target = np.zeros(n, dtype=np.float64)
        self._initialized = False

    @staticmethod
    def _resolve_limits(name: str, limits: dict[str, JointProfileLimits]) -> JointProfileLimits:
        """Match a feature name like 'left_joint_4.pos' against override keys like 'joint_4'."""
        if name in limits:
            return limits[name]
        stripped = name.removesuffix(".pos")
        if stripped in limits:
            return limits[stripped]
        for key, lim in limits.items():
            if stripped.endswith(key):
                return lim
        if "default" in limits:
            return limits["default"]
        raise KeyError(f"No profile limits found for joint '{name}' (keys: {list(limits)})")

    @property
    def initialized(self) -> bool:
        return self._initialized

    def reset(self, positions: np.ndarray) -> None:
        """Initialize the profile state at the given positions with zero velocity."""
        positions = np.asarray(positions, dtype=np.float64)
        if positions.shape != self.pos.shape:
            raise ValueError(f"Expected positions of shape {self.pos.shape}, got {positions.shape}")
        self.pos = positions.copy()
        self.vel = np.zeros_like(self.pos)
        self.acc = np.zeros_like(self.pos)
        self.target = positions.copy()
        self._initialized = True

    def set_target(self, target: np.ndarray) -> None:
        target = np.asarray(target, dtype=np.float64)
        if target.shape != self.pos.shape:
            raise ValueError(f"Expected target of shape {self.pos.shape}, got {target.shape}")
        self.target = target.copy()

    def step(self, dt: float) -> np.ndarray:
        """Advance the profile by ``dt`` seconds and return commanded positions (deg)."""
        if not self._initialized:
            raise RuntimeError("OnlineTrajectoryGenerator.step() called before reset().")
        if dt <= 0:
            raise ValueError(f"dt must be positive, got {dt}")

        err = self.target - self.pos

        if self.profile == "trapezoidal":
            # Decel-aware velocity demand: stopping distance at speed v is v^2/(2a),
            # so demand v_des = sqrt(2*a*|err|) capped at v_max (no-overshoot law).
            v_des = np.sign(err) * np.minimum(self.v_max, np.sqrt(2.0 * self.a_max * np.abs(err)))
            dv = np.clip(v_des - self.vel, -self.a_max * dt, self.a_max * dt)
            self.vel = self.vel + dv
            self.acc = dv / dt
        else:
            # scurve: jerk-limited slew of acceleration. The decel must start earlier than
            # in the trapezoidal case because acceleration itself needs a*j ramp time:
            # stopping distance ~ v^2/(2a) + v*a/(2j). Inverting for the velocity demand:
            # v_des = (-c + sqrt(c^2 + 8*a*|err|)) / 2 with c = a^2/j.
            # Lead compensation: the inner (jerk-limited) velocity loop tracks v_des with a
            # lag of ~a_max/j_max seconds, which integrates into position overshoot. Plan the
            # decel on the predicted position one lag-time ahead.
            err_eff = err - self.vel * (self.a_max / self.j_max)
            c = self.a_max * self.a_max / self.j_max
            v_des_mag = 0.5 * (-c + np.sqrt(c * c + 8.0 * self.a_max * np.abs(err_eff)))
            # Anticipate the cruise entry: while |a| ramps down to 0 at jerk j, v still
            # gains a^2/(2j). Shave that margin off v_max so v converges to v_max from
            # below instead of overshooting it.
            ramp_margin = np.where(
                self.acc * np.sign(err_eff) > 0, self.acc * self.acc / (2.0 * self.j_max), 0.0
            )
            v_des = np.sign(err_eff) * np.minimum(
                np.maximum(self.v_max - ramp_margin, 0.0), v_des_mag
            )
            # Cascaded sqrt law on the velocity error (same shape as the position loop):
            # accel demand ramps down jerk-aware as v approaches v_des, avoiding both
            # velocity overshoot and the bang-bang limit cycle of a raw (v_des-v)/dt term.
            v_err = v_des - self.vel
            a_des = np.sign(v_err) * np.minimum(self.a_max, np.sqrt(2.0 * self.j_max * np.abs(v_err)))
            da = np.clip(a_des - self.acc, -self.j_max * dt, self.j_max * dt)
            self.acc = self.acc + da
            self.vel = self.vel + self.acc * dt

        self.pos = self.pos + self.vel * dt

        # Snap to target once error, velocity and acceleration are all negligible,
        # so the profile settles instead of limit-cycling around the setpoint.
        settled = (
            (np.abs(self.target - self.pos) < 1e-3)
            & (np.abs(self.vel) < 1e-2)
            & (np.abs(self.acc) < 1.0)
        )
        if settled.any():
            self.pos[settled] = self.target[settled]
            self.vel[settled] = 0.0
            self.acc[settled] = 0.0

        return self.pos.copy()

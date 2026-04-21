"""
core/madgwick_filter.py

Madgwick AHRS filter for accurate 3D orientation from IMU data.
Gives much better ROM estimates than gravity-tilt alone.

Reference: Madgwick et al., "Estimation of IMU and MARG orientation
using a gradient descent algorithm", IEEE 2011.

Usage:
    filter = MadgwickFilter(beta=0.1, sample_rate=166.0)
    for frame in frames:
        q = filter.update(frame.gyro_x, frame.gyro_y, frame.gyro_z,
                           frame.accel_x, frame.accel_y, frame.accel_z)
    euler = filter.quaternion_to_euler(q)  # (roll, pitch, yaw) in degrees
"""
import numpy as np
from dataclasses import dataclass, field
from typing import List, Tuple


@dataclass
class MadgwickFilter:
    beta: float        = 0.1      # filter gain (higher = faster but noisier)
    sample_rate: float = 166.0    # Hz, match your sensor

    # Quaternion state [w, x, y, z]
    q: np.ndarray = field(default_factory=lambda: np.array([1.0, 0.0, 0.0, 0.0]))

    def update(self,
               gx: float, gy: float, gz: float,
               ax: float, ay: float, az: float) -> np.ndarray:
        """
        Update orientation estimate.
        Gyro in rad/s. Accel in any consistent unit (will be normalised).
        Returns updated quaternion [w, x, y, z].
        """
        q = self.q
        dt = 1.0 / self.sample_rate

        # Normalize accelerometer
        norm = np.sqrt(ax*ax + ay*ay + az*az)
        if norm < 1e-9:
            return q
        ax, ay, az = ax/norm, ay/norm, az/norm

        # Gradient of objective function
        q0, q1, q2, q3 = q
        f1 = 2*(q1*q3 - q0*q2) - ax
        f2 = 2*(q0*q1 + q2*q3) - ay
        f3 = 2*(0.5 - q1*q1 - q2*q2) - az

        J = np.array([
            [-2*q2,  2*q3, -2*q0,  2*q1],
            [ 2*q1,  2*q0,  2*q3,  2*q2],
            [ 0,    -4*q1, -4*q2,  0   ],
        ])
        step = J.T @ np.array([f1, f2, f3])
        norm_step = np.linalg.norm(step)
        if norm_step > 1e-9:
            step /= norm_step

        # Gyro rate-of-change of quaternion
        qDot = 0.5 * np.array([
            -q1*gx - q2*gy - q3*gz,
             q0*gx + q2*gz - q3*gy,
             q0*gy - q1*gz + q3*gx,
             q0*gz + q1*gy - q2*gx,
        ]) - self.beta * step

        self.q = q + qDot * dt
        self.q /= np.linalg.norm(self.q)
        return self.q.copy()

    @staticmethod
    def quaternion_to_euler(q: np.ndarray) -> Tuple[float, float, float]:
        """
        Convert quaternion [w, x, y, z] to Euler angles (roll, pitch, yaw) in degrees.
        """
        w, x, y, z = q
        roll  = np.degrees(np.arctan2(2*(w*x + y*z), 1 - 2*(x*x + y*y)))
        pitch = np.degrees(np.arcsin(np.clip(2*(w*y - z*x), -1, 1)))
        yaw   = np.degrees(np.arctan2(2*(w*z + x*y), 1 - 2*(y*y + z*z)))
        return roll, pitch, yaw


def compute_rom_madgwick(frames, sample_rate: float = 166.0) -> dict:
    """
    Full ROM computation using Madgwick filter over all session frames.
    Returns min/max for roll, pitch, yaw and their ranges (ROM).
    """
    from core.load_calculator import IMUFrame

    filt = MadgwickFilter(beta=0.033, sample_rate=sample_rate)
    rolls, pitches, yaws = [], [], []

    for f in frames:
        q = filt.update(f.gyro_x, f.gyro_y, f.gyro_z,
                        f.accel_x, f.accel_y, f.accel_z)
        r, p, y = MadgwickFilter.quaternion_to_euler(q)
        rolls.append(r); pitches.append(p); yaws.append(y)

    rolls    = np.array(rolls)
    pitches  = np.array(pitches)
    yaws     = np.array(yaws)

    return {
        "rom_flexion_deg":    float(np.max(pitches) - np.min(pitches)),
        "rom_abduction_deg":  float(np.max(rolls)   - np.min(rolls)),
        "rom_rotation_deg":   float(np.max(yaws)    - np.min(yaws)),
        "pitch_series":       pitches.tolist(),
        "roll_series":        rolls.tolist(),
        "yaw_series":         yaws.tolist(),
    }

"""
core/load_calculator.py

Computes session load metrics from raw IMU samples.

Load definition used here:
  total_load = ∫ |ω(t)| dt   (rad, integral of gyro vector magnitude)

This is analogous to the "training load" concept from wearables literature
(see: Hulin et al., 2016 ACWR; Boyd et al. IJSM).

All inputs/outputs use SI units:
  - gyro: rad/s
  - accel: m/s² or g (consistent with your sensor config)
  - time:  seconds
"""
import numpy as np
from dataclasses import dataclass
from typing import List, Optional


@dataclass
class IMUFrame:
    elapsed_s: float
    accel_x: float
    accel_y: float
    accel_z: float
    gyro_x: float
    gyro_y: float
    gyro_z: float


@dataclass
class LoadResult:
    total_load: float           # rad  (gyro magnitude integral)
    peak_load_rate: float       # rad/s
    avg_load_rate: float        # rad/s
    duration_s: float
    stroke_count: int
    rom_flexion_deg: Optional[float]
    rom_abduction_deg: Optional[float]
    rom_rotation_deg: Optional[float]
    gyro_mag_series: List[float]   # for plotting
    elapsed_series: List[float]
    cumulative_load_series: List[float]


def compute_gyro_magnitude(frames: List[IMUFrame]) -> np.ndarray:
    gx = np.array([f.gyro_x for f in frames])
    gy = np.array([f.gyro_y for f in frames])
    gz = np.array([f.gyro_z for f in frames])
    return np.sqrt(gx**2 + gy**2 + gz**2)


def integrate_load(elapsed: np.ndarray, gyro_mag: np.ndarray) -> np.ndarray:
    """
    Cumulative trapezoidal integration of gyro magnitude.
    Returns array same length as input (cumulative load at each sample).
    """
    if len(elapsed) < 2:
        return np.zeros_like(elapsed)
    dt = np.diff(elapsed, prepend=elapsed[0])
    incremental = gyro_mag * dt
    return np.cumsum(incremental)


def compute_rom(frames: List[IMUFrame]) -> dict:
    """
    Estimates range of motion using orientation from accelerometer gravity vector.

    This is a simplified tilt-based ROM — for full 3D ROM use Madgwick filter
    (see madgwick_filter.py). Useful as a fast fallback.

    Returns degrees for flexion/extension (sagittal), abduction (frontal),
    and axial rotation (approximate from gyro_z integration).
    """
    ax = np.array([f.accel_x for f in frames])
    ay = np.array([f.accel_y for f in frames])
    az = np.array([f.accel_z for f in frames])

    # Normalize acceleration vector to get gravity direction
    norm = np.sqrt(ax**2 + ay**2 + az**2) + 1e-9
    ax_n, ay_n, az_n = ax/norm, ay/norm, az/norm

    # Pitch (flexion/extension) and roll (abduction) from gravity tilt
    pitch_rad = np.arctan2(ax_n, np.sqrt(ay_n**2 + az_n**2))
    roll_rad  = np.arctan2(ay_n, az_n)

    pitch_deg = np.degrees(pitch_rad)
    roll_deg  = np.degrees(roll_rad)

    # Axial rotation: integrate gyro_z
    elapsed = np.array([f.elapsed_s for f in frames])
    gz = np.array([f.gyro_z for f in frames])
    dt = np.diff(elapsed, prepend=elapsed[0])
    rotation_rad = np.cumsum(gz * dt)
    rotation_deg = np.degrees(rotation_rad)

    return {
        "rom_flexion_deg":   float(np.max(pitch_deg) - np.min(pitch_deg)),
        "rom_abduction_deg": float(np.max(roll_deg)  - np.min(roll_deg)),
        "rom_rotation_deg":  float(np.max(rotation_deg) - np.min(rotation_deg)),
    }


def detect_strokes(gyro_mag: np.ndarray, elapsed: np.ndarray,
                   threshold: float = 1.0, min_gap_s: float = 0.5) -> int:
    """
    Simple peak detection for stroke counting.
    A stroke = gyro magnitude peak above threshold with at least min_gap_s separation.
    Tune threshold based on your sensor placement and stroke style.
    """
    above = gyro_mag > threshold
    crossings = np.diff(above.astype(int), prepend=0)
    rising_edges = np.where(crossings == 1)[0]

    if len(rising_edges) == 0:
        return 0

    # Filter for minimum gap between strokes
    strokes = [rising_edges[0]]
    for idx in rising_edges[1:]:
        if (elapsed[idx] - elapsed[strokes[-1]]) >= min_gap_s:
            strokes.append(idx)

    return len(strokes)


def calculate_session_load(frames: List[IMUFrame]) -> LoadResult:
    """
    Main entry point. Pass all IMU frames for a session, get back LoadResult.
    """
    if not frames:
        return LoadResult(0, 0, 0, 0, 0, None, None, None, [], [], [])

    elapsed   = np.array([f.elapsed_s for f in frames])
    gyro_mag  = compute_gyro_magnitude(frames)
    cum_load  = integrate_load(elapsed, gyro_mag)
    rom       = compute_rom(frames)
    strokes   = detect_strokes(gyro_mag, elapsed)

    return LoadResult(
        total_load             = float(cum_load[-1]),
        peak_load_rate         = float(np.max(gyro_mag)),
        avg_load_rate          = float(np.mean(gyro_mag)),
        duration_s             = float(elapsed[-1] - elapsed[0]),
        stroke_count           = strokes,
        rom_flexion_deg        = rom["rom_flexion_deg"],
        rom_abduction_deg      = rom["rom_abduction_deg"],
        rom_rotation_deg       = rom["rom_rotation_deg"],
        gyro_mag_series        = gyro_mag.tolist(),
        elapsed_series         = elapsed.tolist(),
        cumulative_load_series = cum_load.tolist(),
    )

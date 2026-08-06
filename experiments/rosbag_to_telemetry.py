#!/usr/bin/env python
"""Convert RoboRacer/F1TENTH ROS 2 bag data to the SysID telemetry CSV schema."""

from __future__ import annotations

import argparse
import csv
import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
from rosbags.rosbag2 import Reader
from rosbags.typesys import Stores, get_types_from_msg, get_typestore

REPO_ROOT = Path(__file__).resolve().parents[1]

DEFAULT_ODOM_TOPIC = "/ego_racecar/odom"
DEFAULT_DRIVE_TOPIC = "/drive"
DEFAULT_COLLISION_TOPIC = "/f1tenth/collision"
DEFAULT_INTERNAL_STATE_TOPIC = "/f1tenth/internal_state"

ACKERMANN_DRIVE_MSG = """float32 steering_angle
float32 steering_angle_velocity
float32 speed
float32 acceleration
float32 jerk
"""

ACKERMANN_DRIVE_STAMPED_MSG = """std_msgs/Header header
ackermann_msgs/AckermannDrive drive
"""

FIELDNAMES = [
    "run_id",
    "step",
    "time_s",
    "wall_time_s",
    "profile_status",
    "command_speed_mps",
    "command_steer_rad",
    "x_m",
    "y_m",
    "theta_rad",
    "speed_mps",
    "vx_mps",
    "vy_mps",
    "steer_rad",
    "steer_vel_radps",
    "yaw_rate_radps",
    "slip_angle_rad",
    "accel_x_mps2",
    "collision",
]

S_MAX_RAD = 0.4189
SATURATION_THRESHOLD = 0.95 * S_MAX_RAD
SATURATION_FRACTION_LIMIT = 0.02
SATURATION_SEGMENT_LIMIT_S = 0.25


@dataclass
class TimeSeries:
    time_s: np.ndarray
    values: dict[str, np.ndarray]


def build_typestore():
    typestore = get_typestore(Stores.ROS2_HUMBLE)
    if "ackermann_msgs/msg/AckermannDrive" not in typestore.types:
        typestore.register(get_types_from_msg(ACKERMANN_DRIVE_MSG, "ackermann_msgs/msg/AckermannDrive"))
    if "ackermann_msgs/msg/AckermannDriveStamped" not in typestore.types:
        typestore.register(
            get_types_from_msg(ACKERMANN_DRIVE_STAMPED_MSG, "ackermann_msgs/msg/AckermannDriveStamped")
        )
    return typestore


def quaternion_to_yaw(x: float, y: float, z: float, w: float) -> float:
    siny_cosp = 2.0 * (w * z + x * y)
    cosy_cosp = 1.0 - 2.0 * (y * y + z * z)
    return math.atan2(siny_cosp, cosy_cosp)


def unwrap_interp(sample_time: np.ndarray, sample_value: np.ndarray, query_time: np.ndarray) -> np.ndarray:
    return np.interp(query_time, sample_time, np.unwrap(sample_value))


def linear_interp(sample_time: np.ndarray, sample_value: np.ndarray, query_time: np.ndarray) -> np.ndarray:
    return np.interp(query_time, sample_time, sample_value)


def hold_sample(sample_time: np.ndarray, sample_value: np.ndarray, query_time: np.ndarray) -> np.ndarray:
    index = np.searchsorted(sample_time, query_time, side="right") - 1
    index = np.clip(index, 0, len(sample_time) - 1)
    return sample_value[index]


def finite_difference(values: np.ndarray, time_s: np.ndarray) -> np.ndarray:
    if len(values) < 2:
        return np.zeros_like(values)
    diff = np.empty_like(values)
    diff[0] = 0.0
    dt = np.diff(time_s)
    if np.any(dt <= 0.0):
        raise SystemExit("FAIL: differentiation timestamps must be strictly increasing")
    diff[1:] = np.diff(values) / dt
    return diff


def longest_true_segment_s(mask: np.ndarray, dt_s: float) -> float:
    longest = 0
    current = 0
    for value in mask:
        if bool(value):
            current += 1
            longest = max(longest, current)
        else:
            current = 0
    return float(longest * dt_s)


def as_series(records: list[dict[str, float]]) -> TimeSeries | None:
    if not records:
        return None
    records = sorted(records, key=lambda row: row["time_s"])
    time_s = np.array([row["time_s"] for row in records], dtype=float)
    values = {
        key: np.array([row[key] for row in records], dtype=float)
        for key in records[0]
        if key != "time_s"
    }
    return TimeSeries(time_s=time_s, values=values)


def stamp_to_seconds(stamp: Any) -> float:
    return float(stamp.sec) + float(stamp.nanosec) * 1e-9


def series_diagnostics(series: TimeSeries | None) -> dict[str, float | int | None]:
    if series is None:
        return {
            "sample_count": 0,
            "start_time_s": None,
            "stop_time_s": None,
            "duration_s": 0.0,
            "median_period_s": None,
            "observed_rate_hz": None,
            "max_gap_s": None,
            "median_header_bag_skew_s": None,
            "max_header_bag_skew_s": None,
        }
    dt = np.diff(series.time_s)
    median_period = float(np.median(dt)) if dt.size else None
    header_time = series.values.get("header_time_s")
    skew = np.abs(header_time - series.time_s) if header_time is not None else np.array([])
    return {
        "sample_count": int(len(series.time_s)),
        "start_time_s": float(series.time_s[0]),
        "stop_time_s": float(series.time_s[-1]),
        "duration_s": float(series.time_s[-1] - series.time_s[0]),
        "median_period_s": median_period,
        "observed_rate_hz": float(1.0 / median_period) if median_period and median_period > 0.0 else None,
        "max_gap_s": float(np.max(dt)) if dt.size else None,
        "median_header_bag_skew_s": float(np.median(skew)) if skew.size else None,
        "max_header_bag_skew_s": float(np.max(skew)) if skew.size else None,
    }


def read_bag(
    bag_path: Path,
    odom_topic: str,
    drive_topic: str,
    collision_topic: str,
    internal_state_topic: str,
) -> tuple[TimeSeries | None, TimeSeries | None, TimeSeries | None, TimeSeries | None, dict[str, Any]]:
    typestore = build_typestore()
    odom_records: list[dict[str, float]] = []
    drive_records: list[dict[str, float]] = []
    collision_records: list[dict[str, float]] = []
    internal_records: list[dict[str, float]] = []
    topic_types: dict[str, str] = {}

    with Reader(bag_path) as reader:
        connections = [
            connection
            for connection in reader.connections
            if connection.topic in {odom_topic, drive_topic, collision_topic, internal_state_topic}
        ]
        topic_types = {connection.topic: connection.msgtype for connection in connections}
        for connection, timestamp_ns, rawdata in reader.messages(connections=connections):
            message = typestore.deserialize_cdr(rawdata, connection.msgtype)
            time_s = float(timestamp_ns) * 1e-9
            if connection.topic == odom_topic:
                orientation = message.pose.pose.orientation
                twist = message.twist.twist
                vx = float(twist.linear.x)
                vy = float(twist.linear.y)
                speed = math.hypot(vx, vy)
                odom_records.append(
                    {
                        "time_s": time_s,
                        "header_time_s": stamp_to_seconds(message.header.stamp),
                        "x_m": float(message.pose.pose.position.x),
                        "y_m": float(message.pose.pose.position.y),
                        "theta_rad": quaternion_to_yaw(
                            float(orientation.x),
                            float(orientation.y),
                            float(orientation.z),
                            float(orientation.w),
                        ),
                        "vx_mps": vx,
                        "vy_mps": vy,
                        "speed_mps": speed,
                        "yaw_rate_radps": float(twist.angular.z),
                        "slip_angle_rad": math.atan2(vy, vx) if speed > 1e-9 else 0.0,
                    }
                )
            elif connection.topic == drive_topic:
                drive_records.append(
                    {
                        "time_s": time_s,
                        "header_time_s": stamp_to_seconds(message.header.stamp),
                        "command_steer_rad": float(message.drive.steering_angle),
                        "command_speed_mps": float(message.drive.speed),
                    }
                )
            elif connection.topic == collision_topic:
                collision_records.append({"time_s": time_s, "collision": float(bool(message.data))})
            elif connection.topic == internal_state_topic:
                data = list(message.data)
                if len(data) >= 7:
                    record = {
                            "time_s": time_s,
                            "x_m": float(data[0]),
                            "y_m": float(data[1]),
                            "steer_rad": float(data[2]),
                            "speed_mps": float(data[3]),
                            "theta_rad": float(data[4]),
                            "yaw_rate_radps": float(data[5]),
                            "slip_angle_rad": float(data[6]),
                    }
                    if len(data) >= 8:
                        record["sim_time_s"] = float(data[7])
                    internal_records.append(record)

    metadata = {
        "bag_path": str(bag_path),
        "topic_types": topic_types,
        "odom_topic": odom_topic,
        "drive_topic": drive_topic,
        "collision_topic": collision_topic,
        "internal_state_topic": internal_state_topic,
        "has_internal_state": bool(internal_records),
        "has_collision": bool(collision_records),
    }
    return as_series(odom_records), as_series(drive_records), as_series(collision_records), as_series(internal_records), metadata


def require_series(series: TimeSeries | None, name: str) -> TimeSeries:
    if series is None:
        raise SystemExit(f"FAIL: missing required topic data for {name}")
    if len(series.time_s) < 2:
        raise SystemExit(f"FAIL: not enough samples for {name}")
    return series


def sample_source_window(sources: list[TimeSeries]) -> tuple[float, float]:
    start = max(float(source.time_s[0]) for source in sources)
    stop = min(float(source.time_s[-1]) for source in sources)
    if stop <= start:
        raise SystemExit("FAIL: topic timestamps do not overlap")
    return start, stop


def quality_rows(
    rows: list[dict[str, str | float | int]],
    dt_s: float,
    overlap_s: float,
    diagnostics: dict[str, dict[str, float | int | None]],
    collision_observed: bool,
) -> list[dict[str, str | float | bool]]:
    numeric = {field: np.array([float(row[field]) for row in rows], dtype=float) for field in FIELDNAMES if field not in {"run_id", "profile_status"}}
    duration_s = float(numeric["time_s"][-1] - numeric["time_s"][0]) if len(rows) >= 2 else 0.0
    speed_mean = float(np.mean(numeric["speed_mps"]))
    speed_std = float(np.std(numeric["speed_mps"], ddof=1)) if len(rows) > 1 else 0.0
    speed_cv = float(speed_std / max(abs(speed_mean), 1e-6))
    steer_range = float(np.max(numeric["steer_rad"]) - np.min(numeric["steer_rad"]))
    yaw_rate_range = float(np.max(numeric["yaw_rate_radps"]) - np.min(numeric["yaw_rate_radps"]))
    collision = bool(np.max(numeric["collision"]))
    saturation_mask = np.abs(numeric["steer_rad"]) >= SATURATION_THRESHOLD
    saturation_fraction = float(np.mean(saturation_mask))
    max_saturation_segment_s = longest_true_segment_s(saturation_mask, dt_s)
    quality: list[dict[str, str | float | bool]] = [
        {"metric": "duration_s", "value": duration_s, "units": "s", "pass": duration_s >= 15.0},
        {"metric": "num_samples", "value": len(rows), "units": "count", "pass": len(rows) > 0},
        {"metric": "collision", "value": int(collision), "units": "bool", "pass": not collision},
        {"metric": "speed_mean_mps", "value": speed_mean, "units": "m/s", "pass": True},
        {"metric": "speed_std_mps", "value": speed_std, "units": "m/s", "pass": True},
        {"metric": "speed_cv", "value": speed_cv, "units": "unitless", "pass": speed_cv <= 0.15},
        {"metric": "steer_range_rad", "value": steer_range, "units": "rad", "pass": steer_range >= 0.05},
        {"metric": "yaw_rate_range_radps", "value": yaw_rate_range, "units": "rad/s", "pass": yaw_rate_range >= 0.1},
        {"metric": "steering_saturation_fraction", "value": saturation_fraction, "units": "fraction", "pass": saturation_fraction <= SATURATION_FRACTION_LIMIT},
        {"metric": "max_saturation_segment_s", "value": max_saturation_segment_s, "units": "s", "pass": max_saturation_segment_s <= SATURATION_SEGMENT_LIMIT_S},
        {"metric": "required_topic_overlap_s", "value": overlap_s, "units": "s", "pass": overlap_s >= 15.0},
        {"metric": "collision_observed", "value": int(collision_observed), "units": "bool", "pass": True},
    ]
    for topic, values in diagnostics.items():
        slug = topic.strip("/").replace("/", "_")
        for key, units in (("observed_rate_hz", "Hz"), ("max_gap_s", "s")):
            value = values[key]
            if value is not None:
                quality.append(
                    {"metric": f"topic_{slug}_{key}", "value": float(value), "units": units, "pass": True}
                )
        median_skew = values["median_header_bag_skew_s"]
        max_skew = values["max_header_bag_skew_s"]
        if median_skew is not None:
            quality.append(
                {
                    "metric": f"topic_{slug}_median_header_bag_skew_s",
                    "value": float(median_skew),
                    "units": "s",
                    "pass": float(median_skew) <= 0.05,
                }
            )
        if max_skew is not None:
            quality.append(
                {
                    "metric": f"topic_{slug}_max_header_bag_skew_s",
                    "value": float(max_skew),
                    "units": "s",
                    "pass": float(max_skew) <= 0.10,
                }
            )
    return quality


def convert_bag(
    bag_path: Path,
    output_path: Path,
    metadata_path: Path,
    quality_path: Path,
    odom_topic: str = DEFAULT_ODOM_TOPIC,
    drive_topic: str = DEFAULT_DRIVE_TOPIC,
    collision_topic: str = DEFAULT_COLLISION_TOPIC,
    internal_state_topic: str = DEFAULT_INTERNAL_STATE_TOPIC,
    dt_s: float = 0.01,
    sample_clock: str = "fixed",
    sim_step_dt_s: float | None = None,
    command_frequency_start_hz: float | None = None,
    command_frequency_end_hz: float | None = None,
) -> dict[str, Any]:
    odom, drive, collision, internal, metadata = read_bag(
        bag_path,
        odom_topic,
        drive_topic,
        collision_topic,
        internal_state_topic,
    )
    odom = require_series(odom, odom_topic)
    drive = require_series(drive, drive_topic)
    required = [odom, drive]
    if internal is not None:
        required.append(internal)

    start_s, stop_s = sample_source_window(required)
    if sample_clock == "fixed":
        query_bag_time = np.arange(start_s, stop_s + 0.5 * dt_s, dt_s, dtype=float)
        relative_time = query_bag_time - query_bag_time[0]
    elif sample_clock == "internal_state":
        internal = require_series(internal, internal_state_topic)
        if "sim_time_s" not in internal.values:
            raise SystemExit("FAIL: internal_state sampling requires element 8 sim_time_s")
        mask = (internal.time_s >= start_s) & (internal.time_s <= stop_s)
        query_bag_time = internal.time_s[mask]
        relative_time = internal.values["sim_time_s"][mask]
        relative_time = relative_time - relative_time[0]
    elif sample_clock == "odom":
        mask = (odom.time_s >= start_s) & (odom.time_s <= stop_s)
        query_bag_time = odom.time_s[mask]
        relative_time = query_bag_time - query_bag_time[0]
    else:
        raise ValueError(f"unknown sample clock: {sample_clock}")
    if len(query_bag_time) < 2:
        raise SystemExit("FAIL: fixed-rate export produced fewer than two samples")

    command_steer = hold_sample(drive.time_s, drive.values["command_steer_rad"], query_bag_time)
    command_speed = hold_sample(drive.time_s, drive.values["command_speed_mps"], query_bag_time)
    collision_values = (
        hold_sample(collision.time_s, collision.values["collision"], query_bag_time)
        if collision is not None
        else np.zeros_like(query_bag_time)
    )

    if internal is not None:
        x = linear_interp(internal.time_s, internal.values["x_m"], query_bag_time)
        y = linear_interp(internal.time_s, internal.values["y_m"], query_bag_time)
        steer = linear_interp(internal.time_s, internal.values["steer_rad"], query_bag_time)
        speed = linear_interp(internal.time_s, internal.values["speed_mps"], query_bag_time)
        theta = unwrap_interp(internal.time_s, internal.values["theta_rad"], query_bag_time)
        yaw_rate = linear_interp(internal.time_s, internal.values["yaw_rate_radps"], query_bag_time)
        slip_angle = linear_interp(internal.time_s, internal.values["slip_angle_rad"], query_bag_time)
        vx = speed * np.cos(slip_angle)
        vy = speed * np.sin(slip_angle)
        steer_source = "internal_state"
    else:
        x = linear_interp(odom.time_s, odom.values["x_m"], query_bag_time)
        y = linear_interp(odom.time_s, odom.values["y_m"], query_bag_time)
        theta = unwrap_interp(odom.time_s, odom.values["theta_rad"], query_bag_time)
        speed = linear_interp(odom.time_s, odom.values["speed_mps"], query_bag_time)
        vx = linear_interp(odom.time_s, odom.values["vx_mps"], query_bag_time)
        vy = linear_interp(odom.time_s, odom.values["vy_mps"], query_bag_time)
        yaw_rate = linear_interp(odom.time_s, odom.values["yaw_rate_radps"], query_bag_time)
        slip_angle = np.array([math.atan2(vy_i, vx_i) if math.hypot(vx_i, vy_i) > 1e-9 else 0.0 for vx_i, vy_i in zip(vx, vy)])
        steer = command_steer
        steer_source = "command_proxy"

    steer_vel = finite_difference(steer, relative_time)
    accel_x = finite_difference(speed, relative_time)
    wall_time = query_bag_time - query_bag_time[0]
    rows: list[dict[str, str | float | int]] = []
    for index, time_value in enumerate(relative_time):
        rows.append(
            {
                "run_id": bag_path.name,
                "step": index + 1,
                "time_s": f"{time_value:.6f}",
                "wall_time_s": f"{wall_time[index]:.6f}",
                "profile_status": "rosbag_export",
                "command_speed_mps": f"{command_speed[index]:.9f}",
                "command_steer_rad": f"{command_steer[index]:.9f}",
                "x_m": f"{x[index]:.9f}",
                "y_m": f"{y[index]:.9f}",
                "theta_rad": f"{theta[index]:.9f}",
                "speed_mps": f"{speed[index]:.9f}",
                "vx_mps": f"{vx[index]:.9f}",
                "vy_mps": f"{vy[index]:.9f}",
                "steer_rad": f"{steer[index]:.9f}",
                "steer_vel_radps": f"{steer_vel[index]:.9f}",
                "yaw_rate_radps": f"{yaw_rate[index]:.9f}",
                "slip_angle_rad": f"{slip_angle[index]:.9f}",
                "accel_x_mps2": f"{accel_x[index]:.9f}",
                "collision": int(collision_values[index] > 0.5),
            }
        )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    metadata_path.parent.mkdir(parents=True, exist_ok=True)
    quality_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=FIELDNAMES, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)

    diagnostics = {
        odom_topic: series_diagnostics(odom),
        drive_topic: series_diagnostics(drive),
        collision_topic: series_diagnostics(collision),
        internal_state_topic: series_diagnostics(internal),
    }
    overlap_s = float(stop_s - start_s)
    quality = quality_rows(rows, dt_s, overlap_s, diagnostics, collision is not None)
    with quality_path.open("w", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=["metric", "value", "units", "pass"], lineterminator="\n")
        writer.writeheader()
        writer.writerows(quality)

    raw_times = np.concatenate([source.time_s for source in required])
    raw_dt = np.diff(np.sort(raw_times))
    real_time_factor = None
    rtf_source = None
    odom_state_change_count = None
    if wall_time[-1] > 0.0 and sample_clock == "internal_state":
        real_time_factor = float(relative_time[-1] / wall_time[-1])
        rtf_source = "internal_state_sim_time"
    elif wall_time[-1] > 0.0 and sample_clock == "odom" and sim_step_dt_s is not None:
        state_for_changes = np.column_stack([x, y, theta, speed, yaw_rate])
        changed = np.any(np.abs(np.diff(state_for_changes, axis=0)) > 1e-12, axis=1)
        odom_state_change_count = int(np.count_nonzero(changed))
        real_time_factor = float(odom_state_change_count * sim_step_dt_s / wall_time[-1])
        rtf_source = "odom_state_change_count_times_configured_step"
    realized_frequency_band = None
    if (
        real_time_factor is not None
        and real_time_factor > 0.0
        and command_frequency_start_hz is not None
        and command_frequency_end_hz is not None
    ):
        realized_frequency_band = [
            float(command_frequency_start_hz / real_time_factor),
            float(command_frequency_end_hz / real_time_factor),
        ]
    metadata.update(
        {
            "converter": "experiments/rosbag_to_telemetry.py",
            "output_path": str(output_path),
            "quality_path": str(quality_path),
            "dt_s": dt_s,
            "sample_clock": sample_clock,
            "timestamp_basis": "rosbag_receive_time",
            "num_output_samples": len(rows),
            "duration_s": float(relative_time[-1] - relative_time[0]),
            "steer_rad_source": steer_source,
            "collision_observed": collision is not None,
            "topic_diagnostics": diagnostics,
            "required_topic_overlap_s": overlap_s,
            "sim_time_observed": bool(internal is not None and "sim_time_s" in internal.values),
            "real_time_factor": real_time_factor,
            "real_time_factor_source": rtf_source,
            "odom_state_change_count": odom_state_change_count,
            "sim_step_dt_s": sim_step_dt_s,
            "command_frequency_band_wall_hz": (
                [command_frequency_start_hz, command_frequency_end_hz]
                if command_frequency_start_hz is not None and command_frequency_end_hz is not None
                else None
            ),
            "realized_frequency_band_sim_hz": realized_frequency_band,
            "standard_topics_primary": True,
            "internal_state_is_optional_enrichment": True,
            "raw_dt_min_s": float(np.min(raw_dt)) if raw_dt.size else 0.0,
            "raw_dt_max_s": float(np.max(raw_dt)) if raw_dt.size else 0.0,
            "raw_dt_mean_s": float(np.mean(raw_dt)) if raw_dt.size else 0.0,
        }
    )
    metadata_path.write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    return metadata


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bag", type=Path, required=True, help="ROS 2 bag directory.")
    parser.add_argument("--output", type=Path, required=True, help="Output telemetry CSV.")
    parser.add_argument("--metadata", type=Path, required=True, help="Output metadata JSON.")
    parser.add_argument("--quality", type=Path, required=True, help="Output quality metrics CSV.")
    parser.add_argument("--odom-topic", default=DEFAULT_ODOM_TOPIC)
    parser.add_argument("--drive-topic", default=DEFAULT_DRIVE_TOPIC)
    parser.add_argument("--collision-topic", default=DEFAULT_COLLISION_TOPIC)
    parser.add_argument("--internal-state-topic", default=DEFAULT_INTERNAL_STATE_TOPIC)
    parser.add_argument("--dt", type=float, default=0.01, help="Fixed export timestep in seconds.")
    parser.add_argument(
        "--sample-clock",
        choices=["fixed", "internal_state", "odom"],
        default="fixed",
        help="Output sampling clock; fixed preserves the legacy converter behavior.",
    )
    parser.add_argument(
        "--sim-step-dt",
        type=float,
        help="Configured simulator step used for an odometry state-change RTF proxy.",
    )
    parser.add_argument("--command-frequency-start", type=float)
    parser.add_argument("--command-frequency-end", type=float)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    metadata = convert_bag(
        bag_path=args.bag,
        output_path=args.output,
        metadata_path=args.metadata,
        quality_path=args.quality,
        odom_topic=args.odom_topic,
        drive_topic=args.drive_topic,
        collision_topic=args.collision_topic,
        internal_state_topic=args.internal_state_topic,
        dt_s=args.dt,
        sample_clock=args.sample_clock,
        sim_step_dt_s=args.sim_step_dt,
        command_frequency_start_hz=args.command_frequency_start,
        command_frequency_end_hz=args.command_frequency_end,
    )
    print(f"Wrote telemetry to {args.output}")
    print(f"Wrote metadata to {args.metadata}")
    print(f"Wrote quality metrics to {args.quality}")
    print(f"steer_rad_source={metadata['steer_rad_source']}")


if __name__ == "__main__":
    main()

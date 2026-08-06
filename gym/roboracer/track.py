"""Track geometry and pure-pursuit helpers shared by experiment scripts."""

from __future__ import annotations

from argparse import Namespace

import numpy as np


def nearest_point_on_trajectory(point: np.ndarray, trajectory: np.ndarray) -> tuple[np.ndarray, float, float, int]:
    diffs = trajectory[1:, :] - trajectory[:-1, :]
    l2s = diffs[:, 0] ** 2 + diffs[:, 1] ** 2
    dots = np.sum((point - trajectory[:-1, :]) * diffs[:, :], axis=1)
    t = np.clip(dots / l2s, 0.0, 1.0)
    projections = trajectory[:-1, :] + (t * diffs.T).T
    dists = np.linalg.norm(point - projections, axis=1)
    segment = int(np.argmin(dists))
    return projections[segment], float(dists[segment]), float(t[segment]), segment


def first_point_on_trajectory_intersecting_circle(
    point: np.ndarray,
    radius: float,
    trajectory: np.ndarray,
    t: float = 0.0,
    wrap: bool = False,
) -> tuple[np.ndarray | None, int | None, float | None]:
    start_i = int(t)
    start_t = t % 1.0

    ranges = [range(start_i, trajectory.shape[0] - 1)]
    if wrap:
        ranges.append(range(-1, start_i))

    for idx_range in ranges:
        for i in idx_range:
            start = trajectory[i % trajectory.shape[0], :]
            end = trajectory[(i + 1) % trajectory.shape[0], :] + 1e-6
            segment = end - start
            a = float(np.dot(segment, segment))
            b = float(2.0 * np.dot(segment, start - point))
            c = float(np.dot(start, start) + np.dot(point, point) - 2.0 * np.dot(start, point) - radius * radius)
            discriminant = b * b - 4 * a * c
            if discriminant < 0:
                continue

            root = float(np.sqrt(discriminant))
            for candidate_t in ((-b - root) / (2.0 * a), (-b + root) / (2.0 * a)):
                if 0.0 <= candidate_t <= 1.0 and (i != start_i or candidate_t >= start_t):
                    return start + candidate_t * segment, i, float(candidate_t)

    return None, None, None


def get_actuation(
    pose_theta: float,
    lookahead_point: np.ndarray,
    position: np.ndarray,
    lookahead_distance: float,
    wheelbase: float,
) -> tuple[float, float]:
    waypoint_y = float(np.dot(np.array([np.sin(-pose_theta), np.cos(-pose_theta)]), lookahead_point[0:2] - position))
    speed = float(lookahead_point[2])
    if abs(waypoint_y) < 1e-6:
        return speed, 0.0
    radius = 1.0 / (2.0 * waypoint_y / lookahead_distance**2)
    steering_angle = float(np.arctan(wheelbase / radius))
    return speed, steering_angle


class PurePursuitPlanner:
    def __init__(self, conf: Namespace, wheelbase: float):
        self.conf = conf
        self.wheelbase = wheelbase
        self.waypoints = np.loadtxt(conf.wpt_path, delimiter=conf.wpt_delim, skiprows=conf.wpt_rowskip)
        self.max_reacquire = 20.0

    def _get_current_waypoint(
        self,
        waypoints: np.ndarray,
        lookahead_distance: float,
        position: np.ndarray,
    ) -> np.ndarray | None:
        wpts = np.vstack((self.waypoints[:, self.conf.wpt_xind], self.waypoints[:, self.conf.wpt_yind])).T
        _, nearest_dist, t, i = nearest_point_on_trajectory(position, wpts)
        if nearest_dist < lookahead_distance:
            _, i2, _ = first_point_on_trajectory_intersecting_circle(
                position,
                lookahead_distance,
                wpts,
                i + t,
                wrap=True,
            )
            if i2 is None:
                return None
            current_waypoint = np.empty((3,))
            current_waypoint[0:2] = wpts[i2, :]
            current_waypoint[2] = waypoints[i, self.conf.wpt_vind]
            return current_waypoint
        if nearest_dist < self.max_reacquire:
            return np.append(wpts[i, :], waypoints[i, self.conf.wpt_vind])
        return None

    def plan(
        self,
        pose_x: float,
        pose_y: float,
        pose_theta: float,
        lookahead_distance: float,
        vgain: float,
    ) -> tuple[float, float]:
        position = np.array([pose_x, pose_y])
        lookahead_point = self._get_current_waypoint(self.waypoints, lookahead_distance, position)
        if lookahead_point is None:
            return 4.0, 0.0
        speed, steering_angle = get_actuation(
            pose_theta,
            lookahead_point,
            position,
            lookahead_distance,
            self.wheelbase,
        )
        return vgain * speed, steering_angle


def nearest_waypoint_metrics(
    x: float,
    y: float,
    waypoints: np.ndarray,
    conf: Namespace,
) -> tuple[int, float, float, float]:
    point = np.array([x, y], dtype=float)
    xy = waypoints[:, [conf.wpt_xind, conf.wpt_yind]]
    progress = waypoints[:, 0]

    starts = xy[:-1]
    ends = xy[1:]
    segments = ends - starts
    seg_len_sq = np.sum(segments * segments, axis=1)
    valid = seg_len_sq > 0.0
    if not np.any(valid):
        raise ValueError("Waypoint path has no valid segments.")

    t = np.zeros(len(segments))
    t[valid] = np.clip(np.sum((point - starts[valid]) * segments[valid], axis=1) / seg_len_sq[valid], 0.0, 1.0)
    projections = starts + (t * segments.T).T
    deltas = point - projections
    dists = np.linalg.norm(deltas, axis=1)
    dists[~valid] = np.inf

    best_idx = int(np.argmin(dists))
    best_t = float(t[best_idx])
    seg_len = float(np.sqrt(seg_len_sq[best_idx]))
    start = starts[best_idx]
    segment = segments[best_idx]
    cross = float(segment[0] * (point[1] - start[1]) - segment[1] * (point[0] - start[0]))
    signed_dist = cross / seg_len
    progress_m = float(progress[best_idx] + best_t * (progress[best_idx + 1] - progress[best_idx]))
    return best_idx, progress_m, signed_dist, abs(signed_dist)


def scalar(obs: dict, key: str, index: int = 0) -> float:
    return float(obs[key][index])


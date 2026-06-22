# Item 11 ROS-Bag Validation — Design
Status: approved
Date: 2026-06-21

## Goal

Produce auditable evidence that the modeling pipeline accepts genuine ROS 2 middleware data. The project bridge provides an enriched, achieved-steering dataset for controlled Gym-oracle recovery. Stock `f1tenth_gym_ros` proves standard `/ego_racecar/odom` plus `/drive` ingestion only.

## Acceptance criteria

- Raw SQLite3 bags are stored outside Git and linked to committed telemetry through SHA-256 manifests.
- Conversion is byte deterministic and reports topic timing, gaps, overlap, clock basis, steering source, collision observability, and real-time factor.
- Enriched identification uses native internal-state samples and at least 5.5 simulator-seconds of held-out data; it is reported as simulator recovery, not hardware validation.
- The upstream run uses only odometry and drive data and never supports an evidentiary parameter fit.
- Offline regression checks run without ROS, network access, or raw-bag downloads.

## Fixed decisions

- Upstream revision: `883394df0964c555ee05bea69c3002daf6f2d405`.
- Bag storage: SQLite3; release tag: `v11-ros-bag`.
- System clock is used for transport timestamps; enriched simulator time is published as internal-state element 8.
- The raw achieved-steering state is fitted without smoothing or upsampling.
- Held-out duration is the primary evidence gate; transition count is secondary bookkeeping.
- Stock upstream quality metrics derive only from odometry and drive topics.


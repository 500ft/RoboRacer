# Upstream RoboRacer Sources

Retrieved: 2026-06-08

These upstream repositories are referenced for compatibility only. They are not vendored or added as submodules in this repository.

| Repository | Default branch | Pinned HEAD | License | Use in this project |
| --- | --- | --- | --- | --- |
| `f1tenth/f1tenth_gym` | `main` | `4fdb9c7e6fb7c701290f4dc18377d07c1681724f` | MIT | Gym simulator and vehicle dynamics baseline |
| `f1tenth/f1tenth_gym_ros` | `main` | `883394df0964c555ee05bea69c3002daf6f2d405` | MIT | ROS simulator interface reference |
| `f1tenth/f1tenth_system` | `foxy-devel` | `ae64e05fbaf6eda592ef56c13ce89c896d489a55` | MIT | ROS 2 vehicle system reference |
| `f1tenth/vesc` | `main` | `e3f3084408f46bdd09de6a6b69ba9ce1152dc39f` | BSD-3-Clause | VESC driver and hardware interface reference |
| `f1tenth/f1tenth_planning` | `main` | `70f0b6ccd09a975ee8711e132e75800da6cc61e0` | MIT | Planning and controller reference |

## Policy

- Use these pins when comparing interfaces or behavior.
- Do not copy upstream source into this repository unless a later change explicitly vendors it with license review.
- Prefer standard ROS 2 topics (`/drive`, `/ego_racecar/odom`) before project-specific helper topics.

"""ROS2 bridge notes for Fear HRI (no rclpy here)."""

from __future__ import annotations

from dataclasses import dataclass

from fear_mecanumbot.sensing import avoid_retreat_distance_m, fused_min_range


@dataclass(frozen=True)
class RosTopic:
    name: str
    msg: str
    role: str


@dataclass(frozen=True)
class RosAction:
    name: str
    type_name: str
    role: str


FEAR_HRI_SUBSCRIPTIONS = (
    RosTopic("/scan", "sensor_msgs/LaserScan", "forward min range + closing speed"),
    RosTopic("/amcl_pose", "geometry_msgs/PoseWithCovarianceStamped", "robot pose"),
    RosTopic("/mecanumbot/people_fusion", "mecanumbot_msgs (people)", "person pose when LIDAR blind"),
)

FEAR_HRI_ACTIONS = (
    RosAction("/navigate_to_pose", "nav2_msgs/action/NavigateToPose", "task + fear-scaled avoid retreat"),
)

FEAR_HRI_PUBLICATIONS = (
    RosTopic("/cmd_vel", "geometry_msgs/Twist", "freeze stop / SmoothTurner"),
)


def bridge_checklist() -> list[str]:
    return [
        "/scan → min_range + closing_speed; fuse with people_fusion if person behind robot",
        "risk → fear_level (spike on near-collision, slow decay)",
        "Policy: freeze | avoid | catch_attention | task",
        "avoid: Nav2 Approach to retreat pose; distance scales with fear_level (not fixed inflation)",
        "freeze: cancel Nav2 + zero Twist",
        "catch_attention: RelativeTurnPattern + DogBehaviourSequence",
        "task: Approach brick then goal",
    ]


def plan_min_range(
    lidar_min: float,
    robot_xy: tuple[float, float],
    person_xy: tuple[float, float] | None,
    *,
    person_visible_to_lidar: bool = True,
) -> tuple[float, str]:
    """Documented fusion path for the on-robot Fear HRI node."""
    if person_xy is None:
        return lidar_min, "lidar"
    from fear_mecanumbot.sensing import person_distance

    return fused_min_range(
        lidar_min=lidar_min,
        person_range=person_distance(robot_xy, person_xy),
        person_visible_to_lidar=person_visible_to_lidar,
    )


def plan_avoid_distance(fear_level: float, base_m: float = 0.8) -> float:
    return avoid_retreat_distance_m(fear_level, base=base_m)

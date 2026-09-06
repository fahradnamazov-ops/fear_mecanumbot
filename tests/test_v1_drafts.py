"""Draft package and sim scenario sanity checks."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_fear_hri_yaml_has_thresholds():
    text = (ROOT / "ros_draft" / "mecanumbot_fear_hri_behaviour" / "config" / "fear_hri_constants.yaml").read_text(
        encoding="utf-8"
    )
    for key in (
        "safe_distance_m",
        "hit_distance_m",
        "avoid_distance_m",
        "fear_decay_per_step",
        "fear_hri_bt_node",
    ):
        assert key in text


def test_sim_scenario_matches_team_format():
    text = (ROOT / "sim_draft" / "fear_hri_brick_carry.yaml").read_text(encoding="utf-8")
    assert "sim_human_0" in text
    assert "mode: patrol" in text
    assert "fear_hri_brick_carry" in text
    assert text.count("waypoints:") == 1


def test_ros_draft_has_package_xml():
    assert (ROOT / "ros_draft" / "mecanumbot_fear_hri_behaviour" / "package.xml").is_file()

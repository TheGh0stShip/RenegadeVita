from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_campaign_flight_recorder_sources_are_compiled():
    cmake = (ROOT / "CMakeLists.txt").read_text(encoding="utf-8")
    assert "port/developer/a35_campaign_flight_recorder.cpp" in cmake
    assert "a35_campaign_flight_recorder.cpp" in cmake


def test_campaign_flight_recorder_schema_outputs_are_present():
    source = (
        ROOT / "port" / "developer" / "a35_campaign_flight_recorder.cpp"
    ).read_text(encoding="utf-8")
    for artifact in (
        "campaign-flight-events.jsonl",
        "campaign-flight-frames.csv",
        "campaign-flight-summary.json",
        "campaign-flight-log-tail.txt",
    ):
        assert artifact in source
    for field in (
        "slow_counts",
        "mission",
        "resources",
        "active_streams",
        "render_incomplete",
    ):
        assert field in source


def test_campaign_flight_recorder_runtime_hooks_are_present():
    log_runtime = (
        ROOT / "port" / "platform" / "vita" / "a30_vita_runtime.cpp"
    ).read_text(encoding="utf-8")
    assert "A35_Campaign_Flight_Record_Log_Line" in log_runtime

    interactive = (
        ROOT / "port" / "platform" / "vita" / "a31_vita_runtime.cpp"
    ).read_text(encoding="utf-8")
    for hook in (
        "A35_Campaign_Flight_Reset",
        "A35_Campaign_Flight_Record_Frame",
        "A35_Campaign_Flight_Record_Mission",
        "A35_Campaign_Flight_Record_Resource_Snapshot",
        "A35_Campaign_Flight_Flush",
        "A35_Campaign_Flight_Shutdown",
    ):
        assert hook in interactive
    for reason in (
        "mission-progress-change",
        "slow-frame-over-250ms",
        "checkpoint",
        "best-effort-fatal-snapshot",
        "final",
    ):
        assert reason in interactive

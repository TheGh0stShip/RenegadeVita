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


def test_campaign_flight_checkpoints_append_deltas_not_full_snapshots():
    source = (
        ROOT / "port" / "developer" / "a35_campaign_flight_recorder.cpp"
    ).read_text(encoding="utf-8")
    flush = source[source.index("bool A35_Campaign_Flight_Flush("):]
    assert "persisted_frame_sequence / kFlightFrameCapacity" in flush
    assert "persisted_event_sequence / kFlightEventCapacity" in flush
    assert "persisted_log_sequence / kFlightLogCapacity" in flush
    assert "strcmp(reason, \"best-effort-fatal-snapshot\") == 0" in flush
    assert "Make_Directory(gRecorder.capture_root)" not in flush
    assert "Write_Log_Tail(file, log_start, gRecorder.log_sequence)" in flush
    assert "Open_Flight_File(path, !replace_events)" in flush
    assert "Open_Flight_File(path, !replace_frames)" in flush
    assert "Open_Flight_File(path, !replace_log_tail)" in flush
    assert "sceIoRemove(path)" in source
    assert "remove(path) != 0 && errno != ENOENT" in source


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

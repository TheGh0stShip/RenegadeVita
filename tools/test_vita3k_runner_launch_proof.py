from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "tools" / "run_vita3k_demo_windows.ps1"


def test_vita3k_runner_requires_candidate_runtime_log_launch_proof():
    text = RUNNER.read_text(encoding="utf-8")
    assert "$receipt.runtime_log_path = $runtimeLog" in text
    assert "$receipt.title_launch_proven" in text
    assert "$receipt.runtime_candidate_seen" in text
    assert "$receipt.status = 'TITLE_NOT_LAUNCHED'" in text
    assert "Vita3K launch alone is not runtime evidence" in text
    assert "if ($receipt.status -eq 'TITLE_NOT_LAUNCHED') { exit 2 }" in text


def test_launch_proof_is_checked_before_timeout_exit():
    text = RUNNER.read_text(encoding="utf-8")
    launch_exit = text.index("if ($receipt.status -eq 'TITLE_NOT_LAUNCHED') { exit 2 }")
    timeout_exit = text.index("if ($receipt.status -eq 'TIMEOUT_UNASSESSED') { exit 124 }")
    assert launch_exit < timeout_exit

"""Contracts for one-shot action animation completion on Vita."""

from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class AnimationActionCompletionContract(unittest.TestCase):
    def test_one_shot_animation_completion_is_not_exact_float_equality(self):
        header = (ROOT / "staging/combat/animcontrol.h").read_text()
        self.assertIn("(Mode == ANIM_MODE_ONCE) && (Frame >= NumFrames-1)", header)
        self.assertNotIn("(Mode == ANIM_MODE_ONCE) && (Frame == NumFrames-1)", header)

    def test_non_looping_action_animation_has_bounded_vita_escape(self):
        action = (ROOT / "staging/combat/action.cpp").read_text()
        self.assertIn("!Action->Get_Parameters().AnimationLooping", action)
        self.assertIn("elapsed_frames > 1800 || StalledFrames > 300", action)
        self.assertIn("A4 animation action forced complete", action)
        self.assertIn("Action->Done( ACTION_COMPLETE_NORMAL );", action)


if __name__ == "__main__":
    unittest.main()

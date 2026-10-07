"""Line-for-line Python mirror of port/renderer/vita/frame_pacing.h.

The C++ header is the production policy for frame-pacing-v1.flag (RVFR1).
This module ports the same rules statement by statement so the hysteresis can
be exercised on synthetic frame-time traces without a compiler
(tools/test_vita_frame_pacing.py). Names, constants and statement order follow
the header; when one file changes, change the other identically. The test
parses the header and fails if the constants, flag table or decision names
drift apart.

All values are unsigned 32-bit microsecond counts in the C++ code; the inputs
used here stay well inside that range, so Python ints behave identically.
"""

MODE_OFF = 0       # swap interval never touched (current behaviour)
MODE_LOCK30 = 1    # swap interval 2 whenever armed
MODE_ADAPTIVE = 2  # swap interval 1 or 2 per window, with hysteresis
MODE_COUNT = 3


def Mode_Name(mode):
    if mode == MODE_LOCK30:
        return "lock30"
    if mode == MODE_ADAPTIVE:
        return "adaptive"
    return "off"


FLAG_ENTRIES = (("off", MODE_OFF), ("30", MODE_LOCK30), ("auto", MODE_ADAPTIVE))


def Parse_Flag(data):
    """Returns the mode for exactly valid flag bytes, otherwise None
    (C++: returns false and leaves mode untouched)."""
    size = len(data) if data is not None else 0
    if data is None or size < 8 or data[:6] != b"RVFR1 " or data[size - 1:size] != b"\n":
        return None
    value = data[6:]
    length = size - 7
    for text, mode in FLAG_ENTRIES:
        if len(text) == length and text.encode() == value[:length]:
            return mode
    return None


class Cadence:
    def __init__(self):
        self.Reset()
        self._last = 0
        self._have_last = False

    def Reset(self):
        self.frames = 0
        self.zero = 0
        self.one = 0
        self.two = 0
        self.three_plus = 0
        self.changes = 0

    def Break(self):
        self._have_last = False

    def Record(self, delta):
        self.frames += 1
        if delta == 0:
            self.zero += 1
        elif delta == 1:
            self.one += 1
        elif delta == 2:
            self.two += 1
        else:
            self.three_plus += 1
        if self._have_last and delta != self._last:
            self.changes += 1
        self._last = delta
        self._have_last = True


DECISION_NONE = 0
DECISION_HOLD = 1
DECISION_SUSPEND = 2
DECISION_ARM = 3
DECISION_DOWN = 4
DECISION_UP = 5
DECISION_REVERT_UP = 6


def Decision_Name(kind):
    return {
        DECISION_HOLD: "hold",
        DECISION_SUSPEND: "suspend",
        DECISION_ARM: "arm",
        DECISION_DOWN: "down",
        DECISION_UP: "up",
        DECISION_REVERT_UP: "revert-up",
    }.get(kind, "none")


class Decision:
    __slots__ = ("kind", "previous_interval", "interval", "p95_interval_us",
                 "p95_busy_us", "up_lock", "headroom_windows")

    def __init__(self):
        self.kind = DECISION_NONE
        self.previous_interval = 0
        self.interval = 0
        self.p95_interval_us = 0
        self.p95_busy_us = 0
        self.up_lock = 0
        self.headroom_windows = 0


class Controller:
    WINDOW = 60
    DOWN_P95_US = 17500
    UP_BUSY_P95_US = 13000
    UP_DWELL = 3
    PROBATION_WINDOWS = 3
    STALL_US = 200000
    ARM_FRAMES = 60
    BACKOFF_INITIAL = 4
    BACKOFF_MAX = 256

    def __init__(self):
        self._interval_samples = [0] * self.WINDOW
        self._busy_samples = [0] * self.WINDOW
        self.Reset(MODE_OFF)

    def Reset(self, mode):
        self._mode = mode if mode < MODE_COUNT else MODE_OFF
        self._target = 2 if self._mode == MODE_LOCK30 else 1
        self._armed = False
        self._steady = 0
        self._count = 0
        self._probation = 0
        self._headroom = 0
        self._up_lock = 0
        self._backoff = self.BACKOFF_INITIAL

    def Mode(self):
        return self._mode

    def Armed(self):
        return self._armed

    def Target(self):
        return self._target

    def Interval(self):
        return self._target if self._armed else 1

    def Record_Frame(self, interval_us, busy_us, suspend):
        decision = Decision()
        decision.kind = DECISION_NONE
        decision.previous_interval = self.Interval()
        if self._mode != MODE_OFF:
            if suspend or interval_us > self.STALL_US:
                self._count = 0
                self._steady = 0
                self._headroom = 0
                if self._armed:
                    self._armed = False
                    decision.kind = DECISION_SUSPEND
            elif not self._armed:
                self._steady += 1
                if self._steady >= self.ARM_FRAMES:
                    self._armed = True
                    self._count = 0
                    decision.kind = DECISION_ARM
            else:
                self._interval_samples[self._count] = interval_us
                self._busy_samples[self._count] = busy_us
                self._count += 1
                if self._count >= self.WINDOW:
                    self._count = 0
                    decision.p95_interval_us = self._P95(self._interval_samples)
                    decision.p95_busy_us = self._P95(self._busy_samples)
                    decision.kind = self._Decide(decision.p95_interval_us, decision.p95_busy_us)
        decision.interval = self.Interval()
        decision.up_lock = self._up_lock
        decision.headroom_windows = self._headroom
        return decision

    def _P95(self, samples):
        sorted_ = list(samples[:self.WINDOW])
        for i in range(1, self.WINDOW):
            value = sorted_[i]
            j = i
            while j > 0 and sorted_[j - 1] > value:
                sorted_[j] = sorted_[j - 1]
                j -= 1
            sorted_[j] = value
        return sorted_[(self.WINDOW * 95) // 100]

    def _Lock_Up(self):
        self._up_lock = self._backoff
        self._backoff = self.BACKOFF_MAX if self._backoff * 2 > self.BACKOFF_MAX else self._backoff * 2

    def _Decide(self, p95_interval, p95_busy):
        if self._mode != MODE_ADAPTIVE:
            return DECISION_HOLD
        if self._up_lock > 0:
            self._up_lock -= 1
        if self._target == 1:
            if p95_interval <= self.DOWN_P95_US:
                if self._probation > 0:
                    self._probation -= 1
                return DECISION_HOLD
            self._target = 2
            self._headroom = 0
            if self._probation > 0:
                self._probation = 0
                self._Lock_Up()
                return DECISION_REVERT_UP
            return DECISION_DOWN
        if p95_busy <= self.UP_BUSY_P95_US:
            if self._headroom < self.UP_DWELL:
                self._headroom += 1
        else:
            self._headroom = 0
        if self._headroom >= self.UP_DWELL and self._up_lock == 0:
            self._target = 1
            self._headroom = 0
            self._probation = self.PROBATION_WINDOWS
            return DECISION_UP
        return DECISION_HOLD

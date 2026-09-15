#ifndef RENEGADE_EXPERIMENT_DIAGNOSTIC_SAMPLE_POLICY_H
#define RENEGADE_EXPERIMENT_DIAGNOSTIC_SAMPLE_POLICY_H

#include <stdint.h>

// Experimental only: not included in canonical source selection.
// Single game-thread owner; no allocation, clock reads or filesystem polling.
namespace RenegadeExperiments {

class DiagnosticSamplePolicy {
public:
    explicit DiagnosticSamplePolicy(bool enabled = false,
                                    uint64_t interval_frames = 30)
        : Enabled(enabled), Interval(interval_frames ? interval_frames : 1),
          Valid(false), Epoch(0), Frame(0) {}

    bool Needs_Sample(uint64_t scene_epoch, uint64_t frame,
                      bool explicit_capture = false) const {
        return !Enabled || explicit_capture || !Valid || Epoch != scene_epoch ||
               frame < Frame || frame - Frame >= Interval;
    }

    // Call only after the complete expensive snapshot has been collected.
    // A failed/aborted collection must not suppress the next attempt.
    void Commit_Sample(uint64_t scene_epoch, uint64_t frame) {
        Epoch = scene_epoch;
        Frame = frame;
        Valid = true;
    }

    bool Has_Sample(uint64_t scene_epoch, uint64_t frame) const {
        return Valid && Epoch == scene_epoch && frame >= Frame;
    }

    // UINT64_MAX denotes no reusable sample, not an age of zero.
    uint64_t Sample_Age(uint64_t scene_epoch, uint64_t frame) const {
        return Has_Sample(scene_epoch, frame) ? frame - Frame : ~uint64_t(0);
    }

    void Reset() { Valid = false; }

private:
    bool Enabled;
    uint64_t Interval;
    bool Valid;
    uint64_t Epoch;
    uint64_t Frame;
};

} // namespace RenegadeExperiments

#endif

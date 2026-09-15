#pragma once

#include <stddef.h>
#include <stdint.h>

namespace RenegadeTextEntry {
constexpr size_t MaxLength = 2048;
enum class Status { Absent, Running, Finished };

// Storage belongs to the session until the native dialog has terminated.
// Backend supplies Open, Get_Status, Accepted, Close and Abort; WWUI remains
// the text owner and explicitly consumes a completed result.
template<class Backend> class Session {
public:
    bool Begin(const void *owner, const wchar_t *text, int limit) {
        Poll();
        if (!owner || !text || limit <= 0 || active_ || owner_ || release_) return false;
        limit_ = static_cast<size_t>(limit) < MaxLength ? static_cast<size_t>(limit) : MaxLength;
        size_t n = 0;
        for (size_t i = 0; text[i] && n < limit_; ++i) {
            uint32_t c = static_cast<uint32_t>(text[i]);
            if (sizeof(wchar_t) == 2 && c >= 0xD800 && c <= 0xDBFF) {
                const uint32_t low = static_cast<uint32_t>(text[i + 1]);
                if (low < 0xDC00 || low > 0xDFFF) return false;
                if (n + 2 > limit_) break;
                initial_[n++] = static_cast<uint16_t>(c);
                initial_[n++] = static_cast<uint16_t>(low);
                ++i;
            } else {
                if (c > 0x10FFFF || (c >= 0xD800 && c <= 0xDFFF)) return false;
                if (c > 0xFFFF) {
                    if (n + 2 > limit_) break;
                    c -= 0x10000;
                    initial_[n++] = static_cast<uint16_t>(0xD800 + (c >> 10));
                    initial_[n++] = static_cast<uint16_t>(0xDC00 + (c & 1023));
                } else initial_[n++] = static_cast<uint16_t>(c);
            }
        }
        initial_[n] = 0;
        for (size_t i = 0; i <= MaxLength; ++i) output_[i] = 0;
        if (!Backend::Open(initial_, output_, limit_)) return false;
        owner_ = owner;
        active_ = release_ = true;
        finishing_ = accepted_ = false;
        return true;
    }

    void Poll() {
        if (!active_) return;
        const Status status = Backend::Get_Status();
        if (status == Status::Absent) {
            active_ = accepted_ = false;
            return;
        }
        if (status != Status::Finished) return;
        if (!finishing_) {
            accepted_ = owner_ && Backend::Accepted() && Valid_Output();
            finishing_ = true;
        }
        // A failed termination must not free/reuse a buffer still held by OS.
        if (Backend::Close()) active_ = false;
    }

    bool Take_Result(const void *owner, wchar_t *text, size_t capacity) {
        Poll();
        if (!owner || owner != owner_ || active_) return false;
        const bool accepted = accepted_ && text && capacity > limit_;
        if (accepted) {
            size_t n = 0;
            for (size_t i = 0; output_[i]; ++i) {
                uint32_t c = output_[i];
                if (sizeof(wchar_t) > 2 && c >= 0xD800 && c <= 0xDBFF) {
                    c = 0x10000 + ((c - 0xD800) << 10) + (output_[++i] - 0xDC00);
                }
                text[n++] = static_cast<wchar_t>(c);
            }
            text[n] = 0;
        }
        owner_ = nullptr;
        accepted_ = false;
        return accepted;
    }

    void Cancel(const void *owner) {
        if (!owner || owner != owner_) return;
        owner_ = nullptr;
        accepted_ = false;
        if (active_) Backend::Abort();
        Poll();
    }
    void Cancel_All() { Cancel(owner_); }
    bool Active() { Poll(); return active_; }
    bool Block_Input(bool neutral) {
        Poll();
        if (active_ || owner_) return true;
        if (release_) {
            if (neutral) release_ = false;
            return true; // swallow the neutral/release sample too
        }
        return false;
    }

private:
    bool Valid_Output() const {
        for (size_t i = 0; i <= limit_; ++i) {
            const uint16_t c = output_[i];
            if (!c) return true;
            if (c >= 0xDC00 && c <= 0xDFFF) return false;
            if (c >= 0xD800 && c <= 0xDBFF) {
                if (++i >= limit_ || output_[i] < 0xDC00 || output_[i] > 0xDFFF) return false;
            }
        }
        return false;
    }
    const void *owner_ = nullptr;
    uint16_t initial_[MaxLength + 1] = {};
    uint16_t output_[MaxLength + 1] = {};
    size_t limit_ = 0;
    bool active_ = false, finishing_ = false, accepted_ = false, release_ = false;
};
}

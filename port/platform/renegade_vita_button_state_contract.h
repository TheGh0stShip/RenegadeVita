#pragma once

#include <stdint.h>

// This is the original DirectInput polling transition table expressed at the
// Vita device boundary.  It deliberately returns a complete state each poll:
// a release is not also held on the following poll.
namespace RenegadeVitaInput {

enum : uint8_t {
	BUTTON_HELD = 1U,
	BUTTON_HIT = 2U,
	BUTTON_RELEASED = 4U
};

inline uint8_t Advance_Button_State(uint8_t previous_state, bool pressed)
{
	static const uint8_t transition_table[4] = {
		0U,
		static_cast<uint8_t>(BUTTON_HIT | BUTTON_HELD),
		BUTTON_RELEASED,
		BUTTON_HELD
	};
	const unsigned int index =
		((previous_state & BUTTON_HELD) != 0U ? 2U : 0U) +
		(pressed ? 1U : 0U);
	return transition_table[index];
}

} // namespace RenegadeVitaInput

#include "renegade_vita_button_state_contract.h"

#include <stdio.h>

namespace {

void Check(bool condition, const char *name, unsigned &checks, unsigned &failures)
{
	++checks;
	if (!condition) {
		++failures;
		fprintf(stderr, "Vita button-state contract failed: %s\n", name);
	}
}

} // namespace

int main()
{
	using namespace RenegadeVitaInput;
	unsigned checks = 0U;
	unsigned failures = 0U;
	uint8_t fire = 0U;
	uint8_t crouch = 0U;

	fire = Advance_Button_State(fire, true);
	Check(fire == (BUTTON_HIT | BUTTON_HELD), "up to pressed", checks, failures);
	fire = Advance_Button_State(fire, true);
	Check(fire == BUTTON_HELD, "pressed to held", checks, failures);
	fire = Advance_Button_State(fire, false);
	Check(fire == BUTTON_RELEASED, "held to released", checks, failures);
	fire = Advance_Button_State(fire, false);
	Check(fire == 0U, "released to up", checks, failures);

	fire = Advance_Button_State(fire, true);
	crouch = Advance_Button_State(crouch, true);
	Check((fire & BUTTON_HELD) != 0U && (crouch & BUTTON_HELD) != 0U,
		"fire and crouch are independent", checks, failures);
	fire = Advance_Button_State(fire, false);
	crouch = Advance_Button_State(crouch, true);
	Check(fire == BUTTON_RELEASED && crouch == BUTTON_HELD,
		"releasing fire cannot retain or release crouch", checks, failures);
	crouch = Advance_Button_State(crouch, false);
	Check(crouch == BUTTON_RELEASED, "crouch release is an edge", checks, failures);
	Check(Advance_Button_State(0U, false) == 0U &&
		Advance_Button_State(BUTTON_RELEASED, false) == 0U,
		"identical up samples remain up", checks, failures);
	const uint8_t tap_press = Advance_Button_State(0U, true);
	const uint8_t tap_release = Advance_Button_State(tap_press, false);
	Check(tap_press == (BUTTON_HIT | BUTTON_HELD) && tap_release == BUTTON_RELEASED,
		"one-poll tap emits press then release", checks, failures);
	Check(Advance_Button_State(BUTTON_HELD, false) == BUTTON_RELEASED &&
		Advance_Button_State(BUTTON_RELEASED, false) == 0U,
		"focus loss or disconnect clearing reaches up", checks, failures);

	printf("A3.5 Vita button-state contract: %s (%u checks, %u failures)\n",
		failures == 0U ? "PASS" : "FAIL", checks, failures);
	return failures == 0U ? 0 : 1;
}

#include "renegade_ui_pointer_tokens.h"

#include <stdio.h>

namespace {

void Check(bool condition, const char *name, unsigned &checks, unsigned &failures)
{
	++checks;
	if (!condition) {
		++failures;
		fprintf(stderr, "ui-token check failed: %s\n", name);
	}
}

} // namespace

int main()
{
	unsigned checks = 0U;
	unsigned failures = 0U;
	int first = 1;
	int second = 2;
	const uint32_t first_token = Renegade_Ui_Pointer_To_Token(&first);
	const uint32_t second_token = Renegade_Ui_Pointer_To_Token(&second);
	Check(first_token != 0U && second_token != 0U && first_token != second_token,
		"distinct nonzero tokens", checks, failures);
	Check(Renegade_Ui_Pointer_From_Token(first_token) == &first,
		"resolve without transfer", checks, failures);
	Check(Renegade_Ui_Take_Pointer_Token(second_token) == &second,
		"take transfers ownership", checks, failures);
	Check(Renegade_Ui_Pointer_From_Token(second_token) == NULL,
		"taken token is unavailable", checks, failures);
	Check(Renegade_Ui_Take_Pointer_Token(first_token) == &first,
		"remaining token is transferable", checks, failures);
	printf("A4 UI pointer-token contract: %s (%u checks, %u failures)\n",
		failures == 0U ? "PASS" : "FAIL", checks, failures);
	return failures == 0U ? 0 : 1;
}

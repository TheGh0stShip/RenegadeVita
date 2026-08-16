#pragma once

struct WestwoodSelfTestResult
{
	bool passed;
	unsigned checks;
	unsigned failures;
	const char *first_failure;
};

WestwoodSelfTestResult Run_Westwood_Bitpack_Self_Test();


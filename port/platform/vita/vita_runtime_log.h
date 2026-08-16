#pragma once

// Appends one durable renderer breadcrumb to the A2.2 runtime log. Each call
// opens, writes, synchronizes, and closes the file so the last completed
// graphics-init stage survives a subsequent hang or crash.
int Vita_Append_A22_Runtime_Breadcrumb(const char *subsystem,
	const char *format, ...);

#pragma once

// Appends one durable renderer breadcrumb to the shared runtime log.  The file
// handle is retained after first use, while each completed record is still
// synchronized so the last finished graphics/input stage survives a later hang.
int Vita_Append_A22_Runtime_Breadcrumb(const char *subsystem,
	const char *format, ...);

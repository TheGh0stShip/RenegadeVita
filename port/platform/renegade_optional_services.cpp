#include "renegade_optional_services.h"

#include <stdio.h>

namespace RenegadeOptionalServices {
namespace {

SecurityFaultReporter g_security_fault_reporter = NULL;
const char *const kDataSafeSecurityFault =
	"Renegade DataSafe detected a security/integrity fault";

} // namespace

void Set_Security_Fault_Reporter(SecurityFaultReporter reporter)
{
	g_security_fault_reporter = reporter;
}

void Report_DataSafe_Security_Fault()
{
	if (g_security_fault_reporter != NULL) {
		g_security_fault_reporter(kDataSafeSecurityFault);
		return;
	}

	// A runtime owner can install its durable logger above.  Retain a visible,
	// flushed fallback for host tools and early platform initialization.
	fprintf(stderr, "%s\n", kDataSafeSecurityFault);
	fflush(stderr);
}

} // namespace RenegadeOptionalServices

#pragma once

// Boundary for optional Commando services that are intentionally unavailable
// during the single-player Vita bring-up.  The original engine still detects
// DataSafe corruption; only its multiplayer chat notification is redirected.
namespace RenegadeOptionalServices {

typedef void (*SecurityFaultReporter)(const char *message);

void Set_Security_Fault_Reporter(SecurityFaultReporter reporter);
void Report_DataSafe_Security_Fault();

} // namespace RenegadeOptionalServices

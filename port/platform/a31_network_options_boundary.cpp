// Vita network-profile boundary.
//
// The original cNetwork/WWNet transport and replication stack remains the
// session owner.  This file only replaces the retired desktop registry and
// BandTest-backed preference source with deterministic LAN/direct-IP defaults.

#include "bandwidth.h"
#include "bandwidthgraph.h"
#include "devoptions.h"
#include "useroptions.h"

namespace {
constexpr int kLanBaselineBps = 2000000;
}

// The original cNetwork uses this persisted value only for the legacy online
// branch.  LAN/direct-IP owns no GameSpy option state and starts with a safe
// local-link budget.
cRegistryInt cUserOptions::BandwidthBps(NULL, NULL, kLanBaselineBps);
cRegistryInt cUserOptions::BandwidthType(NULL, NULL, BANDWIDTH_LANT1);
cRegistryInt cUserOptions::NetUpdateRate(NULL, NULL, 10);
cRegistryFloat cUserOptions::ClientHintFactor(NULL, NULL, 10.0f);
cRegistryFloat cUserOptions::MaxFacingPenalty(NULL, NULL, 0.3f);
cRegistryFloat cUserOptions::IrrelevancePenalty(NULL, NULL, 0.2f);
cRegistryInt cUserOptions::ResultsLogNumber(NULL, NULL, 1);

// These retained registry-shaped values satisfy original common-session
// queries while the desktop option dialogs and retired GameSpy preferences
// remain outside the provider boundary.  They do not select a public service.
cRegistryBool cUserOptions::ShowNamesOnSoldier(NULL, NULL, true);
cRegistryBool cUserOptions::SkipQuitConfirmDialog(NULL, NULL, false);
cRegistryBool cUserOptions::SkipIngameQuitConfirmDialog(NULL, NULL, false);
cRegistryBool cUserOptions::CameraLockedToTurret(NULL, NULL, false);
cRegistryBool cUserOptions::PermitDiagLogging(NULL, NULL, true);
cRegistryInt cUserOptions::Sku(NULL, NULL, 0);
cRegistryInt cUserOptions::GameSpyBandwidthType(NULL, NULL, BANDWIDTH_LANT1);
cRegistryInt cUserOptions::PreferredGameSpyNic(NULL, NULL, 0);
cRegistryInt cUserOptions::GameSpyGamePort(NULL, NULL, 4848);
cRegistryInt cUserOptions::GameSpyQueryPort(NULL, NULL, 25300);
cRegistryInt cUserOptions::SplashCount(NULL, NULL, 0);
cRegistryBool cUserOptions::DoneClientBandwidthTest(NULL, NULL, false);
cRegistryInt cUserOptions::PreferredLanNic(NULL, NULL, 0);

// NewTCADO is owned by the original DevOptions implementation once the real
// frontend/campaign target is linked. Retain the old lightweight owner only
// for the earlier headless runtime.
#if !defined(RENEGADE_A4_ORIGINAL_GAMEMODE)
cRegistryBool cDevOptions::UseNewTCADO(NULL, NULL, true);
#endif

BANDWIDTH_TYPE_ENUM cUserOptions::Get_Bandwidth_Type(void)
{
	return static_cast<BANDWIDTH_TYPE_ENUM>(cUserOptions::BandwidthType.Get());
}

ULONG cBandwidth::Get_Bandwidth_Bps_From_Type(BANDWIDTH_TYPE_ENUM type)
{
	switch (type) {
	case BANDWIDTH_MODEM_288: return 28800;
	case BANDWIDTH_MODEM_336: return 33600;
	case BANDWIDTH_MODEM_56:  return 56000;
	case BANDWIDTH_ISDN:      return 64000;
	case BANDWIDTH_CABLE:     return 128000;
	case BANDWIDTH_LANT1:
	case BANDWIDTH_AUTO:      return kLanBaselineBps;
	case BANDWIDTH_CUSTOM:    return cUserOptions::BandwidthBps.Get();
	default:                  return kLanBaselineBps;
	}
}

// The graph's desktop renderer is intentionally not linked.  cNetwork still
// preserves the original scale selection as state for later Vita diagnostics.
int cBandwidthGraph::BandwidthScaler = kLanBaselineBps;
void cBandwidthGraph::Render(void) {}

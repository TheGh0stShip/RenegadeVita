#pragma once

// The original Combat owner calls these around its own HUD and screen-fade
// draws. The platform implementation adapts only the 2D presentation space;
// world/camera ownership remains entirely in CombatManager and WW3D.
void A31_Vita_Begin_Original_HUD_Render();
void A31_Vita_End_Original_HUD_Render();

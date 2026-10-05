# Original radio route source wiring

The full-port source selected `AnnounceEvent.cpp` and its original creation/
import owner but excluded the radio input loop and display lifecycle with
`RENEGADE_VITA_FRONTEND_SINGLEPLAYER`. The native simulation boundary also
does not execute CombatGameModeClass::Think/Combat_Keyboard; simply removing
that guard would not establish execution in the native frame path.

Local source changes select `radiocommanddisplay.cpp` through the shared
multiplayer source manifest. Two staging patches separate the original radio
loop from service/UI guards and extract that same loop into
CombatGameModeClass::Process_Radio_Command_Input. The original keyboard
handler and native simulation boundary call this shared owner. Its original
mission/client/star checks, 30 input functions, CNC settings lookup, team
announcement, radio command number and first-hit break remain intact.

Non-mission Combat activation initializes the original TextWindow display;
Combat shutdown releases it. Original Combat rendering and the native HUD
render scope call the original radio display. The M00-only native boundary
does not call the new route. Original input-edge semantics and cNetwork event
ownership remain unchanged. This adds no public-service dependency and makes
no network connection.

The local controller mapping uses Select plus L, R, or both triggers for the
three original modifier pages. Commands 1–8 use Up, Down, Left, Right,
Triangle, Circle, Cross, Square; 9–10 use left-stick Up and Down. The mapping
feeds the aggregate Control/Alt slots read by original Input::Get_Value and
suppresses ordinary movement, weapon and face-button actions during selection.
This mapping has not been compiled or exercised.

Remaining: original translated keyboard hints need controller labels, lifecycle/layout correctness,
staged patch application, compile/link and controlled peer behavior. Public/
team chat entry and team/server dialogs still have separate exclusions.
No tests/builds/device actions were run under the user's hold. No claim of
usable radio controls or network compatibility; edits remain local.

Next priority is single-player completion: trace the original M13 finale,
mission-complete screen and campaign transition into M01. Local Practice round
restart is a related completion boundary: its original core-restart consumer
is excluded from the native frame route and must be reviewed separately.

cmake_minimum_required(VERSION 3.16)

if(NOT DEFINED CMAKE_TOOLCHAIN_FILE)
  if(DEFINED ENV{VITASDK})
    set(CMAKE_TOOLCHAIN_FILE "$ENV{VITASDK}/share/vita.toolchain.cmake"
      CACHE PATH "VitaSDK toolchain")
  else()
    set(CMAKE_TOOLCHAIN_FILE "/usr/local/vitasdk/share/vita.toolchain.cmake"
      CACHE PATH "VitaSDK toolchain")
  endif()
endif()

project(RenegadeVitaA31 VERSION 3.5.4 LANGUAGES C CXX)

# This is provenance for a hardware candidate, not a public milestone claim.
# Keep the artifact identity configurable so a newer candidate can never
# overwrite the symbols and diagnostics that belong to an earlier one.
set(RENEGADE_CANDIDATE_LABEL "A3.5-dev102" CACHE STRING
  "Validated hardware-candidate label (for example A3.5-dev2)")
if(NOT RENEGADE_CANDIDATE_LABEL MATCHES "^A[0-9]+\\.[0-9]+-dev[0-9]+$")
  message(FATAL_ERROR "RENEGADE_CANDIDATE_LABEL must look like A3.5-dev2")
endif()
string(TOLOWER "${RENEGADE_CANDIDATE_LABEL}" RENEGADE_CANDIDATE_STEM)
string(REPLACE "." "" RENEGADE_CANDIDATE_STEM "${RENEGADE_CANDIDATE_STEM}")
option(RENEGADE_VITA_M00_DEMO "Interim M00 community showcase; not the full-port completion target" ON)
option(RENEGADE_VITA_CAMPAIGN_MSAA_4X
  "Use the established 4x MSAA framebuffer in the full-port renderer" ON)
option(RENEGADE_VITA_DEVELOPMENT_CHECKPOINT
  "Enable one-shot diagnostic save/mission launch requests; keep OFF for public packages" OFF)
# Only the native launch boundary consumes this option. A directory-wide
# definition needlessly invalidates every engine object when it changes.
set_property(SOURCE port/platform/vita/a31_vita_runtime.cpp APPEND PROPERTY
  COMPILE_DEFINITIONS
  RENEGADE_VITA_DEVELOPMENT_CHECKPOINT=$<BOOL:${RENEGADE_VITA_DEVELOPMENT_CHECKPOINT}>)
set_property(SOURCE port/renderer/vita/ww3d_vita_renderer.cpp APPEND PROPERTY
  COMPILE_DEFINITIONS
  RENEGADE_VITA_CAMPAIGN_MSAA_4X=$<BOOL:${RENEGADE_VITA_CAMPAIGN_MSAA_4X}>)
if(RENEGADE_VITA_M00_DEMO)
  set(RENEGADE_BUILD_PROFILE "M00-DEMO")
else()
  set(RENEGADE_BUILD_PROFILE "FULL-PORT-DEVELOPMENT")
endif()
set(RENEGADE_RUNTIME_LOG_PATH
  "ux0:data/renegade/user/logs/${RENEGADE_CANDIDATE_STEM}-runtime.log")
set(RENEGADE_STARTUP_PRECACHE_RECEIPT_PATH
  "ux0:data/renegade/user/logs/${RENEGADE_CANDIDATE_STEM}-startup-precache.txt")

# VitaDevBridge's package installer requires a bounded non-empty CONTENT_ID in
# sce_sys/param.sfo. Keep it under the same RNEGA3101 title so the package
# remains an update of the native Vita port; it identifies only this developer
# package and is not an EA or retail entitlement.
set(RENEGADE_VITA_CONTENT_ID "EP9000-RNEGA3101_00-RENEGADEVITA0102" CACHE STRING
  "Developer Vita package content identifier")
set(RENEGADE_VITA_TITLE_ID "RNEGA3101" CACHE STRING
  "Developer Vita title identifier")
string(LENGTH "${RENEGADE_VITA_TITLE_ID}" RENEGADE_VITA_TITLE_ID_LENGTH)
if(NOT RENEGADE_VITA_TITLE_ID_LENGTH EQUAL 9 OR
   NOT RENEGADE_VITA_TITLE_ID MATCHES "^[A-Z0-9]+$")
  message(FATAL_ERROR "RENEGADE_VITA_TITLE_ID must be nine uppercase letters or digits")
endif()
string(LENGTH "${RENEGADE_VITA_CONTENT_ID}" RENEGADE_VITA_CONTENT_ID_LENGTH)
if(NOT RENEGADE_VITA_CONTENT_ID_LENGTH EQUAL 36 OR
   NOT RENEGADE_VITA_CONTENT_ID MATCHES "^[A-Z0-9_-]+$")
  message(FATAL_ERROR
    "RENEGADE_VITA_CONTENT_ID must be a 36-character bounded Vita content identifier")
endif()

include("${CMAKE_CURRENT_SOURCE_DIR}/cmake/RenegadeCcache.cmake")

if(NOT DEFINED ENV{VITASDK})
  set(ENV{VITASDK} "/usr/local/vitasdk")
endif()
set(VITASDK "$ENV{VITASDK}")
include("${VITASDK}/share/vita.cmake" REQUIRED)

set(CMAKE_C_STANDARD 11)
set(CMAKE_C_STANDARD_REQUIRED ON)
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS ON)

set(RENEGADE_ROOT "${CMAKE_CURRENT_SOURCE_DIR}")
set(RENEGADE_UPSTREAM "${RENEGADE_ROOT}/upstream/CnC_Renegade")
set(RENEGADE_STAGE "${RENEGADE_ROOT}/staging")
set(RENEGADE_COMPAT "${RENEGADE_ROOT}/port/compatibility/include")
set(VITASDK_DEBUG_SCREEN "${VITASDK}/share/gcc-arm-vita-eabi/samples/common")
set(RENEGADE_GENERATED_INCLUDE "${CMAKE_CURRENT_BINARY_DIR}/generated")
file(MAKE_DIRECTORY "${RENEGADE_GENERATED_INCLUDE}")
find_package(Python3 REQUIRED COMPONENTS Interpreter)

option(RENEGADE_A4_ORIGINAL_FRONTEND
  "Link original Commando/WWUI frontend and Vita Bink provider path" ON)
set(RENEGADE_BINK_FFMPEG_ROOT
  "${RENEGADE_ROOT}/build/deps/ffmpeg-bink-vita" CACHE PATH
  "Bink-enabled Vita FFmpeg installation produced by tools/build_ffmpeg_bink_vita.sh")
if(RENEGADE_A4_ORIGINAL_FRONTEND)
  foreach(bink_dependency IN ITEMS
      include/libavformat/avformat.h
      lib/libavformat.a
      lib/libavcodec.a
      lib/libswscale.a
      lib/libswresample.a
      lib/libavutil.a)
    if(NOT EXISTS "${RENEGADE_BINK_FFMPEG_ROOT}/${bink_dependency}")
      message(FATAL_ERROR
        "Missing Vita Bink dependency ${bink_dependency}; run tools/build_ffmpeg_bink_vita.sh")
    endif()
  endforeach()
endif()

# The original Scripts project is staged deterministically so its Windows
# include casing and narrow portability corrections never modify upstream.
set(RENEGADE_SCRIPT_SOURCE "${RENEGADE_STAGE}/scripts")
set(RENEGADE_SCRIPT_ALIAS_INCLUDE
  "${RENEGADE_GENERATED_INCLUDE}/scripts-case-aliases")
file(MAKE_DIRECTORY "${RENEGADE_SCRIPT_ALIAS_INCLUDE}")
file(GLOB RENEGADE_SCRIPT_HEADERS "${RENEGADE_SCRIPT_SOURCE}/*.h")
foreach(script_header IN LISTS RENEGADE_SCRIPT_HEADERS)
  get_filename_component(script_header_name "${script_header}" NAME)
  string(TOLOWER "${script_header_name}" script_header_lower)
  if(NOT script_header_name STREQUAL script_header_lower)
    configure_file("${script_header}"
      "${RENEGADE_SCRIPT_ALIAS_INCLUDE}/${script_header_lower}" COPYONLY)
  endif()
endforeach()
configure_file(
  "${RENEGADE_ROOT}/port/platform/vita/build_identity.h.in"
  "${RENEGADE_GENERATED_INCLUDE}/renegade_build_identity.h"
  @ONLY)
include("${RENEGADE_ROOT}/cmake/A31OriginalSources.cmake")

if(RENEGADE_A4_ORIGINAL_FRONTEND)
  set(RENEGADE_A4_DIALOG_TEMPLATE_INCLUDE
    "${RENEGADE_GENERATED_INCLUDE}/renegade_dialog_templates.inc")
  set(RENEGADE_A4_DIALOG_CAMPAIGN_ARG)
  if(NOT RENEGADE_VITA_M00_DEMO)
    set(RENEGADE_A4_DIALOG_CAMPAIGN_ARG --campaign-dialogs)
  endif()
  add_custom_command(
    OUTPUT "${RENEGADE_A4_DIALOG_TEMPLATE_INCLUDE}"
    COMMAND ${Python3_EXECUTABLE}
      "${RENEGADE_ROOT}/tools/generate_wwui_dialog_templates.py"
      --rc "${RENEGADE_UPSTREAM}/Code/Commando/chat.rc"
      --resource-h "${RENEGADE_UPSTREAM}/Code/Commando/resource.h"
      --dialog-resource-h "${RENEGADE_UPSTREAM}/Code/Commando/dialogresource.h"
      --out "${RENEGADE_A4_DIALOG_TEMPLATE_INCLUDE}"
      ${RENEGADE_A4_DIALOG_CAMPAIGN_ARG}
    DEPENDS
      "${RENEGADE_ROOT}/tools/generate_wwui_dialog_templates.py"
      "${RENEGADE_UPSTREAM}/Code/Commando/chat.rc"
      "${RENEGADE_UPSTREAM}/Code/Commando/resource.h"
      "${RENEGADE_UPSTREAM}/Code/Commando/dialogresource.h"
    VERBATIM)
  add_custom_target(a4_dialog_templates
    DEPENDS "${RENEGADE_A4_DIALOG_TEMPLATE_INCLUDE}")

  set(RENEGADE_A4_FRONTEND_ORIGINAL_SOURCES
    ${RENEGADE_STAGE}/wwui/dialogparser.cpp
    ${RENEGADE_STAGE}/wwui/dialogbase.cpp
    ${RENEGADE_STAGE}/wwui/dialogmgr.cpp
    ${RENEGADE_STAGE}/wwui/wwuiinput.cpp
    ${RENEGADE_STAGE}/wwui/dialogcontrol.cpp
    ${RENEGADE_STAGE}/wwui/dialogtext.cpp
    ${RENEGADE_STAGE}/wwui/buttonctrl.cpp
    ${RENEGADE_STAGE}/wwui/checkboxctrl.cpp
    ${RENEGADE_STAGE}/wwui/imagectrl.cpp
    ${RENEGADE_STAGE}/wwui/textmarqueectrl.cpp
    ${RENEGADE_STAGE}/wwui/multilinetextctrl.cpp
    ${RENEGADE_STAGE}/wwui/editctrl.cpp
    ${RENEGADE_STAGE}/wwui/comboboxctrl.cpp
    ${RENEGADE_STAGE}/wwui/dropdownctrl.cpp
    ${RENEGADE_STAGE}/wwui/sliderctrl.cpp
    ${RENEGADE_STAGE}/wwui/tabctrl.cpp
    ${RENEGADE_STAGE}/wwui/treectrl.cpp
    ${RENEGADE_STAGE}/wwui/mapctrl.cpp
    ${RENEGADE_STAGE}/wwui/viewerctrl.cpp
    ${RENEGADE_STAGE}/wwui/inputctrl.cpp
    ${RENEGADE_STAGE}/wwui/shortcutbarctrl.cpp
    ${RENEGADE_STAGE}/wwui/merchandisectrl.cpp
    ${RENEGADE_STAGE}/wwui/ProgressCtrl.cpp
    ${RENEGADE_STAGE}/wwui/healthbarctrl.cpp
    ${RENEGADE_STAGE}/wwui/childdialog.cpp
    ${RENEGADE_STAGE}/wwui/menuentryctrl.cpp
    ${RENEGADE_STAGE}/wwui/menudialog.cpp
    ${RENEGADE_STAGE}/wwui/mousemgr.cpp
    ${RENEGADE_STAGE}/wwui/tooltip.cpp
    ${RENEGADE_STAGE}/wwui/tooltipmgr.cpp
    ${RENEGADE_STAGE}/wwui/dialogtransition.cpp
    ${RENEGADE_STAGE}/wwui/listctrl.cpp
    ${RENEGADE_STAGE}/wwui/listiconmgr.cpp
    ${RENEGADE_STAGE}/wwui/scrollbarctrl.cpp
    ${RENEGADE_STAGE}/wwui/popupdialog.cpp
    ${RENEGADE_STAGE}/wwui/screencursor.cpp
    ${RENEGADE_STAGE}/wwui/IMECandidateCtrl.cpp
    ${RENEGADE_STAGE}/commando/renegadedialogmgr.cpp
    ${RENEGADE_STAGE}/commando/dlgmainmenu.cpp
    ${RENEGADE_STAGE}/commando/DlgMessageBox.cpp
    ${RENEGADE_STAGE}/commando/dialogtests.cpp
    ${RENEGADE_STAGE}/commando/dlgloadspgame.cpp
    ${RENEGADE_STAGE}/commando/dlgsavegame.cpp
    ${RENEGADE_STAGE}/commando/dlghelpscreen.cpp
    ${RENEGADE_STAGE}/commando/dlgtechoptions.cpp
    ${RENEGADE_STAGE}/commando/dlgconfigaudiotab.cpp
    ${RENEGADE_STAGE}/commando/dlgconfigvideotab.cpp
    ${RENEGADE_STAGE}/commando/dlgconfigperformancetab.cpp
    ${RENEGADE_STAGE}/commando/dlgevaencyclopedia.cpp
    ${RENEGADE_STAGE}/commando/dlgevaobjectivestab.cpp
    ${RENEGADE_STAGE}/commando/dlgevamaptab.cpp
    ${RENEGADE_STAGE}/commando/dlgevadatatab.cpp
    ${RENEGADE_STAGE}/commando/dlgevacharacterstab.cpp
    ${RENEGADE_STAGE}/commando/dlgevaweaponstab.cpp
    ${RENEGADE_STAGE}/commando/dlgevavehiclestab.cpp
    ${RENEGADE_STAGE}/commando/dlgevabuildingstab.cpp
    ${RENEGADE_STAGE}/commando/dlgevaviewertab.cpp
    ${RENEGADE_STAGE}/commando/mainmenutransition.cpp
    ${RENEGADE_STAGE}/commando/gamemode.cpp
    ${RENEGADE_STAGE}/commando/gamemenu.cpp
    ${RENEGADE_STAGE}/commando/movie.cpp
    ${RENEGADE_STAGE}/commando/devoptions.cpp
    ${RENEGADE_STAGE}/commando/level.cpp
    ${RENEGADE_STAGE}/commando/bioevent.cpp
    ${RENEGADE_STAGE}/commando/svrgoodbyeevent.cpp
    ${RENEGADE_STAGE}/commando/modpackage.cpp
    ${RENEGADE_STAGE}/commando/modpackagemgr.cpp
    ${RENEGADE_STAGE}/combat/savegame.cpp
  )
  set(RENEGADE_A4_FRONTEND_PORT_SOURCES
    ${RENEGADE_ROOT}/port/filesystem/renegade_find_files.cpp
    ${RENEGADE_ROOT}/port/platform/renegade_vita_ime_boundary.cpp
    ${RENEGADE_ROOT}/port/platform/renegade_ui_pointer_tokens.cpp
    ${RENEGADE_ROOT}/port/platform/renegade_dialog_resource_provider.cpp
    ${RENEGADE_ROOT}/port/platform/a4_frontend_lifecycle_boundary.cpp
    ${RENEGADE_ROOT}/port/platform/a4_binkmovie_boundary.cpp
  )
else()
  set(RENEGADE_A4_FRONTEND_ORIGINAL_SOURCES)
  set(RENEGADE_A4_FRONTEND_PORT_SOURCES)
endif()

# The Vita candidate uses the same direct original replication/session closure
# proven by the A3.1 host harness.  Keep WWNet/Combat ownership in upstream
# translation units; the platform layer remains limited to input, presentation,
# filesystem and discovery-provider boundaries.
set(RENEGADE_A31_INTERACTIVE_ORIGINAL_SOURCES
  ${RENEGADE_A31_GAMEPLAY_SEED_ORIGINAL_SOURCES}
  ${RENEGADE_A35_ORIGINAL_AUDIO_SOURCES}
  ${RENEGADE_STAGE}/wwlib/pipe.cpp ${RENEGADE_STAGE}/wwlib/base64.cpp ${RENEGADE_STAGE}/wwlib/xpipe.cpp ${RENEGADE_STAGE}/wwlib/b64pipe.cpp ${RENEGADE_STAGE}/wwlib/b64straw.cpp
  ${RENEGADE_STAGE}/wwdebug/wwprofile.cpp ${RENEGADE_STAGE}/wwlib/TARGA.CPP ${RENEGADE_STAGE}/ww3d2/bitmaphandler.cpp ${RENEGADE_STAGE}/ww3d2/ww3dformat.cpp ${RENEGADE_STAGE}/ww3d2/font3d.cpp ${RENEGADE_STAGE}/ww3d2/ddsfile.cpp ${RENEGADE_STAGE}/ww3d2/formconv.cpp ${RENEGADE_STAGE}/wwaudio/AudioSaveLoad.cpp ${RENEGADE_STAGE}/wwnet/wwpacket.cpp
  ${RENEGADE_STAGE}/combat/combatsound.cpp ${RENEGADE_STAGE}/combat/SoundEnvironment.cpp ${RENEGADE_STAGE}/combat/sniper.cpp ${RENEGADE_STAGE}/combat/staticnetworkobject.cpp
	${RENEGADE_STAGE}/combat/combatdazzle.cpp
	${RENEGADE_STAGE}/wwui/stylemgr.cpp
	${RENEGADE_STAGE}/wwui/menubackdrop.cpp
	${RENEGADE_STAGE}/commando/loadingscreen.cpp
	${RENEGADE_STAGE}/commando/combatgmode.cpp
	${RENEGADE_STAGE}/commando/commandosaveload.cpp
	${RENEGADE_STAGE}/commando/textdisplay.cpp
  ${RENEGADE_STAGE}/commando/gamedata.cpp ${RENEGADE_STAGE}/commando/gdsingleplayer.cpp ${RENEGADE_STAGE}/commando/gdcnc.cpp ${RENEGADE_STAGE}/commando/campaign.cpp ${RENEGADE_STAGE}/commando/winevent.cpp ${RENEGADE_STAGE}/commando/renegadecheatmgr.cpp ${RENEGADE_STAGE}/commando/player.cpp ${RENEGADE_STAGE}/commando/playermanager.cpp ${RENEGADE_STAGE}/commando/god.cpp ${RENEGADE_STAGE}/commando/team.cpp ${RENEGADE_STAGE}/commando/teammanager.cpp ${RENEGADE_STAGE}/commando/gamedataupdateevent.cpp ${RENEGADE_STAGE}/commando/sctextobj.cpp ${RENEGADE_STAGE}/commando/netinterface.cpp ${RENEGADE_STAGE}/commando/netevent.cpp ${RENEGADE_STAGE}/commando/cnetwork.cpp ${RENEGADE_STAGE}/commando/comnetrcvinst.cpp ${RENEGADE_STAGE}/commando/nethandler.cpp ${RENEGADE_STAGE}/commando/buildnum.cpp ${RENEGADE_STAGE}/commando/gameinitmgr.cpp ${RENEGADE_STAGE}/commando/pkthandlers.cpp ${RENEGADE_STAGE}/commando/apppacketstats.cpp ${RENEGADE_STAGE}/commando/sbbomanager.cpp ${RENEGADE_STAGE}/commando/gameoptionsevent.cpp ${RENEGADE_STAGE}/commando/evictionevent.cpp ${RENEGADE_STAGE}/commando/clientpingmanager.cpp ${RENEGADE_STAGE}/commando/cspingrequestevent.cpp ${RENEGADE_STAGE}/commando/scpingresponseevent.cpp ${RENEGADE_STAGE}/commando/clienthintmanager.cpp ${RENEGADE_STAGE}/commando/cshint.cpp ${RENEGADE_STAGE}/commando/clientgoodbyeevent.cpp ${RENEGADE_STAGE}/commando/playerkill.cpp ${RENEGADE_STAGE}/commando/serverfps.cpp ${RENEGADE_STAGE}/commando/clientfps.cpp ${RENEGADE_STAGE}/commando/priority.cpp ${RENEGADE_STAGE}/commando/regint.cpp ${RENEGADE_STAGE}/commando/regbool.cpp ${RENEGADE_STAGE}/commando/regfloat.cpp
  ${RENEGADE_STAGE}/wwnet/connect.cpp ${RENEGADE_STAGE}/wwnet/rhost.cpp ${RENEGADE_STAGE}/wwnet/netutil.cpp ${RENEGADE_STAGE}/wwnet/netstats.cpp ${RENEGADE_STAGE}/wwnet/msgstat.cpp ${RENEGADE_STAGE}/wwnet/msgstatlist.cpp ${RENEGADE_STAGE}/wwnet/msgstatlistgroup.cpp ${RENEGADE_STAGE}/wwnet/BWBalance.cpp ${RENEGADE_STAGE}/wwnet/packetmgr.cpp ${RENEGADE_STAGE}/wwnet/singlepl.cpp ${RENEGADE_STAGE}/commando/messages.cpp ${RENEGADE_STAGE}/commando/changeteamevent.cpp ${RENEGADE_STAGE}/combat/inventory.cpp ${RENEGADE_STAGE}/combat/colors.cpp
	${RENEGADE_SCRIPT_SOURCE}/ScriptFactory.cpp
	${RENEGADE_SCRIPT_SOURCE}/ScriptRegistrar.cpp
	${RENEGADE_SCRIPT_SOURCE}/scripts.cpp
	${RENEGADE_SCRIPT_SOURCE}/Mission00.cpp
	${RENEGADE_SCRIPT_SOURCE}/Test_Cinematic.cpp
	${RENEGADE_SCRIPT_SOURCE}/Toolkit_Powerup.cpp
	${RENEGADE_A4_FRONTEND_ORIGINAL_SOURCES}
	)
set(RENEGADE_CAMPAIGN_SCRIPT_SOURCES
  ${RENEGADE_SCRIPT_SOURCE}/MissionX0.cpp
  ${RENEGADE_SCRIPT_SOURCE}/Test_DLS.cpp
  ${RENEGADE_SCRIPT_SOURCE}/Mission01.cpp)
list(APPEND RENEGADE_A31_INTERACTIVE_ORIGINAL_SOURCES
  ${RENEGADE_CAMPAIGN_SCRIPT_SOURCES}
  ${RENEGADE_STAGE}/combat/cinematicgameobj.cpp
  ${RENEGADE_STAGE}/wwlib/ramfile.cpp
  ${RENEGADE_STAGE}/commando/scorescreen.cpp)
list(LENGTH RENEGADE_A31_INTERACTIVE_ORIGINAL_SOURCES RENEGADE_A31_INTERACTIVE_ORIGINAL_SOURCE_COUNT)

foreach(required_library
    libvitaGL.a
    libvitashark.a
    libSceShaccCgExt.a
    libSceShaccCg_stub.a
    libSceAudio_stub.a)
  if(NOT EXISTS "${VITASDK}/arm-vita-eabi/lib/${required_library}")
    message(FATAL_ERROR "Required A3.1 Vita renderer library is missing: ${required_library}")
  endif()
endforeach()

set(RENEGADE_VITAGL_LIBRARY "${CMAKE_CURRENT_SOURCE_DIR}/build/deps/vitagl-demo/libvitaGL.a"
  CACHE FILEPATH "Pinned no-splash, shader-cache-enabled demo vitaGL archive")
if(NOT EXISTS "${RENEGADE_VITAGL_LIBRARY}")
  message(FATAL_ERROR "Build the pinned demo graphics dependency with tools/build_vitagl_demo.sh first")
endif()
set(RENEGADE_VITAGL_HEADER "${CMAKE_CURRENT_SOURCE_DIR}/build/deps/vitagl-demo/source/source/vitaGL.h")
file(READ "${RENEGADE_VITAGL_HEADER}" RENEGADE_VITAGL_HEADER_TEXT)
if(RENEGADE_VITAGL_HEADER_TEXT MATCHES "VGL_MEM_PHYCONT[ \t\r\n]*,")
  set(RENEGADE_VITAGL_PHYCONT_MEM "VGL_MEM_PHYCONT")
  set(RENEGADE_VITAGL_HAS_PHYCONT_MEM 1)
elseif(RENEGADE_VITAGL_HEADER_TEXT MATCHES "VGL_MEM_SLOW[ \t\r\n]*,")
  set(RENEGADE_VITAGL_PHYCONT_MEM "VGL_MEM_SLOW")
  set(RENEGADE_VITAGL_HAS_PHYCONT_MEM 1)
else()
  set(RENEGADE_VITAGL_PHYCONT_MEM "VGL_MEM_ALL")
  set(RENEGADE_VITAGL_HAS_PHYCONT_MEM 0)
endif()
message(STATUS "vitaGL physical-contiguous memory enum: ${RENEGADE_VITAGL_PHYCONT_MEM}")

foreach(required_path
    "${RENEGADE_UPSTREAM}/Code/wwbitpack/BitPacker.cpp"
    "${RENEGADE_STAGE}/wwbitpack/BitPacker.cpp"
    "${RENEGADE_STAGE}/wwphys/pscene.cpp"
    "${RENEGADE_STAGE}/combat/savegame.cpp"
    "${RENEGADE_STAGE}/commando/datasafe.cpp"
    "${RENEGADE_ROOT}/port/validation/a30_world_runtime.cpp"
	"${RENEGADE_ROOT}/port/developer/a31_capture_telemetry.cpp"
    "${RENEGADE_ROOT}/port/audio/vita/renegade_miles_provider.cpp"
    "${RENEGADE_ROOT}/port/audio/vita/renegade_wave_decoder.cpp"
    "${RENEGADE_ROOT}/port/platform/vita/a30_main.cpp"
	"${RENEGADE_ROOT}/port/platform/vita/a31_vita_runtime.cpp"
    "${VITASDK_DEBUG_SCREEN}/debugScreen.c")
  if(NOT EXISTS "${required_path}")
    message(FATAL_ERROR "Required A3.1 source is missing: ${required_path}")
  endif()
endforeach()

# These are legitimate Vita/platform and validation boundary TUs. Original
# SaveLoad/WWPhys/Combat objects stay above this boundary in the shared direct
# source list so their translation-unit factory registration is retained.
set(RENEGADE_A30_PORT_SOURCES
	${RENEGADE_ROOT}/port/developer/a31_capture_telemetry.cpp
	${RENEGADE_ROOT}/port/audio/vita/renegade_miles_provider.cpp
	${RENEGADE_ROOT}/port/audio/vita/renegade_wave_decoder.cpp
	${RENEGADE_ROOT}/port/filesystem/renegade_cache_health.cpp
  ${RENEGADE_ROOT}/port/filesystem/renegade_paths.cpp
  ${RENEGADE_ROOT}/port/filesystem/renegade_file_factory.cpp
  ${RENEGADE_ROOT}/port/filesystem/renegade_registry.cpp
  ${RENEGADE_ROOT}/port/platform/renegade_directinput.cpp
  ${RENEGADE_ROOT}/port/platform/renegade_optional_services.cpp
  ${RENEGADE_ROOT}/port/platform/renegade_network_provider.cpp
	${RENEGADE_ROOT}/port/renderer/vita/ww3d_vita_renderer.cpp
	${RENEGADE_ROOT}/port/renderer/vita/ww3d_dx8_boundary.cpp
	${RENEGADE_ROOT}/port/renderer/vita/surface_boundary.cpp
	${RENEGADE_ROOT}/port/renderer/vita/renegade_freetype_font_provider.cpp
  ${RENEGADE_ROOT}/port/validation/wwbitpack_selftest.cpp
  ${RENEGADE_ROOT}/port/validation/a21_filesystem_selftest.cpp
  ${RENEGADE_ROOT}/port/validation/a22_w3d_selftest.cpp
  ${RENEGADE_ROOT}/port/validation/a30_world_runtime.cpp
  ${RENEGADE_ROOT}/port/platform/vita/vita_platform.cpp
  ${RENEGADE_ROOT}/port/platform/vita/renegade_vita_text_entry.cpp
  ${RENEGADE_ROOT}/port/platform/vita/a30_vita_runtime.cpp
	${RENEGADE_ROOT}/port/platform/vita/a31_vita_runtime.cpp
  ${RENEGADE_ROOT}/port/platform/a31_gameplay_boundary.cpp
  ${RENEGADE_ROOT}/port/platform/a31_miscutil_boundary.cpp
	${RENEGADE_ROOT}/port/platform/a31_network_options_boundary.cpp
	${RENEGADE_ROOT}/port/platform/renegade_script_static_provider.cpp
	${RENEGADE_ROOT}/port/platform/vita/a30_main.cpp
)
list(LENGTH RENEGADE_A30_PORT_SOURCES RENEGADE_A30_PORT_SOURCE_COUNT)
if(NOT RENEGADE_A30_PORT_SOURCES)
  message(FATAL_ERROR "Native source manifest must not be empty")
endif()
foreach(native_source IN LISTS RENEGADE_A30_PORT_SOURCES RENEGADE_A4_FRONTEND_PORT_SOURCES)
  if(NOT EXISTS "${native_source}")
    message(FATAL_ERROR "Native source manifest references missing file: ${native_source}")
  endif()
endforeach()

add_executable(${PROJECT_NAME}
  ${RENEGADE_A31_INTERACTIVE_ORIGINAL_SOURCES}
  ${RENEGADE_A30_PORT_SOURCES}
  ${RENEGADE_A4_FRONTEND_PORT_SOURCES}
  ${VITASDK_DEBUG_SCREEN}/debugScreen.c
)
if(RENEGADE_A4_ORIGINAL_FRONTEND)
  add_dependencies(${PROJECT_NAME} a4_dialog_templates)
endif()

target_include_directories(${PROJECT_NAME} PRIVATE
  ${RENEGADE_GENERATED_INCLUDE}
  ${RENEGADE_ROOT}/port/compatibility/include
	${RENEGADE_ROOT}/port/developer
  ${RENEGADE_ROOT}/port/audio/miles
  ${RENEGADE_ROOT}/port/audio/vita
  ${RENEGADE_ROOT}/port/filesystem
  ${RENEGADE_ROOT}/port/platform
  ${RENEGADE_ROOT}/port/platform/vita
  ${RENEGADE_ROOT}/port/renderer/vita
	${VITASDK}/arm-vita-eabi/include/freetype2
  ${RENEGADE_ROOT}/port/validation
  ${RENEGADE_STAGE}/wwbitpack
  ${RENEGADE_STAGE}/wwlib
  ${RENEGADE_STAGE}/wwmath
  ${RENEGADE_STAGE}/wwsaveload
  ${RENEGADE_STAGE}/combat
  ${RENEGADE_STAGE}/commando
  ${RENEGADE_STAGE}/wwui
  ${RENEGADE_STAGE}/wwaudio
  ${RENEGADE_STAGE}/wwnet
  ${RENEGADE_STAGE}/wwtranslatedb
  ${RENEGADE_STAGE}/ww3d2
  ${RENEGADE_STAGE}/wwphys
  ${RENEGADE_UPSTREAM}/Code/wwdebug
  ${RENEGADE_UPSTREAM}/Code/wwlib
  ${RENEGADE_UPSTREAM}/Code/wwutil
  ${RENEGADE_UPSTREAM}/Code/WWMath
  ${RENEGADE_UPSTREAM}/Code/wwsaveload
  ${RENEGADE_UPSTREAM}/Code/ww3d2
  ${RENEGADE_UPSTREAM}/Code/WWPhys
  ${RENEGADE_UPSTREAM}/Code/Combat
  ${RENEGADE_UPSTREAM}/Code/Commando
  ${RENEGADE_UPSTREAM}/Code/WWAudio
  ${RENEGADE_UPSTREAM}/Code/wwnet
  ${RENEGADE_UPSTREAM}/Code/wwui
  ${RENEGADE_UPSTREAM}/Code/wwtranslatedb
  ${RENEGADE_UPSTREAM}/Code/Scripts
	${RENEGADE_SCRIPT_ALIAS_INCLUDE}
  ${VITASDK_DEBUG_SCREEN}
)
if(RENEGADE_A4_ORIGINAL_FRONTEND)
  target_include_directories(${PROJECT_NAME} PRIVATE
    ${RENEGADE_BINK_FFMPEG_ROOT}/include)
endif()
target_compile_definitions(${PROJECT_NAME} PRIVATE
  NDEBUG=1
  _UNIX=1
  UMBRASUPPORT=0
  RENEGADE_RUNTIME_READ_ONLY=1
  RENEGADE_VITA_PORT=1
  RENEGADE_VITA_A30=1
  RENEGADE_VITA_A31=1
  RENEGADE_A35_ORIGINAL_WWAUDIO=1
  RENEGADE_A35_ORIGINAL_COMBATGMODE=1
  RENEGADE_A4_REAL_STYLEMGR=1
  # Original UI and WideStringClass data is UTF-16, as it was under the
  # Win32 compiler.  Keep literals and wchar_t-based ABI calls at that width.
  RENEGADE_SHORT_WCHAR_ABI=1
  RENEGADE_A30_FULL_WWPHYS=1
  RENEGADE_VITA_A22_ORIGINAL_SOURCES=105
  RENEGADE_VITA_A22_PORT_SOURCES=9
  RENEGADE_VITA_A31_ORIGINAL_SOURCES=${RENEGADE_A31_INTERACTIVE_ORIGINAL_SOURCE_COUNT}
  RENEGADE_VITA_A30_PORT_SOURCES=${RENEGADE_A30_PORT_SOURCE_COUNT}
  RENEGADE_VITAGL_HAS_PHYCONT_MEM=${RENEGADE_VITAGL_HAS_PHYCONT_MEM}
  RENEGADE_VITAGL_PHYCONT_MEM=${RENEGADE_VITAGL_PHYCONT_MEM}
	)
if(RENEGADE_A4_ORIGINAL_FRONTEND)
  target_compile_definitions(${PROJECT_NAME} PRIVATE
    RENEGADE_A4_ORIGINAL_FRONTEND=1
    RENEGADE_A4_ORIGINAL_GAMEMODE=1
    RENEGADE_A4_ORIGINAL_MOVIE_OWNER=1
    RENEGADE_A4_BINK_FFMPEG=1
    RENEGADE_VITA_FRONTEND_SINGLEPLAYER=1
    RENEGADE_VITA_A4_FRONTEND_PORT_SOURCES=6
  )
endif()
target_compile_options(${PROJECT_NAME} PRIVATE
  -fshort-wchar
  -fno-strict-aliasing
  -fno-exceptions
  -fno-rtti
  -ffunction-sections
  -fdata-sections
  -Wno-unknown-pragmas
  -Wformat
  $<$<COMPILE_LANGUAGE:CXX>:-include${RENEGADE_COMPAT}/msvc_compat.h>
)
# ScriptCommands is an ABI-fixed MSVC callback table. Its default values on
# function-pointer members are accepted by the original compiler but rejected
# by modern GCC; scope the legacy tolerance to the two original Combat script
# manager translation units that include that table.
set_source_files_properties(
  ${RENEGADE_STAGE}/combat/scripts.cpp
  ${RENEGADE_STAGE}/combat/scriptcommands.cpp
  ${RENEGADE_ROOT}/port/platform/renegade_script_static_provider.cpp
  PROPERTIES
  COMPILE_OPTIONS "-fpermissive"
)
set_source_files_properties(
  ${RENEGADE_SCRIPT_SOURCE}/ScriptFactory.cpp
  ${RENEGADE_SCRIPT_SOURCE}/ScriptRegistrar.cpp
  ${RENEGADE_SCRIPT_SOURCE}/scripts.cpp
  ${RENEGADE_SCRIPT_SOURCE}/Mission00.cpp
  ${RENEGADE_SCRIPT_SOURCE}/Test_Cinematic.cpp
  ${RENEGADE_SCRIPT_SOURCE}/Toolkit_Powerup.cpp
  ${RENEGADE_CAMPAIGN_SCRIPT_SOURCES}
  PROPERTIES COMPILE_OPTIONS "-fpermissive"
)
set_property(SOURCE
  ${RENEGADE_SCRIPT_SOURCE}/Mission00.cpp
  ${RENEGADE_SCRIPT_SOURCE}/Test_Cinematic.cpp
  ${RENEGADE_SCRIPT_SOURCE}/Toolkit_Powerup.cpp
  ${RENEGADE_SCRIPT_SOURCE}/MissionX0.cpp
  ${RENEGADE_SCRIPT_SOURCE}/Test_DLS.cpp
  APPEND PROPERTY
  COMPILE_OPTIONS
  "-include${RENEGADE_COMPAT}/renegade_script_call_defaults.h")
set_property(SOURCE
  ${RENEGADE_SCRIPT_SOURCE}/Mission01.cpp
  APPEND PROPERTY COMPILE_OPTIONS
  "-include${RENEGADE_COMPAT}/renegade_m01_script_defaults.h")
target_link_options(${PROJECT_NAME} PRIVATE
  -fshort-wchar
  -Wl,--gc-sections
  -Wl,--wrap=shark_init
	"-Wl,-Map=${CMAKE_CURRENT_BINARY_DIR}/RenegadeVita-${RENEGADE_CANDIDATE_LABEL}.map"
)
target_include_directories(${PROJECT_NAME} BEFORE PRIVATE
  "${CMAKE_CURRENT_SOURCE_DIR}/build/deps/vitagl-demo/source/source")
target_compile_definitions(${PROJECT_NAME} PRIVATE
  RENEGADE_VITA_M00_DEMO=$<BOOL:${RENEGADE_VITA_M00_DEMO}>)
target_link_libraries(${PROJECT_NAME}
  mpg123
  $<$<BOOL:${RENEGADE_A4_ORIGINAL_FRONTEND}>:${RENEGADE_BINK_FFMPEG_ROOT}/lib/libavformat.a>
  $<$<BOOL:${RENEGADE_A4_ORIGINAL_FRONTEND}>:${RENEGADE_BINK_FFMPEG_ROOT}/lib/libavcodec.a>
  $<$<BOOL:${RENEGADE_A4_ORIGINAL_FRONTEND}>:${RENEGADE_BINK_FFMPEG_ROOT}/lib/libswscale.a>
  $<$<BOOL:${RENEGADE_A4_ORIGINAL_FRONTEND}>:${RENEGADE_BINK_FFMPEG_ROOT}/lib/libswresample.a>
  $<$<BOOL:${RENEGADE_A4_ORIGINAL_FRONTEND}>:${RENEGADE_BINK_FFMPEG_ROOT}/lib/libavutil.a>
  "${RENEGADE_VITAGL_LIBRARY}"
  stdc++
  SceLibKernel_stub
  SceAppMgr_stub
  SceAppUtil_stub
  mathneon
  c
  SceCommonDialog_stub
  SceIme_stub
  m
  SceGxm_stub
  SceDisplay_stub
  ScePower_stub
  SceSysmem_stub
  SceSysmodule_stub
  zip
  z
  vitashark
  SceShaccCgExt
  taihen_stub
	  SceShaccCg_stub
	  SceKernelDmacMgr_stub
	  SceCtrl_stub
	  SceTouch_stub
	  SceAudio_stub
  SceNet_stub
  SceIofilemgr_stub
  # VitaSDK FreeType is static.  Keep its optional decoders after it so the
  # linker can satisfy the archive members selected by true-type loading.
  freetype
  png
  bz2
  z
  pthread
)

vita_create_self(eboot.bin ${PROJECT_NAME})
# vita_create_vpk otherwise emits an empty CONTENT_ID field. Set the narrow
# VitaSDK packaging flag immediately before the macro so only param.sfo changes.
set(VITA_MKSFOEX_FLAGS "-s CONTENT_ID=${RENEGADE_VITA_CONTENT_ID}")
vita_create_vpk(RenegadeVita-${RENEGADE_CANDIDATE_LABEL}.vpk ${RENEGADE_VITA_TITLE_ID} eboot.bin
	VERSION 03.55
	NAME "Renegade Vita ${RENEGADE_CANDIDATE_LABEL}"
)

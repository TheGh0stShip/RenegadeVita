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

project(RenegadeVitaA31 VERSION 3.5.1 LANGUAGES C CXX)

# This is provenance for a hardware candidate, not a public milestone claim.
# Keep the artifact identity configurable so a newer candidate can never
# overwrite the symbols and diagnostics that belong to an earlier one.
set(RENEGADE_CANDIDATE_LABEL "A3.5-dev52" CACHE STRING
  "Validated hardware-candidate label (for example A3.5-dev2)")
if(NOT RENEGADE_CANDIDATE_LABEL MATCHES "^A[0-9]+\\.[0-9]+-dev[0-9]+$")
  message(FATAL_ERROR "RENEGADE_CANDIDATE_LABEL must look like A3.5-dev2")
endif()
string(TOLOWER "${RENEGADE_CANDIDATE_LABEL}" RENEGADE_CANDIDATE_STEM)
string(REPLACE "." "" RENEGADE_CANDIDATE_STEM "${RENEGADE_CANDIDATE_STEM}")
set(RENEGADE_RUNTIME_LOG_PATH
  "ux0:data/renegade/user/logs/${RENEGADE_CANDIDATE_STEM}-runtime.log")

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
  ${RENEGADE_STAGE}/commando/gamedata.cpp ${RENEGADE_STAGE}/commando/gdsingleplayer.cpp ${RENEGADE_STAGE}/commando/gdcnc.cpp ${RENEGADE_STAGE}/commando/campaign.cpp ${RENEGADE_STAGE}/commando/winevent.cpp ${RENEGADE_STAGE}/commando/renegadecheatmgr.cpp ${RENEGADE_STAGE}/commando/player.cpp ${RENEGADE_STAGE}/commando/playermanager.cpp ${RENEGADE_STAGE}/commando/god.cpp ${RENEGADE_STAGE}/commando/team.cpp ${RENEGADE_STAGE}/commando/teammanager.cpp ${RENEGADE_STAGE}/commando/gamedataupdateevent.cpp ${RENEGADE_STAGE}/commando/sctextobj.cpp ${RENEGADE_STAGE}/commando/netinterface.cpp ${RENEGADE_STAGE}/commando/netevent.cpp ${RENEGADE_STAGE}/commando/cnetwork.cpp ${RENEGADE_STAGE}/commando/comnetrcvinst.cpp ${RENEGADE_STAGE}/commando/nethandler.cpp ${RENEGADE_STAGE}/commando/buildnum.cpp ${RENEGADE_STAGE}/commando/gameinitmgr.cpp ${RENEGADE_STAGE}/commando/pkthandlers.cpp ${RENEGADE_STAGE}/commando/apppacketstats.cpp ${RENEGADE_STAGE}/commando/sbbomanager.cpp ${RENEGADE_STAGE}/commando/gameoptionsevent.cpp ${RENEGADE_STAGE}/commando/evictionevent.cpp ${RENEGADE_STAGE}/commando/clientpingmanager.cpp ${RENEGADE_STAGE}/commando/cspingrequestevent.cpp ${RENEGADE_STAGE}/commando/scpingresponseevent.cpp ${RENEGADE_STAGE}/commando/clienthintmanager.cpp ${RENEGADE_STAGE}/commando/cshint.cpp ${RENEGADE_STAGE}/commando/clientgoodbyeevent.cpp ${RENEGADE_STAGE}/commando/playerkill.cpp ${RENEGADE_STAGE}/commando/serverfps.cpp ${RENEGADE_STAGE}/commando/clientfps.cpp ${RENEGADE_STAGE}/commando/priority.cpp ${RENEGADE_STAGE}/commando/regint.cpp ${RENEGADE_STAGE}/commando/regbool.cpp ${RENEGADE_STAGE}/commando/regfloat.cpp
  ${RENEGADE_STAGE}/wwnet/connect.cpp ${RENEGADE_STAGE}/wwnet/rhost.cpp ${RENEGADE_STAGE}/wwnet/netutil.cpp ${RENEGADE_STAGE}/wwnet/netstats.cpp ${RENEGADE_STAGE}/wwnet/msgstat.cpp ${RENEGADE_STAGE}/wwnet/msgstatlist.cpp ${RENEGADE_STAGE}/wwnet/msgstatlistgroup.cpp ${RENEGADE_STAGE}/wwnet/BWBalance.cpp ${RENEGADE_STAGE}/wwnet/packetmgr.cpp ${RENEGADE_STAGE}/wwnet/singlepl.cpp ${RENEGADE_STAGE}/commando/messages.cpp ${RENEGADE_STAGE}/commando/changeteamevent.cpp ${RENEGADE_STAGE}/combat/inventory.cpp ${RENEGADE_STAGE}/combat/colors.cpp
	${RENEGADE_SCRIPT_SOURCE}/ScriptFactory.cpp
	${RENEGADE_SCRIPT_SOURCE}/ScriptRegistrar.cpp
	${RENEGADE_SCRIPT_SOURCE}/scripts.cpp
	${RENEGADE_SCRIPT_SOURCE}/Mission00.cpp
	${RENEGADE_SCRIPT_SOURCE}/Test_Cinematic.cpp
	${RENEGADE_SCRIPT_SOURCE}/Toolkit_Powerup.cpp
)
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

set(RENEGADE_VITAGL_HEADER "${VITASDK}/arm-vita-eabi/include/vitaGL.h")
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
  ${RENEGADE_ROOT}/port/platform/vita/a30_vita_runtime.cpp
	${RENEGADE_ROOT}/port/platform/vita/a31_vita_runtime.cpp
  ${RENEGADE_ROOT}/port/platform/a31_gameplay_boundary.cpp
  ${RENEGADE_ROOT}/port/platform/a31_miscutil_boundary.cpp
	${RENEGADE_ROOT}/port/platform/a31_network_options_boundary.cpp
	${RENEGADE_ROOT}/port/platform/renegade_script_static_provider.cpp
	${RENEGADE_ROOT}/port/platform/vita/a30_main.cpp
)
list(LENGTH RENEGADE_A30_PORT_SOURCES RENEGADE_A30_PORT_SOURCE_COUNT)
if(NOT RENEGADE_A30_PORT_SOURCE_COUNT EQUAL 26)
  message(FATAL_ERROR
    "A3.1 Vita boundary source closure changed: ${RENEGADE_A30_PORT_SOURCE_COUNT}")
endif()

add_executable(${PROJECT_NAME}
  ${RENEGADE_A31_INTERACTIVE_ORIGINAL_SOURCES}
  ${RENEGADE_A30_PORT_SOURCES}
  ${VITASDK_DEBUG_SCREEN}/debugScreen.c
)

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
target_compile_definitions(${PROJECT_NAME} PRIVATE
  NDEBUG=1
  _UNIX=1
  UMBRASUPPORT=0
  RENEGADE_RUNTIME_READ_ONLY=1
  RENEGADE_VITA_PORT=1
  RENEGADE_VITA_A30=1
  RENEGADE_VITA_A31=1
  RENEGADE_A35_ORIGINAL_WWAUDIO=1
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
target_compile_options(${PROJECT_NAME} PRIVATE
  -fshort-wchar
  -fno-strict-aliasing
  -fno-exceptions
  -fno-rtti
  -ffunction-sections
  -fdata-sections
  -Wno-unknown-pragmas
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
  PROPERTIES COMPILE_OPTIONS "-fpermissive"
)
set_property(SOURCE
  ${RENEGADE_SCRIPT_SOURCE}/Mission00.cpp
  ${RENEGADE_SCRIPT_SOURCE}/Test_Cinematic.cpp
  ${RENEGADE_SCRIPT_SOURCE}/Toolkit_Powerup.cpp
  APPEND PROPERTY
  COMPILE_OPTIONS
  "-include${RENEGADE_COMPAT}/renegade_script_call_defaults.h")
target_link_options(${PROJECT_NAME} PRIVATE
  -fshort-wchar
  -Wl,--gc-sections
  -Wl,--wrap=shark_init
	"-Wl,-Map=${CMAKE_CURRENT_BINARY_DIR}/RenegadeVita-${RENEGADE_CANDIDATE_LABEL}.map"
)
target_link_libraries(${PROJECT_NAME}
  vitaGL
  stdc++
  SceLibKernel_stub
  SceAppMgr_stub
  SceAppUtil_stub
  mathneon
  c
  SceCommonDialog_stub
  m
  SceGxm_stub
  SceDisplay_stub
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
vita_create_vpk(RenegadeVita-${RENEGADE_CANDIDATE_LABEL}.vpk RNEGA3101 eboot.bin
	VERSION 03.51
	NAME "Renegade Vita ${RENEGADE_CANDIDATE_LABEL}"
)

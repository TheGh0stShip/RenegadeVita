cmake_minimum_required(VERSION 3.16)
project(RenegadeA30DefinitionRuntimeHost LANGUAGES C CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_EXTENSIONS ON)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
option(RENEGADE_HOST_ORIGINAL_AUDIO "Run original WWAudio over the manual host mixer" OFF)
find_package(Freetype QUIET)
if(NOT Freetype_FOUND)
  find_program(RV_HOST_BREW brew)
  if(RV_HOST_BREW)
    execute_process(COMMAND "${RV_HOST_BREW}" --prefix freetype
      OUTPUT_VARIABLE RV_HOST_FREETYPE_PREFIX OUTPUT_STRIP_TRAILING_WHITESPACE
      RESULT_VARIABLE RV_HOST_FREETYPE_PREFIX_RESULT)
    if(RV_HOST_FREETYPE_PREFIX_RESULT EQUAL 0)
      set(RV_SAVED_PREFIX_PATH "${CMAKE_PREFIX_PATH}")
      list(APPEND CMAKE_PREFIX_PATH "${RV_HOST_FREETYPE_PREFIX}")
      find_package(Freetype REQUIRED)
      set(CMAKE_PREFIX_PATH "${RV_SAVED_PREFIX_PATH}")
    endif()
  endif()
endif()
if(NOT Freetype_FOUND)
  message(FATAL_ERROR "Host FreeType development headers and library are required")
endif()

get_filename_component(RV_ROOT "${CMAKE_CURRENT_LIST_DIR}/../.." ABSOLUTE)
include("${RV_ROOT}/cmake/RenegadeCcache.cmake")
set(RV_STAGE "${RV_ROOT}/staging")
# The original random generator requires 32-bit two's-complement wrap.
# Scoped to this owner; the retained vectors cover signed index rollover.
set_property(SOURCE ${RV_STAGE}/wwlib/random.cpp APPEND PROPERTY COMPILE_OPTIONS -fwrapv)
set(RV_UPSTREAM "${RV_ROOT}/upstream/CnC_Renegade")
set(RV_COMPAT "${RV_ROOT}/port/compatibility/include")
set(RV_SCRIPT_SOURCE "${RV_STAGE}/scripts")
include("${RV_ROOT}/cmake/RenegadeScriptSources.cmake")
renegade_collect_script_dsp_sources(
  "${RV_UPSTREAM}/Code/Scripts"
  "${RV_SCRIPT_SOURCE}"
  RENEGADE_SCRIPT_DSP_SOURCES)
renegade_configure_script_static_helpers("${RV_SCRIPT_SOURCE}")

# The original AssetManager and WW3D shutdown paths retain Font3D/Render2D
# references even in the retained A3.0/A3.1 world probes.  Keep one explicit
# host-only closure shared by those probes so a newly staged original owner
# cannot make their regression link depend on stale objects.
set(RV_WORLD_FONT_RENDERER_CLOSURE_SOURCES
  ${RV_STAGE}/wwlib/TARGA.CPP
  ${RV_STAGE}/ww3d2/bitmaphandler.cpp
  ${RV_STAGE}/ww3d2/ww3dformat.cpp
  ${RV_STAGE}/ww3d2/font3d.cpp
  ${RV_STAGE}/ww3d2/render2d.cpp
  ${RV_STAGE}/ww3d2/render2dsentence.cpp
  ${RV_ROOT}/port/renderer/vita/surface_boundary.cpp
  ${RV_ROOT}/port/renderer/vita/renegade_freetype_font_provider.cpp
)
set(RV_WORLD_HOST_FREETYPE "${FREETYPE_LIBRARIES}")
if(NOT EXISTS "${RV_WORLD_HOST_FREETYPE}")
  message(FATAL_ERROR "Host FreeType runtime library is required for world-runtime regression targets")
endif()

find_package(Python3 REQUIRED COMPONENTS Interpreter)
set(RV_A4_DIALOG_GENERATED_DIR "${CMAKE_CURRENT_BINARY_DIR}/generated")
set(RV_A4_DIALOG_GENERATED "${RV_A4_DIALOG_GENERATED_DIR}/renegade_dialog_templates.inc")
add_custom_command(
  OUTPUT "${RV_A4_DIALOG_GENERATED}"
  COMMAND "${CMAKE_COMMAND}" -E make_directory "${RV_A4_DIALOG_GENERATED_DIR}"
  COMMAND "${Python3_EXECUTABLE}" "${RV_ROOT}/tools/generate_wwui_dialog_templates.py"
    --rc "${RV_UPSTREAM}/Code/Commando/chat.rc"
    --resource-h "${RV_UPSTREAM}/Code/Commando/resource.h"
    --dialog-resource-h "${RV_UPSTREAM}/Code/Commando/dialogresource.h"
    --out "${RV_A4_DIALOG_GENERATED}"
    --multiplayer-dialogs
  DEPENDS "${RV_ROOT}/tools/generate_wwui_dialog_templates.py"
    "${RV_UPSTREAM}/Code/Commando/chat.rc" "${RV_UPSTREAM}/Code/Commando/resource.h"
    "${RV_UPSTREAM}/Code/Commando/dialogresource.h"
  VERBATIM)
add_custom_target(a4_dialog_templates DEPENDS "${RV_A4_DIALOG_GENERATED}")

add_executable(a35_campaign_flight_recorder_selftest
  ${RV_ROOT}/tools/host_a35_campaign_flight_recorder_test.cpp
  ${RV_ROOT}/port/developer/a35_campaign_flight_recorder.cpp
  ${RV_ROOT}/port/developer/a35_script_lookup_telemetry.cpp
)
target_include_directories(a35_campaign_flight_recorder_selftest PRIVATE
  ${RV_ROOT}/port/developer
)
target_link_libraries(a35_campaign_flight_recorder_selftest PRIVATE pthread)

add_executable(a35_script_lookup_selftest
  ${RV_ROOT}/tools/host_a35_script_lookup_test.cpp
  ${RV_ROOT}/port/developer/a35_script_lookup_telemetry.cpp
)
target_include_directories(a35_script_lookup_selftest PRIVATE ${RV_ROOT}/port/developer)
target_link_libraries(a35_script_lookup_selftest PRIVATE pthread)

add_executable(a35_level_load_status_selftest
  ${RV_ROOT}/tools/host_a35_level_load_status_test.cpp
  ${RV_ROOT}/port/platform/vita/a35_level_load_status.cpp)
target_include_directories(a35_level_load_status_selftest PRIVATE ${RV_ROOT}/port/platform/vita)
target_compile_options(a35_level_load_status_selftest PRIVATE -UNDEBUG)

add_executable(a35_winsock_descriptor_selftest
  ${RV_ROOT}/tools/host_a35_winsock_descriptor_test.cpp)
target_include_directories(a35_winsock_descriptor_selftest PRIVATE ${RV_COMPAT})
target_compile_options(a35_winsock_descriptor_selftest PRIVATE -UNDEBUG)

# Include standalone original-owner regressions in the same sanitizer graph.
set_property(SOURCE
  ${RV_ROOT}/tools/host_original_script_vector_parser_test.cpp
  ${RV_ROOT}/tools/host_cinematic_save_test.cpp
  APPEND PROPERTY COMPILE_OPTIONS -fpermissive
    "-include${RV_COMPAT}/renegade_script_call_defaults.h")
foreach(rv_script_probe IN ITEMS vector_parser cinematic_save)
  if(rv_script_probe STREQUAL "vector_parser")
    set(rv_script_probe_source ${RV_ROOT}/tools/host_original_script_vector_parser_test.cpp)
  else()
    set(rv_script_probe_source ${RV_ROOT}/tools/host_cinematic_save_test.cpp)
  endif()
  add_executable(a35_${rv_script_probe}_selftest
    ${rv_script_probe_source}
    ${RV_STAGE}/scripts/scripts.cpp
    ${RV_STAGE}/scripts/ScriptFactory.cpp
    ${RV_STAGE}/scripts/ScriptRegistrar.cpp
    ${RV_STAGE}/scripts/strtrim.cpp)
  if(rv_script_probe STREQUAL "vector_parser")
    target_sources(a35_vector_parser_selftest PRIVATE ${RV_STAGE}/wwlib/trim.cpp)
  endif()
  target_include_directories(a35_${rv_script_probe}_selftest PRIVATE
    ${RV_COMPAT} ${RV_STAGE}/scripts ${RV_STAGE}/wwmath ${RV_STAGE}/wwlib)
  target_compile_definitions(a35_${rv_script_probe}_selftest PRIVATE
    _UNIX=1 RENEGADE_VITA_PORT=1 RENEGADE_HOST_ABI_TEST=1)
  target_compile_options(a35_${rv_script_probe}_selftest PRIVATE -UNDEBUG
    "SHELL:-include ${RV_COMPAT}/msvc_compat.h")
endforeach()

add_executable(a35_raw_animation_selftest
  ${RV_ROOT}/tools/host_raw_animation_test.cpp
  ${RV_STAGE}/ww3d2/motchan.cpp
  ${RV_STAGE}/wwmath/wwmath.cpp
  ${RV_STAGE}/wwmath/quat.cpp
  ${RV_STAGE}/wwmath/matrix3d.cpp)
target_include_directories(a35_raw_animation_selftest PRIVATE
  ${RV_COMPAT} ${RV_STAGE}/ww3d2 ${RV_STAGE}/wwmath ${RV_STAGE}/wwlib
  ${RV_STAGE}/wwsaveload ${RV_UPSTREAM}/Code/wwdebug)
target_compile_definitions(a35_raw_animation_selftest PRIVATE
  _UNIX=1 NDEBUG=1 RENEGADE_VITA_PORT=1 RENEGADE_HOST_ABI_TEST=1)
target_compile_options(a35_raw_animation_selftest PRIVATE
  -fno-rtti -ffunction-sections -fdata-sections "SHELL:-include ${RV_COMPAT}/msvc_compat.h")
target_link_options(a35_raw_animation_selftest PRIVATE -Wl,--gc-sections)

set(rv_track_probe ${CMAKE_CURRENT_BINARY_DIR}/generated/trackedvehicle_probe.cpp)
add_custom_command(OUTPUT ${rv_track_probe}
  COMMAND ${Python3_EXECUTABLE} ${RV_ROOT}/tools/generate_trackedvehicle_probe.py
    --source ${RV_STAGE}/wwphys/trackedvehicle.cpp
    --fixture ${RV_ROOT}/tools/host_trackedvehicle_repeat_render_test.cpp
    --output ${rv_track_probe}
  DEPENDS ${RV_STAGE}/wwphys/trackedvehicle.cpp
    ${RV_ROOT}/tools/host_trackedvehicle_repeat_render_test.cpp
    ${RV_ROOT}/tools/generate_trackedvehicle_probe.py
  VERBATIM)
add_executable(a35_trackedvehicle_repeat_selftest ${rv_track_probe})
target_compile_options(a35_trackedvehicle_repeat_selftest PRIVATE -UNDEBUG)

add_executable(a35_random_wrap_selftest
  ${RV_ROOT}/tools/host_a35_random_wrap_test.cpp ${RV_STAGE}/wwlib/random.cpp)
target_include_directories(a35_random_wrap_selftest PRIVATE
  ${RV_COMPAT} ${RV_STAGE}/wwlib ${RV_STAGE}/wwmath ${RV_UPSTREAM}/Code/wwdebug)
target_compile_definitions(a35_random_wrap_selftest PRIVATE
  NDEBUG=1 _UNIX=1 RENEGADE_VITA_PORT=1 RENEGADE_HOST_ABI_TEST=1)
target_compile_options(a35_random_wrap_selftest PRIVATE
  "SHELL:-include ${RV_COMPAT}/msvc_compat.h")

# Original ThreadClass completion/publication probe.
add_executable(a35_thread_publication_selftest
  ${RV_ROOT}/tools/host_a35_thread_publication_test.cpp
  ${RV_STAGE}/wwlib/thread.cpp
)
target_include_directories(a35_thread_publication_selftest PRIVATE
  ${RV_COMPAT} ${RV_STAGE}/wwlib ${RV_STAGE}/wwdebug ${RV_STAGE}/wwmath)
target_compile_definitions(a35_thread_publication_selftest PRIVATE _UNIX=1 NDEBUG=1)
target_compile_options(a35_thread_publication_selftest PRIVATE
  -O1 -g -fno-exceptions -fno-rtti "SHELL:-include ${RV_COMPAT}/msvc_compat.h")
target_link_options(a35_thread_publication_selftest PRIVATE -Wl,--wrap=pthread_create)
target_link_libraries(a35_thread_publication_selftest PRIVATE pthread)

add_executable(a35_wwmath_validity_selftest
  ${RV_ROOT}/tools/host_a35_wwmath_validity_test.cpp
)
target_include_directories(a35_wwmath_validity_selftest PRIVATE
  ${RV_STAGE}/wwmath
  ${RV_STAGE}/wwlib
  ${RV_COMPAT}
)
target_compile_options(a35_wwmath_validity_selftest PRIVATE
  "SHELL:-include ${RV_COMPAT}/msvc_compat.h"
)
if(CMAKE_CXX_COMPILER_ID MATCHES "GNU|Clang")
  target_compile_options(a35_wwmath_validity_selftest PRIVATE
    -fsanitize=undefined -fno-sanitize-recover=all)
  target_link_options(a35_wwmath_validity_selftest PRIVATE -fsanitize=undefined)
endif()

# This executable is deliberately narrower than the WWPhys compile frontier.
# It exercises the genuine retail DDB entry point and the original WWSaveLoad
# registry first.  Concrete WWPhys/Combat definition factories are added as
# their link closure becomes available; unregistered DDB records are skipped by
# DefinitionMgrClass exactly as in the original engine.
set(RV_WWLIB_SOURCES
  ${RV_STAGE}/wwlib/buff.cpp
  ${RV_STAGE}/wwlib/bufffile.cpp
  ${RV_STAGE}/wwlib/chunkio.cpp
  ${RV_STAGE}/wwlib/crc.cpp
  ${RV_STAGE}/wwlib/cstraw.cpp
  ${RV_STAGE}/wwlib/ffactory.cpp
  ${RV_STAGE}/wwlib/hash.cpp
  ${RV_STAGE}/wwlib/ini.cpp
  ${RV_STAGE}/wwlib/mixfile.cpp
  ${RV_STAGE}/wwlib/multilist.cpp
  ${RV_STAGE}/wwlib/nstrdup.cpp
  ${RV_STAGE}/wwlib/random.cpp
  ${RV_STAGE}/wwlib/rawfile.cpp
  ${RV_STAGE}/wwlib/readline.cpp
  ${RV_STAGE}/wwlib/realcrc.cpp
  ${RV_STAGE}/wwlib/slnode.cpp
  ${RV_STAGE}/wwlib/straw.cpp
  ${RV_STAGE}/wwlib/systimer.cpp
  ${RV_STAGE}/wwlib/trim.cpp
  ${RV_STAGE}/wwlib/wwfile.cpp
  ${RV_STAGE}/wwlib/wwstring.cpp
  ${RV_STAGE}/wwlib/widestring.cpp
  ${RV_STAGE}/wwlib/xstraw.cpp
  ${RV_STAGE}/wwlib/xpipe.cpp
  ${RV_STAGE}/wwlib/b64pipe.cpp
  ${RV_STAGE}/wwlib/b64straw.cpp
)

set(RV_WWSAVELOAD_DEFINITION_SOURCES
  ${RV_STAGE}/wwsaveload/definition.cpp
  ${RV_STAGE}/wwsaveload/definitionfactory.cpp
  ${RV_STAGE}/wwsaveload/definitionfactorymgr.cpp
  ${RV_STAGE}/wwsaveload/definitionmgr.cpp
  ${RV_STAGE}/wwsaveload/persistfactory.cpp
  ${RV_STAGE}/wwsaveload/pointerremap.cpp
  ${RV_STAGE}/wwsaveload/saveload.cpp
  ${RV_STAGE}/wwsaveload/saveloadstatus.cpp
  ${RV_STAGE}/wwsaveload/saveloadsubsystem.cpp
  ${RV_STAGE}/wwsaveload/twiddler.cpp
  ${RV_STAGE}/wwsaveload/wwsaveload.cpp
)

add_executable(a30_definition_runtime
  ${RV_WWLIB_SOURCES}
  ${RV_WWSAVELOAD_DEFINITION_SOURCES}
  ${RV_STAGE}/combat/ffactorylist.cpp
  ${RV_ROOT}/port/filesystem/renegade_paths.cpp
  ${RV_ROOT}/port/filesystem/renegade_file_factory.cpp
  ${RV_ROOT}/port/filesystem/renegade_registry.cpp
  ${CMAKE_CURRENT_LIST_DIR}/main.cpp
)

target_include_directories(a30_definition_runtime PRIVATE
  ${RV_COMPAT}
  ${RV_ROOT}/port/filesystem
  ${RV_STAGE}/wwbitpack
  ${RV_STAGE}/wwlib
  ${RV_STAGE}/wwsaveload
  ${RV_STAGE}/combat
  ${RV_STAGE}/wwphys
  ${RV_STAGE}/ww3d2
  ${RV_UPSTREAM}/Code/wwdebug
  ${RV_UPSTREAM}/Code/wwlib
  ${RV_UPSTREAM}/Code/wwutil
  ${RV_UPSTREAM}/Code/WWMath
  ${RV_UPSTREAM}/Code/wwsaveload
  ${RV_UPSTREAM}/Code/ww3d2
  ${RV_UPSTREAM}/Code/WWPhys
  ${RV_UPSTREAM}/Code/Combat
  ${RV_UPSTREAM}/Code/WWAudio
  ${RV_UPSTREAM}/Code/wwtranslatedb
  ${RV_UPSTREAM}/Code/wwnet
  ${RV_SCRIPT_SOURCE}
)

target_compile_definitions(a30_definition_runtime PRIVATE
  NDEBUG=1
  _UNIX=1
  UMBRASUPPORT=0
  RENEGADE_RUNTIME_READ_ONLY=1
  RENEGADE_HOST_ABI_TEST=1
  RENEGADE_VITA_PORT=1
)
target_compile_options(a30_definition_runtime PRIVATE
  -O1 -g
  -fno-strict-aliasing
  -fno-exceptions
  -fno-rtti
  -ffunction-sections
  -fdata-sections
  -Wno-unknown-pragmas
  "SHELL:-include ${RV_COMPAT}/msvc_compat.h"
)
target_link_options(a30_definition_runtime PRIVATE -Wl,--gc-sections)
target_link_libraries(a30_definition_runtime PRIVATE m pthread)

# v3.6 second-scene preflight: use the original MIX factory directly.  This is
# deliberately distinct from the M00 PhysicsScene runtime; it establishes the
# authentic M01 archive boundary before a full scene-load lifecycle is added.
add_executable(a36_m01_mix_probe
  ${RV_WWLIB_SOURCES}
  ${RV_ROOT}/port/filesystem/renegade_paths.cpp
  ${RV_ROOT}/port/filesystem/renegade_file_factory.cpp
  ${CMAKE_CURRENT_LIST_DIR}/a36_m01_mix_main.cpp
)
target_include_directories(a36_m01_mix_probe PRIVATE
  ${RV_COMPAT}
  ${RV_ROOT}/port/filesystem
  ${RV_STAGE}/wwlib
  ${RV_STAGE}/combat
  ${RV_UPSTREAM}/Code/wwdebug
  ${RV_UPSTREAM}/Code/wwlib
  ${RV_UPSTREAM}/Code/WWMath
)
target_compile_definitions(a36_m01_mix_probe PRIVATE
  NDEBUG=1 _UNIX=1 UMBRASUPPORT=0 RENEGADE_RUNTIME_READ_ONLY=1
  RENEGADE_HOST_ABI_TEST=1 RENEGADE_VITA_PORT=1)
target_compile_options(a36_m01_mix_probe PRIVATE
  -O1 -g -fno-strict-aliasing -fno-exceptions -fno-rtti
  -ffunction-sections -fdata-sections -Wno-unknown-pragmas
  "SHELL:-include ${RV_COMPAT}/msvc_compat.h")
target_link_options(a36_m01_mix_probe PRIVATE -Wl,--gc-sections)
target_link_libraries(a36_m01_mix_probe PRIVATE m pthread)

# Host-only v3.6 cache precursor: original MixFileFactoryClass owns archive
# enumeration while this tool writes a deterministic, content-free index.
add_executable(a36_mix_index
  ${RV_WWLIB_SOURCES}
  ${RV_ROOT}/port/filesystem/renegade_paths.cpp
  ${RV_ROOT}/port/filesystem/renegade_file_factory.cpp
  ${CMAKE_CURRENT_LIST_DIR}/a36_mix_index_main.cpp
)
target_include_directories(a36_mix_index PRIVATE
  ${RV_COMPAT}
  ${RV_ROOT}/port/filesystem
  ${RV_STAGE}/wwlib
  ${RV_STAGE}/combat
  ${RV_UPSTREAM}/Code/wwdebug
  ${RV_UPSTREAM}/Code/wwlib
  ${RV_UPSTREAM}/Code/WWMath
)
target_compile_definitions(a36_mix_index PRIVATE
  NDEBUG=1 _UNIX=1 UMBRASUPPORT=0 RENEGADE_RUNTIME_READ_ONLY=1
  RENEGADE_HOST_ABI_TEST=1 RENEGADE_VITA_PORT=1)
target_compile_options(a36_mix_index PRIVATE
  -O1 -g -fno-strict-aliasing -fno-exceptions -fno-rtti
  -ffunction-sections -fdata-sections -Wno-unknown-pragmas
  "SHELL:-include ${RV_COMPAT}/msvc_compat.h")
target_link_options(a36_mix_index PRIVATE -Wl,--gc-sections)
target_link_libraries(a36_mix_index PRIVATE m pthread)

# Native-side cache safety contract. This validates only the generated index
# format through the existing cache namespace; it never substitutes for an
# original archive loader or consumes retail content.
add_executable(a36_cache_health_contract_selftest
  ${RV_ROOT}/port/filesystem/renegade_paths.cpp
  ${RV_ROOT}/port/filesystem/renegade_cache_health.cpp
  ${CMAKE_CURRENT_LIST_DIR}/cache_health_contract_main.cpp
)
target_include_directories(a36_cache_health_contract_selftest PRIVATE
  ${RV_ROOT}/port/filesystem)
target_compile_options(a36_cache_health_contract_selftest PRIVATE
  -O1 -g -fno-strict-aliasing -Wno-unknown-pragmas)
target_link_libraries(a36_cache_health_contract_selftest PRIVATE m pthread)

# Bounded resource telemetry contract. It exercises only the rooted platform
# factory and temporary files; original MixFileFactoryClass remains the retail
# archive owner in all runtime targets.
add_executable(a36_file_factory_telemetry_contract_selftest
  ${RV_WWLIB_SOURCES}
  ${RV_ROOT}/port/filesystem/renegade_paths.cpp
  ${RV_ROOT}/port/filesystem/renegade_file_factory.cpp
  ${CMAKE_CURRENT_LIST_DIR}/file_factory_telemetry_contract_main.cpp
)
target_include_directories(a36_file_factory_telemetry_contract_selftest PRIVATE
  ${RV_COMPAT}
  ${RV_ROOT}/port/filesystem
  ${RV_STAGE}/wwlib
  ${RV_UPSTREAM}/Code/wwdebug
  ${RV_UPSTREAM}/Code/wwlib
  ${RV_UPSTREAM}/Code/WWMath
)
target_compile_definitions(a36_file_factory_telemetry_contract_selftest PRIVATE
  NDEBUG=1 _UNIX=1 RENEGADE_RUNTIME_READ_ONLY=1 RENEGADE_HOST_ABI_TEST=1
  RENEGADE_VITA_PORT=1)
target_compile_options(a36_file_factory_telemetry_contract_selftest PRIVATE
  -O1 -g -fno-strict-aliasing -fno-exceptions -fno-rtti
  -ffunction-sections -fdata-sections -Wno-unknown-pragmas
  "SHELL:-include ${RV_COMPAT}/msvc_compat.h")
target_link_options(a36_file_factory_telemetry_contract_selftest PRIVATE -Wl,--gc-sections)
target_link_libraries(a36_file_factory_telemetry_contract_selftest PRIVATE m pthread)

# Focused observer-loader contract at the ChunkLoadClass boundary. This route
# validates required-root behavior and child-level balancing without introducing
# replacement gameplay or serialization logic.
add_executable(a35_persistent_observer_loader_contract_selftest
  ${RV_WWLIB_SOURCES}
  ${RV_STAGE}/wwsaveload/persistfactory.cpp
  ${RV_STAGE}/wwsaveload/pointerremap.cpp
  ${RV_STAGE}/wwsaveload/saveload.cpp
  ${RV_STAGE}/wwsaveload/saveloadsubsystem.cpp
  ${RV_STAGE}/combat/persistentgameobjobserver.cpp
  ${RV_ROOT}/port/validation/persistent_observer_loader_contract.cpp
)
target_include_directories(a35_persistent_observer_loader_contract_selftest PRIVATE
  ${RV_COMPAT}
  ${RV_STAGE}/wwlib
  ${RV_STAGE}/combat
  ${RV_STAGE}/wwsaveload
  ${RV_STAGE}/wwmath
  ${RV_UPSTREAM}/Code/wwdebug
  ${RV_UPSTREAM}/Code/wwlib
  ${RV_UPSTREAM}/Code/WWMath
  ${RV_UPSTREAM}/Code/wwsaveload
)
target_compile_definitions(a35_persistent_observer_loader_contract_selftest PRIVATE
  NDEBUG=1 _UNIX=1 RENEGADE_RUNTIME_READ_ONLY=1 RENEGADE_HOST_ABI_TEST=1
  RENEGADE_VITA_PORT=1)
target_compile_options(a35_persistent_observer_loader_contract_selftest PRIVATE
  -O1 -g -fno-strict-aliasing -fno-exceptions -fno-rtti
  -ffunction-sections -fdata-sections -Wno-unknown-pragmas
  "SHELL:-include ${RV_COMPAT}/msvc_compat.h")
target_link_options(a35_persistent_observer_loader_contract_selftest PRIVATE -Wl,--gc-sections)
target_link_libraries(a35_persistent_observer_loader_contract_selftest PRIVATE m pthread)

# The coherent next frontier: retain the complete original WWPhys runtime
# module so its translation-unit static factories register every WWPhys
# definition type present in Objects.DDB.  This is intentionally a link/runtime
# proof rather than another compile-only target.
set(RENEGADE_STAGE "${RV_STAGE}")
include("${RV_ROOT}/cmake/A31OriginalSources.cmake")

# The shared manifest owns the exact direct-object set. This matters for
# static factory registration and prevents the host runtime from drifting from
# canonical Vita as new M00 dependencies are introduced.

add_executable(a35_loading_backdrop_contract
  ${RENEGADE_A22_ORIGINAL_SOURCES}
  ${RV_STAGE}/wwlib/TARGA.CPP
  ${RV_STAGE}/ww3d2/bitmaphandler.cpp
  ${RV_STAGE}/ww3d2/ww3dformat.cpp
  ${RV_STAGE}/ww3d2/font3d.cpp
  ${RV_STAGE}/ww3d2/ddsfile.cpp
  ${RV_STAGE}/ww3d2/formconv.cpp
  ${RV_STAGE}/ww3d2/render2d.cpp
  ${RV_STAGE}/ww3d2/render2dsentence.cpp
  ${RV_ROOT}/port/filesystem/renegade_paths.cpp
  ${RV_ROOT}/port/filesystem/renegade_file_factory.cpp
  ${RV_ROOT}/port/renderer/vita/renegade_freetype_font_provider.cpp
  ${RV_ROOT}/port/renderer/vita/ww3d_vita_renderer.cpp
  ${RV_ROOT}/port/renderer/vita/ww3d_dx8_boundary.cpp
  ${RV_ROOT}/port/renderer/vita/surface_boundary.cpp
  ${CMAKE_CURRENT_LIST_DIR}/loading_backdrop_contract_main.cpp
)
target_include_directories(a35_loading_backdrop_contract PRIVATE
  ${RV_COMPAT}
  ${RV_ROOT}/port/filesystem
  ${RV_ROOT}/port/renderer/vita
  ${FREETYPE_INCLUDE_DIRS}
  ${RV_STAGE}/wwbitpack
  ${RV_STAGE}/wwlib
  ${RV_STAGE}/wwmath
  ${RV_STAGE}/wwsaveload
  ${RV_STAGE}/combat
  ${RV_STAGE}/ww3d2
  ${RV_UPSTREAM}/Code/wwdebug
  ${RV_UPSTREAM}/Code/wwlib
  ${RV_UPSTREAM}/Code/wwutil
  ${RV_UPSTREAM}/Code/WWMath
  ${RV_UPSTREAM}/Code/wwsaveload
  ${RV_UPSTREAM}/Code/ww3d2
  ${RV_UPSTREAM}/Code/WWPhys
  ${RV_UPSTREAM}/Code/Combat
)
target_compile_definitions(a35_loading_backdrop_contract PRIVATE
  NDEBUG=1 _UNIX=1 UMBRASUPPORT=0 RENEGADE_RUNTIME_READ_ONLY=1
  RENEGADE_HOST_ABI_TEST=1 RENEGADE_VITA_PORT=1)
target_compile_options(a35_loading_backdrop_contract PRIVATE
  -O1 -g -fno-strict-aliasing -fno-exceptions -fno-rtti
  -ffunction-sections -fdata-sections -Wno-unknown-pragmas
  "SHELL:-include ${RV_COMPAT}/msvc_compat.h")
target_link_options(a35_loading_backdrop_contract PRIVATE -Wl,--gc-sections)
target_link_libraries(a35_loading_backdrop_contract PRIVATE m pthread "${RV_WORLD_HOST_FREETYPE}")

add_executable(a30_wwphys_definition_runtime
  ${RENEGADE_A30_WORLD_ORIGINAL_SOURCES}
  ${RV_STAGE}/ww3d2/ddsfile.cpp
  ${RV_STAGE}/ww3d2/formconv.cpp
  ${RV_WORLD_FONT_RENDERER_CLOSURE_SOURCES}
  ${RV_ROOT}/port/filesystem/renegade_paths.cpp
  ${RV_ROOT}/port/filesystem/renegade_file_factory.cpp
  ${RV_ROOT}/port/platform/renegade_optional_services.cpp
  ${RV_ROOT}/port/renderer/vita/ww3d_vita_renderer.cpp
  ${RV_ROOT}/port/renderer/vita/ww3d_dx8_boundary.cpp
  ${RV_ROOT}/port/renderer/vita/surface_boundary.cpp
  ${RV_ROOT}/port/validation/a30_world_runtime.cpp
  ${CMAKE_CURRENT_LIST_DIR}/wwphys_definition_dx8_boundary.cpp
  ${CMAKE_CURRENT_LIST_DIR}/world_load_optional_boundary.cpp
  ${CMAKE_CURRENT_LIST_DIR}/world_render_callback.cpp
  ${CMAKE_CURRENT_LIST_DIR}/world_main.cpp
)

# Retain the internal target name so CMake/Ninja can reuse the complete
# 244-step DefinitionMgr/WWPhys object cache.  The accepted 34/34 executable
# is already preserved separately; this successor is now the genuine M00
# world-load runtime.
set_target_properties(a30_wwphys_definition_runtime PROPERTIES
  OUTPUT_NAME a30_m00_world_runtime
)

target_include_directories(a30_wwphys_definition_runtime PRIVATE
  ${RV_COMPAT}
  ${RV_ROOT}/port/renderer/vita
  ${FREETYPE_INCLUDE_DIRS}
  ${RV_ROOT}/port/audio/miles
  ${RV_ROOT}/port/filesystem
  ${RV_ROOT}/port/platform
  ${RV_ROOT}/port/validation
  ${RV_STAGE}/wwbitpack
  ${RV_STAGE}/wwlib
  ${RV_STAGE}/wwmath
  ${RV_STAGE}/wwsaveload
  ${RV_STAGE}/combat
  ${RV_STAGE}/commando
  ${RV_STAGE}/wwaudio
  ${RV_STAGE}/wwnet
  ${RV_STAGE}/wwtranslatedb
  ${RV_STAGE}/ww3d2
  ${RV_STAGE}/wwphys
  ${RV_UPSTREAM}/Code/wwdebug
  ${RV_UPSTREAM}/Code/wwlib
  ${RV_UPSTREAM}/Code/wwutil
  ${RV_UPSTREAM}/Code/WWMath
  ${RV_UPSTREAM}/Code/wwsaveload
  ${RV_UPSTREAM}/Code/ww3d2
  ${RV_UPSTREAM}/Code/WWPhys
  ${RV_UPSTREAM}/Code/Combat
  ${RV_UPSTREAM}/Code/Commando
  ${RV_UPSTREAM}/Code
  ${RV_UPSTREAM}/Code/WWAudio
  ${RV_UPSTREAM}/Code/wwnet
  ${RV_UPSTREAM}/Code/wwui
  ${RV_UPSTREAM}/Code/wwtranslatedb
  ${RV_SCRIPT_SOURCE}
)
target_compile_definitions(a30_wwphys_definition_runtime PRIVATE
  NDEBUG=1
  _UNIX=1
  UMBRASUPPORT=0
  RENEGADE_RUNTIME_READ_ONLY=1
  RENEGADE_HOST_ABI_TEST=1
  RENEGADE_VITA_PORT=1
  RENEGADE_A30_FULL_WWPHYS=1
)
target_compile_options(a30_wwphys_definition_runtime PRIVATE
  -O1 -g
  -fno-strict-aliasing
  -fno-exceptions
  -fno-rtti
  -ffunction-sections
  -fdata-sections
  -Wno-unknown-pragmas
  "SHELL:-include ${RV_COMPAT}/msvc_compat.h"
)
target_link_options(a30_wwphys_definition_runtime PRIVATE -Wl,--gc-sections)
target_link_libraries(a30_wwphys_definition_runtime PRIVATE m pthread "${RV_WORLD_HOST_FREETYPE}")

# A3.1 gameplay seed: preserve the retained A3.0 target above, but link the
# five original owning TUs instead of its static-world-only scalar closures.
# This first target intentionally reuses the accepted M00 harness; it proves
# source ownership and exposes the genuine link closure before the dynamic LDD
# route is switched on.
add_executable(a31_gameplay_seed_runtime
  ${RV_ROOT}/port/developer/a35_campaign_flight_recorder.cpp
  ${RV_ROOT}/port/developer/a35_script_lookup_telemetry.cpp
  ${RENEGADE_A31_GAMEPLAY_SEED_ORIGINAL_SOURCES}
	${RV_STAGE}/ww3d2/ddsfile.cpp
	${RV_STAGE}/ww3d2/formconv.cpp
	${RV_WORLD_FONT_RENDERER_CLOSURE_SOURCES}
	${RV_STAGE}/wwaudio/AudioSaveLoad.cpp
  ${RV_ROOT}/port/filesystem/renegade_paths.cpp
  ${RV_ROOT}/port/filesystem/renegade_file_factory.cpp
  ${RV_ROOT}/port/filesystem/renegade_registry.cpp
  ${RV_ROOT}/port/platform/renegade_directinput.cpp
  ${RV_ROOT}/port/platform/renegade_optional_services.cpp
  ${RV_ROOT}/port/platform/renegade_network_provider.cpp
  ${RV_ROOT}/port/platform/a31_gameplay_boundary.cpp
  ${RV_ROOT}/port/platform/a31_miscutil_boundary.cpp
  ${RV_ROOT}/port/renderer/vita/ww3d_vita_renderer.cpp
  ${RV_ROOT}/port/renderer/vita/ww3d_dx8_boundary.cpp
  ${RV_ROOT}/port/renderer/vita/surface_boundary.cpp
  ${RV_ROOT}/port/validation/a30_world_runtime.cpp
  ${CMAKE_CURRENT_LIST_DIR}/wwphys_definition_dx8_boundary.cpp
  ${CMAKE_CURRENT_LIST_DIR}/world_render_callback.cpp
  ${CMAKE_CURRENT_LIST_DIR}/world_main.cpp
)
set_target_properties(a31_gameplay_seed_runtime PROPERTIES
  OUTPUT_NAME a31_m00_gameplay_seed_runtime
)
target_include_directories(a31_gameplay_seed_runtime PRIVATE
  ${RV_ROOT}/port/developer
  ${RV_COMPAT}
  ${RV_ROOT}/port/renderer/vita
  ${FREETYPE_INCLUDE_DIRS}
  ${RV_ROOT}/port/audio/miles
  ${RV_ROOT}/port/filesystem
  ${RV_ROOT}/port/platform
  ${RV_ROOT}/port/validation
  ${RV_STAGE}/wwbitpack
  ${RV_STAGE}/wwlib
  ${RV_STAGE}/wwmath
  ${RV_STAGE}/wwsaveload
  ${RV_STAGE}/combat
  ${RV_STAGE}/commando
  ${RV_STAGE}/wwaudio
  ${RV_STAGE}/wwnet
  ${RV_STAGE}/wwtranslatedb
  ${RV_STAGE}/ww3d2
  ${RV_STAGE}/wwphys
  ${RV_UPSTREAM}/Code/wwdebug
  ${RV_UPSTREAM}/Code/wwlib
  ${RV_UPSTREAM}/Code/wwutil
  ${RV_UPSTREAM}/Code/WWMath
  ${RV_UPSTREAM}/Code/wwsaveload
  ${RV_UPSTREAM}/Code/ww3d2
  ${RV_UPSTREAM}/Code/WWPhys
  ${RV_UPSTREAM}/Code/Combat
  ${RV_UPSTREAM}/Code/Commando
  ${RV_UPSTREAM}/Code
  ${RV_UPSTREAM}/Code/WWAudio
  ${RV_UPSTREAM}/Code/wwnet
  ${RV_UPSTREAM}/Code/wwui
  ${RV_UPSTREAM}/Code/wwtranslatedb
  ${RV_SCRIPT_SOURCE}
)
target_compile_definitions(a31_gameplay_seed_runtime PRIVATE
  NDEBUG=1
  _UNIX=1
  UMBRASUPPORT=0
  RENEGADE_RUNTIME_READ_ONLY=1
  RENEGADE_HOST_ABI_TEST=1
  RENEGADE_VITA_PORT=1
  RENEGADE_VITA_A30=1
  RENEGADE_VITA_A31=1
  RENEGADE_A30_FULL_WWPHYS=1
)
target_compile_options(a31_gameplay_seed_runtime PRIVATE
  -O1 -g
  -fno-strict-aliasing
  -fno-exceptions
  -fno-rtti
  -ffunction-sections
  -fdata-sections
  -Wno-unknown-pragmas
  "SHELL:-include ${RV_COMPAT}/msvc_compat.h"
)
# ScriptCommands is a binary callback table shared with the historical MSVC
# script DLL. Its default values are MSVC-only syntax and do not affect the
# table ABI; keep that tolerance scoped to the original script manager TUs.
set_source_files_properties(
  ${RV_STAGE}/combat/scripts.cpp
  ${RV_STAGE}/combat/scriptcommands.cpp
  PROPERTIES
  COMPILE_OPTIONS "-fpermissive"
)
target_link_options(a31_gameplay_seed_runtime PRIVATE -Wl,--gc-sections)
target_link_libraries(a31_gameplay_seed_runtime PRIVATE m pthread "${RV_WORLD_HOST_FREETYPE}")

# A4 link-closure additions to the existing original interactive runtime.
# Render2D, Render2DSentence, StyleMgr, and BuildNum are already in the A3.1
# source closure, so they are deliberately not repeated here.  These are the
# same original owners admitted to the compile-only A4 probe; linking them
# against the live M00 source closure exposes genuine ownership gaps without
# changing the frozen Vita candidate or synthesizing a frontend.
set(RV_A4_FRONTEND_RUNTIME_LINK_SOURCES
  # The original WWUI Vita patch disables desktop IMM composition.  This
  # boundary preserves the otherwise-referenced candidate-control ABI without
  # emulating a Win32 IME service on Vita.
  ${RV_ROOT}/port/platform/renegade_vita_ime_boundary.cpp
  ${RV_STAGE}/wwui/dialogparser.cpp
  ${RV_STAGE}/wwui/dialogbase.cpp
  ${RV_STAGE}/wwui/dialogmgr.cpp
  ${RV_STAGE}/wwui/wwuiinput.cpp
  ${RV_STAGE}/wwui/dialogcontrol.cpp
  ${RV_STAGE}/wwui/dialogtext.cpp
  ${RV_STAGE}/wwui/buttonctrl.cpp
  ${RV_STAGE}/wwui/checkboxctrl.cpp
  ${RV_STAGE}/wwui/imagectrl.cpp
  ${RV_STAGE}/wwui/textmarqueectrl.cpp
  ${RV_STAGE}/wwui/multilinetextctrl.cpp
  ${RV_STAGE}/wwui/editctrl.cpp
  ${RV_STAGE}/wwui/comboboxctrl.cpp
  ${RV_STAGE}/wwui/dropdownctrl.cpp
  ${RV_STAGE}/wwui/sliderctrl.cpp
  ${RV_STAGE}/wwui/tabctrl.cpp
  ${RV_STAGE}/wwui/treectrl.cpp
  ${RV_STAGE}/wwui/mapctrl.cpp
  ${RV_STAGE}/wwui/viewerctrl.cpp
  ${RV_STAGE}/wwui/inputctrl.cpp
  ${RV_STAGE}/wwui/shortcutbarctrl.cpp
  ${RV_STAGE}/wwui/merchandisectrl.cpp
  ${RV_STAGE}/wwui/ProgressCtrl.cpp
  ${RV_STAGE}/wwui/healthbarctrl.cpp
  ${RV_STAGE}/wwui/childdialog.cpp
  ${RV_STAGE}/wwui/menuentryctrl.cpp
  ${RV_STAGE}/wwui/menudialog.cpp
  ${RV_STAGE}/wwui/menubackdrop.cpp
  ${RV_STAGE}/wwui/mousemgr.cpp
  ${RV_STAGE}/wwui/tooltip.cpp
  ${RV_STAGE}/wwui/tooltipmgr.cpp
  ${RV_STAGE}/wwui/dialogtransition.cpp
  ${RV_STAGE}/wwui/listctrl.cpp
  ${RV_STAGE}/wwui/listiconmgr.cpp
  ${RV_STAGE}/wwui/scrollbarctrl.cpp
  ${RV_STAGE}/wwui/popupdialog.cpp
  ${RV_STAGE}/wwui/screencursor.cpp
  ${RV_STAGE}/wwui/IMECandidateCtrl.cpp
  ${RV_STAGE}/commando/renegadedialogmgr.cpp
  ${RV_STAGE}/commando/dlgmainmenu.cpp
  ${RV_STAGE}/commando/DlgMessageBox.cpp
  ${RV_STAGE}/commando/dialogtests.cpp
  ${RV_STAGE}/commando/dlgloadspgame.cpp
  ${RV_STAGE}/commando/dlgsavegame.cpp
  ${RV_STAGE}/commando/dlghelpscreen.cpp
  ${RV_STAGE}/commando/dlgtechoptions.cpp
  ${RV_STAGE}/commando/dlgconfigaudiotab.cpp
  ${RV_STAGE}/commando/dlgconfigvideotab.cpp
  ${RV_STAGE}/commando/dlgconfigperformancetab.cpp
  ${RV_STAGE}/commando/mainmenutransition.cpp
  ${RV_STAGE}/commando/gamemode.cpp
  ${RV_STAGE}/commando/movie.cpp
  ${RV_STAGE}/commando/campaign.cpp
  ${RV_STAGE}/commando/loadingscreen.cpp
  ${RV_STAGE}/commando/gameinitmgr.cpp
  ${RV_STAGE}/commando/combatgmode.cpp
  ${RV_STAGE}/commando/devoptions.cpp
  ${RV_STAGE}/commando/level.cpp
  # Original game-init/session owners needed by the genuine campaign route.
  ${RV_STAGE}/commando/bioevent.cpp
  ${RV_STAGE}/commando/svrgoodbyeevent.cpp
  ${RV_STAGE}/commando/modpackage.cpp
  ${RV_STAGE}/commando/modpackagemgr.cpp
  ${RV_STAGE}/combat/savegame.cpp
  ${RV_ROOT}/port/filesystem/renegade_find_files.cpp
  ${RV_ROOT}/port/platform/renegade_ui_pointer_tokens.cpp
  # RT_DIALOG is generated deterministically from the original chat.rc; this
  # is the platform resource ABI bridge, not a synthetic menu template.
  ${RV_ROOT}/port/platform/renegade_dialog_resource_provider.cpp
  ${RV_ROOT}/port/platform/a4_frontend_lifecycle_boundary.cpp
  ${RV_ROOT}/port/platform/a4_binkmovie_boundary.cpp
)

# A3.1 first-interactive runtime: unlike the retained seed target, this enters
# the original Combat level path.  The extra AudioSaveLoad owner is required by
# the retail dynamic LDD subsystem table; the no-output device remains at the
# Vita platform boundary, not in the serialized graph.
include(${RV_ROOT}/cmake/A35MultiplayerBuildingSources.cmake)
add_library(ttfs_host_transfer OBJECT
    ${RV_ROOT}/port/filesystem/renegade_ttfs_download.cpp
    ${RV_ROOT}/port/filesystem/renegade_ttfs_prepare.cpp)
if(NOT CMAKE_CROSSCOMPILING)
  target_compile_options(ttfs_host_transfer PRIVATE
    -idirafter /usr/local/vitasdk/arm-vita-eabi/include)
  target_link_libraries(ttfs_host_transfer PUBLIC -l:libcurl.so.4 z)
else()
  set(RV_TTFS_HTTPS_PREFIX "${RV_ROOT}/build/deps/ttfs-https-vita")
  if(NOT EXISTS "${RV_TTFS_HTTPS_PREFIX}/lib/libcurl.a")
    message(FATAL_ERROR "Run tools/build_ttfs_https_vita.sh before ARM frontend closure")
  endif()
  target_sources(ttfs_host_transfer PRIVATE ${RV_ROOT}/port/platform/vita/renegade_mbedtls_platform.c)
  target_include_directories(ttfs_host_transfer PRIVATE "${RV_TTFS_HTTPS_PREFIX}/include")
  target_compile_options(ttfs_host_transfer PRIVATE -mcpu=cortex-a9 -mfpu=neon -mfloat-abi=hard -mthumb)
  target_link_libraries(ttfs_host_transfer PUBLIC
    "${RV_TTFS_HTTPS_PREFIX}/lib/libcurl.a"
    "${RV_TTFS_HTTPS_PREFIX}/lib/libmbedtls.a"
    "${RV_TTFS_HTTPS_PREFIX}/lib/libmbedx509.a"
    "${RV_TTFS_HTTPS_PREFIX}/lib/libmbedcrypto.a"
    pthread z SceNet_stub SceNetCtl_stub SceLibKernel_stub SceRtc_stub)
endif()
add_executable(a31_interactive_runtime
  ${RV_ROOT}/port/developer/a35_campaign_flight_recorder.cpp
  ${RV_STAGE}/wwlib/ramfile.cpp
  ${RENEGADE_A35_MULTIPLAYER_BUILDING_SOURCES}
  ${RV_ROOT}/port/filesystem/renegade_ttfs.cpp
  ${RV_ROOT}/port/filesystem/renegade_ttfs_cache.cpp
  ${RV_ROOT}/port/filesystem/renegade_ttfs_factory.cpp
  ${RENEGADE_A31_GAMEPLAY_SEED_ORIGINAL_SOURCES}
  ${RV_A4_FRONTEND_RUNTIME_LINK_SOURCES}
  ${RV_STAGE}/combat/cinematicgameobj.cpp
  ${RENEGADE_SCRIPT_DSP_SOURCES}
  ${RV_STAGE}/wwlib/pipe.cpp
  ${RV_STAGE}/wwlib/base64.cpp
  ${RV_STAGE}/wwlib/xpipe.cpp
  ${RV_STAGE}/wwlib/b64pipe.cpp
  ${RV_STAGE}/wwlib/b64straw.cpp
  ${RV_STAGE}/wwdebug/wwprofile.cpp
  ${RV_STAGE}/wwlib/TARGA.CPP
  ${RV_STAGE}/ww3d2/bitmaphandler.cpp
  ${RV_STAGE}/ww3d2/ww3dformat.cpp
  ${RV_STAGE}/ww3d2/font3d.cpp
  ${RV_STAGE}/ww3d2/ddsfile.cpp
  ${RV_STAGE}/ww3d2/formconv.cpp
  ${RV_STAGE}/wwaudio/AudioSaveLoad.cpp
  ${RV_STAGE}/wwnet/wwpacket.cpp
  ${RV_STAGE}/combat/combatsound.cpp
  ${RV_STAGE}/combat/SoundEnvironment.cpp
  ${RV_STAGE}/combat/sniper.cpp
  ${RV_STAGE}/combat/staticnetworkobject.cpp
  ${RV_STAGE}/combat/combatdazzle.cpp
  ${RV_STAGE}/wwui/stylemgr.cpp
  ${RV_STAGE}/commando/gamedata.cpp
  ${RV_STAGE}/commando/gdsingleplayer.cpp
  ${RV_STAGE}/commando/gdskirmish.cpp
  # Original single-player frontend mode owner.  It is admitted separately
  # from the direct harness so Start_Game's required Menu entry can be closed
  # without fabricating a substitute menu mode.
  ${RV_STAGE}/commando/gamemenu.cpp
  # cNetwork::Update retains these original game-data/options/event owners,
  # including the CnC factory branch even while A3.1 selects single-player.
  ${RV_STAGE}/commando/gdcnc.cpp
  ${RV_STAGE}/commando/winevent.cpp
  ${RV_STAGE}/commando/renegadecheatmgr.cpp
  ${RV_STAGE}/commando/player.cpp
  ${RV_STAGE}/commando/playermanager.cpp
  ${RV_STAGE}/commando/god.cpp
  # Replication and player-session owners reached by the original A3.1 path.
  # Keep these in their original translation units instead of substituting
  # local gameplay/network copies.
  ${RV_STAGE}/commando/team.cpp
  ${RV_STAGE}/commando/teammanager.cpp
  ${RV_STAGE}/commando/gamedataupdateevent.cpp
  ${RV_STAGE}/commando/sctextobj.cpp
  ${RV_STAGE}/commando/netinterface.cpp
  ${RV_STAGE}/commando/netevent.cpp
  ${RV_STAGE}/commando/gamespyscchallengeevent.cpp
  ${RV_STAGE}/commando/gamespycschallengeresponseevent.cpp
  ${RV_STAGE}/wwlib/md5.cpp
  ${RV_STAGE}/commando/cnetwork.cpp
  # Keep cNetwork's authoritative receiver, packet dispatch, event, and
  # replicated-combat handlers in their original owners.  The only omitted
  # portion is retired desktop service discovery, isolated below WWNet.
  ${RV_STAGE}/commando/comnetrcvinst.cpp
  ${RV_STAGE}/commando/nethandler.cpp
  ${RV_STAGE}/commando/buildnum.cpp
  ${RV_STAGE}/commando/pkthandlers.cpp
  ${RV_STAGE}/commando/apppacketstats.cpp
  ${RV_STAGE}/commando/sbbomanager.cpp
  ${RV_STAGE}/commando/gameoptionsevent.cpp
  ${RV_STAGE}/commando/evictionevent.cpp
  ${RV_STAGE}/commando/clientpingmanager.cpp
  ${RV_STAGE}/commando/cspingrequestevent.cpp
  ${RV_STAGE}/commando/scpingresponseevent.cpp
  ${RV_STAGE}/commando/clienthintmanager.cpp
  ${RV_STAGE}/commando/cshint.cpp
  ${RV_STAGE}/commando/clientgoodbyeevent.cpp
  ${RV_STAGE}/commando/playerkill.cpp
  ${RV_STAGE}/commando/serverfps.cpp
  ${RV_STAGE}/commando/clientfps.cpp
  ${RV_STAGE}/ww3d2/w3d_dep.cpp
  ${RV_STAGE}/commando/priority.cpp
  ${RV_STAGE}/commando/regint.cpp
  ${RV_STAGE}/commando/regbool.cpp
  ${RV_STAGE}/commando/regfloat.cpp
  # Original transport and replicated-session lifecycle owners.  These are
  # deliberately target-local while the historical 354-TU seed stays frozen.
  ${RV_STAGE}/wwnet/connect.cpp
  ${RV_STAGE}/wwnet/rhost.cpp
  ${RV_STAGE}/wwnet/netutil.cpp
  ${RV_STAGE}/wwnet/netstats.cpp
  ${RV_STAGE}/wwnet/msgstat.cpp
  ${RV_STAGE}/wwnet/msgstatlist.cpp
  ${RV_STAGE}/wwnet/msgstatlistgroup.cpp
  ${RV_STAGE}/wwnet/BWBalance.cpp
  ${RV_STAGE}/wwnet/packetmgr.cpp
  ${RV_STAGE}/wwnet/singlepl.cpp
  ${RV_STAGE}/commando/messages.cpp
  ${RV_STAGE}/commando/changeteamevent.cpp
  ${RV_STAGE}/combat/inventory.cpp
  ${RV_STAGE}/combat/colors.cpp
  ${RV_ROOT}/port/filesystem/renegade_paths.cpp
  ${RV_ROOT}/port/filesystem/renegade_file_factory.cpp
  ${RV_ROOT}/port/filesystem/renegade_registry.cpp
  ${RV_ROOT}/port/platform/renegade_directinput.cpp
  ${RV_ROOT}/port/platform/renegade_optional_services.cpp
  ${RV_ROOT}/port/platform/renegade_network_provider.cpp
  ${RV_ROOT}/port/platform/a31_network_options_boundary.cpp
  ${RV_ROOT}/port/platform/a31_client_connect_boundary.cpp
  ${RV_ROOT}/port/platform/renegade_tt_weapon_event.cpp
  ${RV_ROOT}/port/platform/renegade_tt_purchase_network.cpp
  ${RV_ROOT}/port/platform/a31_client_identity_boundary.cpp
  ${RV_ROOT}/port/platform/renegade_client_identity.cpp
  ${RV_ROOT}/port/platform/a31_gameplay_boundary.cpp
  ${RV_ROOT}/port/platform/a31_miscutil_boundary.cpp
  ${RV_ROOT}/port/platform/renegade_script_static_provider.cpp
  ${RV_ROOT}/port/developer/a35_script_lookup_telemetry.cpp
  ${RV_ROOT}/port/renderer/vita/ww3d_vita_renderer.cpp
  ${RV_ROOT}/port/renderer/vita/ww3d_dx8_boundary.cpp
  ${RV_ROOT}/port/renderer/vita/surface_boundary.cpp
  ${RV_ROOT}/port/renderer/vita/renegade_freetype_font_provider.cpp
  ${CMAKE_CURRENT_LIST_DIR}/wwphys_definition_dx8_boundary.cpp
  ${CMAKE_CURRENT_LIST_DIR}/a31_interactive_main.cpp
)
set_target_properties(a31_interactive_runtime PROPERTIES
  OUTPUT_NAME a31_m00_interactive_runtime
)
target_sources(a31_interactive_runtime PRIVATE
  ${RV_STAGE}/ww3d2/sortingrenderer.cpp
  ${RV_STAGE}/ww3d2/statistics.cpp
  ${RV_STAGE}/ww3d2/sphereobj.cpp
  ${RV_STAGE}/ww3d2/ringobj.cpp
  ${RV_STAGE}/ww3d2/soundrobj.cpp)
target_compile_definitions(a31_interactive_runtime PRIVATE RENEGADE_ORIGINAL_SORTING=1)
if(RENEGADE_HOST_ORIGINAL_AUDIO)
  target_sources(a31_interactive_runtime PRIVATE
    ${RENEGADE_A35_ORIGINAL_AUDIO_SOURCES}
    ${RV_ROOT}/port/audio/vita/renegade_miles_provider.cpp
    ${RV_ROOT}/port/audio/vita/renegade_wave_decoder.cpp)
  target_include_directories(a31_interactive_runtime PRIVATE ${RV_ROOT}/port/audio/vita)
  target_compile_definitions(a31_interactive_runtime PRIVATE
    RENEGADE_A35_ORIGINAL_WWAUDIO=1 RENEGADE_MILES_MANUAL_MIX=1)
endif()
target_include_directories(a31_interactive_runtime PRIVATE
  ${RV_COMPAT}
  ${RV_ROOT}/port/developer
  ${RV_A4_DIALOG_GENERATED_DIR}
  ${RV_ROOT}/port/renderer/vita
  ${FREETYPE_INCLUDE_DIRS}
  ${RV_ROOT}/port/audio/miles
  ${RV_ROOT}/port/filesystem
  ${RV_ROOT}/port/platform
  # The renderer's Vita-only breadcrumb interface lives alongside the native
  # platform implementation. Host builds exclude it through __vita__, while
  # the ARM closure must see the existing declaration rather than a duplicate.
  ${RV_ROOT}/port/platform/vita
  ${RV_ROOT}/port/validation
  ${RV_STAGE}/wwbitpack
  ${RV_STAGE}/wwdebug
  ${RV_STAGE}/wwlib
  ${RV_STAGE}/wwmath
  ${RV_STAGE}/wwsaveload
  ${RV_STAGE}/combat
  ${RV_STAGE}/commando
  ${RV_STAGE}/wwaudio
  ${RV_STAGE}/wwnet
  ${RV_STAGE}/wwtranslatedb
  ${RV_STAGE}/ww3d2
  ${RV_STAGE}/wwphys
  # Frontend source is staged with the Vita IME boundary. It must win over
  # upstream headers so the selected .cpp and its class ABI agree.
  ${RV_STAGE}/wwui
  ${RV_UPSTREAM}/Code/wwdebug
  ${RV_UPSTREAM}/Code/wwlib
  ${RV_UPSTREAM}/Code/wwutil
  ${RV_UPSTREAM}/Code/WWMath
  ${RV_UPSTREAM}/Code/wwsaveload
  ${RV_UPSTREAM}/Code/ww3d2
  ${RV_UPSTREAM}/Code/WWPhys
  ${RV_UPSTREAM}/Code/Combat
  ${RV_UPSTREAM}/Code/Commando
  ${RV_UPSTREAM}/Code/WWAudio
  ${RV_UPSTREAM}/Code/wwnet
  ${RV_UPSTREAM}/Code/wwui
  ${RV_UPSTREAM}/Code/wwtranslatedb
  ${RV_SCRIPT_SOURCE}
)
add_dependencies(a31_interactive_runtime a4_dialog_templates)
target_compile_definitions(a31_interactive_runtime PRIVATE
  NDEBUG=1
  _UNIX=1
  UMBRASUPPORT=0
  RENEGADE_RUNTIME_READ_ONLY=1
  RENEGADE_HOST_ABI_TEST=1
  RENEGADE_VITA_PORT=1
  RENEGADE_VITA_A31=1
  RENEGADE_A4_REAL_STYLEMGR=1
  RENEGADE_A4_ORIGINAL_FRONTEND=1
  RENEGADE_A4_ORIGINAL_GAMEMODE=1
  RENEGADE_A4_ORIGINAL_MOVIE_OWNER=1
  RENEGADE_VITA_FRONTEND_SINGLEPLAYER=1
  RENEGADE_VITA_A4_FRONTEND_PORT_SOURCES=6
  RENEGADE_SHORT_WCHAR_ABI=1
  RENEGADE_A30_FULL_WWPHYS=1
)
target_compile_options(a31_interactive_runtime PRIVATE
  -O1 -g -fshort-wchar
  -fno-strict-aliasing
  -fno-exceptions
  -fno-rtti
  -ffunction-sections
  -fdata-sections
  -Wno-unknown-pragmas
  "SHELL:-include ${RV_COMPAT}/msvc_compat.h"
)
set_source_files_properties(
  ${RENEGADE_SCRIPT_DSP_SOURCES}
  ${RV_ROOT}/port/platform/renegade_script_static_provider.cpp
  PROPERTIES COMPILE_OPTIONS "-fpermissive"
)
set_property(SOURCE ${RENEGADE_SCRIPT_DSP_SOURCES}
  APPEND PROPERTY
  COMPILE_OPTIONS
  "-include${RV_COMPAT}/renegade_script_call_defaults.h")
set_property(SOURCE
  ${RV_SCRIPT_SOURCE}/Mission11.cpp
  APPEND PROPERTY COMPILE_OPTIONS
  "-include${RV_COMPAT}/renegade_m01_script_defaults.h")
set_property(SOURCE
  ${RV_SCRIPT_SOURCE}/Mission01.cpp
  APPEND PROPERTY COMPILE_OPTIONS
  "-include${RV_COMPAT}/renegade_m01_script_defaults.h")
set_property(SOURCE
  ${RV_SCRIPT_SOURCE}/Test_RAD.cpp
  APPEND PROPERTY COMPILE_OPTIONS
  "-include${RV_COMPAT}/renegade_m13_area2_script_defaults.h")
set_property(SOURCE
  ${RV_SCRIPT_SOURCE}/mission08.cpp
  APPEND PROPERTY COMPILE_OPTIONS
  "-include${RV_COMPAT}/renegade_m08_script_defaults.h")
foreach(rv_campaign_default_unit IN ITEMS
    Mission02.cpp Mission03.cpp Mission05.cpp Mission06.cpp Mission07.cpp
    Mission09.cpp Mission10.cpp MissionDemo.cpp Test_PDS.cpp Toolkit_Objectives.cpp)
  set_property(SOURCE ${RV_SCRIPT_SOURCE}/${rv_campaign_default_unit}
    APPEND PROPERTY COMPILE_OPTIONS
    "-include${RV_COMPAT}/renegade_campaign_script_defaults.h")
endforeach()
set_source_files_properties(
  ${RV_STAGE}/combat/scripts.cpp
  PROPERTIES
  COMPILE_OPTIONS "-fpermissive"
)
set_source_files_properties(
  ${RV_STAGE}/commando/gamedata.cpp
  ${RV_STAGE}/commando/player.cpp
  ${RV_STAGE}/commando/playermanager.cpp
  ${RV_STAGE}/commando/god.cpp
  PROPERTIES
  COMPILE_OPTIONS "-fpermissive"
)
target_link_options(a31_interactive_runtime PRIVATE -Wl,--gc-sections)
if(NOT CMAKE_CROSSCOMPILING)
  # Drive original TimeManager's capture-rate override without recording video.
  target_link_options(a31_interactive_runtime PRIVATE
    -Wl,--wrap=_ZN4WW3D28Get_Movie_Capture_Frame_RateEv)
endif()
# The closure target is used for both host validation and genuine ARM/Vita
# source closure.  The former intentionally uses the host runtime library;
# the latter must select VitaSDK's static FreeType plus its decoder archives.
# Never pass a host ELF library to arm-vita-eabi-g++.
if(CMAKE_CROSSCOMPILING)
  # Link the same native renderer boundary used by the packaged Vita target.
  # This closure executable retains the host harness entry point, but needs the
  # real breadcrumb owner and VitaGL/stub ABI to prove its selected original
  # frontend and campaign sources close for ARM.
  # vita_platform.cpp records the accepted A2.2 provenance counts in its
  # startup breadcrumb; preserve the production identities for this ARM-only
  # closure instead of creating a second platform logger.
  target_compile_definitions(a31_interactive_runtime PRIVATE
    RENEGADE_VITA_A22_ORIGINAL_SOURCES=105
    RENEGADE_VITA_A22_PORT_SOURCES=9
  )
  target_sources(a31_interactive_runtime PRIVATE
    ${RV_ROOT}/port/platform/vita/vita_platform.cpp
  )
  # GCC records wchar_t ABI in every object.  Carry the original engine's
  # 16-bit wchar_t selection through the final link as the production target
  # does, otherwise ld marks the closure ELF as 4-byte wchar_t and reports an
  # ABI mismatch for every participating original object.
  target_link_options(a31_interactive_runtime PRIVATE
    -fshort-wchar
    -Wl,--wrap=shark_init
  )
  target_link_libraries(a31_interactive_runtime PRIVATE
    ttfs_host_transfer
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
	    SceTouch_stub
	    SceNet_stub
    SceIofilemgr_stub
    freetype
    png
    bz2
    z
    pthread
  )
else()
  set(RV_HOST_FREETYPE "${FREETYPE_LIBRARIES}")
  if(NOT EXISTS "${RV_HOST_FREETYPE}")
    message(FATAL_ERROR "Host FreeType runtime library is required for the frontend glyph contract")
  endif()
  target_link_libraries(a31_interactive_runtime PRIVATE m pthread z "${RV_HOST_FREETYPE}" ttfs_host_transfer)
endif()

# Bounded A4 frontend frontier: compile the original dialog manager and its
# original message/IME adapter plus the genuine Renegade application bridge,
# without pretending that the complete control stack or a substitute frontend
# is ready. This pinpoints the next platform boundary before those translation
# units are admitted to the runtime link.
add_library(a4_wwui_frontend_probe OBJECT
  # The authentic UI renderer and text-sentence owners selected by the
  # 102-symbol link inventory; these are not substitute draw paths.
  ${RV_STAGE}/ww3d2/render2d.cpp
  ${RV_STAGE}/ww3d2/render2dsentence.cpp
  # These existing original A3.2 runtime owners resolve menu font/style,
  # build text, and released save-slot metadata without adding a new service.
  ${RV_STAGE}/wwui/stylemgr.cpp
  ${RV_STAGE}/wwui/dialogparser.cpp
  ${RV_STAGE}/wwui/dialogbase.cpp
  ${RV_STAGE}/wwui/dialogmgr.cpp
  ${RV_STAGE}/wwui/wwuiinput.cpp
  ${RV_STAGE}/wwui/dialogcontrol.cpp
  ${RV_STAGE}/wwui/dialogtext.cpp
  ${RV_STAGE}/wwui/buttonctrl.cpp
  ${RV_STAGE}/wwui/checkboxctrl.cpp
  ${RV_STAGE}/wwui/imagectrl.cpp
  ${RV_STAGE}/wwui/textmarqueectrl.cpp
  ${RV_STAGE}/wwui/multilinetextctrl.cpp
  ${RV_STAGE}/wwui/editctrl.cpp
  ${RV_STAGE}/wwui/comboboxctrl.cpp
  ${RV_STAGE}/wwui/dropdownctrl.cpp
  ${RV_STAGE}/wwui/sliderctrl.cpp
  ${RV_STAGE}/wwui/tabctrl.cpp
  ${RV_STAGE}/wwui/treectrl.cpp
  ${RV_STAGE}/wwui/mapctrl.cpp
  ${RV_STAGE}/wwui/viewerctrl.cpp
  ${RV_STAGE}/wwui/inputctrl.cpp
  ${RV_STAGE}/wwui/shortcutbarctrl.cpp
  ${RV_STAGE}/wwui/merchandisectrl.cpp
  ${RV_STAGE}/wwui/ProgressCtrl.cpp
  ${RV_STAGE}/wwui/healthbarctrl.cpp
  ${RV_STAGE}/wwui/childdialog.cpp
  ${RV_STAGE}/wwui/menuentryctrl.cpp
  ${RV_STAGE}/wwui/menudialog.cpp
  ${RV_STAGE}/wwui/menubackdrop.cpp
  ${RV_STAGE}/wwui/mousemgr.cpp
  ${RV_STAGE}/wwui/tooltip.cpp
  ${RV_STAGE}/wwui/tooltipmgr.cpp
  ${RV_STAGE}/wwui/dialogtransition.cpp
  ${RV_STAGE}/wwui/listctrl.cpp
  ${RV_STAGE}/wwui/listiconmgr.cpp
  ${RV_STAGE}/wwui/scrollbarctrl.cpp
  ${RV_STAGE}/wwui/popupdialog.cpp
  ${RV_STAGE}/wwui/screencursor.cpp
  ${RV_STAGE}/wwui/IMECandidateCtrl.cpp
  ${RV_STAGE}/commando/renegadedialogmgr.cpp
  ${RV_STAGE}/commando/dlgmainmenu.cpp
  ${RV_STAGE}/commando/dialogtests.cpp
  ${RV_STAGE}/commando/dlgloadspgame.cpp
  ${RV_STAGE}/commando/dlgsavegame.cpp
  ${RV_STAGE}/commando/dlghelpscreen.cpp
  ${RV_STAGE}/commando/dlgtechoptions.cpp
  ${RV_STAGE}/commando/dlgconfigaudiotab.cpp
  ${RV_STAGE}/commando/dlgconfigvideotab.cpp
  ${RV_STAGE}/commando/dlgconfigperformancetab.cpp
  ${RV_STAGE}/commando/mainmenutransition.cpp
  ${RV_STAGE}/commando/buildnum.cpp
  # Original MainMenu/Start-SP lifecycle owners. Their existing platform
  # provider boundaries remain in place; this does not enable WOL/GameSpy.
  ${RV_STAGE}/commando/gamemode.cpp
  ${RV_STAGE}/commando/campaign.cpp
  ${RV_STAGE}/commando/gameinitmgr.cpp
  ${RV_STAGE}/combat/savegame.cpp
  ${RV_ROOT}/port/filesystem/renegade_find_files.cpp
  ${RV_ROOT}/port/platform/renegade_ui_pointer_tokens.cpp
  ${RV_ROOT}/port/platform/a4_binkmovie_boundary.cpp
)
target_include_directories(a4_wwui_frontend_probe PRIVATE
  ${RV_COMPAT}
  ${RV_ROOT}/port/renderer/vita
  ${RV_ROOT}/port/audio/miles
  ${RV_ROOT}/port/filesystem
  ${RV_ROOT}/port/platform
  ${RV_STAGE}/wwbitpack
  ${RV_STAGE}/wwlib
  ${RV_STAGE}/wwmath
  ${RV_STAGE}/wwsaveload
  ${RV_STAGE}/combat
  ${RV_STAGE}/commando
  ${RV_STAGE}/wwaudio
  ${RV_STAGE}/wwnet
  ${RV_STAGE}/wwtranslatedb
  ${RV_STAGE}/ww3d2
  ${RV_STAGE}/wwphys
  ${RV_STAGE}/wwui
  ${RV_UPSTREAM}/Code/wwdebug
  ${RV_UPSTREAM}/Code/wwlib
  ${RV_UPSTREAM}/Code/wwutil
  ${RV_UPSTREAM}/Code/WWMath
  ${RV_UPSTREAM}/Code/wwsaveload
  ${RV_UPSTREAM}/Code/ww3d2
  ${RV_UPSTREAM}/Code/WWPhys
  ${RV_UPSTREAM}/Code/Combat
  ${RV_UPSTREAM}/Code/Commando
  ${RV_UPSTREAM}/Code
  ${RV_UPSTREAM}/Code/WWAudio
  ${RV_UPSTREAM}/Code/wwnet
  ${RV_UPSTREAM}/Code/wwui
  ${RV_UPSTREAM}/Code/wwtranslatedb
  ${RV_SCRIPT_SOURCE}
)
target_compile_definitions(a4_wwui_frontend_probe PRIVATE
  NDEBUG=1
  _UNIX=1
  UMBRASUPPORT=0
  RENEGADE_RUNTIME_READ_ONLY=1
  RENEGADE_HOST_ABI_TEST=1
  RENEGADE_VITA_PORT=1
  RENEGADE_VITA_A31=1
  RENEGADE_A4_REAL_STYLEMGR=1
  RENEGADE_VITA_FRONTEND_SINGLEPLAYER=1
  RENEGADE_SHORT_WCHAR_ABI=1
)
target_compile_options(a4_wwui_frontend_probe PRIVATE
  -O1 -g
  -fshort-wchar
  -fno-strict-aliasing
  -fno-exceptions
  -fno-rtti
  -ffunction-sections
  -fdata-sections
  -Wno-unknown-pragmas
  "SHELL:-include ${RV_COMPAT}/msvc_compat.h"
)

add_executable(a4_find_files_contract_selftest
  ${RV_ROOT}/port/filesystem/renegade_paths.cpp
  ${RV_ROOT}/port/filesystem/renegade_find_files.cpp
  ${CMAKE_CURRENT_LIST_DIR}/find_files_main.cpp
)
target_include_directories(a4_find_files_contract_selftest PRIVATE
  ${RV_COMPAT}
  ${RV_ROOT}/port/filesystem
)

add_executable(a4_listctrl_sort_contract_selftest
  ${CMAKE_CURRENT_LIST_DIR}/listctrl_sort_contract_main.cpp
)
target_include_directories(a4_listctrl_sort_contract_selftest PRIVATE
  ${RV_COMPAT}
)
target_compile_options(a4_listctrl_sort_contract_selftest PRIVATE -fshort-wchar)
target_compile_definitions(a4_find_files_contract_selftest PRIVATE
  RENEGADE_HOST_ABI_TEST=1
  RENEGADE_SHORT_WCHAR_ABI=1
)
target_compile_options(a4_find_files_contract_selftest PRIVATE
  -O1 -g -fshort-wchar
  "SHELL:-include ${RV_COMPAT}/msvc_compat.h"
)

add_executable(a4_ui_pointer_token_contract_selftest
  ${RV_ROOT}/port/platform/renegade_ui_pointer_tokens.cpp
  ${CMAKE_CURRENT_LIST_DIR}/ui_pointer_tokens_main.cpp
)
target_include_directories(a4_ui_pointer_token_contract_selftest PRIVATE
  ${RV_COMPAT}
  ${RV_ROOT}/port/platform
)
target_compile_definitions(a4_ui_pointer_token_contract_selftest PRIVATE
  RENEGADE_HOST_ABI_TEST=1
  RENEGADE_SHORT_WCHAR_ABI=1
)
target_compile_options(a4_ui_pointer_token_contract_selftest PRIVATE
  -O1 -g -fshort-wchar
  "SHELL:-include ${RV_COMPAT}/msvc_compat.h"
)

add_executable(a4_dialog_resource_contract_selftest
  ${RV_ROOT}/port/platform/renegade_dialog_resource_provider.cpp
  ${CMAKE_CURRENT_LIST_DIR}/dialog_resource_provider_main.cpp
)
add_dependencies(a4_dialog_resource_contract_selftest a4_dialog_templates)
target_include_directories(a4_dialog_resource_contract_selftest PRIVATE
  ${RV_COMPAT}
  ${RV_ROOT}/port/platform
  ${RV_A4_DIALOG_GENERATED_DIR}
)
target_compile_definitions(a4_dialog_resource_contract_selftest PRIVATE
  RENEGADE_HOST_ABI_TEST=1
  RENEGADE_VITA_PORT=1
  RENEGADE_SHORT_WCHAR_ABI=1
)
target_compile_options(a4_dialog_resource_contract_selftest PRIVATE
  -O1 -g -Wall -Wextra -Werror -fshort-wchar
  "SHELL:-include ${RV_COMPAT}/msvc_compat.h"
)

add_executable(a31_capture_telemetry_selftest
  ${RV_ROOT}/port/developer/a31_capture_telemetry.cpp
  ${CMAKE_CURRENT_LIST_DIR}/capture_telemetry_main.cpp
)

add_executable(a31_vita_input_contract_selftest
  ${CMAKE_CURRENT_LIST_DIR}/vita_input_contract_main.cpp
)
add_executable(a35_vita_button_state_contract_selftest
  ${CMAKE_CURRENT_LIST_DIR}/vita_button_state_contract_main.cpp
)
add_executable(a35_vita_render_state_contract_selftest
  ${CMAKE_CURRENT_LIST_DIR}/vita_render_state_contract_main.cpp
)
add_executable(a35_ddsfile_tga_alias_contract_selftest
  ${RV_WWLIB_SOURCES}
  ${RV_STAGE}/ww3d2/formconv.cpp
  ${RV_STAGE}/ww3d2/ddsfile.cpp
  ${CMAKE_CURRENT_LIST_DIR}/ddsfile_tga_alias_contract_main.cpp
)
target_include_directories(a35_vita_button_state_contract_selftest PRIVATE
  ${RV_ROOT}/port/platform
)
target_include_directories(a35_vita_render_state_contract_selftest PRIVATE
  ${RV_ROOT}/port/renderer/vita
  ${RV_COMPAT}
  ${RV_STAGE}/wwlib
  ${RV_UPSTREAM}/Code/wwlib
  ${RV_UPSTREAM}/Code/WWMath
  ${RV_STAGE}/ww3d2
  ${RV_UPSTREAM}/Code/ww3d2
)
target_compile_definitions(a35_vita_render_state_contract_selftest PRIVATE
  _UNIX=1 RENEGADE_VITA_PORT=1
)
target_compile_options(a35_vita_render_state_contract_selftest PRIVATE
  -O1 -g -fno-strict-aliasing -Wno-unknown-pragmas
  "SHELL:-include ${RV_COMPAT}/msvc_compat.h"
)
target_include_directories(a35_ddsfile_tga_alias_contract_selftest PRIVATE
  ${RV_COMPAT}
  ${RV_ROOT}/port/renderer/vita
  ${RV_STAGE}/wwlib
  ${RV_STAGE}/ww3d2
  ${RV_UPSTREAM}/Code/wwdebug
  ${RV_UPSTREAM}/Code/wwlib
  ${RV_UPSTREAM}/Code/ww3d2
  ${RV_UPSTREAM}/Code/WWMath
)
target_compile_definitions(a35_ddsfile_tga_alias_contract_selftest PRIVATE
  NDEBUG=1 _UNIX=1 RENEGADE_HOST_ABI_TEST=1 RENEGADE_VITA_PORT=1
)
target_compile_options(a35_ddsfile_tga_alias_contract_selftest PRIVATE
  -O1 -g -fno-strict-aliasing -fno-exceptions -fno-rtti
  -ffunction-sections -fdata-sections -Wno-unknown-pragmas
  "SHELL:-include ${RV_COMPAT}/msvc_compat.h"
)
target_link_options(a35_ddsfile_tga_alias_contract_selftest PRIVATE -Wl,--gc-sections)
target_link_libraries(a35_ddsfile_tga_alias_contract_selftest PRIVATE m pthread)
add_executable(a32_texture_upload_contract_selftest
  ${CMAKE_CURRENT_LIST_DIR}/texture_upload_contract_main.cpp
)
target_include_directories(a31_vita_input_contract_selftest PRIVATE
  ${RV_ROOT}/port/platform
)
target_compile_options(a31_vita_input_contract_selftest PRIVATE
  -O1 -g -Wall -Wextra -Werror
)
target_include_directories(a32_texture_upload_contract_selftest PRIVATE
  ${RV_ROOT}/port/renderer/vita
)
target_compile_options(a32_texture_upload_contract_selftest PRIVATE
  -O1 -g -Wall -Wextra -Werror
)
target_include_directories(a31_capture_telemetry_selftest PRIVATE
  ${RV_ROOT}/port/developer
)
target_compile_options(a31_capture_telemetry_selftest PRIVATE
  -O1 -g -Wall -Wextra -Werror
)

# TextureClass::Apply records every bind through the original Debug_Statistics
# owner (DX8_RECORD_TEXTURE), so every host target that links texture.cpp also
# needs statistics.cpp. Derived source lists copy the A22 manifest early, so
# close the dependency per target once every target is defined.
get_property(rv_host_targets DIRECTORY PROPERTY BUILDSYSTEM_TARGETS)
foreach(rv_host_target IN LISTS rv_host_targets)
  get_target_property(rv_host_target_type ${rv_host_target} TYPE)
  if(rv_host_target_type STREQUAL "INTERFACE_LIBRARY" OR
     rv_host_target_type STREQUAL "UTILITY")
    continue()
  endif()
  get_target_property(rv_host_target_sources ${rv_host_target} SOURCES)
  if(NOT rv_host_target_sources)
    continue()
  endif()
  list(FIND rv_host_target_sources "${RV_STAGE}/ww3d2/texture.cpp" rv_texture_index)
  list(FIND rv_host_target_sources "${RV_STAGE}/ww3d2/statistics.cpp" rv_statistics_index)
  if(NOT rv_texture_index EQUAL -1 AND rv_statistics_index EQUAL -1)
    target_sources(${rv_host_target} PRIVATE "${RV_STAGE}/ww3d2/statistics.cpp")
  endif()
endforeach()

# The audio decoder turns allocation failures into load failures with
# try/catch, as in the Vita build (which keeps C++ exceptions enabled). Host
# targets built with -fno-exceptions compile that one unit with exceptions.
set_source_files_properties("${RV_ROOT}/port/audio/vita/renegade_wave_decoder.cpp"
  PROPERTIES COMPILE_OPTIONS -fexceptions)

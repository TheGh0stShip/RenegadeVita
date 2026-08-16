cmake_minimum_required(VERSION 3.16)
project(RenegadeA30WWPhysCompileFrontier LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_EXTENSIONS ON)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

get_filename_component(RV_ROOT "${CMAKE_CURRENT_LIST_DIR}/../.." ABSOLUTE)
include("${RV_ROOT}/cmake/RenegadeCcache.cmake")
set(RV_STAGE "${RV_ROOT}/staging")
set(RV_UPSTREAM "${RV_ROOT}/upstream/CnC_Renegade")
set(RV_COMPAT "${RV_ROOT}/port/compatibility/include")
set(RENEGADE_STAGE "${RV_STAGE}")

include("${RV_ROOT}/cmake/A30OriginalSources.cmake")

# Compile-only frontiers deliberately separate C++/header portability from
# later subsystem link integration. Every translation unit in the original
# WWPhys runtime project and release WWSaveLoad definition closure must compile;
# no fake definitions are linked here.
add_library(a30_wwphys_compile_frontier OBJECT
  ${RENEGADE_A30_WWPHYS_SOURCES}
)

add_library(a30_wwsaveload_definition_compile_frontier OBJECT
  ${RENEGADE_A30_WWSAVELOAD_DEFINITION_SOURCES}
)

# Original WW3D buffer/FVF implementations now sit directly above the Vita
# CPU-backed DX8-shaped handles. Keep this as a distinct compile frontier so
# both LP64 host diagnostics and the real ILP32 Vita ABI validate the same
# engine implementation.
add_library(a30_ww3d_buffer_compile_frontier OBJECT
  ${RV_STAGE}/ww3d2/dx8fvf.cpp
  ${RV_STAGE}/ww3d2/dx8vertexbuffer.cpp
  ${RV_STAGE}/ww3d2/dx8indexbuffer.cpp
)

add_library(a30_combat_world_factory_compile_frontier OBJECT
  ${RENEGADE_A30_COMBAT_WORLD_FACTORY_SOURCES}
)

# Port-owned validation only: this is not an alternate loader.  It calls the
# original FileFactory/MIX, WWSaveLoad, DefinitionMgr, PhysicsScene and WW3D
# managers and exposes the live world to the eventual Commando continuation.
add_library(a30_world_runtime_harness_compile_frontier OBJECT
  ${RV_ROOT}/port/validation/a30_world_runtime.cpp
)

add_library(a30_datasafe_compile_frontier OBJECT
  ${RENEGADE_A30_DATASAFE_ORIGINAL_SOURCES}
  ${RV_ROOT}/port/platform/renegade_optional_services.cpp
)

function(renegade_configure_a30_compile_frontier target)
  target_include_directories(${target} PRIVATE
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
    ${RV_STAGE}/ww3d2
    ${RV_STAGE}/wwphys
    ${RV_UPSTREAM}/Code/wwdebug
    ${RV_UPSTREAM}/Code/wwlib
    ${RV_UPSTREAM}/Code/wwutil
    ${RV_UPSTREAM}/Code/WWMath
    ${RV_UPSTREAM}/Code/wwsaveload
    ${RV_UPSTREAM}/Code/ww3d2
    ${RV_UPSTREAM}/Code/Combat
    ${RV_UPSTREAM}/Code/Commando
    ${RV_UPSTREAM}/Code/WWAudio
    ${RV_UPSTREAM}/Code/wwnet
    ${RV_UPSTREAM}/Code/wwtranslatedb
    ${RV_UPSTREAM}/Code/Scripts
  )

  target_compile_definitions(${target} PRIVATE
    NDEBUG=1
    _UNIX=1
    UMBRASUPPORT=0
    RENEGADE_RUNTIME_READ_ONLY=1
    RENEGADE_VITA_PORT=1
  )
  if(NOT CMAKE_CXX_COMPILER MATCHES "arm-vita-eabi")
    # Preserve explicit Win32 scalar widths/overload identity on the LP64 host.
    # Vita itself is ILP32 and must use its production ABI definitions.
    target_compile_definitions(${target} PRIVATE
      RENEGADE_HOST_ABI_TEST=1
    )
  endif()
  target_compile_options(${target} PRIVATE
    -O1 -g
    -fno-strict-aliasing
    -fno-exceptions
    -fno-rtti
    -ffunction-sections
    -fdata-sections
    -Wno-unknown-pragmas
    "SHELL:-include ${RV_COMPAT}/msvc_compat.h"
  )
endfunction()

renegade_configure_a30_compile_frontier(a30_wwphys_compile_frontier)
renegade_configure_a30_compile_frontier(a30_wwsaveload_definition_compile_frontier)
renegade_configure_a30_compile_frontier(a30_ww3d_buffer_compile_frontier)
renegade_configure_a30_compile_frontier(a30_combat_world_factory_compile_frontier)
renegade_configure_a30_compile_frontier(a30_world_runtime_harness_compile_frontier)
renegade_configure_a30_compile_frontier(a30_datasafe_compile_frontier)

add_custom_target(a30_original_compile_frontier)
add_dependencies(a30_original_compile_frontier
  a30_wwphys_compile_frontier
  a30_wwsaveload_definition_compile_frontier
  a30_ww3d_buffer_compile_frontier
  a30_combat_world_factory_compile_frontier
  a30_world_runtime_harness_compile_frontier
  a30_datasafe_compile_frontier
)

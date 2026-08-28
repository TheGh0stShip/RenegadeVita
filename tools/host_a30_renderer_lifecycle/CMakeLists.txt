cmake_minimum_required(VERSION 3.16)
project(RenegadeA30RendererLifecycleHost LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_EXTENSIONS ON)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

get_filename_component(RV_ROOT "${CMAKE_CURRENT_LIST_DIR}/../.." ABSOLUTE)
include("${RV_ROOT}/cmake/RenegadeCcache.cmake")
set(RV_STAGE "${RV_ROOT}/staging")
set(RV_UPSTREAM "${RV_ROOT}/upstream/CnC_Renegade")
set(RV_COMPAT "${RV_ROOT}/port/compatibility/include")

add_executable(a30_renderer_lifecycle_selftest
  ${RV_ROOT}/port/renderer/vita/ww3d_vita_renderer.cpp
  ${RV_ROOT}/port/validation/a30_renderer_lifecycle_selftest.cpp
)

target_include_directories(a30_renderer_lifecycle_selftest PRIVATE
  ${RV_COMPAT}
  ${RV_ROOT}/port/renderer/vita
  ${RV_STAGE}/wwlib
  ${RV_STAGE}/wwmath
  ${RV_STAGE}/wwsaveload
  ${RV_STAGE}/ww3d2
  ${RV_UPSTREAM}/Code/wwdebug
  ${RV_UPSTREAM}/Code/wwlib
  ${RV_UPSTREAM}/Code/wwutil
  ${RV_UPSTREAM}/Code/WWMath
  ${RV_UPSTREAM}/Code/wwsaveload
  ${RV_UPSTREAM}/Code/ww3d2
)

target_compile_definitions(a30_renderer_lifecycle_selftest PRIVATE
  NDEBUG=1
  _UNIX=1
  RENEGADE_HOST_ABI_TEST=1
  RENEGADE_HOST_RENDERER_LIFECYCLE_SELFTEST=1
  RENEGADE_VITA_PORT=1
)
target_compile_options(a30_renderer_lifecycle_selftest PRIVATE
  -O1 -g
  -fno-strict-aliasing
  -fno-exceptions
  -fno-rtti
  -ffunction-sections
  -fdata-sections
  -Wno-unknown-pragmas
  "SHELL:-include ${RV_COMPAT}/msvc_compat.h"
)
target_link_options(a30_renderer_lifecycle_selftest PRIVATE
  -Wl,--gc-sections
)
target_link_libraries(a30_renderer_lifecycle_selftest PRIVATE m pthread)

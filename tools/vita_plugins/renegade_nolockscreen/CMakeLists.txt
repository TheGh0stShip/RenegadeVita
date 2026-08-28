cmake_minimum_required(VERSION 3.16)

if(NOT DEFINED CMAKE_TOOLCHAIN_FILE)
  if(DEFINED ENV{VITASDK})
    set(CMAKE_TOOLCHAIN_FILE "$ENV{VITASDK}/share/vita.toolchain.cmake" CACHE PATH "VitaSDK toolchain")
  else()
    message(FATAL_ERROR "VITASDK is required")
  endif()
endif()

project(renegade_nolockscreen C)
include("${VITASDK}/share/vita.cmake" REQUIRED)

option(RNV_NOLOCK_PROBE_ONLY "Build the read-only SceShell fingerprint probe" OFF)

add_executable(renegade_nolockscreen main.c)
if(RNV_NOLOCK_PROBE_ONLY)
  target_compile_definitions(renegade_nolockscreen PRIVATE RNV_NOLOCK_PROBE_ONLY=1)
endif()
target_compile_options(renegade_nolockscreen PRIVATE
  -Wall -Wextra -Werror -Os
)
target_link_options(renegade_nolockscreen PRIVATE -nostdlib)
target_link_libraries(renegade_nolockscreen
  taihen_stub
  SceLibKernel_stub
  SceIofilemgr_stub
  SceKernelModulemgr_stub
  k
  gcc
)

vita_create_self(renegade_nolockscreen.suprx
  renegade_nolockscreen
  CONFIG exports.yml
  UNSAFE
)

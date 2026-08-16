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

project(RenegadeVitaA30 VERSION 3.0.0 LANGUAGES C CXX)

include("${CMAKE_CURRENT_LIST_DIR}/../../cmake/RenegadeCcache.cmake")

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

get_filename_component(RENEGADE_ROOT "${CMAKE_CURRENT_LIST_DIR}/../.." ABSOLUTE)
set(RENEGADE_UPSTREAM "${RENEGADE_ROOT}/upstream/CnC_Renegade")
set(RENEGADE_STAGE "${RENEGADE_ROOT}/staging")
set(RENEGADE_COMPAT "${RENEGADE_ROOT}/port/compatibility/include")
set(VITASDK_DEBUG_SCREEN "${VITASDK}/share/gcc-arm-vita-eabi/samples/common")
include("${RENEGADE_ROOT}/cmake/A30OriginalSources.cmake")

# The 248-TU M00 world closure is owned by the shared manifest. Keep this
# transition target consuming exactly the same direct-object set as canonical
# Vita and host validation so static factory registration cannot drift.

add_executable(${PROJECT_NAME}
	${RENEGADE_A30_WORLD_ORIGINAL_SOURCES}
	${RENEGADE_ROOT}/port/filesystem/renegade_paths.cpp
	${RENEGADE_ROOT}/port/filesystem/renegade_file_factory.cpp
	${RENEGADE_ROOT}/port/platform/renegade_optional_services.cpp
	${RENEGADE_ROOT}/port/renderer/vita/ww3d_vita_renderer.cpp
	${RENEGADE_ROOT}/port/renderer/vita/ww3d_dx8_boundary.cpp
	${RENEGADE_ROOT}/port/validation/wwbitpack_selftest.cpp
	${RENEGADE_ROOT}/port/validation/a21_filesystem_selftest.cpp
	${RENEGADE_ROOT}/port/validation/a22_w3d_selftest.cpp
	${RENEGADE_ROOT}/port/validation/a30_world_runtime.cpp
	${RENEGADE_ROOT}/port/platform/vita/vita_platform.cpp
	${RENEGADE_ROOT}/port/platform/vita/a30_vita_runtime.cpp
	${RENEGADE_ROOT}/port/platform/vita/a30_static_world_boundary.cpp
	${RENEGADE_ROOT}/port/platform/vita/a30_main.cpp
	${VITASDK_DEBUG_SCREEN}/debugScreen.c
)

target_include_directories(${PROJECT_NAME} PRIVATE
	${CMAKE_CURRENT_LIST_DIR}/../host_a30_definitions/include
	${RENEGADE_COMPAT}
	${RENEGADE_ROOT}/port/audio/miles
	${RENEGADE_ROOT}/port/filesystem
	${RENEGADE_ROOT}/port/platform
	${RENEGADE_ROOT}/port/platform/vita
	${RENEGADE_ROOT}/port/renderer/vita
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
	${RENEGADE_UPSTREAM}/Code/wwtranslatedb
	${RENEGADE_UPSTREAM}/Code/Scripts
	${VITASDK_DEBUG_SCREEN}
)

target_compile_definitions(${PROJECT_NAME} PRIVATE
	NDEBUG=1
	_UNIX=1
	UMBRASUPPORT=0
	RENEGADE_RUNTIME_READ_ONLY=1
	RENEGADE_VITA_PORT=1
	RENEGADE_VITA_A30=1
	RENEGADE_A30_FULL_WWPHYS=1
	RENEGADE_VITA_A22_ORIGINAL_SOURCES=105
	RENEGADE_VITA_A22_PORT_SOURCES=9
	RENEGADE_VITA_A30_ORIGINAL_SOURCES=${RENEGADE_A30_WORLD_ORIGINAL_SOURCE_COUNT}
)
target_compile_options(${PROJECT_NAME} PRIVATE
	-fno-strict-aliasing
	-fno-exceptions
	-fno-rtti
	-ffunction-sections
	-fdata-sections
	-Wno-unknown-pragmas
	$<$<COMPILE_LANGUAGE:CXX>:-include${RENEGADE_COMPAT}/msvc_compat.h>
)
target_link_options(${PROJECT_NAME} PRIVATE
	-Wl,--gc-sections
	-Wl,--wrap=shark_init
	"-Wl,-Map=${CMAKE_CURRENT_BINARY_DIR}/RenegadeVita-A3.0.map"
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
	SceIofilemgr_stub
	pthread
)

vita_create_self(eboot.bin ${PROJECT_NAME})
vita_create_vpk(RenegadeVita-A3.0.vpk RNEGA3001 eboot.bin
	VERSION 03.00
	NAME "Renegade Vita A3.0"
)

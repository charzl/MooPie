cmake_minimum_required (VERSION 3.20)

project (MMAPI)

set(IS_WINDOWS FALSE)
set(IS_LINUX FALSE)
set(IS_MACOS FALSE)

if(WIN32)
    set(IS_WINDOWS TRUE)
elseif(APPLE)
    set(IS_MACOS TRUE)
elseif(UNIX)
    set(IS_LINUX TRUE)
else()
    message(FATAL_ERROR "Unknown OS.")
endif()

set(CMAKE_CXX_STANDARD 11)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

set(CONFIG_EXP $<IF:$<CONFIG:Debug>,Debug,Release>)
if(CMAKE_GENERATOR MATCHES "Visual Studio" OR CMAKE_GENERATOR MATCHES "Xcode")
	set(IS_GEN_IDE_PROJ TRUE)
endif ()

if (IS_LINUX OR NOT IS_GEN_IDE_PROJ)
	if ("${CMAKE_BUILD_TYPE}" STREQUAL "Debug")
		set(CONFIG_EXP Debug)
	else()
		set(CONFIG_EXP Release)
	endif()
endif ()

if (IS_WINDOWS)
	set(LIB_SUB_DIR ${CONFIG_EXP})
else ()
	set(LIB_SUB_DIR "")
endif ()
message(STATUS "LIB_SUB_DIR: ${LIB_SUB_DIR}")

option(API_GEN_PROTO "Generate pb.cc from proto files" ON)
option(API_BUILD_EXAMPLE "If build SimpleExample" ON)
set(API_PROTOC_PATH "" CACHE PATH "Path of the protoc executable, used to generate pb.cc from proto files")
set(API_THIRD_LIB_DIR "" CACHE PATH "Directory of third lib. Should contain include and lib subdirectories. Dependent libs are placed here")

set(PROJ_ROOT_DIR ${CMAKE_CURRENT_LIST_DIR})

include(common.cmake)
if (API_GEN_PROTO)
	check_protoc(${API_PROTOC_PATH})
	gen_proto(${API_PROTOC_PATH} "${PROJ_ROOT_DIR}/src/Proto" "${PROJ_ROOT_DIR}/include")
endif()
check_protobuf_include(${API_THIRD_LIB_DIR})

if (IS_LINUX)
	set(CMAKE_POSITION_INDEPENDENT_CODE ON)
endif ()

file(GLOB_RECURSE SRC_FILES "src/*.cpp" "src/*.cc")
file(GLOB_RECURSE HEADER_FILES "src/*.h")

add_library(${PROJECT_NAME} STATIC ${SRC_FILES} ${HEADER_FILES})
add_library(${PROJECT_NAME}::${PROJECT_NAME} ALIAS ${PROJECT_NAME})

target_include_directories(${PROJECT_NAME} SYSTEM PRIVATE ${API_THIRD_LIB_DIR}/include)
target_include_directories(${PROJECT_NAME} PUBLIC ${PROJ_ROOT_DIR}/include)

target_compile_definitions(${PROJECT_NAME} PRIVATE PROTOBUF_USE_DLLS)

if(IS_WINDOWS)
	target_compile_definitions(${PROJECT_NAME} PRIVATE API_OS_WINDOWS)
	target_compile_definitions(${PROJECT_NAME} PRIVATE _UNICODE UNICODE _WINDOWS _WIN32_WINNT=0x0601 WINVER=0x0601 _SILENCE_ALL_MS_EXT_DEPRECATION_WARNINGS)
	target_compile_options(${PROJECT_NAME} PRIVATE "$<$<CXX_COMPILER_ID:MSVC>:/utf-8>" "/MP" "/Zm500")
	target_compile_options(${PROJECT_NAME} PRIVATE "$<$<CXX_COMPILER_ID:MSVC>:/external:W0>")
	target_compile_options(${PROJECT_NAME} PRIVATE /wd4244 /wd4251 /bigobj)
elseif(IS_MACOS)
	target_compile_definitions(${PROJECT_NAME} PRIVATE API_OS_MACOS)
else()
	target_compile_definitions(${PROJECT_NAME} PRIVATE API_OS_LINUX)
endif()

if (API_BUILD_EXAMPLE)
	add_subdirectory(SimpleSample)
endif ()

if(IS_WINDOWS)
	install(TARGETS ${PROJECT_NAME}
		ARCHIVE DESTINATION lib/${CONFIG_EXP})
else()
	install(TARGETS ${PROJECT_NAME}
		ARCHIVE DESTINATION lib)
endif()

install(DIRECTORY include/ DESTINATION include
	FILES_MATCHING PATTERN "*.h" PATTERN "*.hpp")
cmake_minimum_required (VERSION 3.20)

project (MMAPI_Sample)

set(CMAKE_CXX_STANDARD 11)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

set(API_THIRD_LIB_DIR "" CACHE PATH
		"Directory of third lib. Should contain include and lib subdirectories. Dependent libs are placed here")

set(SAMPLE_DIR "${CMAKE_CURRENT_SOURCE_DIR}")

get_filename_component(MMAPI_ROOT_DIR "${SAMPLE_DIR}/.." ABSOLUTE)

file(GLOB SRC "${SAMPLE_DIR}/*.cpp" "${SAMPLE_DIR}/*.cc")
add_executable(${PROJECT_NAME} ${SRC})

message(STATUS "THIRDLIB: ${API_THIRD_LIB_DIR}")
target_include_directories(${PROJECT_NAME} PRIVATE ${API_THIRD_LIB_DIR}/include)

if(TARGET MMAPI)
	target_link_libraries(${PROJECT_NAME} PRIVATE MMAPI)
else()
	find_library(MMAPI_LIB
		NAMES MMAPI libMMAPI
		HINTS "${MMAPI_LIB_DIR}"
		PATHS
			"${MMAPI_ROOT_DIR}/cmake-build-debug"
			"${MMAPI_ROOT_DIR}/cmake-build-release"
			"${MMAPI_ROOT_DIR}/build"
			"${MMAPI_ROOT_DIR}/out"
		NO_DEFAULT_PATH)
	if(NOT MMAPI_LIB)
		message(FATAL_ERROR "MMAPI static library built by the main project was not found; please build the main project first, or specify its path with -DMMAPI_LIB_DIR=<dir>.")
	endif()
	message(STATUS "MMAPI_Sample: using MMAPI static library ${MMAPI_LIB}")
	target_link_libraries(${PROJECT_NAME} PRIVATE "${MMAPI_LIB}")
endif()

target_link_directories(${PROJECT_NAME} PRIVATE "${API_THIRD_LIB_DIR}/lib/${LIB_SUB_DIR}")
target_compile_definitions(${PROJECT_NAME} PRIVATE PROTOBUF_USE_DLLS)

if(WIN32)
	target_compile_definitions(${PROJECT_NAME} PRIVATE API_OS_WINDOWS)
	target_compile_definitions(${PROJECT_NAME} PRIVATE _WIN32_WINNT=0x0601 WINVER=0x0601 _SILENCE_ALL_MS_EXT_DEPRECATION_WARNINGS)
	target_compile_options(${PROJECT_NAME} PRIVATE "$<$<CXX_COMPILER_ID:MSVC>:/utf-8>" "$<$<CXX_COMPILER_ID:MSVC>:/external:W0>")
	link_shared_lib(${PROJECT_NAME} PB_LIB protobuf libprotobuf)
	link_shared_lib(${PROJECT_NAME} SSL_LIB ssl libssl)
	link_shared_lib(${PROJECT_NAME} CRYPTO_LIB crypto libcrypto)
	target_link_libraries(${PROJECT_NAME} PRIVATE "Ws2_32")
elseif(IS_MACOS)
	target_compile_definitions(${PROJECT_NAME} PRIVATE API_OS_MACOS)
	link_shared_lib(${PROJECT_NAME} PB_LIB libprotobuf.32.dylib protobuf libprotobuf)
	link_shared_lib(${PROJECT_NAME} SSL_LIB libssl.3.dylib ssl libssl)
	link_shared_lib(${PROJECT_NAME} CRYPTO_LIB libcrypto.3.dylib crypto libcrypto)
else()
	target_compile_definitions(${PROJECT_NAME} PRIVATE API_OS_LINUX)
	link_shared_lib(${PROJECT_NAME} PB_LIB protobuf libprotobuf)
	link_shared_lib(${PROJECT_NAME} SSL_LIB libssl.so.3 ssl libssl)
	link_shared_lib(${PROJECT_NAME} CRYPTO_LIB libcrypto.so.3 crypto libcrypto)
	find_package(Threads REQUIRED)
	target_link_libraries(${PROJECT_NAME} PRIVATE Threads::Threads)
endif()

add_custom_command(TARGET ${PROJECT_NAME} POST_BUILD
		COMMAND ${CMAKE_COMMAND}
		-DLIB_DIR="${API_THIRD_LIB_DIR}/lib/${LIB_SUB_DIR}"
		-DDEST_DIR="$<TARGET_FILE_DIR:${PROJECT_NAME}>"
		-P "${CMAKE_SOURCE_DIR}/copy_lib.cmake"
		COMMENT "Copying runtime libs to sample..."
)
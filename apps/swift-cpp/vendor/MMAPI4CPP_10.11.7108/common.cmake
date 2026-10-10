function(check_protoc path)
    # 1. 检查 protoc 可执行文件是否存在
    if(NOT EXISTS "${path}")
        message(FATAL_ERROR "check_protoc: protoc executable not found: '${path}'")
    endif()

    # 2. 运行 `path --version` 获取版本信息
    execute_process(
        COMMAND "${path}" --version
        OUTPUT_VARIABLE _protoc_version_output
        ERROR_VARIABLE  _protoc_version_error
        RESULT_VARIABLE _protoc_run_result
        OUTPUT_STRIP_TRAILING_WHITESPACE
    )
    if(NOT _protoc_run_result EQUAL 0)
        message(FATAL_ERROR "check_protoc: failed to run '${path} --version' (exit=${_protoc_run_result}): ${_protoc_version_error}")
    endif()

    # 3. 从输出（形如 "libprotoc 3.21.5"）中提取版本号
    if(NOT _protoc_version_output MATCHES "([0-9]+\\.[0-9]+(\\.[0-9]+)?)")
        message(FATAL_ERROR "check_protoc: cannot parse protoc version from output: '${_protoc_version_output}'")
    endif()
    set(_protoc_version "${CMAKE_MATCH_1}")

    # 4. 校验版本号 >= 3.5.1
    if(_protoc_version VERSION_LESS "3.5.1")
        message(FATAL_ERROR "check_protoc: protoc version ${_protoc_version} is too old, require >= 3.5.1 (path: '${path}')")
    endif()

    message(STATUS "check_protoc: OK, protoc ${_protoc_version} at '${path}'")
endfunction()

# 使用protoc将proto_dir中的.proto文件生成对应的C++代码。
function(gen_proto protoc proto_dir api_include_dir)
    # 收集 proto_dir 下所有 .proto 文件
    file(GLOB_RECURSE _proto_files "${proto_dir}/*.proto")
    if(NOT _proto_files)
        message(WARNING "gen_proto: no .proto files found under '${proto_dir}'")
        return()
    endif()

    # 对每一个 .proto 文件生成对应的 C++ 代码
    foreach(_proto_file ${_proto_files})
        execute_process(
            COMMAND "${protoc}" "-I=${proto_dir}" "--cpp_out=${proto_dir}" "${_proto_file}"
            RESULT_VARIABLE _gen_result
            OUTPUT_VARIABLE _gen_output
            ERROR_VARIABLE  _gen_error
        )
        if(NOT _gen_result EQUAL 0)
            message(FATAL_ERROR "gen_proto: failed to generate for '${_proto_file}' (exit=${_gen_result}): ${_gen_error}${_gen_output}")
        endif()
        message(STATUS "gen_proto: generated ${_proto_file}")
    endforeach()

    file(COPY "${proto_dir}"
            DESTINATION "${api_include_dir}"
            FILES_MATCHING PATTERN "*.h")
    message(STATUS "gen_proto: done, generated C++ for proto files under '${proto_dir}'")
endfunction()

# 检查 third_lib_dir 下的 protobuf 头文件版本 >= 3005001。
function(check_protobuf_include third_lib_dir)
    set(_header "${third_lib_dir}/include/google/protobuf/stubs/common.h")

    # 1. 检查头文件是否存在
    if(NOT EXISTS "${_header}")
        message(FATAL_ERROR "check_protobuf_include: header not found: '${_header}'")
    endif()

    # 2. 读取文件内容，从中提取 GOOGLE_PROTOBUF_VERSION 宏（整数）
    file(READ "${_header}" _content)
    if(NOT _content MATCHES "#define[ \t]+GOOGLE_PROTOBUF_VERSION[ \t]+([0-9]+)")
        message(FATAL_ERROR "check_protobuf_include: cannot find macro GOOGLE_PROTOBUF_VERSION in '${_header}'")
    endif()
    set(_pb_version "${CMAKE_MATCH_1}")

    # 3. 校验版本号 >= 3005001
    if(_pb_version LESS 3005001)
        message(FATAL_ERROR "check_protobuf_include: GOOGLE_PROTOBUF_VERSION ${_pb_version} is too old, require >= 3005001 (header: '${_header}')")
    endif()

    message(STATUS "check_protobuf_include: OK, GOOGLE_PROTOBUF_VERSION ${_pb_version} at '${_header}'")
endfunction()

macro(link_shared_lib target lib_name_var)
    set(_link_shared_lib_names ${ARGN})
    if(NOT _link_shared_lib_names)
        message(FATAL_ERROR "link_shared_lib: no library names given for ${lib_name_var}")
    endif()
    list(GET _link_shared_lib_names 0 _link_shared_lib_label)

    if(IS_GEN_IDE_PROJ)
        if(IS_WINDOWS)
            set(_link_shared_lib_debug_paths "${API_THIRD_LIB_DIR}/lib/Debug")
            set(_link_shared_lib_release_paths "${API_THIRD_LIB_DIR}/lib/Release")
        else()
            # Xcode / macOS: binaries are normally under lib/; also allow Debug/Release.
            set(_link_shared_lib_debug_paths
                "${API_THIRD_LIB_DIR}/lib/Debug"
                "${API_THIRD_LIB_DIR}/lib")
            set(_link_shared_lib_release_paths
                "${API_THIRD_LIB_DIR}/lib/Release"
                "${API_THIRD_LIB_DIR}/lib")
        endif()

        find_library(${lib_name_var}_DEBUG NAMES ${_link_shared_lib_names}
            PATHS ${_link_shared_lib_debug_paths}
            NO_DEFAULT_PATH)
        find_library(${lib_name_var}_RELEASE NAMES ${_link_shared_lib_names}
            PATHS ${_link_shared_lib_release_paths}
            NO_DEFAULT_PATH)
        if(NOT ${lib_name_var}_DEBUG AND NOT ${lib_name_var}_RELEASE)
            message(FATAL_ERROR
                "${_link_shared_lib_label} library not found under '${_link_shared_lib_debug_paths}' or '${_link_shared_lib_release_paths}'. "
                "Expected names: ${_link_shared_lib_names}")
        endif()
        if(NOT ${lib_name_var}_DEBUG)
            set(${lib_name_var}_DEBUG "${${lib_name_var}_RELEASE}")
            message(WARNING "link_shared_lib: ${_link_shared_lib_label} Debug not found, using Release")
        endif()
        if(NOT ${lib_name_var}_RELEASE)
            set(${lib_name_var}_RELEASE "${${lib_name_var}_DEBUG}")
            message(WARNING "link_shared_lib: ${_link_shared_lib_label} Release not found, using Debug")
        endif()
        message(STATUS "link_shared_lib: found ${_link_shared_lib_label} Debug='${${lib_name_var}_DEBUG}' Release='${${lib_name_var}_RELEASE}'")
        target_link_libraries(${target} PRIVATE
            "$<$<CONFIG:Debug>:${${lib_name_var}_DEBUG}>"
            "$<$<NOT:$<CONFIG:Debug>>:${${lib_name_var}_RELEASE}>")
    else()
        find_library(${lib_name_var} NAMES ${_link_shared_lib_names}
            PATHS "${API_THIRD_LIB_DIR}/lib/${LIB_SUB_DIR}"
            NO_DEFAULT_PATH)
        if(NOT ${lib_name_var})
            message(FATAL_ERROR
                "${_link_shared_lib_label} library not found under '${API_THIRD_LIB_DIR}/lib/${LIB_SUB_DIR}'. "
                "Expected names: ${_link_shared_lib_names}")
        endif()
        message(STATUS "link_shared_lib: found ${_link_shared_lib_label} at '${${lib_name_var}}'")
        target_link_libraries(${target} PRIVATE "${${lib_name_var}}")
    endif()
endmacro()
# copy dynamic libs to sample executable dir

if (NOT LIB_DIR OR NOT DEST_DIR)
    message(WARNING "copy_lib.cmake: LIB_DIR or DEST_DIR is empty (LIB_DIR='${LIB_DIR}', DEST_DIR='${DEST_DIR}')")
    return()
endif()

if (WIN32)
    file(GLOB FILES "${LIB_DIR}/*.dll")
elseif(APPLE)
    file(GLOB FILES "${LIB_DIR}/*.dylib")
elseif(UNIX)
    file(GLOB FILES "${LIB_DIR}/*.so*")
endif ()

if (NOT FILES)
    message(WARNING "copy_lib.cmake: no runtime libs found under '${LIB_DIR}'")
    return()
endif()

foreach(F ${FILES})
    get_filename_component(_name "${F}" NAME)
    file(COPY_FILE "${F}" "${DEST_DIR}/${_name}" ONLY_IF_DIFFERENT)  # CMake 3.21+
endforeach()
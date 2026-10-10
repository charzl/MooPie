# MMAPI C++ SDK

## Introduction

The MMAPI C++ SDK (hereinafter referred to as the SDK) can be used to communicate with Moomoo OpenD. For detailed features, please refer to the [documentation](https://openapi.moomoo.com/moomoo-api-doc/intro/intro.html). This document mainly describes how to build and compile the SDK.

## Requirements

Windows, macOS, and Linux are supported. A compiler with at least C++11 support is required.

## Directory Structure

include: SDK header files  
src: SDK source code  
src/Proto: Protocol Buffer (proto) files  
SimpleSample: Sample project  
ThirdLibSrc: Source code of third-party dependencies; you may build the third-party libraries yourself if needed.

## Dependencies

- cmake: Required, version 3.20 or later
- protobuf: Required, version 3.5.1 or later；the shared/dynamic library build is required
- openssl: Required, version 3.0.17 or later

## Build

Prepare a third-party library directory to hold the required dependencies. The directory layout must follow this convention:

- include: Third-party library headers
- lib: Third-party library binaries
  - On Windows, create `Debug` and `Release` subdirectories under `lib`, and place the corresponding binaries in each subdirectory
  - On macOS and Linux, place the binaries directly under `lib`

CMake configuration options:

- API_PROTOC_PATH: Path to the `protoc` executable used to generate code from proto files
- API_THIRD_LIB_DIR: Path to the third-party library directory
- API_GEN_PROTO: ON/OFF. When ON, generate .pb.cc and .pb.h files from the proto files. Default is ON (proto conversion is required). If proto files have not been converted yet, conversion must be done first.
- API_BUILD_EXAMPLE: ON/OFF. When ON, builds the sample project. Default is ON

Examples:

- First-time generation of a Visual Studio 2022 project on Windows, output to the `build` directory:

```
cmake -B build -G "Visual Studio 17 2022" -DAPI_PROTOC_PATH="D:\ThirdLib\bin\protoc.exe" -DAPI_THIRD_LIB_DIR="D:\ThirdLib"  .
```

- Generate an Xcode project on Mac, output to the `build` directory:

```
cmake -B build -G "Xcode" -DAPI_PROTOC_PATH="/Users/admin/work/ThirdLib/bin/protoc" -DAPI_THIRD_LIB_DIR="/Users/admin/work/ThirdLib"  .
```

- Generate a Makefile on Linux, output to the `build` directory:

```
cmake -B build -DAPI_PROTOC_PATH="/home/admin/work/ThirdLib/bin/protoc" -DAPI_THIRD_LIB_DIR="/home/admin/work/ThirdLib"  .
```

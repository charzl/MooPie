#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/.."
ROOT="$PWD"
SDK="$ROOT/vendor/MMAPI4CPP_10.11.7108"
PREFIX="$ROOT/thirdlib"
JOBS="${BUILD_JOBS:-$(sysctl -n hw.logicalcpu)}"
mkdir -p "$PREFIX" build-deps
if [[ ! -x "$PREFIX/bin/protoc" ]]; then
  tar -xzf "$SDK/ThirdLibSrc/protobuf-3.21.5.tar.gz" -C build-deps
  cmake -S build-deps/protobuf-3.21.5/cmake -B build-deps/protobuf-build \
    -Dprotobuf_BUILD_TESTS=OFF -Dprotobuf_BUILD_SHARED_LIBS=ON \
    -DCMAKE_BUILD_TYPE=Release -DCMAKE_OSX_DEPLOYMENT_TARGET=14.0 \
    -DCMAKE_INSTALL_PREFIX="$PREFIX" -DCMAKE_POLICY_VERSION_MINIMUM=3.5
  cmake --build build-deps/protobuf-build --parallel "$JOBS"
  cmake --install build-deps/protobuf-build
fi
if [[ ! -f "$PREFIX/lib/libssl.3.dylib" ]]; then
  tar -xzf "$SDK/ThirdLibSrc/openssl-3.0.17.tar.gz" -C build-deps
  pushd build-deps/openssl-3.0.17
  if [[ "$(uname -m)" == arm64 ]]; then TARGET=darwin64-arm64-cc; else TARGET=darwin64-x86_64-cc; fi
  ./Configure "$TARGET" shared no-tests --prefix="$PREFIX" --libdir=lib -mmacosx-version-min=14.0
  make -j "$JOBS"
  make install_sw
  popd
fi
cmake -S "$SDK" -B build-sdk -DAPI_PROTOC_PATH="$PREFIX/bin/protoc" \
  -DAPI_THIRD_LIB_DIR="$PREFIX" -DAPI_BUILD_EXAMPLE=OFF \
  -DCMAKE_BUILD_TYPE=Release -DCMAKE_OSX_DEPLOYMENT_TARGET=14.0
cmake --build build-sdk --parallel "$JOBS"

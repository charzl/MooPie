#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/.."
ROOT="$PWD"
SDK_REL=$(python3 -c 'import json;print(json.load(open("sdk.json"))["source_dir"])')
SDK="$ROOT/$SDK_REL"
PROTO_NAME=$(python3 -c 'import pathlib,sys; a=list(pathlib.Path(sys.argv[1]).glob("protobuf-*.tar.gz")); assert len(a)==1,"Expected one protobuf source archive"; print(a[0].name[:-7])' "$SDK/ThirdLibSrc")
SSL_NAME=$(python3 -c 'import pathlib,sys; a=list(pathlib.Path(sys.argv[1]).glob("openssl-*.tar.gz")); assert len(a)==1,"Expected one OpenSSL source archive"; print(a[0].name[:-7])' "$SDK/ThirdLibSrc")
PREFIX="$ROOT/thirdlib"
JOBS="${BUILD_JOBS:-$(sysctl -n hw.logicalcpu)}"
mkdir -p "$PREFIX" build-deps
if [[ ! -x "$PREFIX/bin/protoc" ]]; then
  tar -xzf "$SDK/ThirdLibSrc/${PROTO_NAME}.tar.gz" -C build-deps
  PROTO_CMAKE="build-deps/${PROTO_NAME}"
  if [[ -f "$PROTO_CMAKE/cmake/CMakeLists.txt" ]]; then PROTO_CMAKE="$PROTO_CMAKE/cmake"; fi
  cmake -S "$PROTO_CMAKE" -B build-deps/protobuf-build \
    -Dprotobuf_BUILD_TESTS=OFF -Dprotobuf_BUILD_SHARED_LIBS=ON \
    -DCMAKE_BUILD_TYPE=Release -DCMAKE_OSX_DEPLOYMENT_TARGET=14.0 \
    -DCMAKE_INSTALL_PREFIX="$PREFIX" -DCMAKE_POLICY_VERSION_MINIMUM=3.5
  cmake --build build-deps/protobuf-build --parallel "$JOBS"
  cmake --install build-deps/protobuf-build
fi
if [[ ! -f "$PREFIX/lib/libssl.dylib" ]]; then
  tar -xzf "$SDK/ThirdLibSrc/${SSL_NAME}.tar.gz" -C build-deps
  pushd build-deps/${SSL_NAME}
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

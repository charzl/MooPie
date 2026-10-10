# MMAPI C++ SDK

## 简介

MMAPI C++ SDK（以下简称为SDK）可用于和Moomoo OpenD通信，详细功能可参考[文档](https://openapi.moomoo.com/moomoo-api-doc/intro/intro.html)。本文档主要说明如何构建编译。

## 环境要求

支持Windows/MacOS和Linux，至少需要支持C++ 11的编译器。

## 目录结构

include: SDK头文件  
src：SDK源码  
src/Proto：proto协议文件  
SimpleSample：示例工程  
ThirdLibSrc: 依赖的第三方库源码，必要时可自行构建第三方库。

## 依赖说明

- cmake：必需，3.20及以上版本
- protobuf：必需，3.5.1及以上版本，需要动态库版本
- openssl：必需，3.0.17及以上版本

## 编译构建

准备好第三方库目录，用于存放依赖的库，该目录的结构应遵循如下约定：

- include: 存放第三方库头文件
- lib：存放二进制第三方库
  ** 对于Windows，需要在lib下再创建Debug和Release目录，然后将库二进制放在对应目录下
  ** MacOS和Linux则将二进制库直接放在lib目录

cmake配置时的参数：

- API_PROTOC_PATH：用于转换proto文件的protoc可执行文件路径
- API_THIRD_LIB_DIR：第三方库目录
- API_GEN_PROTO：ON/OFF，ON表示从proto文件生成对应的pb.cc和pb.h文件，默认是ON，即需要转换proto文件。没有转换过proto的情况下必须先转换。
- API_BUILD_EXAMPLE：ON/OFF，ON表示构建样例工程，默认是ON

举例：

- Windows首次生成Visual Studio 2022工程，存放到build目录：

```
cmake -B build -G "Visual Studio 17 2022" -DAPI_PROTOC_PATH="D:\ThirdLib\bin\protoc.exe" -DAPI_THIRD_LIB_DIR="D:\ThirdLib"  .
```

- Mac上生成Xcode工程，存放到build目录：

```
cmake -B build -G "Xcode" -DAPI_PROTOC_PATH="/Users/admin/work/ThirdLib/bin/protoc" -DAPI_THIRD_LIB_DIR="/Users/admin/work/ThirdLib"  .
```

- Linux上生成Makefile，存放到build目录：

```
cmake -B build -DAPI_PROTOC_PATH="/home/admin/work/ThirdLib/bin/protoc" -DAPI_THIRD_LIB_DIR="/home/admin/work/ThirdLib"  .
```


// Copyright 2026 Moomoo
#ifndef OPENAPI_APICRYPT_H
#define OPENAPI_APICRYPT_H

#include "APICommon.h"

bool APICrypto_Hash_SHA1(const i8_t* pData, i32_t nDataLen, i8_t sha1[20]);

/**
 * @brief  计算 RSA 加密所需缓冲区长度（块大小 117/128）
 */
i32_t APICrypto_RSA_CalcEncBufLen(i32_t nDataLen);

/**
 * @brief  计算 FTAES+MD5 加密所需缓冲区长度
 */
i32_t APICrypto_FTAES_MD5_CalcEncBufLen(i32_t nDataLen);

i32_t APICrypto_RSA_PublicEncrypt(const char* strPEMKey, bool bBareKey, const i8_t* pData, i32_t nDataLen,
    i8_t* pBuf,	i32_t nBufLen, APICrypto_RSAPaddingMode enPaddingMode, bool bFromPrivateKey);

i32_t APICrypto_RSA_PrivateDecrypt(const char* strPEMKey, bool bBareKey, const i8_t* pData, i32_t nDataLen,
    i8_t* pBuf, i32_t nBufLen, APICrypto_RSAPaddingMode enPaddingMode=APICrypto_RSAPaddingMode_Default);

i32_t APICrypto_AES_ECB_Encrypt(const i8_t* pKey, i32_t nKeyLen, const i8_t* pData, i32_t nDataLen,
    i8_t* pBuf, i32_t nBufLen, APICrypto_AESPaddingMode enPaddingMode=APICrypto_AESPaddingMode_Default);

i32_t APICrypto_AES_ECB_Decrypt(const i8_t* pKey, i32_t nKeyLen, const i8_t* pData, i32_t nDataLen,
    i8_t* pBuf, i32_t nBufLen, APICrypto_AESPaddingMode enPaddingMode=APICrypto_AESPaddingMode_Default);

#endif //OPENAPI_APICRYPT_H

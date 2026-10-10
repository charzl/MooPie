// Copyright 2026 Moomoo
#include "APICrypt.h"
#include <stdexcept>
#include <string>
#include <algorithm>
#include "openssl/md5.h"
#include "openssl/sha.h"
#include "openssl/hmac.h"
#include "openssl/aes.h"
#include "openssl/rsa.h"
#include "openssl/pem.h"
#include "openssl/bio.h"
#include "openssl/err.h"

#define API_RSA_BlockSize_Enc (117) // RSA 单块最大明文 = 密钥长度(128) - 11
#define API_RSA_BlockSize_Dec (128)


i32_t APICrypto_RSA_CalcEncBufLen(i32_t nDataLen)
{
    API_If_Warn_Return(nDataLen <= 0, API_RSA_BlockSize_Dec);
    return (API_RSA_BlockSize_Dec * (nDataLen / API_RSA_BlockSize_Enc + ((nDataLen % API_RSA_BlockSize_Enc == 0) ? 0 : 1)));
}

i32_t APICrypto_FTAES_MD5_CalcEncBufLen(i32_t nDataLen)
{
    API_If_Warn_Return(nDataLen <= 0, 32);
    i32_t nMod = nDataLen % 16;
    return (nMod == 0) ? (nDataLen + 32) : (nDataLen - nMod + 48);
}


bool APICrypto_Hash_SHA1(const i8_t* pData, i32_t nDataLen, i8_t sha1[20])
{
    API_If_Warn_Return(API_IsNullData(pData, nDataLen) || API_IsNullPtr(sha1), false);

    SHA1((const unsigned char*)pData, (size_t)nDataLen, (unsigned char*)sha1);
    return true;
}

// RSA PEM 密钥头尾（用于 bareKey 拼接成标准 PEM 格式）
#define API_RSA_PEMKey_PublicBegin  "-----BEGIN PUBLIC KEY-----\n"
#define API_RSA_PEMKey_PublicEnd    "-----END PUBLIC KEY-----\n"
#define API_RSA_PEMKey_PrivateBegin "-----BEGIN RSA PRIVATE KEY-----\n"
#define API_RSA_PEMKey_PrivateEnd   "-----END RSA PRIVATE KEY-----\n"

// RSA 默认 padding（默认 PKCS1）
static APICrypto_RSAPaddingMode gs_enRSADefPaddingMode = APICrypto_RSAPaddingMode_PKCS1;

// 将裸密钥拼接为标准 PEM 文本；非裸密钥原样返回
static std::string APIFormatKey(bool bPubkey, const char* strPEMKey, bool bBareKey)
{
    API_If_Warn_Return(API_IsNullOrEmptyStr(strPEMKey), std::string());

    std::string strFormatKey;
    if (bBareKey)
    {
        strFormatKey += (bPubkey ? API_RSA_PEMKey_PublicBegin : API_RSA_PEMKey_PrivateBegin);
        strFormatKey += strPEMKey;
        strFormatKey += "\n";
        strFormatKey += (bPubkey ? API_RSA_PEMKey_PublicEnd : API_RSA_PEMKey_PrivateEnd);
    }
    else
    {
        strFormatKey = strPEMKey;
    }
    return strFormatKey;
}

// 从 PEM 文本创建 RSA 对象，调用方负责 RSA_free
static RSA* APICreateRSA(bool bPubkey, const char* strPEMKey, bool bFromPrivateKey)
{
    API_If_Warn_Return(API_IsNullOrEmptyStr(strPEMKey), nullptr);

    BIO* pBIO = BIO_new_mem_buf(strPEMKey, -1);
    API_If_Warn_Return(API_IsNullPtr(pBIO), nullptr);

    RSA* pRSA{ nullptr };
    if (bPubkey && !bFromPrivateKey)
    {
        pRSA = PEM_read_bio_RSA_PUBKEY(pBIO, &pRSA, nullptr, nullptr);
    }
    else
    {
        pRSA = PEM_read_bio_RSAPrivateKey(pBIO, &pRSA, nullptr, nullptr);
    }
    BIO_free(pBIO);
    return pRSA;
}

// RSA 分块加密核心实现
static i32_t APICrypt_RSA_Encrypt(bool bPubkey, const char* strPEMKey, const i8_t* pData, i32_t nDataLen, i8_t* pBuf,
    i32_t nBufLen, APICrypto_RSAPaddingMode enPaddingMode, bool bFromPrivateKey)
{
    API_If_Warn_Return(API_IsNullOrEmptyStr(strPEMKey) || API_IsNullData(pData, nDataLen) || API_IsNullData(pBuf, nBufLen), 0);
    API_If_Do(enPaddingMode == APICrypto_RSAPaddingMode_Default, enPaddingMode = gs_enRSADefPaddingMode);

    i32_t nPadding = -1;
    API_If_Do(enPaddingMode == APICrypto_RSAPaddingMode_PKCS1, nPadding = RSA_PKCS1_PADDING);
    API_If_Warn_Return(nPadding < 0, 0);

    API_If_Warn_Return(nBufLen < APICrypto_RSA_CalcEncBufLen(nDataLen), 0);

    RSA* pRSA = APICreateRSA(bPubkey, strPEMKey, bFromPrivateKey);
    API_If_Warn_Return(API_IsNullPtr(pRSA), 0);

    i32_t nEncLen{};
    i32_t nEncRetLen{};
    i32_t nOnceEncLen{};
    i32_t nOnceEncRetLen{};
    while (nEncLen < nDataLen)
    {
        nOnceEncLen = (std::min)(API_RSA_BlockSize_Enc, nDataLen - nEncLen);
        if (bPubkey)
        {
            nOnceEncRetLen = RSA_public_encrypt(nOnceEncLen, (const unsigned char*)pData + nEncLen, (unsigned char*)pBuf + nEncRetLen, pRSA, nPadding);
        }
        else
        {
            nOnceEncRetLen = RSA_private_encrypt(nOnceEncLen, (const unsigned char*)pData + nEncLen, (unsigned char*)pBuf + nEncRetLen, pRSA, nPadding);
        }
        API_If_Do_Warn_Return(nOnceEncRetLen != API_RSA_BlockSize_Dec, RSA_free(pRSA), 0);
        nEncRetLen += nOnceEncRetLen;
        nEncLen += nOnceEncLen;
    }

    RSA_free(pRSA);
    return nEncRetLen;
}

// RSA 分块解密核心实现
static i32_t APICrypt_RSA_Decrypt(bool bPubkey, const char* strPEMKey, const i8_t* pData, i32_t nDataLen, i8_t* pBuf,
    i32_t nBufLen, APICrypto_RSAPaddingMode enPaddingMode, bool bFromPrivateKey)
{
    API_If_Warn_Return(API_IsNullOrEmptyStr(strPEMKey) || API_IsNullData(pData, nDataLen) || API_IsNullData(pBuf, nBufLen), 0);
    API_If_Do(enPaddingMode == APICrypto_RSAPaddingMode_Default, enPaddingMode = gs_enRSADefPaddingMode);

    i32_t nPadding = -1;
    API_If_Do(enPaddingMode == APICrypto_RSAPaddingMode_PKCS1, nPadding = RSA_PKCS1_PADDING);
    API_If_Warn_Return(nPadding < 0, 0);

    // 密文长度必须是 128 的整数倍；暂要求 buf 长度不小于密文长度（其实可更小，此处不做复杂化）
    API_If_Warn_Return((nDataLen % API_RSA_BlockSize_Dec) != 0 || nBufLen < nDataLen, 0);

    RSA* pRSA = APICreateRSA(bPubkey, strPEMKey, bFromPrivateKey);
    API_If_Warn_Return(API_IsNullPtr(pRSA), 0);

    i32_t nDecRetLen{};
    i32_t nDecLen{};
    i32_t nOnceDecRetLen{};
    while (nDecLen < nDataLen)
    {
        if (bPubkey)
        {
            nOnceDecRetLen = RSA_public_decrypt(API_RSA_BlockSize_Dec, (const unsigned char*)pData + nDecLen, (unsigned char*)pBuf + nDecRetLen, pRSA, nPadding);
        }
        else
        {
            nOnceDecRetLen = RSA_private_decrypt(API_RSA_BlockSize_Dec, (const unsigned char*)pData + nDecLen, (unsigned char*)pBuf + nDecRetLen, pRSA, nPadding);
        }
        API_If_Do_Warn_Return(nOnceDecRetLen <= 0, RSA_free(pRSA), 0);
        nDecRetLen += nOnceDecRetLen;
        nDecLen += API_RSA_BlockSize_Dec;
    }

    RSA_free(pRSA);
    return nDecRetLen;
}

i32_t APICrypto_RSA_PublicEncrypt(const char* strPEMKey, bool bBareKey, const i8_t* pData, i32_t nDataLen, i8_t* pBuf,
    i32_t nBufLen, APICrypto_RSAPaddingMode enPaddingMode, bool bFromPrivateKey)
{
    return APICrypt_RSA_Encrypt(true, APIFormatKey(!bFromPrivateKey, strPEMKey, bBareKey).c_str(), pData, nDataLen, pBuf, nBufLen, enPaddingMode, bFromPrivateKey);
}

i32_t APICrypto_RSA_PrivateDecrypt(const char* strPEMKey, bool bBareKey, const i8_t* pData, i32_t nDataLen, i8_t* pBuf,
    i32_t nBufLen, APICrypto_RSAPaddingMode enPaddingMode)
{
    return APICrypt_RSA_Decrypt(false, APIFormatKey(false, strPEMKey, bBareKey).c_str(), pData, nDataLen, pBuf, nBufLen, enPaddingMode, true);
}

// ---------------------------------------------------------------------------
// AES-ECB
// ---------------------------------------------------------------------------
#define API_AES_BlockSize 16 // openssl 块大小固定 16 字节，仅支持 128 位数据块加密

// AES 默认 padding（默认 PKCS7）
static APICrypto_AESPaddingMode gs_enAESDefPaddingMode = APICrypto_AESPaddingMode_PKCS7;

// 计算 AES 加密所需缓冲区长度：向上对齐到块大小，明文为块大小整数倍时额外补一个填充块
static i32_t APICrypt_AES_CalcEncBufLen(i32_t nDataLen)
{
    API_If_Warn_Return(nDataLen <= 0, API_AES_BlockSize);

    i32_t nMod = nDataLen % API_AES_BlockSize;
    return (nDataLen - nMod + API_AES_BlockSize);
}

// 生成最后一个填充块
static bool APICrypt_AES_PadLastBlock(APICrypto_AESPaddingMode enPaddingMode, i8_t lastBlock[16], const i8_t* pData, i32_t nDataLen)
{
    i32_t nMod = nDataLen % API_AES_BlockSize;
    memcpy(lastBlock, pData + (nDataLen - nMod), nMod);
    unsigned char chPadding_Last = (unsigned char)(API_AES_BlockSize - nMod);
    unsigned char chPadding_Other = chPadding_Last;
    switch (enPaddingMode)
    {
    case APICrypto_AESPaddingMode_PKCS7:
    case APICrypto_AESPaddingMode_Zero:
    case APICrypto_AESPaddingMode_ANSIX923:
        {
            API_If_Do(enPaddingMode == APICrypto_AESPaddingMode_Zero, { chPadding_Last = 0; chPadding_Other = 0; });
            API_If_Do(enPaddingMode == APICrypto_AESPaddingMode_ANSIX923, chPadding_Other = 0);
            for (i32_t i = nMod; i < API_AES_BlockSize - 1; i++)
            {
                lastBlock[i] = chPadding_Other;
            }
            lastBlock[API_AES_BlockSize - 1] = chPadding_Last;
        }
        break;
    case APICrypto_AESPaddingMode_ISO10126:
        {
            u64_t nRand = APIGetRand_U64();
            i32_t nPaddingByte = API_AES_BlockSize - 1 - nMod;
            i32_t nCopyCount = nPaddingByte / (i32_t)sizeof(nRand) + 1;
            for (i32_t i = 0; i < nCopyCount; i++)
            {
                memcpy(lastBlock + nMod + i * sizeof(nRand), &nRand, (std::min)(sizeof(nRand), (size_t)(nPaddingByte - i * (i32_t)sizeof(nRand))));
            }
            lastBlock[API_AES_BlockSize - 1] = chPadding_Last;
        }
        break;
    default:
        API_Warn;
        return false;
    }

    return true;
}

i32_t APICrypto_AES_ECB_Encrypt(const i8_t* pKey, i32_t nKeyLen, const i8_t* pData, i32_t nDataLen, i8_t* pBuf,
    i32_t nBufLen, APICrypto_AESPaddingMode enPaddingMode)
{
    API_If_Warn_Return(API_IsNullPtr(pKey) || nKeyLen < 16 || API_IsNullData(pData, nDataLen) || API_IsNullData(pBuf, nBufLen), 0);
    API_If_Do(enPaddingMode == APICrypto_AESPaddingMode_Default, enPaddingMode = gs_enAESDefPaddingMode);

    i32_t nEncBufLen = APICrypt_AES_CalcEncBufLen(nDataLen);
    API_If_Warn_Return(nBufLen < nEncBufLen, 0);

    i8_t lastBlock[API_AES_BlockSize]{};
    API_If_Warn_Return(!APICrypt_AES_PadLastBlock(enPaddingMode, lastBlock, pData, nDataLen), 0);

    AES_KEY aesKey{};
    API_If_Warn_Return(AES_set_encrypt_key((const unsigned char*)pKey, nKeyLen * 8, &aesKey) != 0, 0);

    i32_t nEncLen{};
    while ((nEncLen + API_AES_BlockSize) < nEncBufLen)
    {
        AES_ecb_encrypt((const unsigned char*)pData + nEncLen, (unsigned char*)pBuf + nEncLen, &aesKey, AES_ENCRYPT);
        nEncLen += API_AES_BlockSize;
    }
    AES_ecb_encrypt((const unsigned char*)lastBlock, (unsigned char*)pBuf + nEncLen, &aesKey, AES_ENCRYPT);
    nEncLen += API_AES_BlockSize;
    return nEncLen;
}

// 校验并扣除填充长度
static bool APICrypt_AES_SubtractPadLen(APICrypto_AESPaddingMode enPaddingMode, i8_t* pBuf, i32_t& nDecLen)
{
    switch (enPaddingMode)
    {
    case APICrypto_AESPaddingMode_PKCS7:
    case APICrypto_AESPaddingMode_ANSIX923:
    case APICrypto_AESPaddingMode_ISO10126:
        {
            API_If_Warn_Return(!(pBuf[nDecLen - 1] >= 1 && pBuf[nDecLen - 1] <= API_AES_BlockSize), false);
            nDecLen -= pBuf[nDecLen - 1];
        }
        break;
    case APICrypto_AESPaddingMode_Zero:
        {
            i32_t nZeroCount{};
            for (i32_t i = nDecLen - 1; i >= 0; i--)
            {
                if (pBuf[i] == 0) { nZeroCount++; } else { break; }
            }
            API_If_Warn_Return(!(nZeroCount >= 1 && nZeroCount <= API_AES_BlockSize), false);
            nDecLen -= nZeroCount;
        }
        break;
    default:
        API_Warn;
        return false;
    }

    return true;
}

i32_t APICrypto_AES_ECB_Decrypt(const i8_t* pKey, i32_t nKeyLen, const i8_t* pData, i32_t nDataLen, i8_t* pBuf,
    i32_t nBufLen, APICrypto_AESPaddingMode enPaddingMode)
{
    API_If_Warn_Return(API_IsNullPtr(pKey) || nKeyLen < 16 || API_IsNullData(pData, nDataLen) || API_IsNullData(pBuf, nBufLen), 0);
    API_If_Do(enPaddingMode == APICrypto_AESPaddingMode_Default, enPaddingMode = gs_enAESDefPaddingMode);

    API_If_Warn_Return((nDataLen % API_AES_BlockSize) != 0 || nBufLen < nDataLen, 0);

    AES_KEY aesKey{};
    API_If_Warn_Return(AES_set_decrypt_key((const unsigned char*)pKey, nKeyLen * 8, &aesKey) != 0, 0);

    i32_t nDecLen{};
    while (nDecLen < nDataLen)
    {
        AES_ecb_encrypt((const unsigned char*)pData + nDecLen, (unsigned char*)pBuf + nDecLen, &aesKey, AES_DECRYPT);
        nDecLen += API_AES_BlockSize;
    }

    API_If_Warn_Return(!APICrypt_AES_SubtractPadLen(enPaddingMode, pBuf, nDecLen), 0);
    return nDecLen;
}


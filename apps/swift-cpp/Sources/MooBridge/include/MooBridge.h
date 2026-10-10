#pragma once
#include <stdint.h>
#ifdef __cplusplus
extern "C" {
#endif
typedef void (*MooCallback)(void *, int, uint32_t, uint32_t, const char *);
void *moo_cpp_create(MooCallback callback, void *context);
int moo_cpp_connect(void *handle, const char *host, uint16_t port);
uint32_t moo_cpp_request(void *handle, uint32_t protocol_id, const char *json);
int moo_cpp_validate_request(uint32_t protocol_id, const char *json);
void moo_cpp_destroy(void *handle);
#ifdef __cplusplus
}
#endif

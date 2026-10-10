#include "MooBridge.h"
#include "MMAPIChannel.h"
#include "Proto/Qot_Sub.pb.h"
#include "Proto/Qot_GetBasicQot.pb.h"
#include "Proto/Qot_UpdateBasicQot.pb.h"
#include "Proto/Qot_GetKL.pb.h"
#include "Proto/Qot_UpdateKL.pb.h"
#include <google/protobuf/util/json_util.h>
#include <google/protobuf/struct.pb.h>
#include <mutex>
#include <memory>
#include <unordered_map>
#include <string>
namespace {
struct Context { MooCallback callback; void *user; };
std::mutex mutex;
std::unordered_map<void *, std::shared_ptr<Context>> contexts;
void emit(void *channel, int event, uint32_t id, uint32_t serial, const std::string &json) {
 std::shared_ptr<Context> context;
 { std::lock_guard<std::mutex> lock(mutex); auto it = contexts.find(channel); if (it != contexts.end()) context = it->second; }
 if (context && context->callback) context->callback(context->user, event, id, serial, json.c_str());
}
std::string status(bool ok, const std::string &message) {
 google::protobuf::Struct object;
 (*object.mutable_fields())["retType"].set_number_value(ok ? 0 : -1);
 (*object.mutable_fields())["retMsg"].set_string_value(message);
 std::string json; google::protobuf::util::MessageToJsonString(object, &json); return json;
}
template<class Response> std::string decode(const char *data, int length) {
 Response response;
 if (!response.ParseFromArray(data, length)) return status(false, "Invalid SDK response");
 google::protobuf::util::JsonPrintOptions options;
 options.preserve_proto_field_names = true; options.always_print_primitive_fields = true;
 std::string json;
 if (!google::protobuf::util::MessageToJsonString(response, &json, options).ok()) return status(false, "SDK JSON conversion failed");
 return json;
}
std::string decode(uint32_t id, const char *data, int length) {
 switch (id) {
 case 3001: return decode<Qot_Sub::Response>(data, length);
 case 3004: return decode<Qot_GetBasicQot::Response>(data, length);
 case 3005: return decode<Qot_UpdateBasicQot::Response>(data, length);
 case 3006: return decode<Qot_GetKL::Response>(data, length);
 case 3007: return decode<Qot_UpdateKL::Response>(data, length);
 default: return status(false, "Unsupported protocol");
 }
}
template<class Request> bool encode(const char *json, std::string &data) {
 Request request;
 return google::protobuf::util::JsonStringToMessage(json, &request).ok() && request.IsInitialized() && request.SerializeToString(&data);
}
bool encode(uint32_t id, const char *json, std::string &data) {
 if (!json) return false;
 switch (id) {
 case 3001: return encode<Qot_Sub::Request>(json, data);
 case 3004: return encode<Qot_GetBasicQot::Request>(json, data);
 case 3006: return encode<Qot_GetKL::Request>(json, data);
 default: return false;
 }
}
void connected(void *channel, Moomoo::i64_t error, const char *description) {
 emit(channel, 0, 1001, 0, status(error == 0, description ? description : ""));
}
void disconnected(void *channel, Moomoo::i64_t error) { emit(channel, 1, 0, 0, status(false, "OpenD disconnected: " + std::to_string(error))); }
void reply(void *channel, MMAPI_ReqReplyType type, const MMAPI_ProtoHeader *header, const char *data, int length) {
 if (!header || header->nProtoID == 1001 || header->nProtoID == 1004) return;
 emit(channel, 2, header->nProtoID, header->nSerialNo,
 type == MMAPI_ReqReplyType_SvrReply ? decode(header->nProtoID, data, length) : status(false, "SDK request failed: " + std::to_string(type)));
}
void push(void *channel, const MMAPI_ProtoHeader *header, const char *data, int length) {
 if (header && (header->nProtoID == 3005 || header->nProtoID == 3007)) emit(channel, 3, header->nProtoID, header->nSerialNo, decode(header->nProtoID, data, length));
}
}
void *moo_cpp_create(MooCallback callback, void *user) {
 void *channel = CreateMMAPIChannel(); if (!channel) return nullptr;
 { std::lock_guard<std::mutex> lock(mutex); contexts[channel] = std::make_shared<Context>(Context{callback, user}); }
 MMAPIChannel_SetClientInfo(channel, "MooSwiftCpp", 100);
 MMAPIChannel_SetProgrammingLanguage(channel, "Swift+C++");
 MMAPIChannel_SetOnInitConnectCallback(channel, connected);
 MMAPIChannel_SetOnDisconnectCallback(channel, disconnected);
 MMAPIChannel_SetOnReplyCallback(channel, reply);
 MMAPIChannel_SetOnPushCallback(channel, push);
 return channel;
}
int moo_cpp_connect(void *handle, const char *host, uint16_t port) { return MMAPIChannel_InitConnect(handle, host, port, 0); }
uint32_t moo_cpp_request(void *handle, uint32_t id, const char *json) {
 std::string bytes; if (!encode(id, json, bytes)) return 0;
 return MMAPIChannel_SendProto(handle, id, 0, bytes.data(), static_cast<int>(bytes.size()));
}
int moo_cpp_validate_request(uint32_t id, const char *json) { std::string bytes; return encode(id, json, bytes) ? 1 : 0; }
void moo_cpp_destroy(void *handle) {
 if (!handle) return;
 { std::lock_guard<std::mutex> lock(mutex); contexts.erase(handle); }
 ReleaseMMAPIChannel(handle);
}

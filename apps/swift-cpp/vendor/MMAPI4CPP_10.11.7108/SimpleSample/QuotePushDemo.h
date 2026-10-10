#pragma once
#include "FTAPIDemoBase.h"

class QuotePushDemo: public FTAPIDemoBase
{
public:
	QuotePushDemo();
	~QuotePushDemo();

	void Run();

private:
	bool bSubSuc;

protected:
	void OnReply_Sub(Moomoo::u32_t nSerialNo, const Qot_Sub::Response &stRsp);
	void OnPush_UpdateBasicQot(const Qot_UpdateBasicQot::Response &stRsp);
	void OnPush_UpdateOrderBook(const Qot_UpdateOrderBook::Response &stRsp);
	void OnPush_UpdateTicker(const Qot_UpdateTicker::Response &stRsp);
	void OnPush_UpdateKL(const Qot_UpdateKL::Response &stRsp);
	void OnPush_UpdateRT(const Qot_UpdateRT::Response &stRsp);
	void OnPush_UpdateBroker(const Qot_UpdateBroker::Response &stRsp);
};
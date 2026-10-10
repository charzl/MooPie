#pragma once
#include "FTAPIDemoBase.h"

class PlaceOrderDemo: public FTAPIDemoBase
{
public:
	PlaceOrderDemo();
	~PlaceOrderDemo();

	void Run();

private:
	void GetLotSize();
	void GetSellPrice();
	void PlaceOrder();
	void GetOrderList();

private:
	int32_t m_nTCHLotSize;
	double m_fSellPrice;
	uint64_t m_nOrderID;

protected:
	void OnReply_GetStaticInfo(Moomoo::u32_t nSerialNo, const Qot_GetStaticInfo::Response &stRsp);
	void OnReply_Sub(Moomoo::u32_t nSerialNo, const Qot_Sub::Response &stRsp);
	void OnReply_GetOrderBook(Moomoo::u32_t nSerialNo, const Qot_GetOrderBook::Response &stRsp);

	void OnReply_PlaceOrder(Moomoo::u32_t nSerialNo, const Trd_PlaceOrder::Response &stRsp);
	void OnReply_GetOrderList(Moomoo::u32_t nSerialNo, const Trd_GetOrderList::Response &stRsp);
	void OnPush_UpdateOrder(const Trd_UpdateOrder::Response &stRsp);
	void OnPush_UpdateOrderFill(const Trd_UpdateOrderFill::Response &stRsp);
};
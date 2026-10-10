#pragma once
#include "FTAPIDemoBase.h"
#include <atomic> 

class MACDStrategy: public FTAPIDemoBase
{
public:
	MACDStrategy();
	~MACDStrategy();

	void Run();

private:
	void SubKL();
	void GetKL();

	void GetPosistion();
	void GetMaxBuy();
	void PlaceOrder(Trd_Common::TrdSide enTrdSide);

private:
	int32_t m_nMaxCanSell;
	int32_t m_nMaxCanBuy;

	vector<double> m_vClose;
	int64_t m_nCloseMaxTimestamp;

	int32_t m_nLastTrdSide;

	atomic_int m_nTradeSign;//原子变量，同于简单的同步

protected:
	void OnReply_Sub(Moomoo::u32_t nSerialNo, const Qot_Sub::Response &stRsp);
	void OnReply_GetKL(Moomoo::u32_t nSerialNo, const Qot_GetKL::Response &stRsp);

	void OnReply_GetPositionList(Moomoo::u32_t nSerialNo, const Trd_GetPositionList::Response &stRsp);
	void OnReply_GetMaxTrdQtys(Moomoo::u32_t nSerialNo, const Trd_GetMaxTrdQtys::Response &stRsp);
	void OnReply_PlaceOrder(Moomoo::u32_t nSerialNo, const Trd_PlaceOrder::Response &stRsp);

	void OnPush_UpdateKL(const Qot_UpdateKL::Response &stRsp);
	void OnPush_UpdateOrder(const Trd_UpdateOrder::Response &stRsp);
	void OnPush_UpdateOrderFill(const Trd_UpdateOrderFill::Response &stRsp);
};
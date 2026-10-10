#pragma once
#include "FTAPIDemoBase.h"

class StockFilterDemo: public FTAPIDemoBase
{
public:
	StockFilterDemo();
	~StockFilterDemo();

	void Run();

private:
	void ParseStockFilterRes();

private:
	vector<Qot_StockFilter::S2C> m_vRes;

protected:
	void OnReply_StockFilter(Moomoo::u32_t nSerialNo, const Qot_StockFilter::Response &stRsp);
};
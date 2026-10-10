#include "MACDStrategy.h"

MACDStrategy::MACDStrategy()
{
	m_nMaxCanSell = -1;
	m_nMaxCanBuy = -1;
	m_nCloseMaxTimestamp = 0;
	m_nLastTrdSide = 0;

	m_nTradeSign = 0;
}

MACDStrategy::~MACDStrategy()
{
}

//EMA这类迭代指标（计算当前周期用到前周期的指标），理论上要从第一根K线开始算，所以与PC牛牛指标对比有误差
//计算的K线越多越误差越小，计算的K线足够多的情况下，误差可以忽略
static void EMA(const vector<double> &vInput, int32_t nN, vector<double> &vOutput)
{
	int32_t nCount = (int32_t)vInput.size();
	if (nCount > 0)
	{
		double fLastEMA = vInput[0];
		vOutput.push_back(fLastEMA);
		for (int32_t i = 1; i < nCount; ++i)
		{
			double fEMA = (vInput[i] * 2 + fLastEMA * (nN - 1)) / (nN + 1);
			vOutput.push_back(fEMA);
			fLastEMA = fEMA;
		}
	}
}

static void MACD(const vector<double> &vClose, int32_t nShort, int32_t nLong, int32_t nSmooth,
	vector<double> &vDIF, vector<double> &vDEA, vector<double> &vMACD)
{
	vDIF.clear();
	vDEA.clear();
	vMACD.clear();

	vector<double> vShort, vLong;
	EMA(vClose, nShort, vShort);
	EMA(vClose, nLong, vLong);
	int32_t nShortCount = (i32_t)vShort.size();
	int32_t nLongCount = (i32_t)vLong.size();
	for (int32_t i = 0; i < nShortCount && i < nLongCount; ++i)
	{
		vDIF.push_back(vShort[i] - vLong[i]);
	}

	EMA(vDIF, nSmooth, vDEA);
	int32_t nDIFCount = (i32_t)vDIF.size();
	int32_t nDEACount = (i32_t)vDEA.size();
	for (int32_t i = 0; i < nDIFCount && i < nDEACount; ++i)
	{
		vMACD.push_back((vDIF[i] - vDEA[i]) * 2);
	}
}

void MACDStrategy::Run()
{
	cout << "Run MACDStrategy" << endl;

	m_nMaxCanSell = -1;
	m_nMaxCanBuy = -1;
	m_vClose.clear();
	m_nCloseMaxTimestamp = 0;
	m_nLastTrdSide = 0;
	m_nTradeSign = 0;

	//创建行情连接
	InitQot("127.0.0.1", 11111);
	//创建交易连接，真实交易需要解锁，模拟交易不需要解锁
	InitTrd("127.0.0.1", 11111, "");

	if (m_pQotApi != nullptr && m_pTrdApi != nullptr)
	{
		//订阅实时K线推送行情
		SubKL();
		//拉取历史K线数据
		GetKL();
		//执行策略一分钟
		for (int32_t i = 0; i < 60; ++i)
		{
			CPSleep(1);		
			if (m_nTradeSign == Trd_Common::TrdSide_Sell)
			{
				m_nTradeSign = 0;
				//获取当前持仓
				GetPosistion();
				//清仓					
				PlaceOrder(Trd_Common::TrdSide_Sell);
			}
			else if (m_nTradeSign == Trd_Common::TrdSide_Buy)
			{
				m_nTradeSign = 0;
				//计算最大可买
				GetMaxBuy();
				//全仓买入
				PlaceOrder(Trd_Common::TrdSide_Buy);
			}		
		}
	}

	//关闭行情连接，连接不再使用之后，要关闭，否则占用不必要资源
	//同时OpenD也限制了最多128条连接
	UnInitQot();
	cout << "MACDStrategy End" << endl << endl;
}

void MACDStrategy::SubKL()
{
	if (m_pQotApi != nullptr)
	{
		Qot_Sub::Request pbSub;
		Qot_Sub::C2S *pSubC2S = pbSub.mutable_c2s();
		//repeated Qot_Common.Security securityList = 1;
		//需要订阅的股票
		Qot_Common::Security *pSec = pSubC2S->add_securitylist();
		pSec->set_market(Qot_Common::QotMarket_HK_Security);
		pSec->set_code("00700");
		//repeated int32 subTypeList = 2;
		//订阅数据类型
		pSubC2S->add_subtypelist(Qot_Common::SubType_KL_Day);
		//required bool isSubOrUnSub = 3;
		//ture表示订阅,false表示反订阅
		//订阅有额度限制，不需要的行情要反订阅，反订阅后就会返还额度
		pSubC2S->set_issuborunsub(true);
		//optional bool isRegOrUnRegPush = 4;
		//是否注册或反注册该连接上面行情的推送
		pSubC2S->set_isregorunregpush(true);
		WaitReply(m_pQotApi->Sub(pbSub));
		cout << "Sub KL push" << endl;
	}
}

void MACDStrategy::GetKL()
{
	if (m_pQotApi != nullptr)
	{
		Qot_GetKL::Request pbGetKL;
		Qot_GetKL::C2S *pGetKLC2S = pbGetKL.mutable_c2s();
		//required int32 rehabType = 1;
		//复权类型
		pGetKLC2S->set_rehabtype(Qot_Common::RehabType_Forward);
		//required int32 klType = 2;
		//K线类型
		pGetKLC2S->set_kltype(Qot_Common::KLType_Day);
		//required Qot_Common.Security security = 3;
		//股票
		Qot_Common::Security *pSec = pGetKLC2S->mutable_security();
		pSec->set_market(Qot_Common::QotMarket_HK_Security);
		pSec->set_code("00700");
		//required int32 reqNum = 4;
		//请求K线根数，有限制最多最近1000根
		pGetKLC2S->set_reqnum(1000);
		WaitReply(m_pQotApi->GetKL(pbGetKL));
	}
}

void MACDStrategy::GetPosistion()
{
	if (m_pTrdApi != nullptr)
	{
		uint64_t nAccID = GetFirstAccID(Trd_Common::TrdMarket_HK, Trd_Common::TrdEnv_Simulate);
		if (nAccID > 0)
		{
			Trd_GetPositionList::Request pbGetPositionList;
			Trd_GetPositionList::C2S *pGetPositionListC2S = pbGetPositionList.mutable_c2s();
			//required Trd_Common.TrdHeader header = 1;
			//交易公共参数头
			Trd_Common::TrdHeader *pTrdHeader = pGetPositionListC2S->mutable_header();
			pTrdHeader->set_trdenv(Trd_Common::TrdEnv_Simulate);
			pTrdHeader->set_accid(nAccID);
			pTrdHeader->set_trdmarket(Trd_Common::TrdMarket_HK);
			//optional Trd_Common.TrdFilterConditions filterConditions = 2;
			//过滤条件
			Trd_Common::TrdFilterConditions *pCond = pGetPositionListC2S->mutable_filterconditions();
			pCond->add_codelist("00700");
			//optional bool refreshCache = 5;
			pGetPositionListC2S->set_refreshcache(true);
			WaitReply(m_pTrdApi->GetPositionList(pbGetPositionList));
		}
	}
}

void MACDStrategy::GetMaxBuy()
{
	double fCurPrice = -1;
	int32_t nCloseCount = (i32_t)m_vClose.size();
	if (nCloseCount > 0)
	{
		fCurPrice = m_vClose[nCloseCount - 1];
	}

	if (m_pTrdApi != nullptr && fCurPrice > 0)
	{
		uint64_t nAccID = GetFirstAccID(Trd_Common::TrdMarket_HK, Trd_Common::TrdEnv_Simulate);
		if (nAccID > 0)
		{
			Trd_GetMaxTrdQtys::Request pbGetMaxTrdQtys;
			Trd_GetMaxTrdQtys::C2S *pGetMaxTrdQtys = pbGetMaxTrdQtys.mutable_c2s();
			//required Trd_Common.TrdHeader header = 1;
			//交易公共参数头
			Trd_Common::TrdHeader *pTrdHeader = pGetMaxTrdQtys->mutable_header();
			pTrdHeader->set_trdenv(Trd_Common::TrdEnv_Simulate);
			pTrdHeader->set_accid(nAccID);
			pTrdHeader->set_trdmarket(Trd_Common::TrdMarket_HK);
			//required int32 orderType = 2;
			//订单类型
			pGetMaxTrdQtys->set_ordertype(Trd_Common::OrderType_Normal);
			//required string code = 3;
			//代码
			pGetMaxTrdQtys->set_code("00700");
			//required double price = 4;
			//价格
			pGetMaxTrdQtys->set_price(fCurPrice);
			//optional int32 secMarket = 8; 
			//证券所属市场
			pGetMaxTrdQtys->set_secmarket(Trd_Common::TrdSecMarket_HK);
			WaitReply(m_pTrdApi->GetMaxTrdQtys(pbGetMaxTrdQtys));
		}
	}
}

void MACDStrategy::PlaceOrder(Trd_Common::TrdSide enTrdSide)
{
	double fCurPrice = -1;
	int32_t nCloseCount = (i32_t)m_vClose.size();
	if (nCloseCount > 0)
	{
		fCurPrice = m_vClose[nCloseCount - 1];
	}

	if (m_pTrdApi != nullptr && fCurPrice > 0)
	{		
		uint64_t nAccID = GetFirstAccID(Trd_Common::TrdMarket_HK, Trd_Common::TrdEnv_Simulate);
		if (nAccID != 0)
		{
			Trd_PlaceOrder::Request pbPlaceOrder;
			Trd_PlaceOrder::C2S *pPlaceOrderC2S = pbPlaceOrder.mutable_c2s();
			//required Common.PacketID packetID = 1;
			//这个字段在API内部会自动填写，用户不需要关心
			//required Trd_Common.TrdHeader header = 2;
			//交易公共参数头
			Trd_Common::TrdHeader *pTrdHeader = pPlaceOrderC2S->mutable_header();
			pTrdHeader->set_trdenv(Trd_Common::TrdEnv_Simulate);
			pTrdHeader->set_accid(nAccID);
			pTrdHeader->set_trdmarket(Trd_Common::TrdMarket_HK);
			//required int32 orderType = 4;
			//订单类型
			pPlaceOrderC2S->set_ordertype(Trd_Common::OrderType_Normal);
			//required string code = 5;
			//下单的股票代码
			pPlaceOrderC2S->set_code("00700");
			//optional double price = 7;
			//下单价格
			pPlaceOrderC2S->set_price(fCurPrice);
			//optional int32 secMarket = 10;
			//证券所属市场
			pPlaceOrderC2S->set_secmarket(Trd_Common::TrdSecMarket_HK);
			//optional string remark = 11;
			//用户备注字符串，最多只能传64字节。可用于标识订单唯一信息等，下单填上，订单结构就会带上
			pPlaceOrderC2S->set_remark("macd 00700");

			//required int32 trdSide = 3;
			//交易方向，下单只传买或卖，无持仓卖出表示卖空，负持仓买入表示买回
			pPlaceOrderC2S->set_trdside(enTrdSide);
			//required double qty = 6;
			//下单数量，要整手
			pPlaceOrderC2S->set_qty(enTrdSide == Trd_Common::TrdSide_Buy ? m_nMaxCanBuy : m_nMaxCanSell);

			m_nMaxCanBuy = -1;
			m_nMaxCanSell = -1;
			
			WaitReply(m_pTrdApi->PlaceOrder(pbPlaceOrder));
			cout << "PlaceOrder, HK.00700" << endl;
		}
	}
}

void MACDStrategy::OnReply_Sub(Moomoo::u32_t nSerialNo, const Qot_Sub::Response &stRsp)
{
	if (stRsp.rettype() != Common::RetType_Succeed)
	{
		PrintUTF8(stRsp.retmsg());
	}
	PostReply();
}

void MACDStrategy::OnReply_GetKL(Moomoo::u32_t nSerialNo, const Qot_GetKL::Response &stRsp)
{
	if (stRsp.rettype() == Common::RetType_Succeed)
	{
		//收集历史收盘价存到m_vClose
		const Qot_GetKL::S2C &pbS2C = stRsp.s2c();
		int32_t nKLCount = pbS2C.kllist_size();
		for (int32_t i = 0; i < nKLCount; ++i)
		{
			const Qot_Common::KLine &pbKL = pbS2C.kllist(i);
			//required bool isBlank = 2; 
			//是否是空内容的点,若为ture则只有时间信息
			if (!pbKL.isblank())
			{
				//optional double timestamp = 13; 
				//时间戳，数据按时间由远到近排序
				if (pbKL.has_timestamp())
				{
					//optional double closePrice = 6; 
					//收盘价
					if (pbKL.has_closeprice())
					{
						m_vClose.push_back(pbKL.closeprice());
						m_nCloseMaxTimestamp = (int64_t)pbKL.timestamp();
					}
				}
			}
		}
	}
	else
	{
		PrintUTF8(stRsp.retmsg());
	}
	PostReply();
}

void MACDStrategy::OnReply_GetPositionList(Moomoo::u32_t nSerialNo, const Trd_GetPositionList::Response &stRsp)
{
	if (stRsp.rettype() == Common::RetType_Succeed)
	{
		const Trd_GetPositionList::S2C &pbS2C = stRsp.s2c();
		int32_t nPositionSize = pbS2C.positionlist_size();
		if (nPositionSize > 0)
		{
			//repeated Trd_Common.Position positionList = 2;
			//持仓列表，设置了筛选条件，所以最多只会返回一个
			const Trd_Common::Position &pbPosition = pbS2C.positionlist(0);
			//required double canSellQty = 6;
			//可卖数量
			m_nMaxCanSell = (int32_t)pbPosition.cansellqty();
		}
	}
	else
	{
		PrintUTF8(stRsp.retmsg());
	}
	PostReply();
}

void MACDStrategy::OnReply_GetMaxTrdQtys(Moomoo::u32_t nSerialNo, const Trd_GetMaxTrdQtys::Response &stRsp)
{
	if (stRsp.rettype() == Common::RetType_Succeed)
	{
		const Trd_GetMaxTrdQtys::S2C &pbS2C = stRsp.s2c();
		if (pbS2C.has_maxtrdqtys())
		{
			const Trd_Common::MaxTrdQtys &pbMaxTrdQtys = pbS2C.maxtrdqtys();
			m_nMaxCanBuy = (int32_t)pbMaxTrdQtys.maxcashbuy();
		}
	}
	else
	{
		PrintUTF8(stRsp.retmsg());
	}
	PostReply();
}

void MACDStrategy::OnReply_PlaceOrder(Moomoo::u32_t nSerialNo, const Trd_PlaceOrder::Response &stRsp)
{
	if (stRsp.rettype() != Common::RetType_Succeed)
	{
		PrintUTF8(stRsp.retmsg());
	}
	PostReply();
}

void MACDStrategy::OnPush_UpdateKL(const Qot_UpdateKL::Response &stRsp)
{
	if (!m_vClose.empty())
	{
		//更新最后一根收盘价
		const Qot_UpdateKL::S2C &pbS2C = stRsp.s2c();
		int32_t nKLCount = pbS2C.kllist_size();
		for (int32_t i = 0; i < nKLCount; ++i)
		{
			const Qot_Common::KLine &pbKL = pbS2C.kllist(i);
			//required bool isBlank = 2; 
			//是否是空内容的点,若为ture则只有时间信息
			if (!pbKL.isblank())
			{
				int64_t nTimestamp = 0;
				//optional double timestamp = 13; 
				if (pbKL.has_timestamp())
				{
					nTimestamp = (int64_t)pbKL.timestamp();
					//optional double closePrice = 6; 
					//收盘价
					if (pbKL.has_closeprice())
					{
						double fClose = pbKL.closeprice();
						int32_t nCloseCount = (i32_t)m_vClose.size();
						if (m_nCloseMaxTimestamp == nTimestamp)
						{
							m_vClose[nCloseCount - 1] = fClose;
						}
						else if (nTimestamp > m_nCloseMaxTimestamp)
						{
							m_nCloseMaxTimestamp = nTimestamp;
							m_vClose.push_back(fClose);
						}
					}
				}				
			}
		}

		//计算MACD
		vector<double> vDIF, vDEA, vMACD;
		MACD(m_vClose, 12, 26, 9, vDIF, vDEA, vMACD);
		int32_t nDIFCount = (i32_t)vDIF.size();
		int32_t nDEACount = (i32_t)vDEA.size();
		if (nDIFCount > 0 && nDEACount > 0)
		{
			cout << "MACD = (" << vDIF[nDIFCount - 1] << ", " << vDEA[nDEACount - 1] << ", " << vMACD[vMACD.size() - 1] << ")" << endl;
			if (vDIF[nDIFCount - 1] < vDEA[nDEACount - 1] && vDIF[nDIFCount - 2] > vDEA[nDEACount - 2])
			{
				//触发卖出操作
				cout << "sell triger" << endl;
				if (m_nLastTrdSide != Trd_Common::TrdSide_Sell)
				{
					m_nLastTrdSide = Trd_Common::TrdSide_Sell;
					m_nTradeSign = Trd_Common::TrdSide_Sell;
				}
			}
			else if (vDIF[nDIFCount - 1] > vDEA[nDEACount - 1] && vDIF[nDIFCount - 2] < vDEA[nDEACount - 2])
			{
				//触发买入操作
				cout << "buy triger" << endl;
				if (m_nLastTrdSide != Trd_Common::TrdSide_Buy)
				{
					m_nLastTrdSide = Trd_Common::TrdSide_Buy;
					m_nTradeSign = Trd_Common::TrdSide_Buy;
				}	
			}
		}	
	}
}

void MACDStrategy::OnPush_UpdateOrder(const Trd_UpdateOrder::Response &stRsp)
{
	const Trd_UpdateOrder::S2C &pbS2C = stRsp.s2c();
	const Trd_Common::Order &pbOrder = pbS2C.order();

	//required int32 orderStatus = 3;
	//订单状态
	Trd_Common::OrderStatus enOrderStatus = (Trd_Common::OrderStatus)pbOrder.orderstatus();

	//required string updateTime = 11;
	//订单更新时间
	string strUpdateTime = pbOrder.updatetime();

	//optional double fillQty = 12;
	//成交数量
	double fFillQty = pbOrder.fillqty();

	cout << "OnPush_UpdateOrder, status = " << enOrderStatus << endl;
}

void MACDStrategy::OnPush_UpdateOrderFill(const Trd_UpdateOrderFill::Response &stRsp)
{
	const Trd_UpdateOrderFill::S2C &pbS2C = stRsp.s2c();
	const Trd_Common::OrderFill &pbOrderFill = pbS2C.orderfill();

	//required uint64 fillID = 2;
	//成交ID
	uint64_t nOrderFillID = pbOrderFill.fillid();

	//required double qty = 8;
	//成交数量
	double fQty = pbOrderFill.qty();

	//required double price = 9;
	//成交价格
	double fPrice = pbOrderFill.price();

	//optional int32 status = 16;
	//成交状态
	Trd_Common::OrderFillStatus enOrderFillStatus = (Trd_Common::OrderFillStatus)pbOrderFill.status();
}
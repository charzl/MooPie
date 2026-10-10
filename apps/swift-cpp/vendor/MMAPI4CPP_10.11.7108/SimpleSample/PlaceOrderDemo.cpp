#include "PlaceOrderDemo.h"

PlaceOrderDemo::PlaceOrderDemo()
{
	m_nTCHLotSize = -1;
	m_fSellPrice = -1.0;
}

PlaceOrderDemo::~PlaceOrderDemo()
{
}

void PlaceOrderDemo::Run()
{
	cout << "Run PlaceOrderDemo" << endl;

	//创建行情连接
	InitQot("127.0.0.1", 11111);
	//创建交易连接，真实交易需要解锁，模拟交易不需要解锁
	InitTrd("127.0.0.1", 11111, "");

	if (m_pQotApi != nullptr && m_pTrdApi != nullptr)
	{
		GetLotSize();	
		GetSellPrice();
		PlaceOrder();
		GetOrderList();
		CPSleep(20);
		//在异步推送里关注订单成交变化
		//OnPush_UpdateOrder
		//OnPush_UpdateOrderFill
	}

	//关闭行情交易连接，连接不再使用之后，要关闭，否则占用不必要资源
	//同时OpenD也限制了最多128条连接
	UnInitQot();
	UnInitTrd();

	cout << "PlaceOrderDemo End" << endl << endl;
}

void PlaceOrderDemo::GetLotSize()
{
	if (m_pQotApi != nullptr)
	{
		//先用GetStaticInfo协议获取到腾讯控股每手股数，存到m_nTCHLotSize
		Qot_GetStaticInfo::Request pbGetStaticInfo;
		Qot_GetStaticInfo::C2S *pGetStaticInfoC2S = pbGetStaticInfo.mutable_c2s();
		//repeated Qot_Common.Security securityList = 3; 
		//股票，若该字段存在，忽略其他字段，只返回该字段股票的静态信息
		Qot_Common::Security *pSec = pGetStaticInfoC2S->add_securitylist();
		pSec->set_market(Qot_Common::QotMarket_HK_Security);
		pSec->set_code("00700");
		WaitReply(m_pQotApi->GetStaticInfo(pbGetStaticInfo));
		cout << "GetLotSize, HK.00700 lotSize = " << m_nTCHLotSize << endl;
	}
}

void PlaceOrderDemo::GetSellPrice()
{
	if (m_pQotApi != nullptr)
	{
		//获取卖一价
		//GetSecuritySnapshot协议也能拿到，更简单，可参考GetSecuritySnapshotDemo
		//这里使用订阅接口来演示获取
		//订阅接口好处在于可以当摆盘变化，OpenD会通过UpdateOrderBook来通知，而不需要定时去拉取，更及时且节省资源
		Qot_Sub::Request pbSub;
		Qot_Sub::C2S *pSubC2S = pbSub.mutable_c2s();
		//repeated Qot_Common.Security securityList = 1;
		//需要订阅的股票
		Qot_Common::Security *pSubSec = pSubC2S->add_securitylist();
		pSubSec->set_market(Qot_Common::QotMarket_HK_Security);
		pSubSec->set_code("00700");
		//repeated int32 subTypeList = 2;
		//订阅数据类型
		pSubC2S->add_subtypelist(Qot_Common::SubType_OrderBook);
		//required bool isSubOrUnSub = 3;
		//ture表示订阅,false表示反订阅
		//订阅有额度限制，不需要的行情要反订阅，反订阅后就会返还额度
		pSubC2S->set_issuborunsub(true);
		//optional bool isRegOrUnRegPush = 4;
		//是否注册或反注册该连接上面行情的推送
		//目前不需要推送，
		pSubC2S->set_isregorunregpush(false);
		WaitReply(m_pQotApi->Sub(pbSub));

		//等待一会，等后台把摆盘数据推送下来
		CPSleep(1);

		//请求摆盘数据
		Qot_GetOrderBook::Request pbGetOrderBook;
		Qot_GetOrderBook::C2S *pGetOrderBookC2S = pbGetOrderBook.mutable_c2s();
		//required Qot_Common.Security security = 1;
		//需要获取摆盘的股票
		Qot_Common::Security *pGetOrderBookSec = pGetOrderBookC2S->mutable_security();
		pGetOrderBookSec->set_market(Qot_Common::QotMarket_HK_Security);
		pGetOrderBookSec->set_code("00700");
		//required int32 num = 2;
		//请求的摆盘档数
		pGetOrderBookC2S->set_num(1);
		WaitReply(m_pQotApi->GetOrderBook(pbGetOrderBook));
		cout << "GetSellPrice, HK.00700 sellPrice = " << m_fSellPrice << endl;
	}
}

void PlaceOrderDemo::PlaceOrder()
{
	if (m_fSellPrice > 0.0 && m_nTCHLotSize > 0 && m_pTrdApi != nullptr)
	{
		uint64_t nAccID = GetFirstAccID(Trd_Common::TrdMarket_HK, Trd_Common::TrdEnv_Simulate);
		if (nAccID != 0)
		{
			//拿到股票每手股数和当前卖价就可以去下单
			//这里我们演示在模拟环境下单
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
			//required int32 trdSide = 3;
			//交易方向，下单只传买或卖，无持仓卖出表示卖空，负持仓买入表示买回
			pPlaceOrderC2S->set_trdside(Trd_Common::TrdSide_Buy);
			//required int32 orderType = 4;
			//订单类型
			pPlaceOrderC2S->set_ordertype(Trd_Common::OrderType_Normal);
			//required string code = 5;
			//下单的股票代码
			pPlaceOrderC2S->set_code("00700");
			//required double qty = 6;
			//下单数量，要整手
			pPlaceOrderC2S->set_qty(m_nTCHLotSize);
			//optional double price = 7;
			//下单价格，以当前卖一价上涨5%的价格买入
			pPlaceOrderC2S->set_price(m_fSellPrice * 1.05);
			//optional bool adjustPrice = 8;
			//是否调整价格，如果价格不合法，是否调整到合法价位，true调整，false不调整
			pPlaceOrderC2S->set_adjustprice(true);
			//optional double adjustSideAndLimit = 9;
			pPlaceOrderC2S->set_adjustsideandlimit(0.05);
			//optional int32 secMarket = 10;
			//证券所属市场
			pPlaceOrderC2S->set_secmarket(Trd_Common::TrdSecMarket_HK);
			//optional string remark = 11;
			//用户备注字符串，最多只能传64字节。可用于标识订单唯一信息等，下单填上，订单结构就会带上
			pPlaceOrderC2S->set_remark("buy00700");
			WaitReply(m_pTrdApi->PlaceOrder(pbPlaceOrder));
			cout << "PlaceOrder, HK.00700, orderID = " << m_nOrderID << endl;
		}
	}
}

void PlaceOrderDemo::GetOrderList()
{
	if (m_nOrderID > 0 && m_pTrdApi != nullptr)
	{
		uint64_t nAccID = GetFirstAccID(Trd_Common::TrdMarket_HK, Trd_Common::TrdEnv_Simulate);
		//查询当日订单信息
		Trd_GetOrderList::Request pbGetOrderList;
		Trd_GetOrderList::C2S *pGetOrderListC2S = pbGetOrderList.mutable_c2s();
		//required Trd_Common.TrdHeader header = 1;
		Trd_Common::TrdHeader *pTrdHeader = pGetOrderListC2S->mutable_header();
		pTrdHeader->set_trdenv(Trd_Common::TrdEnv_Simulate);
		pTrdHeader->set_accid(nAccID);
		pTrdHeader->set_trdmarket(Trd_Common::TrdMarket_HK);
		//optional Trd_Common.TrdFilterConditions filterConditions = 2; 
		//过滤条件
		Trd_Common::TrdFilterConditions *pCond = pGetOrderListC2S->mutable_filterconditions();
		pCond->add_codelist("00700");
		pCond->add_idlist(m_nOrderID);
		//optional bool refreshCache = 4;
		pGetOrderListC2S->set_refreshcache(true);
		//在OnReply_GetOrderList回调中观察订单数据
		WaitReply(m_pTrdApi->GetOrderList(pbGetOrderList));
	}
}

void PlaceOrderDemo::OnReply_GetStaticInfo(Moomoo::u32_t nSerialNo, const Qot_GetStaticInfo::Response &stRsp)
{
	//判断协议成功或失败
	if (stRsp.rettype() == Common::RetType_Succeed)
	{
		//协议解包，将腾讯控股每手股数存到m_nTCHLotSize
		const Qot_GetStaticInfo::S2C &pbS2C = stRsp.s2c();
		if (pbS2C.staticinfolist_size() == 1)
		{
			const Qot_Common::SecurityStaticInfo &pbSecStaticInfo = pbS2C.staticinfolist(0);
			m_nTCHLotSize = pbSecStaticInfo.basic().lotsize();
		}
	}
	else
	{
		PrintUTF8(stRsp.retmsg());
	}
	PostReply();
}

void PlaceOrderDemo::OnReply_Sub(Moomoo::u32_t nSerialNo, const Qot_Sub::Response &stRsp)
{
	if (stRsp.rettype() != Common::RetType_Succeed)
	{
		PrintUTF8(stRsp.retmsg());
	}
	PostReply();
}

void PlaceOrderDemo::OnReply_GetOrderBook(Moomoo::u32_t nSerialNo, const Qot_GetOrderBook::Response &stRsp)
{
	//判断协议成功或失败
	if (stRsp.rettype() == Common::RetType_Succeed)
	{
		//协议解包，将腾讯控股当前买一价存到m_fBuyPrice
		const Qot_GetOrderBook::S2C &pbS2C = stRsp.s2c();
		if (pbS2C.orderbookbidlist_size() > 0)
		{
			m_fSellPrice = pbS2C.orderbookbidlist(0).price();
		}
	}
	else
	{
		PrintUTF8(stRsp.retmsg());
	}
	PostReply();
}

void PlaceOrderDemo::OnReply_PlaceOrder(Moomoo::u32_t nSerialNo, const Trd_PlaceOrder::Response &stRsp)
{
	//判断协议成功或失败
	if (stRsp.rettype() == Common::RetType_Succeed)
	{
		//协议解包，将订单ID存到m_nOrderID
		const Trd_PlaceOrder::S2C &pbS2C = stRsp.s2c();
		m_nOrderID = pbS2C.orderid();
	}
	else
	{
		PrintUTF8(stRsp.retmsg());
	}
	PostReply();
}

void PlaceOrderDemo::OnReply_GetOrderList(Moomoo::u32_t nSerialNo, const Trd_GetOrderList::Response &stRsp)
{
	//判断协议成功或失败
	if (stRsp.rettype() == Common::RetType_Succeed)
	{
		const Trd_GetOrderList::S2C &pbS2C = stRsp.s2c();
		if (pbS2C.orderlist_size() > 0)
		{
			const Trd_Common::Order &pbOrder = pbS2C.orderlist(0);

			//required int32 orderStatus = 3;
			//订单状态
			Trd_Common::OrderStatus enOrderStatus = (Trd_Common::OrderStatus)pbOrder.orderstatus();

			//required string updateTime = 11;
			//订单更新时间
			string strUpdateTime = pbOrder.updatetime();

			//optional double fillQty = 12;
			//成交数量
			double fFillQty = pbOrder.fillqty();
		}
	}
	else
	{
		PrintUTF8(stRsp.retmsg());
	}
	PostReply();
}


void PlaceOrderDemo::OnPush_UpdateOrder(const Trd_UpdateOrder::Response &stRsp)
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

void PlaceOrderDemo::OnPush_UpdateOrderFill(const Trd_UpdateOrderFill::Response &stRsp)
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

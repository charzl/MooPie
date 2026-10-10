#include "QuotePushDemo.h"

QuotePushDemo::QuotePushDemo()
{
	bSubSuc = false;
}

QuotePushDemo::~QuotePushDemo()
{
}

void QuotePushDemo::Run()
{
	cout << "Run QuotePushDemo" << endl;

	bSubSuc = false;
	//创建行情连接
	InitQot("127.0.0.1", 11111);

	if (m_pQotApi)
	{
		//订阅一批港股的基础报价，摆盘，经纪队列，逐笔，日K，分时的实时推送数据
		//盘中运行会有持续的推送，非盘中时段运行只有一条最近的数据推送
		const int32_t nCodeCount = 3;
		string strCodes[nCodeCount] = { "00700", "00001", "00002" };
		const int32_t nSubTypeCount = 6;
		Qot_Common::SubType enSubTypes[nSubTypeCount] = { Qot_Common::SubType_Basic, Qot_Common::SubType_OrderBook,
			Qot_Common::SubType_Broker, Qot_Common::SubType_Ticker, Qot_Common::SubType_KL_Day, Qot_Common::SubType_RT};

		Qot_Sub::Request pbSub;
		Qot_Sub::C2S *pSubC2S = pbSub.mutable_c2s();
		//repeated Qot_Common.Security securityList = 1;
		//需要订阅的股票		
		for (int32_t i = 0; i < nCodeCount; ++i)
		{
			Qot_Common::Security *pSubSec = pSubC2S->add_securitylist();
			pSubSec->set_code(strCodes[i]);
			pSubSec->set_market(Qot_Common::QotMarket_HK_Security);
		}
		//repeated int32 subTypeList = 2;
		//需要订阅的数据类型
		for (int32_t i = 0; i < nSubTypeCount; ++i)
		{
			pSubC2S->add_subtypelist(enSubTypes[i]);
		}
		//required bool isSubOrUnSub = 3;
		//ture表示订阅,false表示反订阅
		//订阅有额度限制，不需要的行情要反订阅，反订阅后就会返还额度
		pSubC2S->set_issuborunsub(true);
		//optional bool isRegOrUnRegPush = 4;
		//是否注册或反注册该连接上面行情的推送
		//接收推送
		pSubC2S->set_isregorunregpush(true);
		cout << "Sub" << endl;
		WaitReply(m_pQotApi->Sub(pbSub));

		if (bSubSuc)
		{
			//请在OnPush_UpdateXXX回调里面观察数据
			CPSleep(60);

			//反订阅
			pSubC2S = pbSub.mutable_c2s();
			pSubC2S->set_issuborunsub(false);
			pSubC2S->set_isregorunregpush(false);
			WaitReply(m_pQotApi->Sub(pbSub));
		}
		else
		{
			PrintError("Sub failed");
		}
	}

	//关闭行情连接，连接不再使用之后，要关闭，否则占用不必要资源
	//同时OpenD也限制了最多128条连接
	UnInitQot();

	cout << "QuotePushDemo End" << endl << endl;
}

void QuotePushDemo::OnReply_Sub(Moomoo::u32_t nSerialNo, const Qot_Sub::Response &stRsp)
{
	if (stRsp.rettype() == Common::RetType_Succeed)
	{
		bSubSuc = true;
	}
	else
	{
		bSubSuc = false;
		PrintUTF8(stRsp.retmsg());
	}
	PostReply();
}

void QuotePushDemo::OnPush_UpdateBasicQot(const Qot_UpdateBasicQot::Response &stRsp)
{
	const Qot_UpdateBasicQot::S2C &pbS2C = stRsp.s2c();
	//repeated Qot_Common.BasicQot basicQotList = 1;
	//股票基本行情，这个字段虽然是repeated字段，但是在推送里面只会有一个数据
	if (pbS2C.basicqotlist_size() > 0)
	{
		const Qot_Common::BasicQot &pbBasicQot = pbS2C.basicqotlist(0);
		//required Qot_Common.Security security = 1;
		const Qot_Common::Security &pbSec = pbBasicQot.security();
		//股票Code
		string strCode = pbSec.code();
		//required double highPrice = 6;
		//最高价
		double fHighPrice = pbBasicQot.highprice();

		//required double openPrice = 7;
		//开盘价
		double fOpenPrice = pbBasicQot.openprice();

		//required double lowPrice = 8;
		//最低价
		double fLowPrice = pbBasicQot.lowprice();

		//required double curPrice = 9;
		//最新价
		double fCurPrice = pbBasicQot.curprice();

		//optional int32 secStatus = 21;
		//股票状态
		if (pbBasicQot.has_secstatus())
		{
			Qot_Common::SecurityStatus enStatus = (Qot_Common::SecurityStatus)pbBasicQot.secstatus();
		}

		//......
		cout << "OnPush_UpdateBasicQot, (" << strCode << ", " << fCurPrice << ")" << endl;
	}
}

void QuotePushDemo::OnPush_UpdateOrderBook(const Qot_UpdateOrderBook::Response &stRsp)
{
	const Qot_UpdateOrderBook::S2C &pbS2C = stRsp.s2c();
	
	//required Qot_Common.Security security = 1;
	const Qot_Common::Security &pbSec = pbS2C.security();
	//股票Code
	string strCode = pbSec.code();

	//repeated Qot_Common.OrderBook orderBookAskList = 2;
	//卖盘
	int32_t nAskCount = pbS2C.orderbookasklist_size();
	for (int32_t i = 0; i < nAskCount; ++i)
	{
		const Qot_Common::OrderBook &pbOrderBook = pbS2C.orderbookasklist(i);
		//required double price = 1;
		//摆盘价格
		double fPrice = pbOrderBook.price();

		//optional double hpVolume = 5;
		//摆盘数量（高精度）
		double fVolume = 0.0;
		if (pbOrderBook.has_hpvolume())
		{
			fVolume = pbOrderBook.hpvolume();
		}

		//required int32 orederCount = 3;
		//摆盘订单个数
		int32_t nOrderCount = pbOrderBook.oredercount();

		if (i == 0)
		{
			cout << "OnPush_UpdateOrderBook, (" << strCode << ", " << fPrice << ", " << fVolume << ")" << endl;
		}
	}
}

void QuotePushDemo::OnPush_UpdateBroker(const Qot_UpdateBroker::Response &stRsp)
{
	const Qot_UpdateBroker::S2C &pbS2C = stRsp.s2c();
	
	//required Qot_Common.Security security = 1;
	const Qot_Common::Security &pbSec = pbS2C.security();
	//股票Code
	string strCode = pbSec.code();

	//repeated Qot_Common.Broker brokerAskList = 2;
	//卖盘经纪队列
	int32_t nAskCount = pbS2C.brokerasklist_size();
	for (int32_t i = 0; i < nAskCount; ++i)
	{
		const Qot_Common::Broker &pbBroker = pbS2C.brokerasklist(i);
		//required int64 id = 1; 
		//经纪ID
		int64_t nID = pbBroker.id();

		//required string name = 2; 
		//经纪名称
		string strName = pbBroker.name();

		//required int32 pos = 3; 
		//经纪档位
		int32_t nPos = pbBroker.pos();

		if (i == 0)
		{
			cout << "OnPush_UpdateBroker, (" << strCode << ", " << nID << ", " << nPos << ")" << endl;
		}
	}
}

void QuotePushDemo::OnPush_UpdateTicker(const Qot_UpdateTicker::Response &stRsp)
{
	const Qot_UpdateTicker::S2C &pbS2C = stRsp.s2c();
	
	//required Qot_Common.Security security = 1;
	const Qot_Common::Security &pbSec = pbS2C.security();
	//股票Code
	string strCode = pbSec.code();

	//一个逐笔推送包可能会包含该只股票多条成交记录
	int32_t nTickerCount = pbS2C.tickerlist_size();
	for (int32_t i = 0; i < nTickerCount; ++i)
	{
		const Qot_Common::Ticker &pbTicker = pbS2C.tickerlist(i);
		//required string time = 1;
		//时间字符串，按股票交易所时区转换得到
		string strTime = pbTicker.time();

		//required int64 sequence = 2; 
		//唯一标识，保持递增
		int64_t nSequence = pbTicker.sequence();

		//required int32 dir = 3;
		//成交方向
		Qot_Common::TickerDirection enDir = (Qot_Common::TickerDirection)pbTicker.dir();

		//required double price = 4;
		//成交价格
		double fPrice = pbTicker.price();

		//optional int32 type = 8;
		//逐笔类型
		if (pbTicker.has_type())
		{
			Qot_Common::TickerType enType = (Qot_Common::TickerType)pbTicker.type();
		}

		cout << "OnPush_UpdateTicker, (" << strCode << ", " << fPrice << ", " << enDir << ")" << endl;
	}
}

void QuotePushDemo::OnPush_UpdateKL(const Qot_UpdateKL::Response &stRsp)
{
	const Qot_UpdateKL::S2C &pbS2C = stRsp.s2c();

	//required int32 rehabType = 1;
	Qot_Common::RehabType enRehabType = (Qot_Common::RehabType)pbS2C.rehabtype();

	//required int32 klType = 2; 
	Qot_Common::KLType enKLType = (Qot_Common::KLType)pbS2C.kltype();

	//required Qot_Common.Security security = 3;
	const Qot_Common::Security &pbSec = pbS2C.security();
	//股票Code
	string strCode = pbSec.code();

	//一个K线推送包可能会包含该只股票多条K线数据，一般就一条
	int32_t nKLCount = pbS2C.kllist_size();
	for (int32_t i = 0; i < nKLCount; ++i)
	{
		const Qot_Common::KLine &pbKL = pbS2C.kllist(i);

		//required string time = 1; 
		//时间字符串，按股票交易所时区转换得到
		string strTime = pbKL.time();

		//required bool isBlank = 2; 
		//是否是空内容的点,若为ture则只有时间信息
		bool isBlank = pbKL.isblank();

		if (!isBlank)
		{
			double fHighPrice = 0.0, fOpenPrice = 0.0, fLowPrice = 0.0, fClosePrice = 0.0;
			//optional double highPrice = 3; 
			//最高价
			if (pbKL.has_highprice())
			{
				fHighPrice = pbKL.highprice();
			}

			//optional double openPrice = 4; 
			//开盘价
			if (pbKL.has_openprice())
			{
				fOpenPrice = pbKL.openprice();
			}

			//optional double lowPrice = 5; 
			//最低价
			if (pbKL.has_lowprice())
			{
				fLowPrice = pbKL.lowprice();
			}

			//optional double closePrice = 6; 
			//收盘价
			
			if (pbKL.has_closeprice())
			{
				fClosePrice = pbKL.closeprice();
			}

			cout << "OnPush_UpdateKL, (" << strCode << ", " << fHighPrice << ", " << fOpenPrice << ", " << fLowPrice << ", " << fClosePrice << ")" << endl;
		}
	}
}

void QuotePushDemo::OnPush_UpdateRT(const Qot_UpdateRT::Response &stRsp)
{
	const Qot_UpdateRT::S2C &pbS2C = stRsp.s2c();
	//required Qot_Common.Security security = 1;
	const Qot_Common::Security &pbSec = pbS2C.security();
	//股票Code
	string strCode = pbSec.code();

	//一个分时推送包可能会包含该只股票多条分时数据，一般就一条
	i32_t nRTDataCount = pbS2C.rtlist_size();
	for (int32_t i = 0; i < nRTDataCount; ++i)
	{
		const Qot_Common::TimeShare &pbRT = pbS2C.rtlist(i);

		//required string time = 1; 
		//时间字符串，按股票交易所时区转换得到
		string strTime = pbRT.time();

		//required int32 minute = 2; 
		//距离0点过了多少分钟
		int32_t nMin = pbRT.minute();

		//required bool isBlank = 3; 
		//是否是空内容的点,若为ture则只有时间信息
		bool isBlank = pbRT.isblank();

		if (!isBlank)
		{
			//optional double price = 4; 
			//当前价
			double fPrice = 0.0, fLastClosePrice = 0.0, fAvgPrice = 0.0;
			if (pbRT.has_price())
			{
				fPrice = pbRT.price();
			}

			//optional double lastClosePrice = 5; 
			//昨收价
			if (pbRT.has_lastcloseprice())
			{
				fLastClosePrice = pbRT.lastcloseprice();
			}

			//optional double avgPrice = 6; 
			//均价
			if (pbRT.has_avgprice())
			{
				fAvgPrice = pbRT.avgprice();
			}
			cout << "OnPush_UpdateRT, (" << strCode << ", " << fPrice << ", " << fLastClosePrice << ", " << fAvgPrice << ")" << endl;
		}
	}
}


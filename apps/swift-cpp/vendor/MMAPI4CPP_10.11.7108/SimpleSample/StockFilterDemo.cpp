#include "StockFilterDemo.h"

StockFilterDemo::StockFilterDemo()
{
}

StockFilterDemo::~StockFilterDemo()
{
}

void StockFilterDemo::Run()
{
	cout << "Run StockFilterDemo" << endl;

	//创建行情连接
	InitQot("127.0.0.1", 11111);

	m_vRes.clear();

	if (m_pQotApi != nullptr)
	{
		//筛选当前价在[1, 50]区间的港股，并指定按照当前价升序排序返回，将数据存到m_pbRes
		Qot_StockFilter::Request pbStockFilter;
		Qot_StockFilter::C2S *pC2S = pbStockFilter.mutable_c2s();
		//required int32 begin = 1;
		//数据的请求起点，例如筛选后的股票有600，每次最大200支，需要请求3次，则begin则可以分别填0, 200, 400 
		pC2S->set_begin(0);
		//required int32 num =  2;
		//请求数据个数，最大200		
		pC2S->set_num(200);
		//required int32 market= 3;
		//股票市场，支持沪股和深股，且沪股和深股不做区分都代表A股市场
		pC2S->set_market(Qot_Common::QotMarket_HK_Security);

		//repeated BaseFilter baseFilterList = 5;
		//简单属性过滤器
		Qot_StockFilter::BaseFilter *pBaseFilter = pC2S->add_basefilterlist();	
		//required int32 fieldName = 1;
		//StockField 指定筛选哪个简单属性
		pBaseFilter->set_fieldname(Qot_StockFilter::StockField_CurPrice);
		//optional double filterMin = 2;
		//区间下限（闭区间），不传代表下限为-∞
		pBaseFilter->set_filtermin(1.0);
		//optional double filterMax = 3;
		//区间上限（闭区间），不传代表上限为+∞
		pBaseFilter->set_filtermax(50.0);
		//optional bool isNoFilter = 4;
		//false表示筛选且返回数据，true表示只返回数据但是不筛选
		pBaseFilter->set_isnofilter(false);
		//optional int32 sortDir = 5;
		//排序方向
		pBaseFilter->set_sortdir(Qot_StockFilter::SortDir_Ascend);
		//其他筛选器同理
		cout << "StockFilter, HK curPrice in [1, 50]" << endl;
		WaitReply(m_pQotApi->StockFilter(pbStockFilter));

		//得到第一个回包后，根据回包里面的总个数来循环请求
		if (!m_vRes.empty())
		{
			const Qot_StockFilter::S2C &pbS2C = m_vRes[0];
			//required int32 allCount = 2;
			int32_t nAllCount = pbS2C.allcount();
			//每批请求股票个数
			const int32_t nEachReqSecCount = 200;
			//计算总共需要请求多少次i
			int32_t nReqCount = (nAllCount + nEachReqSecCount - 1) / nEachReqSecCount;
			//循环请求，第一页已经拿到了，从1开始
			for (int32_t i = 1; i < nReqCount; ++i)
			{
				Qot_StockFilter::C2S *pC2S = pbStockFilter.mutable_c2s();
				pC2S->set_begin(i * nEachReqSecCount);
				WaitReply(m_pQotApi->StockFilter(pbStockFilter));
				//控制请求频率，3秒一次
				CPSleep(3);
			}
		}
	}
	//关闭行情连接，连接不再使用之后，要关闭，否则占用不必要资源
	//同时OpenD也限制了最多128条连接
	UnInitQot();

	ParseStockFilterRes();

	//清理数据
	m_vRes.clear();

	cout << "StockFilterDemo End" << endl << endl;
}

void StockFilterDemo::ParseStockFilterRes()
{
	//数据保存或展示
	//用户可以在这里打断点观察数据，或者将数据输出到文件、控制台等
	if (!m_vRes.empty())
	{
		const Qot_StockFilter::S2C &pbS2C = m_vRes[0];
		if (pbS2C.datalist_size() > 0)
		{
			const Qot_StockFilter::StockData &pbData = pbS2C.datalist(0);
			//required Qot_Common.Security security = 1;
			const Qot_Common::Security &pbSec = pbData.security();
			//股票市场
			Qot_Common::QotMarket enMarket = (Qot_Common::QotMarket)pbSec.market();
			//股票代码
			string strCode = pbSec.code();

			double fCurPrice = 0;
			if (pbData.basedatalist_size() > 0)
			{
				const Qot_StockFilter::BaseData &pbBaseData = pbData.basedatalist(0);
				//required int32 fieldName = 1;
				if (pbBaseData.fieldname() == Qot_StockFilter::StockField_CurPrice)
				{
					//required double value = 2;
					fCurPrice = pbBaseData.value();
				}
			}
			cout << "ParseStockFilterRes, first = (HK." << strCode << ", " << fCurPrice << ")" << endl;
		}	
	}
}

void StockFilterDemo::OnReply_StockFilter(Moomoo::u32_t nSerialNo, const Qot_StockFilter::Response &stRsp)
{
	//判断协议成功或失败
	if (stRsp.rettype() == Common::RetType_Succeed)
	{
		m_vRes.push_back(stRsp.s2c());
	}
	else
	{
		PrintUTF8(stRsp.retmsg());
	}
	PostReply();
}

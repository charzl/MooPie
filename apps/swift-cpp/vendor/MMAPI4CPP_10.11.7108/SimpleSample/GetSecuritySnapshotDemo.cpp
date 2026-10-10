#include "GetSecuritySnapshotDemo.h"

GetSecuritySnapshotDemo::GetSecuritySnapshotDemo()
{
}

GetSecuritySnapshotDemo::~GetSecuritySnapshotDemo()
{
}

void GetSecuritySnapshotDemo::Run()
{
	cout << "Run GetSecuritySnapshotDemo" << endl;

	//创建行情连接
	InitQot("127.0.0.1", 11111);

	m_vHKEqtySecList.clear();
	m_vHKEqtySecQot.clear();

	if (m_pQotApi != nullptr)
	{
		GetHKEqtySecList();
		GetHKEqtySecQot();
	}
	//关闭行情连接，连接不再使用之后，要关闭，否则占用不必要资源
	//同时OpenD也限制了最多128条连接
	UnInitQot();

	ParseHKEqtySecQot();

	//清理数据
	m_vHKEqtySecList.clear();
	m_vHKEqtySecQot.clear();

	cout << "GetSecuritySnapshotDemo End" << endl << endl;
}

void GetSecuritySnapshotDemo::GetHKEqtySecList()
{
	if (m_pQotApi != nullptr)
	{
		//先用GetStaticInfo协议获取港股正股，将股票列表保存在m_vHKEqtySecList
		Qot_GetStaticInfo::Request pbGetStaticInfo;
		Qot_GetStaticInfo::C2S *pGetStaticInfoC2S = pbGetStaticInfo.mutable_c2s();
		//optional int32 market = 1;
		//股票市场
		pGetStaticInfoC2S->set_market(Qot_Common::QotMarket_HK_Security);
		//optional int32 secType = 2;
		//股票类型
		pGetStaticInfoC2S->set_sectype(Qot_Common::SecurityType_Eqty);
		WaitReply(m_pQotApi->GetStaticInfo(pbGetStaticInfo));
		cout << "GetHKEqtySecList, count = " << m_vHKEqtySecList.size() << endl;
	}
}

void GetSecuritySnapshotDemo::GetHKEqtySecQot()
{
	if (m_pQotApi != nullptr)
	{
		//将m_vHKEqtySecList里的股票分批（3秒一次，一次200只股票）传入GetSecuritySnapshot，将获取到的行情保存在m_vHKEqtySecQot
		int32_t nHKEqtySecCount = (int32_t)m_vHKEqtySecList.size();
		if (nHKEqtySecCount > 0)
		{
			//每批请求股票个数
			const int32_t nEachReqSecCount = 200;
			//计算总共需要请求多少次
			int32_t nReqCount = (nHKEqtySecCount + nEachReqSecCount - 1) / nEachReqSecCount;
			//循环请求
			for (int32_t i = 0; i < nReqCount; ++i)
			{
				Qot_GetSecuritySnapshot::Request pbGetSecuritySnapshot;
				Qot_GetSecuritySnapshot::C2S *pGetSecuritySnapshotC2S = pbGetSecuritySnapshot.mutable_c2s();
				//快照请求包加入一批股票
				for (int32_t j = 0; j < nEachReqSecCount; ++j)
				{
					int32_t nIdx = i * nEachReqSecCount + j;
					if (nIdx < nHKEqtySecCount)
					{
						const Qot_Common::Security &pbSec = m_vHKEqtySecList[nIdx];
						Qot_Common::Security *pSec = pGetSecuritySnapshotC2S->add_securitylist();
						pSec->CopyFrom(pbSec);
					}
				}
				WaitReply(m_pQotApi->GetSecuritySnapshot(pbGetSecuritySnapshot));
				cout << "GetSecuritySnapshot, i = " << i << endl;
				//控制请求频率，3秒一次
				CPSleep(3);
			}
			// 检查请求的股票快照是否和拿到的数量一致
			if (nHKEqtySecCount == (int32_t)m_vHKEqtySecQot.size())
			{
				cout << "GetHKEqtySecQot, count = " << m_vHKEqtySecQot.size() << endl;
			}
			else
			{
				PrintError("Snapshot num error");
			}
		}
	}
}

void GetSecuritySnapshotDemo::ParseHKEqtySecQot()
{
	//数据保存或展示
	//用户可以在这里打断点观察数据，或者将数据输出到文件、控制台等
	if (!m_vHKEqtySecQot.empty())
	{
		//取第一个数据演示如何解包，更多用法请网上查询google protobuf使用教程
		const Qot_GetSecuritySnapshot::Snapshot &pbSnapshot = m_vHKEqtySecQot[0];
		//基本数据
		const Qot_GetSecuritySnapshot::SnapshotBasicData &pbBasic = pbSnapshot.basic();
		//required Qot_Common.Security security = 1;
		const Qot_Common::Security &pbSec = pbBasic.security();
		//股票市场
		Qot_Common::QotMarket enMarket = (Qot_Common::QotMarket)pbSec.market();
		//股票代码
		string strCode = pbSec.code();

		//required int32 type = 2;
		//股票类型
		Qot_Common::SecurityType enSecType = (Qot_Common::SecurityType)pbBasic.type();

		//required double curPrice = 12; 
		//最新价
		double fCurPrice = pbBasic.curprice();

		//......

		//optional double askPrice;
		//卖一价
		//注意：optional字段需要先用has_xxx接口判断是否有该数据才能访问，否则会引发崩溃
		if (pbBasic.has_askprice())
		{
			//注意：用double传值并不能准确表示浮点数，所以都会约定有效小数，如果没有特别提示，默认3位小数
			double fAskPrice = pbBasic.askprice();
		}

		//正股特有数据
		if (pbSnapshot.has_equityexdata())
		{
			const Qot_GetSecuritySnapshot::EquitySnapshotExData &pbEquityExData = pbSnapshot.equityexdata();

			//required double eyRate = 9;
			//收益率（该字段为百分比字段，默认不展示%，如20实际对应20%）
			double fEYRate = pbEquityExData.eyrate();
		}

		cout << "ParseHKEqtySecQot, first = (HK." << strCode << ", " << fCurPrice << ")" << endl;
	}
}

void GetSecuritySnapshotDemo::OnReply_GetStaticInfo(Moomoo::u32_t nSerialNo, const Qot_GetStaticInfo::Response &stRsp)
{
	//判断协议成功或失败
	if (stRsp.rettype() == Common::RetType_Succeed)
	{
		//协议解包，将数据存入m_vHKEqtySecList
		const Qot_GetStaticInfo::S2C &pbS2C = stRsp.s2c();
		i32_t nSecCount = pbS2C.staticinfolist_size();
		for (int32_t i = 0; i < nSecCount; ++i)
		{
			const Qot_Common::SecurityStaticInfo &pbSecStaticInfo = pbS2C.staticinfolist(i);
			m_vHKEqtySecList.push_back(pbSecStaticInfo.basic().security());
		}
	}
	else
	{
		PrintUTF8(stRsp.retmsg());
	}
	PostReply();
}

void GetSecuritySnapshotDemo::OnReply_GetSecuritySnapshot(Moomoo::u32_t nSerialNo, const Qot_GetSecuritySnapshot::Response &stRsp)
{
	//判断协议成功或失败
	if (stRsp.rettype() == Common::RetType_Succeed)
	{
		//协议解包，将数据存入m_vHKEqtySecQot
		const Qot_GetSecuritySnapshot::S2C &pbS2C = stRsp.s2c();
		i32_t nSecCount = pbS2C.snapshotlist_size();
		for (int32_t i = 0; i < nSecCount; ++i)
		{
			const Qot_GetSecuritySnapshot::Snapshot &pbSnapshot = pbS2C.snapshotlist(i);
			m_vHKEqtySecQot.push_back(pbSnapshot);
		}
	}
	else
	{
		PrintUTF8(stRsp.retmsg());
	}
	PostReply();
}

#include "FTAPIDemoBase.h"

FTAPIDemoBase::FTAPIDemoBase()
{
	m_pQotApi = MMAPI::CreateQotApi();
	m_pQotApi->RegisterQotSpi(this);
	m_pQotApi->RegisterConnSpi(this);
	m_bQotInitSuc = false;

	m_pTrdApi = MMAPI::CreateTrdApi();
	m_pTrdApi->RegisterTrdSpi(this);
	m_pTrdApi->RegisterConnSpi(this);
	m_bTrdInitSuc = false;

	m_pSem = new Semaphore(0);
}

FTAPIDemoBase::~FTAPIDemoBase()
{
	UnInitQot();
	UnInitTrd();
	delete m_pSem;
}

bool FTAPIDemoBase::InitQot(const char *szIP, uint16_t nPort)
{
	if (!m_bQotInitSuc && m_pQotApi != nullptr)
	{
		m_pQotApi->InitConnect(szIP, nPort, false);
		m_pSem->wait();
	}
	cout << "InitQot, suc = " << m_bQotInitSuc << endl;
	return m_bQotInitSuc;
}

void FTAPIDemoBase::UnInitQot()
{
	if (m_pQotApi != nullptr)
	{
		m_pQotApi->UnregisterQotSpi();
		m_pQotApi->UnregisterConnSpi();
		MMAPI::ReleaseQotApi(m_pQotApi);
		m_pQotApi = nullptr;
		m_bQotInitSuc = false;
	}
}

bool FTAPIDemoBase::InitTrd(const char *szIP, uint16_t nPort, const char *szPwdMD5, Trd_Common::SecurityFirm enFirm)
{
	if (!m_bTrdInitSuc && m_pTrdApi != nullptr)
	{
		m_vRealAccID.clear();
		m_vSimAccID.clear();
		m_setAllAccID.clear();

		m_pTrdApi->InitConnect(szIP, nPort, false);
		m_pSem->wait();
		if (m_bTrdInitSuc)
		{
			//先解锁交易(模拟交易不需要解锁)
			Unlock(szPwdMD5, enFirm);
			//拉取交易账户，并且订阅交易账户的推送
			GetAccListAndSubTradePush();
		}
	}
	cout << "InitTrd, suc = " << m_bTrdInitSuc << endl;
	return m_bTrdInitSuc;
}

void FTAPIDemoBase::UnInitTrd()
{
	if (m_pTrdApi != nullptr)
	{
		m_pTrdApi->UnregisterTrdSpi();
		m_pTrdApi->UnregisterConnSpi();
		MMAPI::ReleaseTrdApi(m_pTrdApi);
		m_pTrdApi = nullptr;
		m_bTrdInitSuc = false;
	}

    m_vRealAccID.clear();
    m_vSimAccID.clear();
	m_setAllAccID.clear();
}

void FTAPIDemoBase::Unlock(const char *szPwdMD5, Trd_Common::SecurityFirm enFirm)
{
	if (m_pTrdApi != nullptr && szPwdMD5 != nullptr && strlen(szPwdMD5) != 0)
	{
		Trd_UnlockTrade::Request pbUnlockTrade;
		Trd_UnlockTrade::C2S *pUnlockTradeC2S = pbUnlockTrade.mutable_c2s();
		pUnlockTradeC2S->set_unlock(true);
		pUnlockTradeC2S->set_pwdmd5(szPwdMD5);
		pUnlockTradeC2S->set_securityfirm(enFirm);
		WaitReply(m_pTrdApi->UnlockTrade(pbUnlockTrade));
	}
}

void FTAPIDemoBase::GetAccListAndSubTradePush()
{
	if (m_pTrdApi != nullptr)
	{		
		Trd_GetAccList::Request pbGetAccList;
		Trd_GetAccList::C2S* pGetAccListC2S = pbGetAccList.mutable_c2s();
		pGetAccListC2S->set_userid(0);
		pGetAccListC2S->set_trdcategory(Trd_Common::TrdCategory::TrdCategory_Security);
		pGetAccListC2S->set_needgeneralsecaccount(true);
		WaitReply(m_pTrdApi->GetAccList(pbGetAccList));

		if (!m_setAllAccID.empty())
		{
			Trd_SubAccPush::Request pbSubAccPush;
			Trd_SubAccPush::C2S* pSubAccC2S = pbSubAccPush.mutable_c2s();
			for (auto iter = m_setAllAccID.begin(); iter != m_setAllAccID.end(); ++iter)
			{
				pSubAccC2S->add_accidlist(*iter);
			}
			WaitReply(m_pTrdApi->SubAccPush(pbSubAccPush));
		}
	}
}

void FTAPIDemoBase::OnInitConnect(MMAPI_Conn* pConn, Moomoo::i64_t nErrCode, const char* strDesc)
{
	if (pConn != nullptr)
	{
		if (pConn == m_pQotApi)
		{
			m_bQotInitSuc = (nErrCode == 0);
		}
		else if (pConn == m_pTrdApi)
		{
			m_bTrdInitSuc = (nErrCode == 0);
		}
		PostReply();
	}
}

void FTAPIDemoBase::OnReply_GetAccList(Moomoo::u32_t nSerialNo, const Trd_GetAccList::Response &stRsp)
{
    if (stRsp.rettype() == Common::RetType_Succeed)
    {
        m_setAllAccID.clear();
        m_vRealAccID.clear();
        m_vSimAccID.clear();
        const Trd_GetAccList::S2C& pbS2C = stRsp.s2c();
        i32_t nAccCount = pbS2C.acclist_size();
        for (int32_t i = 0; i < nAccCount; ++i)
        {
            const Trd_Common::TrdAcc& pbTrdAcc = pbS2C.acclist(i);
            //业务账号
            uint64_t nAccID = pbTrdAcc.accid();
            //交易环境
            Trd_Common::TrdEnv enTrdEnv = (Trd_Common::TrdEnv)pbTrdAcc.trdenv();
            //收集交易范例必要信息
            m_setAllAccID.insert(nAccID);
            //业务账户支持的交易市场权限，即此账户能交易那些市场, 可拥有多个交易市场权限
            set<int32_t> setMarket;
            for (int32_t j = 0; j < pbTrdAcc.trdmarketauthlist_size(); ++j)
            {
                setMarket.insert(pbTrdAcc.trdmarketauthlist(j));
            }
            if (enTrdEnv == Trd_Common::TrdEnv::TrdEnv_Real)
            {
                m_vRealAccID.push_back(make_pair(nAccID, setMarket));
            }
            else
            {
                m_vSimAccID.push_back(make_pair(nAccID, setMarket));
            }
        }
    }
    else
    {
        PrintUTF8(stRsp.retmsg());
    }
    PostReply();
}

void FTAPIDemoBase::OnReply_UnlockTrade(Moomoo::u32_t nSerialNo, const Trd_UnlockTrade::Response &stRsp)
{
	if (stRsp.rettype() != Common::RetType_Succeed)
	{
		PrintUTF8(stRsp.retmsg());
	}
	PostReply();
}

void FTAPIDemoBase::OnReply_SubAccPush(Moomoo::u32_t nSerialNo, const Trd_SubAccPush::Response &stRsp)
{
	if (stRsp.rettype() != Common::RetType_Succeed)
	{
		PrintUTF8(stRsp.retmsg());
	}
	PostReply();
}

void FTAPIDemoBase::WaitReply(int32_t nSerilNo)
{
	//接口返回的nSerilNo与回调函数OnReply_XXX第一个参数对应
	//用于对应请求和回包，本范例以同步接口的形式调用，每次只发送一个请求所以需要记录、对比该字段
	if (nSerilNo != 0)
	{
		m_pSem->wait();
	}
}

void FTAPIDemoBase::PostReply()
{
	m_pSem->post();
}

uint64_t FTAPIDemoBase::GetFirstAccID(Trd_Common::TrdMarket enTrdMarket, Trd_Common::TrdEnv enTrdEnv)
{
    uint64_t nAccID = 0;
    vector<pair<uint64_t, set<int32_t>>>& vAccID = (enTrdEnv == Trd_Common::TrdEnv_Real) ? m_vRealAccID : m_vSimAccID;
    for (vector<pair<uint64_t, set<int32_t>>>::iterator iter = vAccID.begin();
         iter != vAccID.end(); ++iter)
    {
        if (iter->second.count((int32_t)enTrdMarket) > 0)
        {
            nAccID = iter->first;
            break;
        }
    }
    return nAccID;
}

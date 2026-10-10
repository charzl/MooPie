// Copyright 2026 Moomoo
#include "MMAPIImp.h"
#include "MMAPI_Define_ProtoID.h"

using namespace std;

CLock MMAPIImp::m_safe;

static inline bool PbObj2BinData(const protobuf::Message& pbObj, Buf_t& binData)
{
	binData.clear();

	i32_t nSize = pbObj.ByteSize();
	If_OMWarn_Return(nSize < 0, false);
	If_Return(nSize == 0, true); // pb为空

	binData.resize(nSize);
	If_Do_OMWarn_Return(!pbObj.SerializeToString(&binData), binData.clear(), false);
	return true;
}

static inline bool BinData2PbObj(const i8_t* pData, i32_t nDataLen, u8_t nProtoFmtType, protobuf::Message& pbObj)
{
	If_OMWarn_Return(IsNullPtr(pData) || nDataLen <= 0, false);
	bool bRet = false;
	if (nProtoFmtType == MMAPI_ProtoFmtType_Protobuf)
	{
		bRet = pbObj.ParseFromArray(pData, nDataLen);
	}
	else if (nProtoFmtType == MMAPI_ProtoFmtType_Json)
	{
		protobuf::util::JsonParseOptions ops;
		ops.ignore_unknown_fields = true;

		Str_t strJosn(pData, nDataLen);
		protobuf::util::Status status = JsonStringToMessage(strJosn, &pbObj, ops);
		bRet = status.ok();
	}
	If_OMWarn(!bRet);
	return bRet;
}

static inline bool IsTrdPorto(u32_t nPorotID)
{
	return nPorotID >= MMAPI_ProtoID_Trd_Begin && nPorotID <= MMAPI_ProtoID_Trd_End;
}

static inline bool IsQotPorto(u32_t nPorotID)
{
	return nPorotID >= MMAPI_ProtoID_Qot_Begin && nPorotID <= MMAPI_ProtoID_Qot_End;
}

MMAPIImp::MMAPIImp(MMAPI_Conn *pConnApi)
{
    CAutoLock(m_safe);
	m_pConnApi = pConnApi;
	If_OMWarn(IsNullPtr(m_pConnApi));
}

MMAPIImp::~MMAPIImp(void)
{
    CAutoLock(m_safe);
	// 先断开与连接层的回调（等价于原 ReleaseMMAPIChannel 中的 UnInit）：
	// 必须在派生对象仍完整时执行，确保网络线程不再回调到即将析构的本对象。
	MMAPI_Client::UnInit();
}

void MMAPIImp::SetClientInfo(const char* szClientID, i32_t nClientVer)
{
    CAutoLock(m_safe);
	MMAPI_Client::SetClientInfo(szClientID, nClientVer);
}

void MMAPIImp::SetProgrammingLanguage(const char* szLanguage)
{
    CAutoLock(m_safe);
	MMAPI_Client::SetProgrammingLanguage(szLanguage);
}

void MMAPIImp::SetRSAPrivateKey(const char* strRSAPrivateKey)
{
    CAutoLock(m_safe);
	MMAPI_Client::SetRSAPrivateKey(strRSAPrivateKey);
}

bool MMAPIImp::InitConnect(const char* szIPAddr, u16_t nPort, bool bEnableEncrypt)
{
    CAutoLock(m_safe);
	SetProtoFmtType(MMAPI_ProtoFmtType_Protobuf);
	DisablePacketEnc(bEnableEncrypt == 0);
	return MMAPI_Client::InitConnect(szIPAddr, nPort);
}

u64_t MMAPIImp::GetConnectID()
{
    CAutoLock(m_safe);
	return MMAPI_Client::GetSvrConnectID();
}

bool MMAPIImp::Close()
{
    CAutoLock(m_safe);
	return MMAPI_Client::Close();
}

void MMAPIImp::RegisterConnSpi(MMSPI_Conn *pSpi)
{
	CAutoLock(m_safe);
	m_pConnSpi = pSpi;
}

void MMAPIImp::UnregisterConnSpi()
{
	CAutoLock(m_safe);
	m_pConnSpi = nullptr;
}

void MMAPIImp::RegisterQotSpi(MMSPI_Qot *pSpi)
{
	CAutoLock(m_safe);
	m_pQotSpi = pSpi;
}

void MMAPIImp::UnregisterQotSpi()
{
	CAutoLock(m_safe);
	m_pQotSpi = nullptr;
}

u32_t MMAPIImp::Sub(const Qot_Sub::Request &stReq)
{
	return SendProto(MMAPI_ProtoID_Qot_Sub, stReq);
}

u32_t MMAPIImp::GetGlobalState(const GetGlobalState::Request &stReq)
{
	return SendProto(MMAPI_ProtoID_GetGlobalState, stReq);
}

u32_t MMAPIImp::RegQotPush(const Qot_RegQotPush::Request &stReq)
{
	return SendProto(MMAPI_ProtoID_Qot_RegQotPush, stReq);
}

u32_t MMAPIImp::GetSubInfo(const Qot_GetSubInfo::Request &stReq)
{
	return SendProto(MMAPI_ProtoID_Qot_GetSubInfo, stReq);
}

u32_t MMAPIImp::GetTicker(const Qot_GetTicker::Request &stReq)
{
	return SendProto(MMAPI_ProtoID_Qot_GetTicker, stReq);
}

u32_t MMAPIImp::GetBasicQot(const Qot_GetBasicQot::Request &stReq)
{
	return SendProto(MMAPI_ProtoID_Qot_GetBasicQot, stReq);
}

u32_t MMAPIImp::GetOrderBook(const Qot_GetOrderBook::Request &stReq)
{
	return SendProto(MMAPI_ProtoID_Qot_GetOrderBook, stReq);
}

u32_t MMAPIImp::GetKL(const Qot_GetKL::Request &stReq)
{
	return SendProto(MMAPI_ProtoID_Qot_GetKL, stReq);
}

u32_t MMAPIImp::GetRT(const Qot_GetRT::Request &stReq)
{
	return SendProto(MMAPI_ProtoID_Qot_GetRT, stReq);
}

u32_t MMAPIImp::GetBroker(const Qot_GetBroker::Request &stReq)
{
	return SendProto(MMAPI_ProtoID_Qot_GetBroker, stReq);
}

u32_t MMAPIImp::RequestRehab(const Qot_RequestRehab::Request &stReq)
{
	return SendProto(MMAPI_ProtoID_Qot_RequestRehab, stReq);
}

u32_t MMAPIImp::RequestHistoryKL(const Qot_RequestHistoryKL::Request &stReq)
{
	return SendProto(MMAPI_ProtoID_Qot_RequestHistoryKL, stReq);
}

u32_t MMAPIImp::RequestHistoryKLQuota(const Qot_RequestHistoryKLQuota::Request &stReq)
{
	return SendProto(MMAPI_ProtoID_Qot_RequestHistoryKLQuota, stReq);
}

u32_t MMAPIImp::GetStaticInfo(const Qot_GetStaticInfo::Request &stReq)
{
	return SendProto(MMAPI_ProtoID_Qot_GetStaticInfo, stReq);
}

u32_t MMAPIImp::GetSecuritySnapshot(const Qot_GetSecuritySnapshot::Request &stReq)
{
	return SendProto(MMAPI_ProtoID_Qot_GetSecuritySnapshot, stReq);
}

u32_t MMAPIImp::GetPlateSet(const Qot_GetPlateSet::Request &stReq)
{
	return SendProto(MMAPI_ProtoID_Qot_GetPlateSet, stReq);
}

u32_t MMAPIImp::GetPlateSecurity(const Qot_GetPlateSecurity::Request &stReq)
{
	return SendProto(MMAPI_ProtoID_Qot_GetPlateSecurity, stReq);
}

u32_t MMAPIImp::GetReference(const Qot_GetReference::Request &stReq)
{
	return SendProto(MMAPI_ProtoID_Qot_GetReference, stReq);
}

u32_t MMAPIImp::GetOwnerPlate(const Qot_GetOwnerPlate::Request &stReq)
{
	return SendProto(MMAPI_ProtoID_Qot_GetOwnerPlate, stReq);
}

u32_t MMAPIImp::GetHoldingChangeList(const Qot_GetHoldingChangeList::Request &stReq)
{
	return SendProto(MMAPI_ProtoID_Qot_GetHoldingChangeList, stReq);
}

u32_t MMAPIImp::GetOptionChain(const Qot_GetOptionChain::Request &stReq)
{
	return SendProto(MMAPI_ProtoID_Qot_GetOptionChain, stReq);
}

u32_t MMAPIImp::GetWarrant(const Qot_GetWarrant::Request &stReq)
{
	return SendProto(MMAPI_ProtoID_Qot_GetWarrant, stReq);
}

u32_t MMAPIImp::GetCapitalFlow(const Qot_GetCapitalFlow::Request &stReq)
{
	return SendProto(MMAPI_ProtoID_Qot_GetCapitalFlow, stReq);
}

u32_t MMAPIImp::GetCapitalDistribution(const Qot_GetCapitalDistribution::Request &stReq)
{
	return SendProto(MMAPI_ProtoID_Qot_GetCapitalDistribution, stReq);
}

u32_t MMAPIImp::GetUserSecurity(const Qot_GetUserSecurity::Request &stReq)
{
	return SendProto(MMAPI_ProtoID_Qot_GetUserSecurity, stReq);
}

u32_t MMAPIImp::ModifyUserSecurity(const Qot_ModifyUserSecurity::Request &stReq)
{
	return SendProto(MMAPI_ProtoID_Qot_ModifyUserSecurity, stReq);
}

u32_t MMAPIImp::StockFilter(const Qot_StockFilter::Request &stReq)
{
	return SendProto(MMAPI_ProtoID_Qot_StockFilter, stReq);
}

Moomoo::u32_t MMAPIImp::GetCodeChange(const Qot_GetCodeChange::Request &stReq)
{
	return SendProto(MMAPI_ProtoID_Qot_GetCodeChange, stReq);
}

u32_t MMAPIImp::GetIpoList(const Qot_GetIpoList::Request &stReq)
{
	return SendProto(MMAPI_ProtoID_Qot_GetIpoList, stReq);
}

u32_t MMAPIImp::GetFutureInfo(const Qot_GetFutureInfo::Request &stReq)
{
	return SendProto(MMAPI_ProtoID_Qot_GetFutureInfo, stReq);
}

u32_t MMAPIImp::RequestTradeDate(const Qot_RequestTradeDate::Request &stReq)
{
	return SendProto(MMAPI_ProtoID_Qot_RequestTradeDate, stReq);
}

u32_t MMAPIImp::SetPriceReminder(const Qot_SetPriceReminder::Request &stReq)
{
	return SendProto(MMAPI_ProtoID_Qot_SetPriceReminder, stReq);
}

u32_t MMAPIImp::GetPriceReminder(const Qot_GetPriceReminder::Request &stReq)
{
	return SendProto(MMAPI_ProtoID_Qot_GetPriceReminder, stReq);
}

u32_t MMAPIImp::GetUserSecurityGroup(const Qot_GetUserSecurityGroup::Request &stReq)
{
	return SendProto(MMAPI_ProtoID_Qot_GetUserSecurityGroup, stReq);
}

u32_t MMAPIImp::GetMarketState(const Qot_GetMarketState::Request &stReq)
{
	return SendProto(MMAPI_ProtoID_Qot_GetMarketState, stReq);
}

u32_t MMAPIImp::GetOptionExpirationDate(const Qot_GetOptionExpirationDate::Request &stReq)
{
	return SendProto(MMAPI_ProtoID_Qot_GetOptionExpirationDate, stReq);
}

u32_t MMAPIImp::GetOptionQuote(const Qot_GetOptionQuote::Request &stReq)
{
	return SendProto(MMAPI_ProtoID_Qot_GetOptionQuote, stReq);
}

u32_t MMAPIImp::GetOptionStrategy(const Qot_GetOptionStrategy::Request &stReq)
{
	return SendProto(MMAPI_ProtoID_Qot_GetOptionStrategy, stReq);
}

u32_t MMAPIImp::GetOptionStrategyAnalysis(const Qot_GetOptionStrategyAnalysis::Request &stReq)
{
	return SendProto(MMAPI_ProtoID_Qot_GetOptionStrategyAnalysis, stReq);
}

u32_t MMAPIImp::GetOptionStrategySpread(const Qot_GetOptionStrategySpread::Request &stReq)
{
	return SendProto(MMAPI_ProtoID_Qot_GetOptionStrategySpread, stReq);
}

u32_t MMAPIImp::GetFinancialsEarningsPriceMove(const Qot_GetFinancialsEarningsPriceMove::Request &stReq)
{
	return SendProto(MMAPI_ProtoID_Qot_GetFinancialsEarningsPriceMove, stReq);
}

u32_t MMAPIImp::GetFinancialsEarningsPriceHistory(const Qot_GetFinancialsEarningsPriceHistory::Request &stReq)
{
	return SendProto(MMAPI_ProtoID_Qot_GetFinancialsEarningsPriceHistory, stReq);
}

u32_t MMAPIImp::GetFinancialsStatements(const Qot_GetFinancialsStatements::Request &stReq)
{
	return SendProto(MMAPI_ProtoID_Qot_GetFinancialsStatements, stReq);
}

u32_t MMAPIImp::GetFinancialsRevenueBreakdown(const Qot_GetFinancialsRevenueBreakdown::Request &stReq)
{
	return SendProto(MMAPI_ProtoID_Qot_GetFinancialsRevenueBreakdown, stReq);
}

u32_t MMAPIImp::GetResearchAnalystConsensus(const Qot_GetResearchAnalystConsensus::Request &stReq)
{
	return SendProto(MMAPI_ProtoID_Qot_GetResearchAnalystConsensus, stReq);
}

u32_t MMAPIImp::GetResearchRatingSummary(const Qot_GetResearchRatingSummary::Request &stReq)
{
	return SendProto(MMAPI_ProtoID_Qot_GetResearchRatingSummary, stReq);
}

u32_t MMAPIImp::GetResearchMorningstarReport(const Qot_GetResearchMorningstarReport::Request &stReq)
{
	return SendProto(MMAPI_ProtoID_Qot_GetResearchMorningstarReport, stReq);
}

u32_t MMAPIImp::GetValuationDetail(const Qot_GetValuationDetail::Request &stReq)
{
	return SendProto(MMAPI_ProtoID_Qot_GetValuationDetail, stReq);
}

u32_t MMAPIImp::GetValuationPlateStockList(const Qot_GetValuationPlateStockList::Request &stReq)
{
	return SendProto(MMAPI_ProtoID_Qot_GetValuationPlateStockList, stReq);
}

u32_t MMAPIImp::GetCorporateActionsDividends(const Qot_GetCorporateActionsDividends::Request &stReq)
{
	return SendProto(MMAPI_ProtoID_Qot_GetCorporateActionsDividends, stReq);
}

u32_t MMAPIImp::GetCorporateActionsBuybacks(const Qot_GetCorporateActionsBuybacks::Request &stReq)
{
	return SendProto(MMAPI_ProtoID_Qot_GetCorporateActionsBuybacks, stReq);
}

u32_t MMAPIImp::GetCorporateActionsStockSplits(const Qot_GetCorporateActionsStockSplits::Request &stReq)
{
	return SendProto(MMAPI_ProtoID_Qot_GetCorporateActionsStockSplits, stReq);
}

u32_t MMAPIImp::GetShareholdersOverview(const Qot_GetShareholdersOverview::Request &stReq)
{
	return SendProto(MMAPI_ProtoID_Qot_GetShareholdersOverview, stReq);
}

u32_t MMAPIImp::GetShareholdersHoldingChanges(const Qot_GetShareholdersHoldingChanges::Request &stReq)
{
	return SendProto(MMAPI_ProtoID_Qot_GetShareholdersHoldingChanges, stReq);
}

u32_t MMAPIImp::GetShareholdersHolderDetail(const Qot_GetShareholdersHolderDetail::Request &stReq)
{
	return SendProto(MMAPI_ProtoID_Qot_GetShareholdersHolderDetail, stReq);
}

u32_t MMAPIImp::GetShareholdersInstitutional(const Qot_GetShareholdersInstitutional::Request &stReq)
{
	return SendProto(MMAPI_ProtoID_Qot_GetShareholdersInstitutional, stReq);
}

u32_t MMAPIImp::GetInsiderHolderList(const Qot_GetInsiderHolderList::Request &stReq)
{
	return SendProto(MMAPI_ProtoID_Qot_GetInsiderHolderList, stReq);
}

u32_t MMAPIImp::GetInsiderTradeList(const Qot_GetInsiderTradeList::Request &stReq)
{
	return SendProto(MMAPI_ProtoID_Qot_GetInsiderTradeList, stReq);
}

u32_t MMAPIImp::GetCompanyProfile(const Qot_GetCompanyProfile::Request &stReq)
{
	return SendProto(MMAPI_ProtoID_Qot_GetCompanyProfile, stReq);
}

u32_t MMAPIImp::GetCompanyExecutives(const Qot_GetCompanyExecutives::Request &stReq)
{
	return SendProto(MMAPI_ProtoID_Qot_GetCompanyExecutives, stReq);
}

u32_t MMAPIImp::GetCompanyExecutiveBackground(const Qot_GetCompanyExecutiveBackground::Request &stReq)
{
	return SendProto(MMAPI_ProtoID_Qot_GetCompanyExecutiveBackground, stReq);
}

u32_t MMAPIImp::GetCompanyOperationalEfficiency(const Qot_GetCompanyOperationalEfficiency::Request &stReq)
{
	return SendProto(MMAPI_ProtoID_Qot_GetCompanyOperationalEfficiency, stReq);
}

u32_t MMAPIImp::GetTopTenBuySellBrokers(const Qot_GetTopTenBuySellBrokers::Request &stReq)
{
	return SendProto(MMAPI_ProtoID_Qot_GetTopTenBuySellBrokers, stReq);
}

u32_t MMAPIImp::GetDailyShortVolume(const Qot_GetDailyShortVolume::Request &stReq)
{
	return SendProto(MMAPI_ProtoID_Qot_GetDailyShortVolume, stReq);
}

u32_t MMAPIImp::GetShortInterest(const Qot_GetShortInterest::Request &stReq)
{
	return SendProto(MMAPI_ProtoID_Qot_GetShortInterest, stReq);
}

u32_t MMAPIImp::GetOptionVolatility(const Qot_GetOptionVolatility::Request &stReq)
{
	return SendProto(MMAPI_ProtoID_Qot_GetOptionVolatility, stReq);
}

u32_t MMAPIImp::GetOptionExerciseProbability(const Qot_GetOptionExerciseProbability::Request &stReq)
{
	return SendProto(MMAPI_ProtoID_Qot_GetOptionExerciseProbability, stReq);
}

u32_t MMAPIImp::StockScreen(const Qot_StockScreen::Request &stReq)
{
	return SendProto(MMAPI_ProtoID_Qot_StockScreen, stReq);
}

u32_t MMAPIImp::OptionScreen(const Qot_OptionScreen::Request &stReq)
{
	return SendProto(MMAPI_ProtoID_Qot_OptionScreen, stReq);
}

u32_t MMAPIImp::WarrantScreen(const Qot_WarrantScreen::Request &stReq)
{
	return SendProto(MMAPI_ProtoID_Qot_WarrantScreen, stReq);
}

u32_t MMAPIImp::GetOptionMarketStatistic(const Qot_GetOptionMarketStatistic::Request &stReq)
{
	return SendProto(MMAPI_ProtoID_Qot_GetOptionMarketStatistic, stReq);
}

u32_t MMAPIImp::GetOptionUnderlyingHisStatistic(const Qot_GetOptionUnderlyingHisStatistic::Request &stReq)
{
	return SendProto(MMAPI_ProtoID_Qot_GetOptionUnderlyingHisStatistic, stReq);
}

u32_t MMAPIImp::GetOptionUnderlyingOverview(const Qot_GetOptionUnderlyingOverview::Request &stReq)
{
	return SendProto(MMAPI_ProtoID_Qot_GetOptionUnderlyingOverview, stReq);
}

u32_t MMAPIImp::GetOptionUnderlyingHisVolatility(const Qot_GetOptionUnderlyingHisVolatility::Request &stReq)
{
	return SendProto(MMAPI_ProtoID_Qot_GetOptionUnderlyingHisVolatility, stReq);
}

u32_t MMAPIImp::GetOptionUnderlyingRank(const Qot_GetOptionUnderlyingRank::Request &stReq)
{
	return SendProto(MMAPI_ProtoID_Qot_GetOptionUnderlyingRank, stReq);
}

u32_t MMAPIImp::GetOptionRank(const Qot_GetOptionRank::Request &stReq)
{
	return SendProto(MMAPI_ProtoID_Qot_GetOptionRank, stReq);
}

u32_t MMAPIImp::GetOptionEvent(const Qot_GetOptionEvent::Request &stReq)
{
	return SendProto(MMAPI_ProtoID_Qot_GetOptionEvent, stReq);
}

u32_t MMAPIImp::GetOptionEventAlert(const Qot_GetOptionEventAlert::Request &stReq)
{
	return SendProto(MMAPI_ProtoID_Qot_GetOptionEventAlert, stReq);
}

u32_t MMAPIImp::SetOptionEventAlert(const Qot_SetOptionEventAlert::Request &stReq)
{
	return SendProto(MMAPI_ProtoID_Qot_SetOptionEventAlert, stReq);
}

u32_t MMAPIImp::GetOptionZeroDteScreener(const Qot_GetOptionZeroDteScreener::Request &stReq)
{
	return SendProto(MMAPI_ProtoID_Qot_GetOptionZeroDteScreener, stReq);
}

u32_t MMAPIImp::GetOptionZeroDteContract(const Qot_GetOptionZeroDteContract::Request &stReq)
{
	return SendProto(MMAPI_ProtoID_Qot_GetOptionZeroDteContract, stReq);
}

u32_t MMAPIImp::GetOptionEarningsScreener(const Qot_GetOptionEarningsScreener::Request &stReq)
{
	return SendProto(MMAPI_ProtoID_Qot_GetOptionEarningsScreener, stReq);
}

u32_t MMAPIImp::GetOptionSellerScreener(const Qot_GetOptionSellerScreener::Request &stReq)
{
	return SendProto(MMAPI_ProtoID_Qot_GetOptionSellerScreener, stReq);
}

u32_t MMAPIImp::GetIndicatorList(const Qot_GetIndicatorList::Request &stReq)
{
	return SendProto(MMAPI_ProtoID_Qot_GetIndicatorList, stReq);
}

u32_t MMAPIImp::RequestIndicatorCalc(const Qot_RequestIndicatorCalc::Request &stReq)
{
	return SendProto(MMAPI_ProtoID_Qot_RequestIndicatorCalc, stReq);
}

u32_t MMAPIImp::GetSearchQuote(const Qot_GetSearchQuote::Request &stReq)
{
	return SendProto(MMAPI_ProtoID_Qot_GetSearchQuote, stReq);
}

u32_t MMAPIImp::GetSearchNews(const Qot_GetSearchNews::Request &stReq)
{
	return SendProto(MMAPI_ProtoID_Qot_GetSearchNews, stReq);
}

u32_t MMAPIImp::GetEarningsCalendar(const Qot_GetEarningsCalendar::Request &stReq)
{
	return SendProto(MMAPI_ProtoID_Qot_GetEarningsCalendar, stReq);
}

u32_t MMAPIImp::GetMacroIndicatorList(const Qot_GetMacroIndicatorList::Request &stReq)
{
	return SendProto(MMAPI_ProtoID_Qot_GetMacroIndicatorList, stReq);
}

u32_t MMAPIImp::GetMacroIndicatorHistory(const Qot_GetMacroIndicatorHistory::Request &stReq)
{
	return SendProto(MMAPI_ProtoID_Qot_GetMacroIndicatorHistory, stReq);
}

u32_t MMAPIImp::GetFedWatchTargetRate(const Qot_GetFedWatchTargetRate::Request &stReq)
{
	return SendProto(MMAPI_ProtoID_Qot_GetFedWatchTargetRate, stReq);
}

u32_t MMAPIImp::GetFedWatchDotPlot(const Qot_GetFedWatchDotPlot::Request &stReq)
{
	return SendProto(MMAPI_ProtoID_Qot_GetFedWatchDotPlot, stReq);
}

u32_t MMAPIImp::GetEarningsBeatRank(const Qot_GetEarningsBeatRank::Request &stReq)
{
	return SendProto(MMAPI_ProtoID_Qot_GetEarningsBeatRank, stReq);
}

u32_t MMAPIImp::GetDividendRank(const Qot_GetDividendRank::Request &stReq)
{
	return SendProto(MMAPI_ProtoID_Qot_GetDividendRank, stReq);
}

u32_t MMAPIImp::GetDividendCalendar(const Qot_GetDividendCalendar::Request &stReq)
{
	return SendProto(MMAPI_ProtoID_Qot_GetDividendCalendar, stReq);
}

u32_t MMAPIImp::GetEconomicCalendar(const Qot_GetEconomicCalendar::Request &stReq)
{
	return SendProto(MMAPI_ProtoID_Qot_GetEconomicCalendar, stReq);
}

u32_t MMAPIImp::GetUSPreMarketRank(const Qot_GetUSPreMarketRank::Request &stReq)
{
	return SendProto(MMAPI_ProtoID_Qot_GetUSPreMarketRank, stReq);
}

u32_t MMAPIImp::GetUSAfterHoursRank(const Qot_GetUSAfterHoursRank::Request &stReq)
{
	return SendProto(MMAPI_ProtoID_Qot_GetUSAfterHoursRank, stReq);
}

u32_t MMAPIImp::GetUSOvernightRank(const Qot_GetUSOvernightRank::Request &stReq)
{
	return SendProto(MMAPI_ProtoID_Qot_GetUSOvernightRank, stReq);
}

u32_t MMAPIImp::GetTopMoversRank(const Qot_GetTopMoversRank::Request &stReq)
{
	return SendProto(MMAPI_ProtoID_Qot_GetTopMoversRank, stReq);
}

u32_t MMAPIImp::GetHotList(const Qot_GetHotList::Request &stReq)
{
	return SendProto(MMAPI_ProtoID_Qot_GetHotList, stReq);
}

u32_t MMAPIImp::GetShortSellingRank(const Qot_GetShortSellingRank::Request &stReq)
{
	return SendProto(MMAPI_ProtoID_Qot_GetShortSellingRank, stReq);
}

u32_t MMAPIImp::GetPeriodChangeRank(const Qot_GetPeriodChangeRank::Request &stReq)
{
	return SendProto(MMAPI_ProtoID_Qot_GetPeriodChangeRank, stReq);
}

u32_t MMAPIImp::GetHighDividendSOERank(const Qot_GetHighDividendSOERank::Request &stReq)
{
	return SendProto(MMAPI_ProtoID_Qot_GetHighDividendSOERank, stReq);
}

u32_t MMAPIImp::GetInstitutionList(const Qot_GetInstitutionList::Request &stReq)
{
	return SendProto(MMAPI_ProtoID_Qot_GetInstitutionList, stReq);
}

u32_t MMAPIImp::GetInstitutionProfile(const Qot_GetInstitutionProfile::Request &stReq)
{
	return SendProto(MMAPI_ProtoID_Qot_GetInstitutionProfile, stReq);
}

u32_t MMAPIImp::GetInstitutionDistribution(const Qot_GetInstitutionDistribution::Request &stReq)
{
	return SendProto(MMAPI_ProtoID_Qot_GetInstitutionDistribution, stReq);
}

u32_t MMAPIImp::GetInstitutionHoldingChange(const Qot_GetInstitutionHoldingChange::Request &stReq)
{
	return SendProto(MMAPI_ProtoID_Qot_GetInstitutionHoldingChange, stReq);
}

u32_t MMAPIImp::GetInstitutionHoldingList(const Qot_GetInstitutionHoldingList::Request &stReq)
{
	return SendProto(MMAPI_ProtoID_Qot_GetInstitutionHoldingList, stReq);
}

u32_t MMAPIImp::GetArkFundHolding(const Qot_GetArkFundHolding::Request &stReq)
{
	return SendProto(MMAPI_ProtoID_Qot_GetArkFundHolding, stReq);
}

u32_t MMAPIImp::GetArkStockDynamic(const Qot_GetArkStockDynamic::Request &stReq)
{
	return SendProto(MMAPI_ProtoID_Qot_GetArkStockDynamic, stReq);
}

u32_t MMAPIImp::GetArkActiveTransaction(const Qot_GetArkActiveTransaction::Request &stReq)
{
	return SendProto(MMAPI_ProtoID_Qot_GetArkActiveTransaction, stReq);
}

u32_t MMAPIImp::GetRatingChange(const Qot_GetRatingChange::Request &stReq)
{
	return SendProto(MMAPI_ProtoID_Qot_GetRatingChange, stReq);
}

u32_t MMAPIImp::GetIndustrialChainList(const Qot_GetIndustrialChainList::Request &stReq)
{
	return SendProto(MMAPI_ProtoID_Qot_GetIndustrialChainList, stReq);
}

u32_t MMAPIImp::GetIndustrialChainDetail(const Qot_GetIndustrialChainDetail::Request &stReq)
{
	return SendProto(MMAPI_ProtoID_Qot_GetIndustrialChainDetail, stReq);
}

u32_t MMAPIImp::GetIndustrialChainByPlate(const Qot_GetIndustrialChainByPlate::Request &stReq)
{
	return SendProto(MMAPI_ProtoID_Qot_GetIndustrialChainByPlate, stReq);
}

u32_t MMAPIImp::GetIndustrialPlateInfo(const Qot_GetIndustrialPlateInfo::Request &stReq)
{
	return SendProto(MMAPI_ProtoID_Qot_GetIndustrialPlateInfo, stReq);
}

u32_t MMAPIImp::GetIndustrialPlateStock(const Qot_GetIndustrialPlateStock::Request &stReq)
{
	return SendProto(MMAPI_ProtoID_Qot_GetIndustrialPlateStock, stReq);
}

u32_t MMAPIImp::GetHeatMapData(const Qot_GetHeatMapData::Request &stReq)
{
	return SendProto(MMAPI_ProtoID_Qot_GetHeatMapData, stReq);
}

u32_t MMAPIImp::GetRiseFallDistribution(const Qot_GetRiseFallDistribution::Request &stReq)
{
	return SendProto(MMAPI_ProtoID_Qot_GetRiseFallDistribution, stReq);
}

void MMAPIImp::RegisterTrdSpi(MMSPI_Trd *pSpi)
{
	CAutoLock(m_safe);
	m_pTrdSpi = pSpi;
}

void MMAPIImp::UnregisterTrdSpi()
{
	CAutoLock(m_safe);
	m_pTrdSpi = nullptr;
}

bool MMAPIImp::GetPacketID(Common::PacketID &stPacketID)
{
	CAutoLock(m_safe);
	u64_t nConnectID = GetConnectID();
	stPacketID.set_connid(nConnectID);
	stPacketID.set_serialno(++m_nTrdSerialNo);
	return nConnectID != 0;
}

u32_t MMAPIImp::GetAccList(const Trd_GetAccList::Request &stReq)
{
	return SendProto(MMAPI_ProtoID_Trd_GetAccList, stReq);
}

u32_t MMAPIImp::UnlockTrade(const Trd_UnlockTrade::Request &stReq)
{
	return SendProto(MMAPI_ProtoID_Trd_UnlockTrade, stReq);
}

u32_t MMAPIImp::SubAccPush(const Trd_SubAccPush::Request &stReq)
{
	return SendProto(MMAPI_ProtoID_Trd_SubAccPush, stReq);
}

u32_t MMAPIImp::GetFunds(const Trd_GetFunds::Request &stReq)
{
	return SendProto(MMAPI_ProtoID_Trd_GetFunds, stReq);
}

u32_t MMAPIImp::GetPositionList(const Trd_GetPositionList::Request &stReq)
{
	return SendProto(MMAPI_ProtoID_Trd_GetPositionList, stReq);
}

u32_t MMAPIImp::GetMaxTrdQtys(const Trd_GetMaxTrdQtys::Request &stReq)
{
	return SendProto(MMAPI_ProtoID_Trd_GetMaxTrdQtys, stReq);
}

u32_t MMAPIImp::GetComboMaxTrdQtys(const Trd_GetComboMaxTrdQtys::Request &stReq)
{
	return SendProto(MMAPI_ProtoID_Trd_GetComboMaxTrdQtys, stReq);
}

u32_t MMAPIImp::GetOrderList(const Trd_GetOrderList::Request &stReq)
{
	return SendProto(MMAPI_ProtoID_Trd_GetOrderList, stReq);
}

u32_t MMAPIImp::PlaceOrder(const Trd_PlaceOrder::Request &stReq)
{
	Trd_PlaceOrder::Request stRealReq;
	stRealReq.CopyFrom(stReq);
	if (stRealReq.has_c2s())
	{
		Common::PacketID *pPacketID = stRealReq.mutable_c2s()->mutable_packetid();
		GetPacketID(*pPacketID);
	}
	return SendProto(MMAPI_ProtoID_Trd_PlaceOrder, stRealReq);
}

u32_t MMAPIImp::PlaceComboOrder(const Trd_PlaceComboOrder::Request &stReq)
{
	Trd_PlaceComboOrder::Request stRealReq;
	stRealReq.CopyFrom(stReq);
	if (stRealReq.has_c2s())
	{
		Common::PacketID *pPacketID = stRealReq.mutable_c2s()->mutable_packetid();
		GetPacketID(*pPacketID);
	}
	return SendProto(MMAPI_ProtoID_Trd_PlaceComboOrder, stRealReq);
}

u32_t MMAPIImp::ModifyOrder(const Trd_ModifyOrder::Request &stReq)
{
	Trd_ModifyOrder::Request stRealReq;
	stRealReq.CopyFrom(stReq);
	if (stRealReq.has_c2s())
	{
		Common::PacketID *pPacketID = stRealReq.mutable_c2s()->mutable_packetid();
		GetPacketID(*pPacketID);
	}
	return SendProto(MMAPI_ProtoID_Trd_ModifyOrder, stRealReq);
}

u32_t MMAPIImp::GetOrderFillList(const Trd_GetOrderFillList::Request &stReq)
{
	return SendProto(MMAPI_ProtoID_Trd_GetOrderFillList, stReq);
}

u32_t MMAPIImp::GetHistoryOrderList(const Trd_GetHistoryOrderList::Request &stReq)
{
	return SendProto(MMAPI_ProtoID_Trd_GetHistoryOrderList, stReq);
}

u32_t MMAPIImp::GetHistoryOrderFillList(const Trd_GetHistoryOrderFillList::Request &stReq)
{
	return SendProto(MMAPI_ProtoID_Trd_GetHistoryOrderFillList, stReq);
}

u32_t MMAPIImp::GetMarginRatio(const Trd_GetMarginRatio::Request &stReq)
{
	return SendProto(MMAPI_ProtoID_Trd_GetMarginRatio, stReq);
}

u32_t MMAPIImp::GetOrderFee(const Trd_GetOrderFee::Request& stReq)
{
    return SendProto(MMAPI_ProtoID_Trd_GetOrderFee, stReq);
}

u32_t MMAPIImp::GetFlowSummary(const Trd_FlowSummary::Request& stReq)
{
    return SendProto(MMAPI_ProtoID_Trd_FlowSummary, stReq);
}

#define OnReplyNotify(strProtoType, strProtoName)	\
	case MMAPI_ProtoID_##strProtoType##_##strProtoName:\
	{\
		strProtoType##_##strProtoName::Response stRsp;\
		if (enReqReplyType == MMAPI_ReqReplyType_SvrReply)\
		{\
			if(!BinData2PbObj(pProtoData, nDataLen, pProtoHeader->nProtoFmtType, stRsp))\
			{\
				stRsp.set_rettype(Common::RetType_Invalid);\
			}\
		}\
		else {stRsp.set_rettype(enReqReplyType);}\
		m_p##strProtoType##Spi->OnReply_##strProtoName(pProtoHeader->nSerialNo, stRsp);\
	}\
	break;

#define OnReplyNotify2(strProtoType, strInterfaceName, strProtoName)	\
	case MMAPI_ProtoID_##strProtoType##_##strProtoName:\
	{\
		strProtoType##_##strProtoName::Response stRsp;\
		if (enReqReplyType == MMAPI_ReqReplyType_SvrReply)\
		{\
			if(!BinData2PbObj(pProtoData, nDataLen, pProtoHeader->nProtoFmtType, stRsp))\
			{\
				stRsp.set_rettype(Common::RetType_Invalid);\
			}\
		}\
		else {stRsp.set_rettype(enReqReplyType);}\
		m_p##strProtoType##Spi->OnReply_##strInterfaceName(pProtoHeader->nSerialNo, stRsp);\
	}\
	break;

#define OnTrdReply(strProto)	OnReplyNotify(Trd, strProto)
#define OnQotReply(strProto)	OnReplyNotify(Qot, strProto)

void MMAPIImp::OnReply(u32_t nConnectID, MMAPI_ReqReplyType enReqReplyType, const MMAPI_ProtoHeader& protoHeader, const i8_t* pProtoData, i32_t nDataLen)
{
	MMAPI_Client::OnReply(nConnectID, enReqReplyType, protoHeader, pProtoData, nDataLen);
	If_ReturnVoid(MMAPI_Client::GetLocalConnectID() != nConnectID);

	CAutoLock(m_safe);
	const MMAPI_ProtoHeader* pProtoHeader = &protoHeader;

	u32_t nProtoID = pProtoHeader->nProtoID;
	If_ReturnVoid(IsTrdPorto(nProtoID) && IsNullPtr(m_pTrdSpi));
	If_ReturnVoid(IsQotPorto(nProtoID) && IsNullPtr(m_pQotSpi));

	switch (nProtoID)
	{
	case MMAPI_ProtoID_GetGlobalState:
		{
			if (IsNotNullPtr(m_pQotSpi))
			{
				GetGlobalState::Response stRsp;
				if (enReqReplyType == MMAPI_ReqReplyType_SvrReply)
				{
					if (!BinData2PbObj(pProtoData, nDataLen, pProtoHeader->nProtoFmtType, stRsp))
					{
						stRsp.set_rettype(Common::RetType_Invalid);
					}
				}
				else
				{
					stRsp.set_rettype(enReqReplyType);
				}
				m_pQotSpi->OnReply_GetGlobalState(pProtoHeader->nSerialNo, stRsp);
			}
		}
		break;
		OnQotReply(Sub);
		OnQotReply(RegQotPush);
		OnQotReply(GetSubInfo);
		OnQotReply(GetTicker);
		OnQotReply(GetBasicQot);
		OnQotReply(GetOrderBook);
		OnQotReply(GetKL);
		OnQotReply(GetRT);
		OnQotReply(GetBroker);
		OnQotReply(RequestRehab);
		OnQotReply(RequestHistoryKL);
		OnQotReply(RequestHistoryKLQuota);
		OnQotReply(GetStaticInfo);
		OnQotReply(GetSecuritySnapshot);
		OnQotReply(GetPlateSet);
		OnQotReply(GetPlateSecurity);
		OnQotReply(GetReference);
		OnQotReply(GetOwnerPlate);
		OnQotReply(GetHoldingChangeList);
		OnQotReply(GetOptionChain);
		OnQotReply(GetWarrant);
		OnQotReply(GetCapitalFlow);
		OnQotReply(GetCapitalDistribution);
		OnQotReply(GetUserSecurity);
		OnQotReply(ModifyUserSecurity);
		OnQotReply(StockFilter);
		OnQotReply(GetCodeChange);
		OnQotReply(GetIpoList);
		OnQotReply(GetFutureInfo);
		OnQotReply(RequestTradeDate);
		OnQotReply(SetPriceReminder);
		OnQotReply(GetPriceReminder);
		OnQotReply(GetUserSecurityGroup);
		OnQotReply(GetMarketState);
		OnQotReply(GetOptionExpirationDate);
		OnQotReply(GetFinancialsEarningsPriceMove);
		OnQotReply(GetFinancialsEarningsPriceHistory);
		OnQotReply(GetFinancialsStatements);
		OnQotReply(GetFinancialsRevenueBreakdown);
		OnQotReply(GetResearchAnalystConsensus);
		OnQotReply(GetResearchRatingSummary);
		OnQotReply(GetResearchMorningstarReport);
		OnQotReply(GetValuationDetail);
		OnQotReply(GetValuationPlateStockList);
		OnQotReply(GetCorporateActionsDividends);
		OnQotReply(GetCorporateActionsBuybacks);
		OnQotReply(GetCorporateActionsStockSplits);
		OnQotReply(GetShareholdersOverview);
		OnQotReply(GetShareholdersHoldingChanges);
		OnQotReply(GetShareholdersHolderDetail);
		OnQotReply(GetShareholdersInstitutional);
		OnQotReply(GetInsiderHolderList);
		OnQotReply(GetInsiderTradeList);
		OnQotReply(GetCompanyProfile);
		OnQotReply(GetCompanyExecutives);
		OnQotReply(GetCompanyExecutiveBackground);
		OnQotReply(GetCompanyOperationalEfficiency);
		OnQotReply(GetTopTenBuySellBrokers);
		OnQotReply(GetDailyShortVolume);
		OnQotReply(GetShortInterest);
		OnQotReply(GetOptionVolatility);
		OnQotReply(GetOptionExerciseProbability);
		OnQotReply(StockScreen);
		OnQotReply(OptionScreen);
		OnQotReply(WarrantScreen);
		OnQotReply(GetOptionQuote);
		OnQotReply(GetOptionStrategy);
		OnQotReply(GetOptionStrategyAnalysis);
		OnQotReply(GetOptionStrategySpread);
		OnQotReply(GetOptionMarketStatistic);
		OnQotReply(GetOptionUnderlyingHisStatistic);
		OnQotReply(GetOptionUnderlyingOverview);
		OnQotReply(GetOptionUnderlyingHisVolatility);
		OnQotReply(GetOptionUnderlyingRank);
		OnQotReply(GetOptionRank);
		OnQotReply(GetOptionEvent);
		OnQotReply(GetOptionEventAlert);
		OnQotReply(SetOptionEventAlert);
		OnQotReply(GetOptionZeroDteScreener);
		OnQotReply(GetOptionZeroDteContract);
		OnQotReply(GetOptionEarningsScreener);
		OnQotReply(GetOptionSellerScreener);
		OnQotReply(GetIndicatorList);
		OnQotReply(RequestIndicatorCalc);
		OnQotReply(GetSearchQuote);
		OnQotReply(GetSearchNews);
		OnQotReply(GetEarningsCalendar);
		OnQotReply(GetMacroIndicatorList);
		OnQotReply(GetMacroIndicatorHistory);
		OnQotReply(GetFedWatchTargetRate);
		OnQotReply(GetFedWatchDotPlot);
		OnQotReply(GetEarningsBeatRank);
		OnQotReply(GetDividendRank);
		OnQotReply(GetDividendCalendar);
		OnQotReply(GetEconomicCalendar);
		OnQotReply(GetUSPreMarketRank);
		OnQotReply(GetUSAfterHoursRank);
		OnQotReply(GetUSOvernightRank);
		OnQotReply(GetTopMoversRank);
		OnQotReply(GetHotList);
		OnQotReply(GetShortSellingRank);
		OnQotReply(GetPeriodChangeRank);
		OnQotReply(GetHighDividendSOERank);
		OnQotReply(GetInstitutionList);
		OnQotReply(GetInstitutionProfile);
		OnQotReply(GetInstitutionDistribution);
		OnQotReply(GetInstitutionHoldingChange);
		OnQotReply(GetInstitutionHoldingList);
		OnQotReply(GetArkFundHolding);
		OnQotReply(GetArkStockDynamic);
		OnQotReply(GetArkActiveTransaction);
		OnQotReply(GetRatingChange);
		OnQotReply(GetIndustrialChainList);
		OnQotReply(GetIndustrialChainDetail);
		OnQotReply(GetIndustrialChainByPlate);
		OnQotReply(GetIndustrialPlateInfo);
		OnQotReply(GetIndustrialPlateStock);
		OnQotReply(GetHeatMapData);
		OnQotReply(GetRiseFallDistribution);

		OnTrdReply(GetAccList);
		OnTrdReply(UnlockTrade);
		OnTrdReply(SubAccPush);
		OnTrdReply(GetFunds);
		OnTrdReply(GetPositionList);
		OnTrdReply(GetMaxTrdQtys);
		OnTrdReply(GetComboMaxTrdQtys);
		OnTrdReply(GetOrderList);
		OnTrdReply(PlaceOrder);
		OnTrdReply(PlaceComboOrder);
		OnTrdReply(ModifyOrder);
		OnTrdReply(GetOrderFillList);
		OnTrdReply(GetHistoryOrderList);
		OnTrdReply(GetHistoryOrderFillList);
		OnTrdReply(GetMarginRatio);
        OnTrdReply(GetOrderFee);
		OnReplyNotify2(Trd, GetFlowSummary, FlowSummary);
	}
}

#define OnPushNotify(strProtoType, strProtoName)	\
	case MMAPI_ProtoID_##strProtoType##_##strProtoName:\
	{\
		strProtoType##_##strProtoName::Response stRsp;\
		if (!BinData2PbObj(pProtoData, nDataLen, pProtoHeader->nProtoFmtType, stRsp))\
		{stRsp.set_rettype(Common::RetType_Invalid);}\
		m_p##strProtoType##Spi->OnPush_##strProtoName(stRsp);\
	}break;

#define OnTrdPush(strProto)	OnPushNotify(Trd, strProto)
#define OnQotPush(strProto)	OnPushNotify(Qot, strProto)

void MMAPIImp::OnPush(u32_t nConnectID, const MMAPI_ProtoHeader& protoHeader, const i8_t* pProtoData, i32_t nDataLen)
{
	MMAPI_Client::OnPush(nConnectID, protoHeader, pProtoData, nDataLen);
	If_ReturnVoid(MMAPI_Client::GetLocalConnectID() != nConnectID);

	CAutoLock(m_safe);
	const MMAPI_ProtoHeader* pProtoHeader = &protoHeader;

	u32_t nProtoID = pProtoHeader->nProtoID;
	If_ReturnVoid(IsTrdPorto(nProtoID) && IsNullPtr(m_pTrdSpi));
	If_ReturnVoid(IsQotPorto(nProtoID) && IsNullPtr(m_pQotSpi));

	switch (nProtoID)
	{
	case MMAPI_ProtoID_Notify:
		{
			if (IsNotNullPtr(m_pQotSpi))
			{
				Notify::Response stRsp;
				if (!BinData2PbObj(pProtoData, nDataLen, pProtoHeader->nProtoFmtType, stRsp))
				{
					stRsp.set_rettype(Common::RetType_Invalid);
				}
				m_pQotSpi->OnPush_Notify(stRsp);
			}
		}
		break;
		OnQotPush(UpdateTicker);
		OnQotPush(UpdateBasicQot);
		OnQotPush(UpdateOrderBook);
		OnQotPush(UpdateKL);
		OnQotPush(UpdateRT);
		OnQotPush(UpdateBroker);
		OnQotPush(UpdatePriceReminder);
		OnQotPush(UpdateOptionEvent);
		OnQotPush(PushIndicatorCalc);

		OnTrdPush(UpdateOrder);
		OnTrdPush(UpdateOrderFill);
	}
}

void MMAPIImp::OnDisConnect(u32_t nConnectID, i64_t nErrCode, APITcpDisConnectType enDisConnType)
{
	MMAPI_Client::OnDisConnect(nConnectID, nErrCode, enDisConnType);
	If_ReturnVoid(MMAPI_Client::GetLocalConnectID() != nConnectID);

	CAutoLock(m_safe);
	If_ReturnVoid(IsNullPtr(m_pConnSpi));
	m_pConnSpi->OnDisConnect(m_pConnApi, nErrCode);
}

void MMAPIImp::OnInitConnect(i64_t nErrCode, const char* strDesc)
{
	MMAPI_Client::OnInitConnect(nErrCode, strDesc);

	CAutoLock(m_safe);
	If_ReturnVoid(IsNullPtr(m_pConnSpi));
	m_pConnSpi->OnInitConnect(m_pConnApi, nErrCode, strDesc);
}

u32_t MMAPIImp::SendProto(u32_t nProtoID, const protobuf::Message& pbObj)
{
    CAutoLock(m_safe);
	Buf_t binData;
	If_OMWarn_Return(!PbObj2BinData(pbObj, binData), 0);
	return MMAPI_Client::Send(nProtoID, 0, binData.data(), ContainerSize(binData));
}
// Copyright 2026 Moomoo
#include "MMAPI.h"
#include "MMSPI.h"
#include "MMAPIImp.h"

MMAPI_Conn::MMAPI_Conn()
{
	m_pImp = new MMAPIImp(this);
	If_Do(IsNotNullPtr(m_pImp), m_pImp->SetProgrammingLanguage("C++"));
}

MMAPI_Conn::~MMAPI_Conn()
{
	UnregisterConnSpi();
	delete m_pImp;
}

void MMAPI_Conn::SetClientInfo(const char* szClientID, i32_t nClientVer)
{
	If_ReturnVoid(IsNullPtr(m_pImp));
	return m_pImp->SetClientInfo(szClientID, nClientVer);
}

void MMAPI_Conn::SetRSAPrivateKey(const char* szRSAPrivateKey)
{
	If_ReturnVoid(IsNullPtr(m_pImp));
	return m_pImp->SetRSAPrivateKey(szRSAPrivateKey);
}

bool MMAPI_Conn::InitConnect(const char* szIPAddr, u16_t nPort, bool bEnableEncrypt)
{
	If_Return(IsNullPtr(m_pImp), false);
	return m_pImp->InitConnect(szIPAddr, nPort, bEnableEncrypt);
}

u64_t MMAPI_Conn::GetConnectID()
{
	If_Return(IsNullPtr(m_pImp), 0);
	return m_pImp->GetConnectID();
}

bool MMAPI_Conn::Close()
{
	If_Return(IsNullPtr(m_pImp), false);
	return m_pImp->Close();
}

void MMAPI_Conn::RegisterConnSpi(MMSPI_Conn* pSpi)
{
	If_ReturnVoid(IsNullPtr(m_pImp));
	return m_pImp->RegisterConnSpi(pSpi);
}

void MMAPI_Conn::UnregisterConnSpi()
{
	If_ReturnVoid(IsNullPtr(m_pImp));
	return m_pImp->UnregisterConnSpi();
}

/////////////////////////////////////////////////////////////////////////////////
//行情

MMAPI_Qot::MMAPI_Qot()
{
}

MMAPI_Qot::~MMAPI_Qot()
{
	UnregisterQotSpi();
}

void MMAPI_Qot::RegisterQotSpi(MMSPI_Qot* pSpi)
{
	If_ReturnVoid(IsNullPtr(m_pImp));
	return m_pImp->RegisterQotSpi(pSpi);
}

void MMAPI_Qot::UnregisterQotSpi()
{
	If_ReturnVoid(IsNullPtr(m_pImp));
	return m_pImp->UnregisterQotSpi();
}

u32_t MMAPI_Qot::Sub(const Qot_Sub::Request &stReq)
{
	If_Return(IsNullPtr(m_pImp), 0);
	return m_pImp->Sub(stReq);
}

u32_t MMAPI_Qot::GetGlobalState(const GetGlobalState::Request &stReq)
{
	If_Return(IsNullPtr(m_pImp), 0);
	return m_pImp->GetGlobalState(stReq);
}

u32_t MMAPI_Qot::RegQotPush(const Qot_RegQotPush::Request &stReq)
{
	If_Return(IsNullPtr(m_pImp), 0);
	return m_pImp->RegQotPush(stReq);
}

u32_t MMAPI_Qot::GetSubInfo(const Qot_GetSubInfo::Request &stReq)
{
	If_Return(IsNullPtr(m_pImp), 0);
	return m_pImp->GetSubInfo(stReq);
}

u32_t MMAPI_Qot::GetTicker(const Qot_GetTicker::Request &stReq)
{
	If_Return(IsNullPtr(m_pImp), 0);
	return m_pImp->GetTicker(stReq);
}

u32_t MMAPI_Qot::GetBasicQot(const Qot_GetBasicQot::Request &stReq)
{
	If_Return(IsNullPtr(m_pImp), 0);
	return m_pImp->GetBasicQot(stReq);
}

u32_t MMAPI_Qot::GetOrderBook(const Qot_GetOrderBook::Request &stReq)
{
	If_Return(IsNullPtr(m_pImp), 0);
	return m_pImp->GetOrderBook(stReq);
}

u32_t MMAPI_Qot::GetKL(const Qot_GetKL::Request &stReq)
{
	If_Return(IsNullPtr(m_pImp), 0);
	return m_pImp->GetKL(stReq);
}

u32_t MMAPI_Qot::GetRT(const Qot_GetRT::Request &stReq)
{
	If_Return(IsNullPtr(m_pImp), 0);
	return m_pImp->GetRT(stReq);
}

u32_t MMAPI_Qot::GetBroker(const Qot_GetBroker::Request &stReq)
{
	If_Return(IsNullPtr(m_pImp), 0);
	return m_pImp->GetBroker(stReq);
}

u32_t MMAPI_Qot::RequestRehab(const Qot_RequestRehab::Request &stReq)
{
	If_Return(IsNullPtr(m_pImp), 0);
	return m_pImp->RequestRehab(stReq);
}

u32_t MMAPI_Qot::RequestHistoryKL(const Qot_RequestHistoryKL::Request &stReq)
{
	If_Return(IsNullPtr(m_pImp), 0);
	return m_pImp->RequestHistoryKL(stReq);
}

u32_t MMAPI_Qot::RequestHistoryKLQuota(const Qot_RequestHistoryKLQuota::Request &stReq)
{
	If_Return(IsNullPtr(m_pImp), 0);
	return m_pImp->RequestHistoryKLQuota(stReq);
}

u32_t MMAPI_Qot::GetStaticInfo(const Qot_GetStaticInfo::Request &stReq)
{
	If_Return(IsNullPtr(m_pImp), 0);
	return m_pImp->GetStaticInfo(stReq);
}

u32_t MMAPI_Qot::GetSecuritySnapshot(const Qot_GetSecuritySnapshot::Request &stReq)
{
	If_Return(IsNullPtr(m_pImp), 0);
	return m_pImp->GetSecuritySnapshot(stReq);
}

u32_t MMAPI_Qot::GetPlateSet(const Qot_GetPlateSet::Request &stReq)
{
	If_Return(IsNullPtr(m_pImp), 0);
	return m_pImp->GetPlateSet(stReq);
}

u32_t MMAPI_Qot::GetPlateSecurity(const Qot_GetPlateSecurity::Request &stReq)
{
	If_Return(IsNullPtr(m_pImp), 0);
	return m_pImp->GetPlateSecurity(stReq);
}

u32_t MMAPI_Qot::GetReference(const Qot_GetReference::Request &stReq)
{
	If_Return(IsNullPtr(m_pImp), 0);
	return m_pImp->GetReference(stReq);
}

u32_t MMAPI_Qot::GetOwnerPlate(const Qot_GetOwnerPlate::Request &stReq)
{
	If_Return(IsNullPtr(m_pImp), 0);
	return m_pImp->GetOwnerPlate(stReq);
}

u32_t MMAPI_Qot::GetHoldingChangeList(const Qot_GetHoldingChangeList::Request &stReq)
{
	If_Return(IsNullPtr(m_pImp), 0);
	return m_pImp->GetHoldingChangeList(stReq);
}

u32_t MMAPI_Qot::GetOptionChain(const Qot_GetOptionChain::Request &stReq)
{
	If_Return(IsNullPtr(m_pImp), 0);
	return m_pImp->GetOptionChain(stReq);
}

u32_t MMAPI_Qot::GetWarrant(const Qot_GetWarrant::Request &stReq)
{
	If_Return(IsNullPtr(m_pImp), 0);
	return m_pImp->GetWarrant(stReq);
}

u32_t MMAPI_Qot::GetCapitalFlow(const Qot_GetCapitalFlow::Request &stReq)
{
	If_Return(IsNullPtr(m_pImp), 0);
	return m_pImp->GetCapitalFlow(stReq);
}

u32_t MMAPI_Qot::GetCapitalDistribution(const Qot_GetCapitalDistribution::Request &stReq)
{
	If_Return(IsNullPtr(m_pImp), 0);
	return m_pImp->GetCapitalDistribution(stReq);
}

u32_t MMAPI_Qot::GetUserSecurity(const Qot_GetUserSecurity::Request &stReq)
{
	If_Return(IsNullPtr(m_pImp), 0);
	return m_pImp->GetUserSecurity(stReq);
}

u32_t MMAPI_Qot::ModifyUserSecurity(const Qot_ModifyUserSecurity::Request &stReq)
{
	If_Return(IsNullPtr(m_pImp), 0);
	return m_pImp->ModifyUserSecurity(stReq);
}

u32_t MMAPI_Qot::StockFilter(const Qot_StockFilter::Request &stReq)
{
	If_Return(IsNullPtr(m_pImp), 0);
	return m_pImp->StockFilter(stReq);
}

Moomoo::u32_t Moomoo::MMAPI_Qot::GetCodeChange(const Qot_GetCodeChange::Request &stReq)
{
	If_Return(IsNullPtr(m_pImp), 0);
	return m_pImp->GetCodeChange(stReq);
}

u32_t MMAPI_Qot::GetIpoList(const Qot_GetIpoList::Request &stReq)
{
	If_Return(IsNullPtr(m_pImp), 0);
	return m_pImp->GetIpoList(stReq);
}

u32_t MMAPI_Qot::GetFutureInfo(const Qot_GetFutureInfo::Request &stReq)
{
	If_Return(IsNullPtr(m_pImp), 0);
	return m_pImp->GetFutureInfo(stReq);
}

u32_t MMAPI_Qot::RequestTradeDate(const Qot_RequestTradeDate::Request &stReq)
{
	If_Return(IsNullPtr(m_pImp), 0);
	return m_pImp->RequestTradeDate(stReq);
}

Moomoo::u32_t MMAPI_Qot::SetPriceReminder(const Qot_SetPriceReminder::Request &stReq)
{
	If_Return(IsNullPtr(m_pImp), 0);
	return m_pImp->SetPriceReminder(stReq);
}

Moomoo::u32_t MMAPI_Qot::GetPriceReminder(const Qot_GetPriceReminder::Request &stReq)
{
	If_Return(IsNullPtr(m_pImp), 0);
	return m_pImp->GetPriceReminder(stReq);
}

Moomoo::u32_t MMAPI_Qot::GetUserSecurityGroup(const Qot_GetUserSecurityGroup::Request &stReq)
{
	If_Return(IsNullPtr(m_pImp), 0);
	return m_pImp->GetUserSecurityGroup(stReq);
}

Moomoo::u32_t MMAPI_Qot::GetMarketState(const Qot_GetMarketState::Request &stReq)
{
	If_Return(IsNullPtr(m_pImp), 0);
	return m_pImp->GetMarketState(stReq);
}

Moomoo::u32_t MMAPI_Qot::GetOptionExpirationDate(const Qot_GetOptionExpirationDate::Request &stReq)
{
	If_Return(IsNullPtr(m_pImp), 0);
	return m_pImp->GetOptionExpirationDate(stReq);
}

Moomoo::u32_t MMAPI_Qot::GetOptionQuote(const Qot_GetOptionQuote::Request &stReq)
{
	If_Return(IsNullPtr(m_pImp), 0);
	return m_pImp->GetOptionQuote(stReq);
}

Moomoo::u32_t MMAPI_Qot::GetOptionStrategy(const Qot_GetOptionStrategy::Request &stReq)
{
	If_Return(IsNullPtr(m_pImp), 0);
	return m_pImp->GetOptionStrategy(stReq);
}

Moomoo::u32_t MMAPI_Qot::GetOptionStrategyAnalysis(const Qot_GetOptionStrategyAnalysis::Request &stReq)
{
	If_Return(IsNullPtr(m_pImp), 0);
	return m_pImp->GetOptionStrategyAnalysis(stReq);
}

Moomoo::u32_t MMAPI_Qot::GetOptionStrategySpread(const Qot_GetOptionStrategySpread::Request &stReq)
{
	If_Return(IsNullPtr(m_pImp), 0);
	return m_pImp->GetOptionStrategySpread(stReq);
}

Moomoo::u32_t MMAPI_Qot::GetFinancialsEarningsPriceMove(const Qot_GetFinancialsEarningsPriceMove::Request &stReq)
{
	If_Return(IsNullPtr(m_pImp), 0);
	return m_pImp->GetFinancialsEarningsPriceMove(stReq);
}

Moomoo::u32_t MMAPI_Qot::GetFinancialsEarningsPriceHistory(const Qot_GetFinancialsEarningsPriceHistory::Request &stReq)
{
	If_Return(IsNullPtr(m_pImp), 0);
	return m_pImp->GetFinancialsEarningsPriceHistory(stReq);
}

Moomoo::u32_t MMAPI_Qot::GetFinancialsStatements(const Qot_GetFinancialsStatements::Request &stReq)
{
	If_Return(IsNullPtr(m_pImp), 0);
	return m_pImp->GetFinancialsStatements(stReq);
}

Moomoo::u32_t MMAPI_Qot::GetFinancialsRevenueBreakdown(const Qot_GetFinancialsRevenueBreakdown::Request &stReq)
{
	If_Return(IsNullPtr(m_pImp), 0);
	return m_pImp->GetFinancialsRevenueBreakdown(stReq);
}

Moomoo::u32_t MMAPI_Qot::GetResearchAnalystConsensus(const Qot_GetResearchAnalystConsensus::Request &stReq)
{
	If_Return(IsNullPtr(m_pImp), 0);
	return m_pImp->GetResearchAnalystConsensus(stReq);
}

Moomoo::u32_t MMAPI_Qot::GetResearchRatingSummary(const Qot_GetResearchRatingSummary::Request &stReq)
{
	If_Return(IsNullPtr(m_pImp), 0);
	return m_pImp->GetResearchRatingSummary(stReq);
}

Moomoo::u32_t MMAPI_Qot::GetResearchMorningstarReport(const Qot_GetResearchMorningstarReport::Request &stReq)
{
	If_Return(IsNullPtr(m_pImp), 0);
	return m_pImp->GetResearchMorningstarReport(stReq);
}

Moomoo::u32_t MMAPI_Qot::GetValuationDetail(const Qot_GetValuationDetail::Request &stReq)
{
	If_Return(IsNullPtr(m_pImp), 0);
	return m_pImp->GetValuationDetail(stReq);
}

Moomoo::u32_t MMAPI_Qot::GetValuationPlateStockList(const Qot_GetValuationPlateStockList::Request &stReq)
{
	If_Return(IsNullPtr(m_pImp), 0);
	return m_pImp->GetValuationPlateStockList(stReq);
}

Moomoo::u32_t MMAPI_Qot::GetCorporateActionsDividends(const Qot_GetCorporateActionsDividends::Request &stReq)
{
	If_Return(IsNullPtr(m_pImp), 0);
	return m_pImp->GetCorporateActionsDividends(stReq);
}

Moomoo::u32_t MMAPI_Qot::GetCorporateActionsBuybacks(const Qot_GetCorporateActionsBuybacks::Request &stReq)
{
	If_Return(IsNullPtr(m_pImp), 0);
	return m_pImp->GetCorporateActionsBuybacks(stReq);
}

Moomoo::u32_t MMAPI_Qot::GetCorporateActionsStockSplits(const Qot_GetCorporateActionsStockSplits::Request &stReq)
{
	If_Return(IsNullPtr(m_pImp), 0);
	return m_pImp->GetCorporateActionsStockSplits(stReq);
}

Moomoo::u32_t MMAPI_Qot::GetShareholdersOverview(const Qot_GetShareholdersOverview::Request &stReq)
{
	If_Return(IsNullPtr(m_pImp), 0);
	return m_pImp->GetShareholdersOverview(stReq);
}

Moomoo::u32_t MMAPI_Qot::GetShareholdersHoldingChanges(const Qot_GetShareholdersHoldingChanges::Request &stReq)
{
	If_Return(IsNullPtr(m_pImp), 0);
	return m_pImp->GetShareholdersHoldingChanges(stReq);
}

Moomoo::u32_t MMAPI_Qot::GetShareholdersHolderDetail(const Qot_GetShareholdersHolderDetail::Request &stReq)
{
	If_Return(IsNullPtr(m_pImp), 0);
	return m_pImp->GetShareholdersHolderDetail(stReq);
}

Moomoo::u32_t MMAPI_Qot::GetShareholdersInstitutional(const Qot_GetShareholdersInstitutional::Request &stReq)
{
	If_Return(IsNullPtr(m_pImp), 0);
	return m_pImp->GetShareholdersInstitutional(stReq);
}

Moomoo::u32_t MMAPI_Qot::GetInsiderHolderList(const Qot_GetInsiderHolderList::Request &stReq)
{
	If_Return(IsNullPtr(m_pImp), 0);
	return m_pImp->GetInsiderHolderList(stReq);
}

Moomoo::u32_t MMAPI_Qot::GetInsiderTradeList(const Qot_GetInsiderTradeList::Request &stReq)
{
	If_Return(IsNullPtr(m_pImp), 0);
	return m_pImp->GetInsiderTradeList(stReq);
}

Moomoo::u32_t MMAPI_Qot::GetCompanyProfile(const Qot_GetCompanyProfile::Request &stReq)
{
	If_Return(IsNullPtr(m_pImp), 0);
	return m_pImp->GetCompanyProfile(stReq);
}

Moomoo::u32_t MMAPI_Qot::GetCompanyExecutives(const Qot_GetCompanyExecutives::Request &stReq)
{
	If_Return(IsNullPtr(m_pImp), 0);
	return m_pImp->GetCompanyExecutives(stReq);
}

Moomoo::u32_t MMAPI_Qot::GetCompanyExecutiveBackground(const Qot_GetCompanyExecutiveBackground::Request &stReq)
{
	If_Return(IsNullPtr(m_pImp), 0);
	return m_pImp->GetCompanyExecutiveBackground(stReq);
}

Moomoo::u32_t MMAPI_Qot::GetCompanyOperationalEfficiency(const Qot_GetCompanyOperationalEfficiency::Request &stReq)
{
	If_Return(IsNullPtr(m_pImp), 0);
	return m_pImp->GetCompanyOperationalEfficiency(stReq);
}

Moomoo::u32_t MMAPI_Qot::GetTopTenBuySellBrokers(const Qot_GetTopTenBuySellBrokers::Request &stReq)
{
	If_Return(IsNullPtr(m_pImp), 0);
	return m_pImp->GetTopTenBuySellBrokers(stReq);
}

Moomoo::u32_t MMAPI_Qot::GetDailyShortVolume(const Qot_GetDailyShortVolume::Request &stReq)
{
	If_Return(IsNullPtr(m_pImp), 0);
	return m_pImp->GetDailyShortVolume(stReq);
}

Moomoo::u32_t MMAPI_Qot::GetShortInterest(const Qot_GetShortInterest::Request &stReq)
{
	If_Return(IsNullPtr(m_pImp), 0);
	return m_pImp->GetShortInterest(stReq);
}

Moomoo::u32_t MMAPI_Qot::GetOptionVolatility(const Qot_GetOptionVolatility::Request &stReq)
{
	If_Return(IsNullPtr(m_pImp), 0);
	return m_pImp->GetOptionVolatility(stReq);
}

Moomoo::u32_t MMAPI_Qot::GetOptionExerciseProbability(const Qot_GetOptionExerciseProbability::Request &stReq)
{
	If_Return(IsNullPtr(m_pImp), 0);
	return m_pImp->GetOptionExerciseProbability(stReq);
}

Moomoo::u32_t MMAPI_Qot::StockScreen(const Qot_StockScreen::Request &stReq)
{
	If_Return(IsNullPtr(m_pImp), 0);
	return m_pImp->StockScreen(stReq);
}

Moomoo::u32_t MMAPI_Qot::OptionScreen(const Qot_OptionScreen::Request &stReq)
{
	If_Return(IsNullPtr(m_pImp), 0);
	return m_pImp->OptionScreen(stReq);
}

Moomoo::u32_t MMAPI_Qot::WarrantScreen(const Qot_WarrantScreen::Request &stReq)
{
	If_Return(IsNullPtr(m_pImp), 0);
	return m_pImp->WarrantScreen(stReq);
}

Moomoo::u32_t MMAPI_Qot::GetOptionMarketStatistic(const Qot_GetOptionMarketStatistic::Request &stReq)
{
	If_Return(IsNullPtr(m_pImp), 0);
	return m_pImp->GetOptionMarketStatistic(stReq);
}

Moomoo::u32_t MMAPI_Qot::GetOptionUnderlyingHisStatistic(const Qot_GetOptionUnderlyingHisStatistic::Request &stReq)
{
	If_Return(IsNullPtr(m_pImp), 0);
	return m_pImp->GetOptionUnderlyingHisStatistic(stReq);
}

Moomoo::u32_t MMAPI_Qot::GetOptionUnderlyingOverview(const Qot_GetOptionUnderlyingOverview::Request &stReq)
{
	If_Return(IsNullPtr(m_pImp), 0);
	return m_pImp->GetOptionUnderlyingOverview(stReq);
}

Moomoo::u32_t MMAPI_Qot::GetOptionUnderlyingHisVolatility(const Qot_GetOptionUnderlyingHisVolatility::Request &stReq)
{
	If_Return(IsNullPtr(m_pImp), 0);
	return m_pImp->GetOptionUnderlyingHisVolatility(stReq);
}

Moomoo::u32_t MMAPI_Qot::GetOptionUnderlyingRank(const Qot_GetOptionUnderlyingRank::Request &stReq)
{
	If_Return(IsNullPtr(m_pImp), 0);
	return m_pImp->GetOptionUnderlyingRank(stReq);
}

Moomoo::u32_t MMAPI_Qot::GetOptionRank(const Qot_GetOptionRank::Request &stReq)
{
	If_Return(IsNullPtr(m_pImp), 0);
	return m_pImp->GetOptionRank(stReq);
}

Moomoo::u32_t MMAPI_Qot::GetOptionEvent(const Qot_GetOptionEvent::Request &stReq)
{
	If_Return(IsNullPtr(m_pImp), 0);
	return m_pImp->GetOptionEvent(stReq);
}

Moomoo::u32_t MMAPI_Qot::GetOptionEventAlert(const Qot_GetOptionEventAlert::Request &stReq)
{
	If_Return(IsNullPtr(m_pImp), 0);
	return m_pImp->GetOptionEventAlert(stReq);
}

Moomoo::u32_t MMAPI_Qot::SetOptionEventAlert(const Qot_SetOptionEventAlert::Request &stReq)
{
	If_Return(IsNullPtr(m_pImp), 0);
	return m_pImp->SetOptionEventAlert(stReq);
}

Moomoo::u32_t MMAPI_Qot::GetOptionZeroDteScreener(const Qot_GetOptionZeroDteScreener::Request &stReq)
{
	If_Return(IsNullPtr(m_pImp), 0);
	return m_pImp->GetOptionZeroDteScreener(stReq);
}

Moomoo::u32_t MMAPI_Qot::GetOptionZeroDteContract(const Qot_GetOptionZeroDteContract::Request &stReq)
{
	If_Return(IsNullPtr(m_pImp), 0);
	return m_pImp->GetOptionZeroDteContract(stReq);
}

Moomoo::u32_t MMAPI_Qot::GetOptionEarningsScreener(const Qot_GetOptionEarningsScreener::Request &stReq)
{
	If_Return(IsNullPtr(m_pImp), 0);
	return m_pImp->GetOptionEarningsScreener(stReq);
}

Moomoo::u32_t MMAPI_Qot::GetOptionSellerScreener(const Qot_GetOptionSellerScreener::Request &stReq)
{
	If_Return(IsNullPtr(m_pImp), 0);
	return m_pImp->GetOptionSellerScreener(stReq);
}

Moomoo::u32_t MMAPI_Qot::GetIndicatorList(const Qot_GetIndicatorList::Request &stReq)
{
	If_Return(IsNullPtr(m_pImp), 0);
	return m_pImp->GetIndicatorList(stReq);
}

Moomoo::u32_t MMAPI_Qot::RequestIndicatorCalc(const Qot_RequestIndicatorCalc::Request &stReq)
{
	If_Return(IsNullPtr(m_pImp), 0);
	return m_pImp->RequestIndicatorCalc(stReq);
}

Moomoo::u32_t MMAPI_Qot::GetSearchQuote(const Qot_GetSearchQuote::Request &stReq)
{
	If_Return(IsNullPtr(m_pImp), 0);
	return m_pImp->GetSearchQuote(stReq);
}

Moomoo::u32_t MMAPI_Qot::GetSearchNews(const Qot_GetSearchNews::Request &stReq)
{
	If_Return(IsNullPtr(m_pImp), 0);
	return m_pImp->GetSearchNews(stReq);
}

Moomoo::u32_t MMAPI_Qot::GetEarningsCalendar(const Qot_GetEarningsCalendar::Request &stReq)
{
	If_Return(IsNullPtr(m_pImp), 0);
	return m_pImp->GetEarningsCalendar(stReq);
}

Moomoo::u32_t MMAPI_Qot::GetMacroIndicatorList(const Qot_GetMacroIndicatorList::Request &stReq)
{
	If_Return(IsNullPtr(m_pImp), 0);
	return m_pImp->GetMacroIndicatorList(stReq);
}

Moomoo::u32_t MMAPI_Qot::GetMacroIndicatorHistory(const Qot_GetMacroIndicatorHistory::Request &stReq)
{
	If_Return(IsNullPtr(m_pImp), 0);
	return m_pImp->GetMacroIndicatorHistory(stReq);
}

Moomoo::u32_t MMAPI_Qot::GetFedWatchTargetRate(const Qot_GetFedWatchTargetRate::Request &stReq)
{
	If_Return(IsNullPtr(m_pImp), 0);
	return m_pImp->GetFedWatchTargetRate(stReq);
}

Moomoo::u32_t MMAPI_Qot::GetFedWatchDotPlot(const Qot_GetFedWatchDotPlot::Request &stReq)
{
	If_Return(IsNullPtr(m_pImp), 0);
	return m_pImp->GetFedWatchDotPlot(stReq);
}

Moomoo::u32_t MMAPI_Qot::GetEarningsBeatRank(const Qot_GetEarningsBeatRank::Request &stReq)
{
	If_Return(IsNullPtr(m_pImp), 0);
	return m_pImp->GetEarningsBeatRank(stReq);
}

Moomoo::u32_t MMAPI_Qot::GetDividendRank(const Qot_GetDividendRank::Request &stReq)
{
	If_Return(IsNullPtr(m_pImp), 0);
	return m_pImp->GetDividendRank(stReq);
}

Moomoo::u32_t MMAPI_Qot::GetDividendCalendar(const Qot_GetDividendCalendar::Request &stReq)
{
	If_Return(IsNullPtr(m_pImp), 0);
	return m_pImp->GetDividendCalendar(stReq);
}

Moomoo::u32_t MMAPI_Qot::GetEconomicCalendar(const Qot_GetEconomicCalendar::Request &stReq)
{
	If_Return(IsNullPtr(m_pImp), 0);
	return m_pImp->GetEconomicCalendar(stReq);
}

Moomoo::u32_t MMAPI_Qot::GetUSPreMarketRank(const Qot_GetUSPreMarketRank::Request &stReq)
{
	If_Return(IsNullPtr(m_pImp), 0);
	return m_pImp->GetUSPreMarketRank(stReq);
}

Moomoo::u32_t MMAPI_Qot::GetUSAfterHoursRank(const Qot_GetUSAfterHoursRank::Request &stReq)
{
	If_Return(IsNullPtr(m_pImp), 0);
	return m_pImp->GetUSAfterHoursRank(stReq);
}

Moomoo::u32_t MMAPI_Qot::GetUSOvernightRank(const Qot_GetUSOvernightRank::Request &stReq)
{
	If_Return(IsNullPtr(m_pImp), 0);
	return m_pImp->GetUSOvernightRank(stReq);
}

Moomoo::u32_t MMAPI_Qot::GetTopMoversRank(const Qot_GetTopMoversRank::Request &stReq)
{
	If_Return(IsNullPtr(m_pImp), 0);
	return m_pImp->GetTopMoversRank(stReq);
}

Moomoo::u32_t MMAPI_Qot::GetHotList(const Qot_GetHotList::Request &stReq)
{
	If_Return(IsNullPtr(m_pImp), 0);
	return m_pImp->GetHotList(stReq);
}

Moomoo::u32_t MMAPI_Qot::GetShortSellingRank(const Qot_GetShortSellingRank::Request &stReq)
{
	If_Return(IsNullPtr(m_pImp), 0);
	return m_pImp->GetShortSellingRank(stReq);
}

Moomoo::u32_t MMAPI_Qot::GetPeriodChangeRank(const Qot_GetPeriodChangeRank::Request &stReq)
{
	If_Return(IsNullPtr(m_pImp), 0);
	return m_pImp->GetPeriodChangeRank(stReq);
}

Moomoo::u32_t MMAPI_Qot::GetHighDividendSOERank(const Qot_GetHighDividendSOERank::Request &stReq)
{
	If_Return(IsNullPtr(m_pImp), 0);
	return m_pImp->GetHighDividendSOERank(stReq);
}

Moomoo::u32_t MMAPI_Qot::GetInstitutionList(const Qot_GetInstitutionList::Request &stReq)
{
	If_Return(IsNullPtr(m_pImp), 0);
	return m_pImp->GetInstitutionList(stReq);
}

Moomoo::u32_t MMAPI_Qot::GetInstitutionProfile(const Qot_GetInstitutionProfile::Request &stReq)
{
	If_Return(IsNullPtr(m_pImp), 0);
	return m_pImp->GetInstitutionProfile(stReq);
}

Moomoo::u32_t MMAPI_Qot::GetInstitutionDistribution(const Qot_GetInstitutionDistribution::Request &stReq)
{
	If_Return(IsNullPtr(m_pImp), 0);
	return m_pImp->GetInstitutionDistribution(stReq);
}

Moomoo::u32_t MMAPI_Qot::GetInstitutionHoldingChange(const Qot_GetInstitutionHoldingChange::Request &stReq)
{
	If_Return(IsNullPtr(m_pImp), 0);
	return m_pImp->GetInstitutionHoldingChange(stReq);
}

Moomoo::u32_t MMAPI_Qot::GetInstitutionHoldingList(const Qot_GetInstitutionHoldingList::Request &stReq)
{
	If_Return(IsNullPtr(m_pImp), 0);
	return m_pImp->GetInstitutionHoldingList(stReq);
}

Moomoo::u32_t MMAPI_Qot::GetArkFundHolding(const Qot_GetArkFundHolding::Request &stReq)
{
	If_Return(IsNullPtr(m_pImp), 0);
	return m_pImp->GetArkFundHolding(stReq);
}

Moomoo::u32_t MMAPI_Qot::GetArkStockDynamic(const Qot_GetArkStockDynamic::Request &stReq)
{
	If_Return(IsNullPtr(m_pImp), 0);
	return m_pImp->GetArkStockDynamic(stReq);
}

Moomoo::u32_t MMAPI_Qot::GetArkActiveTransaction(const Qot_GetArkActiveTransaction::Request &stReq)
{
	If_Return(IsNullPtr(m_pImp), 0);
	return m_pImp->GetArkActiveTransaction(stReq);
}

Moomoo::u32_t MMAPI_Qot::GetRatingChange(const Qot_GetRatingChange::Request &stReq)
{
	If_Return(IsNullPtr(m_pImp), 0);
	return m_pImp->GetRatingChange(stReq);
}

Moomoo::u32_t MMAPI_Qot::GetIndustrialChainList(const Qot_GetIndustrialChainList::Request &stReq)
{
	If_Return(IsNullPtr(m_pImp), 0);
	return m_pImp->GetIndustrialChainList(stReq);
}

Moomoo::u32_t MMAPI_Qot::GetIndustrialChainDetail(const Qot_GetIndustrialChainDetail::Request &stReq)
{
	If_Return(IsNullPtr(m_pImp), 0);
	return m_pImp->GetIndustrialChainDetail(stReq);
}

Moomoo::u32_t MMAPI_Qot::GetIndustrialChainByPlate(const Qot_GetIndustrialChainByPlate::Request &stReq)
{
	If_Return(IsNullPtr(m_pImp), 0);
	return m_pImp->GetIndustrialChainByPlate(stReq);
}

Moomoo::u32_t MMAPI_Qot::GetIndustrialPlateInfo(const Qot_GetIndustrialPlateInfo::Request &stReq)
{
	If_Return(IsNullPtr(m_pImp), 0);
	return m_pImp->GetIndustrialPlateInfo(stReq);
}

Moomoo::u32_t MMAPI_Qot::GetIndustrialPlateStock(const Qot_GetIndustrialPlateStock::Request &stReq)
{
	If_Return(IsNullPtr(m_pImp), 0);
	return m_pImp->GetIndustrialPlateStock(stReq);
}

Moomoo::u32_t MMAPI_Qot::GetHeatMapData(const Qot_GetHeatMapData::Request &stReq)
{
	If_Return(IsNullPtr(m_pImp), 0);
	return m_pImp->GetHeatMapData(stReq);
}

Moomoo::u32_t MMAPI_Qot::GetRiseFallDistribution(const Qot_GetRiseFallDistribution::Request &stReq)
{
	If_Return(IsNullPtr(m_pImp), 0);
	return m_pImp->GetRiseFallDistribution(stReq);
}

/////////////////////////////////////////////////////////////////////////////////
//交易

MMAPI_Trd::MMAPI_Trd()
{
}

MMAPI_Trd::~MMAPI_Trd()
{
	UnregisterTrdSpi();
}

void MMAPI_Trd::RegisterTrdSpi(MMSPI_Trd* pSpi)
{
	If_ReturnVoid(IsNullPtr(m_pImp));
	return m_pImp->RegisterTrdSpi(pSpi);
}

void MMAPI_Trd::UnregisterTrdSpi()
{
	If_ReturnVoid(IsNullPtr(m_pImp));
	return m_pImp->UnregisterTrdSpi();
}

bool MMAPI_Trd::GetPacketID(Common::PacketID &stPacketID)
{
	If_Return(IsNullPtr(m_pImp), false);
	return m_pImp->GetPacketID(stPacketID);
}

u32_t MMAPI_Trd::GetAccList(const Trd_GetAccList::Request &stReq)
{
	If_Return(IsNullPtr(m_pImp), 0);
	return m_pImp->GetAccList(stReq);
}

u32_t MMAPI_Trd::UnlockTrade(const Trd_UnlockTrade::Request &stReq)
{
	If_Return(IsNullPtr(m_pImp), 0);
	return m_pImp->UnlockTrade(stReq);
}

u32_t MMAPI_Trd::SubAccPush(const Trd_SubAccPush::Request &stReq)
{
	If_Return(IsNullPtr(m_pImp), 0);
	return m_pImp->SubAccPush(stReq);
}

u32_t MMAPI_Trd::GetFunds(const Trd_GetFunds::Request &stReq)
{
	If_Return(IsNullPtr(m_pImp), 0);
	return m_pImp->GetFunds(stReq);
}

u32_t MMAPI_Trd::GetPositionList(const Trd_GetPositionList::Request &stReq)
{
	If_Return(IsNullPtr(m_pImp), 0);
	return m_pImp->GetPositionList(stReq);
}

u32_t MMAPI_Trd::GetMaxTrdQtys(const Trd_GetMaxTrdQtys::Request &stReq)
{
	If_Return(IsNullPtr(m_pImp), 0);
	return m_pImp->GetMaxTrdQtys(stReq);
}

u32_t MMAPI_Trd::GetComboMaxTrdQtys(const Trd_GetComboMaxTrdQtys::Request &stReq)
{
	If_Return(IsNullPtr(m_pImp), 0);
	return m_pImp->GetComboMaxTrdQtys(stReq);
}

u32_t MMAPI_Trd::GetOrderList(const Trd_GetOrderList::Request &stReq)
{
	If_Return(IsNullPtr(m_pImp), 0);
	return m_pImp->GetOrderList(stReq);
}

u32_t MMAPI_Trd::PlaceOrder(const Trd_PlaceOrder::Request &stReq)
{
	If_Return(IsNullPtr(m_pImp), 0);
	return m_pImp->PlaceOrder(stReq);
}

u32_t MMAPI_Trd::PlaceComboOrder(const Trd_PlaceComboOrder::Request &stReq)
{
	If_Return(IsNullPtr(m_pImp), 0);
	return m_pImp->PlaceComboOrder(stReq);
}

u32_t MMAPI_Trd::ModifyOrder(const Trd_ModifyOrder::Request &stReq)
{
	If_Return(IsNullPtr(m_pImp), 0);
	return m_pImp->ModifyOrder(stReq);
}

u32_t MMAPI_Trd::GetOrderFillList(const Trd_GetOrderFillList::Request &stReq)
{
	If_Return(IsNullPtr(m_pImp), 0);
	return m_pImp->GetOrderFillList(stReq);
}

u32_t MMAPI_Trd::GetHistoryOrderList(const Trd_GetHistoryOrderList::Request &stReq)
{
	If_Return(IsNullPtr(m_pImp), 0);
	return m_pImp->GetHistoryOrderList(stReq);
}

u32_t MMAPI_Trd::GetHistoryOrderFillList(const Trd_GetHistoryOrderFillList::Request &stReq)
{
	If_Return(IsNullPtr(m_pImp), 0);
	return m_pImp->GetHistoryOrderFillList(stReq);
}

u32_t MMAPI_Trd::GetMarginRatio(const Trd_GetMarginRatio::Request &stReq)
{
	If_Return(IsNullPtr(m_pImp), 0);
	return m_pImp->GetMarginRatio(stReq);
}

u32_t MMAPI_Trd::GetOrderFee(const Trd_GetOrderFee::Request& stReq)
{
    If_Return(IsNullPtr(m_pImp), 0);
    return m_pImp->GetOrderFee(stReq);
}

u32_t MMAPI_Trd::GetFlowSummary(const Trd_FlowSummary::Request& stReq)
{
    If_Return(IsNullPtr(m_pImp), 0);
    return m_pImp->GetFlowSummary(stReq);
}

MMAPI_Qot* MMAPI::CreateQotApi()
{
	return new MMAPI_Qot();
}

void MMAPI::ReleaseQotApi(MMAPI_Qot* pQot)
{
	delete pQot;
}

MMAPI_Trd* MMAPI::CreateTrdApi()
{
	return new MMAPI_Trd();
}

void MMAPI::ReleaseTrdApi(MMAPI_Trd* pTrd)
{
	delete pTrd;
}

void MMAPI::Init()
{
	MMAPIChannel_Init();
}

void MMAPI::UnInit()
{
	MMAPIChannel_UnInit();
}
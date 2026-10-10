#pragma once
#include "tool.h"

class FTAPIDemoBase : public MMSPI_Qot, public MMSPI_Trd, public MMSPI_Conn
{
public:
	FTAPIDemoBase();
	~FTAPIDemoBase();

	//连接OpenD
	bool InitQot(const char *szIP, uint16_t nPort);
	void UnInitQot();

	//连接OpenD，解锁，订阅交易推送
	bool InitTrd(const char *szIP, uint16_t nPort, const char *szPwdMD5, Trd_Common::SecurityFirm enFirm = Trd_Common::SecurityFirm_FutuSecurities);
	void UnInitTrd();

private:
	void Unlock(const char *szPwdMD5, Trd_Common::SecurityFirm enFirm);
	void GetAccListAndSubTradePush();

protected:
	//注意不能在OnReply_XXX或者OnPush_XXX回调里面调用WaitReply(GetXXX)，否则会m_pSem与API内部的锁构成死锁
	//这种场景请自行异步处理，本范例只是为了代码简便使用了简单的同步
	void WaitReply(int32_t nSerilNo);
	void PostReply();
	uint64_t GetFirstAccID(Trd_Common::TrdMarket enTrdMarket, Trd_Common::TrdEnv enTrdEnv);

protected:
	MMAPI_Qot *m_pQotApi;
	bool m_bQotInitSuc;

	MMAPI_Trd *m_pTrdApi;
	bool m_bTrdInitSuc;
    vector<pair<uint64_t, set<int32_t>>> m_vRealAccID;
    vector<pair<uint64_t, set<int32_t>>> m_vSimAccID;
	set<uint64_t> m_setAllAccID;

	Semaphore *m_pSem;

protected:
	virtual void OnInitConnect(MMAPI_Conn* pConn, Moomoo::i64_t nErrCode, const char* strDesc);
	virtual void OnDisConnect(MMAPI_Conn* pConn, Moomoo::i64_t nErrCode){}

protected:
	virtual void OnReply_GetGlobalState(Moomoo::u32_t nSerialNo, const GetGlobalState::Response &stRsp){}
	virtual void OnReply_Sub(Moomoo::u32_t nSerialNo, const Qot_Sub::Response &stRsp){}
	virtual void OnReply_RegQotPush(Moomoo::u32_t nSerialNo, const Qot_RegQotPush::Response &stRsp){}
	virtual void OnReply_GetSubInfo(Moomoo::u32_t nSerialNo, const Qot_GetSubInfo::Response &stRsp){}
	virtual void OnReply_GetTicker(Moomoo::u32_t nSerialNo, const Qot_GetTicker::Response &stRsp){}
	virtual void OnReply_GetBasicQot(Moomoo::u32_t nSerialNo, const Qot_GetBasicQot::Response &stRsp){}
	virtual void OnReply_GetOrderBook(Moomoo::u32_t nSerialNo, const Qot_GetOrderBook::Response &stRsp){}
	virtual void OnReply_GetKL(Moomoo::u32_t nSerialNo, const Qot_GetKL::Response &stRsp){}
	virtual void OnReply_GetRT(Moomoo::u32_t nSerialNo, const Qot_GetRT::Response &stRsp){}
	virtual void OnReply_GetBroker(Moomoo::u32_t nSerialNo, const Qot_GetBroker::Response &stRsp){}
	virtual void OnReply_RequestRehab(Moomoo::u32_t nSerialNo, const Qot_RequestRehab::Response &stRsp){}
	virtual void OnReply_RequestHistoryKL(Moomoo::u32_t nSerialNo, const Qot_RequestHistoryKL::Response &stRsp){}
	virtual void OnReply_RequestHistoryKLQuota(Moomoo::u32_t nSerialNo, const Qot_RequestHistoryKLQuota::Response &stRsp){}
	virtual void OnReply_GetStaticInfo(Moomoo::u32_t nSerialNo, const Qot_GetStaticInfo::Response &stRsp){}
	virtual void OnReply_GetSecuritySnapshot(Moomoo::u32_t nSerialNo, const Qot_GetSecuritySnapshot::Response &stRsp){}
	virtual void OnReply_GetPlateSet(Moomoo::u32_t nSerialNo, const Qot_GetPlateSet::Response &stRsp){}
	virtual void OnReply_GetPlateSecurity(Moomoo::u32_t nSerialNo, const Qot_GetPlateSecurity::Response &stRsp){}
	virtual void OnReply_GetReference(Moomoo::u32_t nSerialNo, const Qot_GetReference::Response &stRsp){}
	virtual void OnReply_GetOwnerPlate(Moomoo::u32_t nSerialNo, const Qot_GetOwnerPlate::Response &stRsp){}
	virtual void OnReply_GetHoldingChangeList(Moomoo::u32_t nSerialNo, const Qot_GetHoldingChangeList::Response &stRsp){}
	virtual void OnReply_GetOptionChain(Moomoo::u32_t nSerialNo, const Qot_GetOptionChain::Response &stRsp){}
	virtual void OnReply_GetWarrant(Moomoo::u32_t nSerialNo, const Qot_GetWarrant::Response &stRsp){}
	virtual void OnReply_GetCapitalFlow(Moomoo::u32_t nSerialNo, const Qot_GetCapitalFlow::Response &stRsp){}
	virtual void OnReply_GetCapitalDistribution(Moomoo::u32_t nSerialNo, const Qot_GetCapitalDistribution::Response &stRsp){}
	virtual void OnReply_GetUserSecurity(Moomoo::u32_t nSerialNo, const Qot_GetUserSecurity::Response &stRsp){}
	virtual void OnReply_ModifyUserSecurity(Moomoo::u32_t nSerialNo, const Qot_ModifyUserSecurity::Response &stRsp){}
	virtual void OnReply_StockFilter(Moomoo::u32_t nSerialNo, const Qot_StockFilter::Response &stRsp){}
	virtual void OnReply_GetCodeChange(Moomoo::u32_t nSerialNo, const Qot_GetCodeChange::Response &stRsp){}
	virtual void OnReply_GetIpoList(Moomoo::u32_t nSerialNo, const Qot_GetIpoList::Response &stRsp){}
	virtual void OnReply_GetFutureInfo(Moomoo::u32_t nSerialNo, const Qot_GetFutureInfo::Response &stRsp){}
	virtual void OnReply_RequestTradeDate(Moomoo::u32_t nSerialNo, const Qot_RequestTradeDate::Response &stRsp){}
	virtual void OnReply_SetPriceReminder(Moomoo::u32_t nSerialNo, const Qot_SetPriceReminder::Response &stRsp){}
	virtual void OnReply_GetPriceReminder(Moomoo::u32_t nSerialNo, const Qot_GetPriceReminder::Response &stRsp){}
	virtual void OnReply_GetUserSecurityGroup(Moomoo::u32_t nSerialNo, const Qot_GetUserSecurityGroup::Response &stRsp){}
	virtual void OnReply_GetMarketState(Moomoo::u32_t nSerialNo, const Qot_GetMarketState::Response &stRsp){}
	virtual void OnReply_GetOptionExpirationDate(Moomoo::u32_t nSerialNo, const Qot_GetOptionExpirationDate::Response &stRsp){}
	virtual void OnReply_GetFinancialsEarningsPriceMove(Moomoo::u32_t nSerialNo, const Qot_GetFinancialsEarningsPriceMove::Response &stRsp){}
	virtual void OnReply_GetFinancialsEarningsPriceHistory(Moomoo::u32_t nSerialNo, const Qot_GetFinancialsEarningsPriceHistory::Response &stRsp){}
	virtual void OnReply_GetFinancialsStatements(Moomoo::u32_t nSerialNo, const Qot_GetFinancialsStatements::Response &stRsp){}
	virtual void OnReply_GetFinancialsRevenueBreakdown(Moomoo::u32_t nSerialNo, const Qot_GetFinancialsRevenueBreakdown::Response &stRsp){}
	virtual void OnReply_GetResearchAnalystConsensus(Moomoo::u32_t nSerialNo, const Qot_GetResearchAnalystConsensus::Response &stRsp){}
	virtual void OnReply_GetResearchRatingSummary(Moomoo::u32_t nSerialNo, const Qot_GetResearchRatingSummary::Response &stRsp){}
	virtual void OnReply_GetResearchMorningstarReport(Moomoo::u32_t nSerialNo, const Qot_GetResearchMorningstarReport::Response &stRsp){}
	virtual void OnReply_GetValuationDetail(Moomoo::u32_t nSerialNo, const Qot_GetValuationDetail::Response &stRsp){}
	virtual void OnReply_GetValuationPlateStockList(Moomoo::u32_t nSerialNo, const Qot_GetValuationPlateStockList::Response &stRsp){}
	virtual void OnReply_GetCorporateActionsDividends(Moomoo::u32_t nSerialNo, const Qot_GetCorporateActionsDividends::Response &stRsp){}
	virtual void OnReply_GetCorporateActionsBuybacks(Moomoo::u32_t nSerialNo, const Qot_GetCorporateActionsBuybacks::Response &stRsp){}
	virtual void OnReply_GetCorporateActionsStockSplits(Moomoo::u32_t nSerialNo, const Qot_GetCorporateActionsStockSplits::Response &stRsp){}
	virtual void OnReply_GetShareholdersOverview(Moomoo::u32_t nSerialNo, const Qot_GetShareholdersOverview::Response &stRsp){}
	virtual void OnReply_GetShareholdersHoldingChanges(Moomoo::u32_t nSerialNo, const Qot_GetShareholdersHoldingChanges::Response &stRsp){}
	virtual void OnReply_GetShareholdersHolderDetail(Moomoo::u32_t nSerialNo, const Qot_GetShareholdersHolderDetail::Response &stRsp){}
	virtual void OnReply_GetShareholdersInstitutional(Moomoo::u32_t nSerialNo, const Qot_GetShareholdersInstitutional::Response &stRsp){}
	virtual void OnReply_GetInsiderHolderList(Moomoo::u32_t nSerialNo, const Qot_GetInsiderHolderList::Response &stRsp){}
	virtual void OnReply_GetInsiderTradeList(Moomoo::u32_t nSerialNo, const Qot_GetInsiderTradeList::Response &stRsp){}
	virtual void OnReply_GetCompanyProfile(Moomoo::u32_t nSerialNo, const Qot_GetCompanyProfile::Response &stRsp){}
	virtual void OnReply_GetCompanyExecutives(Moomoo::u32_t nSerialNo, const Qot_GetCompanyExecutives::Response &stRsp){}
	virtual void OnReply_GetCompanyExecutiveBackground(Moomoo::u32_t nSerialNo, const Qot_GetCompanyExecutiveBackground::Response &stRsp){}
	virtual void OnReply_GetCompanyOperationalEfficiency(Moomoo::u32_t nSerialNo, const Qot_GetCompanyOperationalEfficiency::Response &stRsp){}
	virtual void OnReply_GetTopTenBuySellBrokers(Moomoo::u32_t nSerialNo, const Qot_GetTopTenBuySellBrokers::Response &stRsp){}
	virtual void OnReply_GetDailyShortVolume(Moomoo::u32_t nSerialNo, const Qot_GetDailyShortVolume::Response &stRsp){}
	virtual void OnReply_GetShortInterest(Moomoo::u32_t nSerialNo, const Qot_GetShortInterest::Response &stRsp){}
	virtual void OnReply_GetOptionVolatility(Moomoo::u32_t nSerialNo, const Qot_GetOptionVolatility::Response &stRsp){}
	virtual void OnReply_GetOptionExerciseProbability(Moomoo::u32_t nSerialNo, const Qot_GetOptionExerciseProbability::Response &stRsp){}
	virtual void OnReply_StockScreen(Moomoo::u32_t nSerialNo, const Qot_StockScreen::Response &stRsp){}
	virtual void OnReply_OptionScreen(Moomoo::u32_t nSerialNo, const Qot_OptionScreen::Response &stRsp){}
	virtual void OnReply_WarrantScreen(Moomoo::u32_t nSerialNo, const Qot_WarrantScreen::Response &stRsp){}
	virtual void OnReply_GetOptionQuote(Moomoo::u32_t nSerialNo, const Qot_GetOptionQuote::Response &stRsp){}
	virtual void OnReply_GetOptionStrategy(Moomoo::u32_t nSerialNo, const Qot_GetOptionStrategy::Response &stRsp){}
	virtual void OnReply_GetOptionStrategyAnalysis(Moomoo::u32_t nSerialNo, const Qot_GetOptionStrategyAnalysis::Response &stRsp){}
	virtual void OnReply_GetOptionStrategySpread(Moomoo::u32_t nSerialNo, const Qot_GetOptionStrategySpread::Response &stRsp){}
	virtual void OnReply_GetOptionMarketStatistic(Moomoo::u32_t nSerialNo, const Qot_GetOptionMarketStatistic::Response &stRsp){}
	virtual void OnReply_GetOptionUnderlyingHisStatistic(Moomoo::u32_t nSerialNo, const Qot_GetOptionUnderlyingHisStatistic::Response &stRsp){}
	virtual void OnReply_GetOptionUnderlyingOverview(Moomoo::u32_t nSerialNo, const Qot_GetOptionUnderlyingOverview::Response &stRsp){}
	virtual void OnReply_GetOptionUnderlyingHisVolatility(Moomoo::u32_t nSerialNo, const Qot_GetOptionUnderlyingHisVolatility::Response &stRsp){}
	virtual void OnReply_GetOptionUnderlyingRank(Moomoo::u32_t nSerialNo, const Qot_GetOptionUnderlyingRank::Response &stRsp){}
	virtual void OnReply_GetOptionRank(Moomoo::u32_t nSerialNo, const Qot_GetOptionRank::Response &stRsp){}
	virtual void OnReply_GetOptionEvent(Moomoo::u32_t nSerialNo, const Qot_GetOptionEvent::Response &stRsp){}
	virtual void OnReply_GetOptionEventAlert(Moomoo::u32_t nSerialNo, const Qot_GetOptionEventAlert::Response &stRsp){}
	virtual void OnReply_SetOptionEventAlert(Moomoo::u32_t nSerialNo, const Qot_SetOptionEventAlert::Response &stRsp){}
	virtual void OnReply_GetOptionZeroDteScreener(Moomoo::u32_t nSerialNo, const Qot_GetOptionZeroDteScreener::Response &stRsp){}
	virtual void OnReply_GetOptionZeroDteContract(Moomoo::u32_t nSerialNo, const Qot_GetOptionZeroDteContract::Response &stRsp){}
	virtual void OnReply_GetOptionEarningsScreener(Moomoo::u32_t nSerialNo, const Qot_GetOptionEarningsScreener::Response &stRsp){}
	virtual void OnReply_GetOptionSellerScreener(Moomoo::u32_t nSerialNo, const Qot_GetOptionSellerScreener::Response &stRsp){}
	virtual void OnReply_GetIndicatorList(Moomoo::u32_t nSerialNo, const Qot_GetIndicatorList::Response &stRsp){}
	virtual void OnReply_RequestIndicatorCalc(Moomoo::u32_t nSerialNo, const Qot_RequestIndicatorCalc::Response &stRsp){}
	virtual void OnReply_GetSearchQuote(Moomoo::u32_t nSerialNo, const Qot_GetSearchQuote::Response &stRsp){}
	virtual void OnReply_GetSearchNews(Moomoo::u32_t nSerialNo, const Qot_GetSearchNews::Response &stRsp){}
	virtual void OnReply_GetEarningsCalendar(Moomoo::u32_t nSerialNo, const Qot_GetEarningsCalendar::Response &stRsp){}
	virtual void OnReply_GetMacroIndicatorList(Moomoo::u32_t nSerialNo, const Qot_GetMacroIndicatorList::Response &stRsp){}
	virtual void OnReply_GetMacroIndicatorHistory(Moomoo::u32_t nSerialNo, const Qot_GetMacroIndicatorHistory::Response &stRsp){}
	virtual void OnReply_GetFedWatchTargetRate(Moomoo::u32_t nSerialNo, const Qot_GetFedWatchTargetRate::Response &stRsp){}
	virtual void OnReply_GetFedWatchDotPlot(Moomoo::u32_t nSerialNo, const Qot_GetFedWatchDotPlot::Response &stRsp){}
	virtual void OnReply_GetEarningsBeatRank(Moomoo::u32_t nSerialNo, const Qot_GetEarningsBeatRank::Response &stRsp){}
	virtual void OnReply_GetDividendRank(Moomoo::u32_t nSerialNo, const Qot_GetDividendRank::Response &stRsp){}
	virtual void OnReply_GetDividendCalendar(Moomoo::u32_t nSerialNo, const Qot_GetDividendCalendar::Response &stRsp){}
	virtual void OnReply_GetEconomicCalendar(Moomoo::u32_t nSerialNo, const Qot_GetEconomicCalendar::Response &stRsp){}
	virtual void OnReply_GetUSPreMarketRank(Moomoo::u32_t nSerialNo, const Qot_GetUSPreMarketRank::Response &stRsp){}
	virtual void OnReply_GetUSAfterHoursRank(Moomoo::u32_t nSerialNo, const Qot_GetUSAfterHoursRank::Response &stRsp){}
	virtual void OnReply_GetUSOvernightRank(Moomoo::u32_t nSerialNo, const Qot_GetUSOvernightRank::Response &stRsp){}
	virtual void OnReply_GetTopMoversRank(Moomoo::u32_t nSerialNo, const Qot_GetTopMoversRank::Response &stRsp){}
	virtual void OnReply_GetHotList(Moomoo::u32_t nSerialNo, const Qot_GetHotList::Response &stRsp){}
	virtual void OnReply_GetShortSellingRank(Moomoo::u32_t nSerialNo, const Qot_GetShortSellingRank::Response &stRsp){}
	virtual void OnReply_GetPeriodChangeRank(Moomoo::u32_t nSerialNo, const Qot_GetPeriodChangeRank::Response &stRsp){}
	virtual void OnReply_GetHighDividendSOERank(Moomoo::u32_t nSerialNo, const Qot_GetHighDividendSOERank::Response &stRsp){}
	virtual void OnReply_GetInstitutionList(Moomoo::u32_t nSerialNo, const Qot_GetInstitutionList::Response &stRsp){}
	virtual void OnReply_GetInstitutionProfile(Moomoo::u32_t nSerialNo, const Qot_GetInstitutionProfile::Response &stRsp){}
	virtual void OnReply_GetInstitutionDistribution(Moomoo::u32_t nSerialNo, const Qot_GetInstitutionDistribution::Response &stRsp){}
	virtual void OnReply_GetInstitutionHoldingChange(Moomoo::u32_t nSerialNo, const Qot_GetInstitutionHoldingChange::Response &stRsp){}
	virtual void OnReply_GetInstitutionHoldingList(Moomoo::u32_t nSerialNo, const Qot_GetInstitutionHoldingList::Response &stRsp){}
	virtual void OnReply_GetArkFundHolding(Moomoo::u32_t nSerialNo, const Qot_GetArkFundHolding::Response &stRsp){}
	virtual void OnReply_GetArkStockDynamic(Moomoo::u32_t nSerialNo, const Qot_GetArkStockDynamic::Response &stRsp){}
	virtual void OnReply_GetArkActiveTransaction(Moomoo::u32_t nSerialNo, const Qot_GetArkActiveTransaction::Response &stRsp){}
	virtual void OnReply_GetRatingChange(Moomoo::u32_t nSerialNo, const Qot_GetRatingChange::Response &stRsp){}
	virtual void OnReply_GetIndustrialChainList(Moomoo::u32_t nSerialNo, const Qot_GetIndustrialChainList::Response &stRsp){}
	virtual void OnReply_GetIndustrialChainDetail(Moomoo::u32_t nSerialNo, const Qot_GetIndustrialChainDetail::Response &stRsp){}
	virtual void OnReply_GetIndustrialChainByPlate(Moomoo::u32_t nSerialNo, const Qot_GetIndustrialChainByPlate::Response &stRsp){}
	virtual void OnReply_GetIndustrialPlateInfo(Moomoo::u32_t nSerialNo, const Qot_GetIndustrialPlateInfo::Response &stRsp){}
	virtual void OnReply_GetIndustrialPlateStock(Moomoo::u32_t nSerialNo, const Qot_GetIndustrialPlateStock::Response &stRsp){}
	virtual void OnReply_GetHeatMapData(Moomoo::u32_t nSerialNo, const Qot_GetHeatMapData::Response &stRsp){}
	virtual void OnReply_GetRiseFallDistribution(Moomoo::u32_t nSerialNo, const Qot_GetRiseFallDistribution::Response &stRsp){}

	virtual void OnPush_Notify(const Notify::Response &stRsp){}
	virtual void OnPush_UpdateBasicQot(const Qot_UpdateBasicQot::Response &stRsp){}
	virtual void OnPush_UpdateOrderBook(const Qot_UpdateOrderBook::Response &stRsp){}
	virtual void OnPush_UpdateTicker(const Qot_UpdateTicker::Response &stRsp){}
	virtual void OnPush_UpdateKL(const Qot_UpdateKL::Response &stRsp){}
	virtual void OnPush_UpdateRT(const Qot_UpdateRT::Response &stRsp){}
	virtual void OnPush_UpdateBroker(const Qot_UpdateBroker::Response &stRsp){}
	virtual void OnPush_UpdatePriceReminder(const Qot_UpdatePriceReminder::Response &stRsp){}
	virtual void OnPush_UpdateOptionEvent(const Qot_UpdateOptionEvent::Response &stRsp){}
	virtual void OnPush_PushIndicatorCalc(const Qot_PushIndicatorCalc::Response &stRsp){}

	virtual void OnReply_GetAccList(Moomoo::u32_t nSerialNo, const Trd_GetAccList::Response &stRsp);
	virtual void OnReply_UnlockTrade(Moomoo::u32_t nSerialNo, const Trd_UnlockTrade::Response &stRsp);
	virtual void OnReply_SubAccPush(Moomoo::u32_t nSerialNo, const Trd_SubAccPush::Response &stRsp);
	virtual void OnReply_GetFunds(Moomoo::u32_t nSerialNo, const Trd_GetFunds::Response &stRsp){}
	virtual void OnReply_GetPositionList(Moomoo::u32_t nSerialNo, const Trd_GetPositionList::Response &stRsp){}
	virtual void OnReply_GetMaxTrdQtys(Moomoo::u32_t nSerialNo, const Trd_GetMaxTrdQtys::Response &stRsp){}
	virtual void OnReply_GetComboMaxTrdQtys(Moomoo::u32_t nSerialNo, const Trd_GetComboMaxTrdQtys::Response &stRsp){}
	virtual void OnReply_GetOrderList(Moomoo::u32_t nSerialNo, const Trd_GetOrderList::Response &stRsp){}
	virtual void OnReply_PlaceOrder(Moomoo::u32_t nSerialNo, const Trd_PlaceOrder::Response &stRsp){}
	virtual void OnReply_PlaceComboOrder(Moomoo::u32_t nSerialNo, const Trd_PlaceComboOrder::Response &stRsp){}
	virtual void OnReply_ModifyOrder(Moomoo::u32_t nSerialNo, const Trd_ModifyOrder::Response &stRsp){}
	virtual void OnReply_GetOrderFillList(Moomoo::u32_t nSerialNo, const Trd_GetOrderFillList::Response &stRsp){}
	virtual void OnReply_GetHistoryOrderList(Moomoo::u32_t nSerialNo, const Trd_GetHistoryOrderList::Response &stRsp){}
	virtual void OnReply_GetHistoryOrderFillList(Moomoo::u32_t nSerialNo, const Trd_GetHistoryOrderFillList::Response &stRsp){}
	virtual void OnReply_GetMarginRatio(Moomoo::u32_t nSerialNo, const Trd_GetMarginRatio::Response &stRsp){}
    virtual void OnReply_GetOrderFee(Moomoo::u32_t nSerialNo, const Trd_GetOrderFee::Response& stRsp){}
	virtual void OnReply_GetFlowSummary(Moomoo::u32_t nSerialNo, const Trd_FlowSummary::Response& stRsp){}

	virtual void OnPush_UpdateOrder(const Trd_UpdateOrder::Response &stRsp){}
	virtual void OnPush_UpdateOrderFill(const Trd_UpdateOrderFill::Response &stRsp){}
};
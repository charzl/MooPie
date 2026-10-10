// Copyright 2026 Moomoo
#pragma once

#include "MMSPI.h"
#include "MMAPI_InnerDefine.h"
#include "Lock.h"
#include "Include_3rd_protobuf.h"
#include "MMAPI_Client.h"
using namespace google;

class MMAPIImp : public MMAPI_Client
{
public:
	MMAPIImp(MMAPI_Conn *pConnApi);
	~MMAPIImp(void);

public:
	//设置客户端信息
	void SetClientInfo(const char* szClientID, i32_t nClientVer);
	
	//设置接口编程语言，用于统计
	void SetProgrammingLanguage(const char* szLanguage);

	//设置密钥
	void SetRSAPrivateKey(const char* strRSAPrivateKey);
	
	//初始化连接，连接并初始化
	bool InitConnect(const char* szIPAddr, u16_t nPort, bool bEnableEncrypt);

	//此连接的连接ID，连接的唯一标识，InitConnect协议返回，没有初始化前为0
	u64_t GetConnectID();

	//关闭连接
	bool Close();

	//注册回调
	void RegisterConnSpi(MMSPI_Conn *pSpi);

	//清理回调，回调对象没有反注册前不可销毁
	void UnregisterConnSpi();

	/////////////////////////////////////////////////////////////////////////////////
	//行情接口实现

	//注册回调
	void RegisterQotSpi(MMSPI_Qot *pSpi);

	//清理回调，回调对象没有反注册前不可销毁
	void UnregisterQotSpi();

	//订阅，反订阅
	u32_t Sub(const Qot_Sub::Request &stReq);
	//获取全局信息
	u32_t GetGlobalState(const GetGlobalState::Request &stReq);
	//注册推送
	u32_t RegQotPush(const Qot_RegQotPush::Request &stReq);
	//获取订阅信息
	u32_t GetSubInfo(const Qot_GetSubInfo::Request &stReq);
	//获取逐笔
	u32_t GetTicker(const Qot_GetTicker::Request &stReq);
	//获取报价
	u32_t GetBasicQot(const Qot_GetBasicQot::Request &stReq);
	//获取摆盘
	u32_t GetOrderBook(const Qot_GetOrderBook::Request &stReq);
	//获取K线
	u32_t GetKL(const Qot_GetKL::Request &stReq);
	//获取分时
	u32_t GetRT(const Qot_GetRT::Request &stReq);
	//获取经纪队列
	u32_t GetBroker(const Qot_GetBroker::Request &stReq);
	//在线请求历史复权信息，不读本地历史数据DB
	u32_t RequestRehab(const Qot_RequestRehab::Request &stReq);
	//在线请求历史K线，不读本地历史数据DB
	u32_t RequestHistoryKL(const Qot_RequestHistoryKL::Request &stReq);
	//获取历史K线已经用掉的额度 
	u32_t RequestHistoryKLQuota(const Qot_RequestHistoryKLQuota::Request &stReq);
	//获取静态信息
	u32_t GetStaticInfo(const Qot_GetStaticInfo::Request &stReq);
	//获取股票快照
	u32_t GetSecuritySnapshot(const Qot_GetSecuritySnapshot::Request &stReq);
	//获取板块集合下的板块
	u32_t GetPlateSet(const Qot_GetPlateSet::Request &stReq);
	//获取板块下的股票
	u32_t GetPlateSecurity(const Qot_GetPlateSecurity::Request &stReq);
	//获取相关股票
	u32_t GetReference(const Qot_GetReference::Request &stReq);
	//获取股票所属的板块
	u32_t GetOwnerPlate(const Qot_GetOwnerPlate::Request &stReq);
	//获取大股东持股变化列表
	u32_t GetHoldingChangeList(const Qot_GetHoldingChangeList::Request &stReq);
	//筛选期权
	u32_t GetOptionChain(const Qot_GetOptionChain::Request &stReq);
	//筛选窝轮
	u32_t GetWarrant(const Qot_GetWarrant::Request &stReq);
	//获取资金流向
	u32_t GetCapitalFlow(const Qot_GetCapitalFlow::Request &stReq);
	//获取资金分布
	u32_t GetCapitalDistribution(const Qot_GetCapitalDistribution::Request &stReq);
	//获取自选股分组下的股票
	u32_t GetUserSecurity(const Qot_GetUserSecurity::Request &stReq);
	//修改自选股分组下的股票
	u32_t ModifyUserSecurity(const Qot_ModifyUserSecurity::Request &stReq);
	//条件选股
	u32_t StockFilter(const Qot_StockFilter::Request &stReq);
	//股票代码变化
	u32_t GetCodeChange(const Qot_GetCodeChange::Request &stReq);
	//新股IPO
	u32_t GetIpoList(const Qot_GetIpoList::Request &stReq);
	//期货合约资料
	u32_t GetFutureInfo(const Qot_GetFutureInfo::Request &stReq);
	//获取市场交易日，在线拉取不在本地计算
	u32_t RequestTradeDate(const Qot_RequestTradeDate::Request &stReq);
	//设置到价提醒
	u32_t SetPriceReminder(const Qot_SetPriceReminder::Request &stReq);
	//获取到价提醒
	u32_t GetPriceReminder(const Qot_GetPriceReminder::Request &stReq);
	//获取自选股分组列表
	u32_t GetUserSecurityGroup(const Qot_GetUserSecurityGroup::Request &stReq); 
	//获取市场状态
	u32_t GetMarketState(const Qot_GetMarketState::Request &stReq);
	//获取期权到期日
	u32_t GetOptionExpirationDate(const Qot_GetOptionExpirationDate::Request &stReq);
	//获取期权行情
	u32_t GetOptionQuote(const Qot_GetOptionQuote::Request &stReq);
	//获取期权策略
	u32_t GetOptionStrategy(const Qot_GetOptionStrategy::Request &stReq);
	//获取期权策略分析
	u32_t GetOptionStrategyAnalysis(const Qot_GetOptionStrategyAnalysis::Request &stReq);
	//获取期权策略价差
	u32_t GetOptionStrategySpread(const Qot_GetOptionStrategySpread::Request &stReq);
	//获取个股财报日前后价格涨跌幅表现
	u32_t GetFinancialsEarningsPriceMove(const Qot_GetFinancialsEarningsPriceMove::Request &stReq);
	//获取个股财报日前后股价历史
	u32_t GetFinancialsEarningsPriceHistory(const Qot_GetFinancialsEarningsPriceHistory::Request &stReq);
	//获取财务报表
	u32_t GetFinancialsStatements(const Qot_GetFinancialsStatements::Request &stReq);
	//获取主营构成
	u32_t GetFinancialsRevenueBreakdown(const Qot_GetFinancialsRevenueBreakdown::Request &stReq);
	//获取分析师评级概述
	u32_t GetResearchAnalystConsensus(const Qot_GetResearchAnalystConsensus::Request &stReq);
	//获取评级汇总
	u32_t GetResearchRatingSummary(const Qot_GetResearchRatingSummary::Request &stReq);
	//获取晨星研究报告
	u32_t GetResearchMorningstarReport(const Qot_GetResearchMorningstarReport::Request &stReq);
	//获取估值详情
	u32_t GetValuationDetail(const Qot_GetValuationDetail::Request &stReq);
	//获取板块/指数成分股估值
	u32_t GetValuationPlateStockList(const Qot_GetValuationPlateStockList::Request &stReq);
	//获取分红派息
	u32_t GetCorporateActionsDividends(const Qot_GetCorporateActionsDividends::Request &stReq);
	//获取回购
	u32_t GetCorporateActionsBuybacks(const Qot_GetCorporateActionsBuybacks::Request &stReq);
	//获取拆合股
	u32_t GetCorporateActionsStockSplits(const Qot_GetCorporateActionsStockSplits::Request &stReq);
	//获取持股统计
	u32_t GetShareholdersOverview(const Qot_GetShareholdersOverview::Request &stReq);
	//获取持股变动
	u32_t GetShareholdersHoldingChanges(const Qot_GetShareholdersHoldingChanges::Request &stReq);
	//获取持股明细
	u32_t GetShareholdersHolderDetail(const Qot_GetShareholdersHolderDetail::Request &stReq);
	//获取机构持股
	u32_t GetShareholdersInstitutional(const Qot_GetShareholdersInstitutional::Request &stReq);
	//获取内部人持股列表
	u32_t GetInsiderHolderList(const Qot_GetInsiderHolderList::Request &stReq);
	//获取内部人交易列表
	u32_t GetInsiderTradeList(const Qot_GetInsiderTradeList::Request &stReq);
	//获取公司详情
	u32_t GetCompanyProfile(const Qot_GetCompanyProfile::Request &stReq);
	//获取公司高管信息
	u32_t GetCompanyExecutives(const Qot_GetCompanyExecutives::Request &stReq);
	//获取公司高管背景
	u32_t GetCompanyExecutiveBackground(const Qot_GetCompanyExecutiveBackground::Request &stReq);
	//获取公司经营效率
	u32_t GetCompanyOperationalEfficiency(const Qot_GetCompanyOperationalEfficiency::Request &stReq);
	//获取十大买卖经纪商
	u32_t GetTopTenBuySellBrokers(const Qot_GetTopTenBuySellBrokers::Request &stReq);
	//获取每日卖空
	u32_t GetDailyShortVolume(const Qot_GetDailyShortVolume::Request &stReq);
	//获取空头持仓
	u32_t GetShortInterest(const Qot_GetShortInterest::Request &stReq);
	//获取期权波动率分析
	u32_t GetOptionVolatility(const Qot_GetOptionVolatility::Request &stReq);
	//获取期权行权概率
	u32_t GetOptionExerciseProbability(const Qot_GetOptionExerciseProbability::Request &stReq);
	//条件选股V2
	u32_t StockScreen(const Qot_StockScreen::Request &stReq);
	//期权选股
	u32_t OptionScreen(const Qot_OptionScreen::Request &stReq);
	//窝轮筛选V2
	u32_t WarrantScreen(const Qot_WarrantScreen::Request &stReq);
	//获取期权市场统计
	u32_t GetOptionMarketStatistic(const Qot_GetOptionMarketStatistic::Request &stReq);
	//获取期权标的历史统计
	u32_t GetOptionUnderlyingHisStatistic(const Qot_GetOptionUnderlyingHisStatistic::Request &stReq);
	//获取批量标的最新数据
	u32_t GetOptionUnderlyingOverview(const Qot_GetOptionUnderlyingOverview::Request &stReq);
	//获取历史波动率
	u32_t GetOptionUnderlyingHisVolatility(const Qot_GetOptionUnderlyingHisVolatility::Request &stReq);
	//获取标的排行
	u32_t GetOptionUnderlyingRank(const Qot_GetOptionUnderlyingRank::Request &stReq);
	//获取期权合约排行
	u32_t GetOptionRank(const Qot_GetOptionRank::Request &stReq);
	//获取期权异动列表
	u32_t GetOptionEvent(const Qot_GetOptionEvent::Request &stReq);
	//获取期权异动告警设置
	u32_t GetOptionEventAlert(const Qot_GetOptionEventAlert::Request &stReq);
	//修改期权异动告警条件
	u32_t SetOptionEventAlert(const Qot_SetOptionEventAlert::Request &stReq);
	//获取末日期权标的列表
	u32_t GetOptionZeroDteScreener(const Qot_GetOptionZeroDteScreener::Request &stReq);
	//获取末日期权合约列表
	u32_t GetOptionZeroDteContract(const Qot_GetOptionZeroDteContract::Request &stReq);
	//获取财报期权标的列表
	u32_t GetOptionEarningsScreener(const Qot_GetOptionEarningsScreener::Request &stReq);
	//获取期权卖方策略列表
	u32_t GetOptionSellerScreener(const Qot_GetOptionSellerScreener::Request &stReq);
	//获取指标列表
	u32_t GetIndicatorList(const Qot_GetIndicatorList::Request &stReq);
	//异步发起指标计算
	u32_t RequestIndicatorCalc(const Qot_RequestIndicatorCalc::Request &stReq);
	//搜索行情
	u32_t GetSearchQuote(const Qot_GetSearchQuote::Request &stReq);
	//搜索资讯
	u32_t GetSearchNews(const Qot_GetSearchNews::Request &stReq);
	u32_t GetEarningsCalendar(const Qot_GetEarningsCalendar::Request &stReq);
	u32_t GetMacroIndicatorList(const Qot_GetMacroIndicatorList::Request &stReq);
	u32_t GetMacroIndicatorHistory(const Qot_GetMacroIndicatorHistory::Request &stReq);
	u32_t GetFedWatchTargetRate(const Qot_GetFedWatchTargetRate::Request &stReq);
	u32_t GetFedWatchDotPlot(const Qot_GetFedWatchDotPlot::Request &stReq);
	u32_t GetEarningsBeatRank(const Qot_GetEarningsBeatRank::Request &stReq);
	u32_t GetDividendRank(const Qot_GetDividendRank::Request &stReq);
	u32_t GetDividendCalendar(const Qot_GetDividendCalendar::Request &stReq);
	u32_t GetEconomicCalendar(const Qot_GetEconomicCalendar::Request &stReq);
	u32_t GetUSPreMarketRank(const Qot_GetUSPreMarketRank::Request &stReq);
	u32_t GetUSAfterHoursRank(const Qot_GetUSAfterHoursRank::Request &stReq);
	u32_t GetUSOvernightRank(const Qot_GetUSOvernightRank::Request &stReq);
	u32_t GetTopMoversRank(const Qot_GetTopMoversRank::Request &stReq);
	u32_t GetHotList(const Qot_GetHotList::Request &stReq);
	u32_t GetShortSellingRank(const Qot_GetShortSellingRank::Request &stReq);
	u32_t GetPeriodChangeRank(const Qot_GetPeriodChangeRank::Request &stReq);
	u32_t GetHighDividendSOERank(const Qot_GetHighDividendSOERank::Request &stReq);
	u32_t GetInstitutionList(const Qot_GetInstitutionList::Request &stReq);
	u32_t GetInstitutionProfile(const Qot_GetInstitutionProfile::Request &stReq);
	u32_t GetInstitutionDistribution(const Qot_GetInstitutionDistribution::Request &stReq);
	u32_t GetInstitutionHoldingChange(const Qot_GetInstitutionHoldingChange::Request &stReq);
	u32_t GetInstitutionHoldingList(const Qot_GetInstitutionHoldingList::Request &stReq);
	u32_t GetArkFundHolding(const Qot_GetArkFundHolding::Request &stReq);
	u32_t GetArkStockDynamic(const Qot_GetArkStockDynamic::Request &stReq);
	u32_t GetArkActiveTransaction(const Qot_GetArkActiveTransaction::Request &stReq);
	u32_t GetRatingChange(const Qot_GetRatingChange::Request &stReq);
	u32_t GetIndustrialChainList(const Qot_GetIndustrialChainList::Request &stReq);
	u32_t GetIndustrialChainDetail(const Qot_GetIndustrialChainDetail::Request &stReq);
	u32_t GetIndustrialChainByPlate(const Qot_GetIndustrialChainByPlate::Request &stReq);
	u32_t GetIndustrialPlateInfo(const Qot_GetIndustrialPlateInfo::Request &stReq);
	u32_t GetIndustrialPlateStock(const Qot_GetIndustrialPlateStock::Request &stReq);
	u32_t GetHeatMapData(const Qot_GetHeatMapData::Request &stReq);
	u32_t GetRiseFallDistribution(const Qot_GetRiseFallDistribution::Request &stReq);

	/////////////////////////////////////////////////////////////////////////////////
	//交易接口实现
	//注册回调
	void RegisterTrdSpi(MMSPI_Trd *pSpi);

	//清理回调，回调对象没有反注册前不可销毁
	void UnregisterTrdSpi();

	//获取交易包标识
	bool GetPacketID(Common::PacketID &stPacketID);

	//获取交易账户列表
	u32_t GetAccList(const Trd_GetAccList::Request &stReq);
	//解锁
	u32_t UnlockTrade(const Trd_UnlockTrade::Request &stReq);
	//订阅接收推送数据的交易账户
	u32_t SubAccPush(const Trd_SubAccPush::Request &stReq);
	//获取账户资金
	u32_t GetFunds(const Trd_GetFunds::Request &stReq);
	//获取账户持仓
	u32_t GetPositionList(const Trd_GetPositionList::Request &stReq);
	//获取最大交易数量
	u32_t GetMaxTrdQtys(const Trd_GetMaxTrdQtys::Request &stReq);
	u32_t GetComboMaxTrdQtys(const Trd_GetComboMaxTrdQtys::Request &stReq);
	//获取当日订单列表
	u32_t GetOrderList(const Trd_GetOrderList::Request &stReq);
	//下单
	u32_t PlaceOrder(const Trd_PlaceOrder::Request &stReq);
	u32_t PlaceComboOrder(const Trd_PlaceComboOrder::Request &stReq);
	//修改订单
	u32_t ModifyOrder(const Trd_ModifyOrder::Request &stReq);
	//获取当日成交列表
	u32_t GetOrderFillList(const Trd_GetOrderFillList::Request &stReq);
	//获取历史订单列表
	u32_t GetHistoryOrderList(const Trd_GetHistoryOrderList::Request &stReq);
	//获取历史成交列表
	u32_t GetHistoryOrderFillList(const Trd_GetHistoryOrderFillList::Request &stReq);
	//获取融资融券数据
	u32_t GetMarginRatio(const Trd_GetMarginRatio::Request &stReq);
	//获取订单费用
    u32_t GetOrderFee(const Trd_GetOrderFee::Request& stReq);
    //获取现价流水
    u32_t GetFlowSummary(const Trd_FlowSummary::Request& stReq);

private:
	// 重写 MMAPI_Client 的连接/收发回调（由网络线程触发）。均先调用基类同名逻辑，
	// 再按连接 ID 过滤后派发到对应 SPI。
	virtual void OnDisConnect(u32_t nConnectID, i64_t nErrCode, APITcpDisConnectType enDisConnType) override;
	virtual void OnInitConnect(i64_t nErrCode, const char* strDesc) override;
	virtual void OnReply(u32_t nConnectID, MMAPI_ReqReplyType enReqReplyType, const MMAPI_ProtoHeader& protoHeader, const i8_t* pProtoData, i32_t nDataLen) override;
	virtual void OnPush(u32_t nConnectID, const MMAPI_ProtoHeader& protoHeader, const i8_t* pProtoData, i32_t nDataLen) override;

private:
	u32_t SendProto(u32_t nProtoID, const protobuf::Message &pbObj);

private:
	static CLock m_safe;

	MMSPI_Conn* m_pConnSpi{ nullptr };
	MMSPI_Qot* m_pQotSpi{ nullptr };
	MMSPI_Trd* m_pTrdSpi{ nullptr };
	MMAPI_Conn* m_pConnApi{ nullptr };
	u32_t m_nTrdSerialNo{ 100 };
};
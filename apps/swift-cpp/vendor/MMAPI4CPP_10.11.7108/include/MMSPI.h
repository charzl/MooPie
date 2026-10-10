// Copyright 2026 Moomoo
#pragma once
#include "MMAPI_Define.h"

namespace Moomoo {
class MMAPI_Conn;
class MMSPI_Conn
{
public:
	/**
	* @brief 初始化连接
	* @praram pConn 对应连接实例指针
	* @param nErrCode 当高32位为MMAPI_ConnectFailType类型，则低32位为系统错误码；
	*				  当高32位为MMAPI_InitFail，则低32位为MMAPI_InitFailType类型。
	* @param strDesc 错误描述
	*/
	virtual void OnInitConnect(MMAPI_Conn* pConn, Moomoo::i64_t nErrCode, const char* strDesc) = 0;
	/**
	* @brief 连接断开
	* @praram pConn 对应连接实例指针
	* @param nErrCode 高32位为MMAPI_ConnectFailType类型，低32位为系统错误码；
	*/
	virtual void OnDisConnect(MMAPI_Conn* pConn, Moomoo::i64_t nErrCode) = 0;
};

class MMSPI_Qot
{
public:
	/**
	* @brief 请求全局状态
	* @praram nSerialNo 包序列号
	* @param stRsp 回包，具体字段请参考GetGlobalState.proto协议
	*/
	virtual void OnReply_GetGlobalState(Moomoo::u32_t nSerialNo, const GetGlobalState::Response &stRsp) = 0;
	/**
	* @brief 订阅
	* @praram nSerialNo 包序列号
	* @param stRsp 回包，具体字段请参考Qot_Sub.proto协议
	*/
	virtual void OnReply_Sub(Moomoo::u32_t nSerialNo, const Qot_Sub::Response &stRsp) = 0;
	/**
	* @brief 注册推送
	* @praram nSerialNo 包序列号
	* @param stRsp 回包，具体字段请参考Qot_RegQotPush.proto协议
	*/
	virtual void OnReply_RegQotPush(Moomoo::u32_t nSerialNo, const Qot_RegQotPush::Response &stRsp) = 0;
	/**
	* @brief 获取订阅信息
	* @praram nSerialNo 包序列号
	* @param stRsp 回包，具体字段请参考Qot_GetSubInfo.proto协议
	*/
	virtual void OnReply_GetSubInfo(Moomoo::u32_t nSerialNo, const Qot_GetSubInfo::Response &stRsp) = 0;
	/**
	* @brief 获取逐笔
	* @praram nSerialNo 包序列号
	* @param stRsp 回包，具体字段请参考Qot_GetTicker.proto协议
	*/
	virtual void OnReply_GetTicker(Moomoo::u32_t nSerialNo, const Qot_GetTicker::Response &stRsp) = 0;
	/**
	* @brief 获取报价
	* @praram nSerialNo 包序列号
	* @param stRsp 回包，具体字段请参考Qot_GetBasicQot.proto协议
	*/
	virtual void OnReply_GetBasicQot(Moomoo::u32_t nSerialNo, const Qot_GetBasicQot::Response &stRsp) = 0;
	/**
	* @brief 获取摆盘
	* @praram nSerialNo 包序列号
	* @param stRsp 回包，具体字段请参考Qot_GetOrderBook.proto协议
	*/
	virtual void OnReply_GetOrderBook(Moomoo::u32_t nSerialNo, const Qot_GetOrderBook::Response &stRsp) = 0;
	/**
	* @brief 获取K线
	* @praram nSerialNo 包序列号
	* @param stRsp 回包，具体字段请参考Qot_GetKL.proto协议
	*/
	virtual void OnReply_GetKL(Moomoo::u32_t nSerialNo, const Qot_GetKL::Response &stRsp) = 0;
	/**
	* @brief 获取分时
	* @praram nSerialNo 包序列号
	* @param stRsp 回包，具体字段请参考Qot_GetRT.proto协议
	*/
	virtual void OnReply_GetRT(Moomoo::u32_t nSerialNo, const Qot_GetRT::Response &stRsp) = 0;
	/**
	* @brief 获取经纪队列
	* @praram nSerialNo 包序列号
	* @param stRsp 回包，具体字段请参考Qot_GetBroker.proto协议
	*/
	virtual void OnReply_GetBroker(Moomoo::u32_t nSerialNo, const Qot_GetBroker::Response &stRsp) = 0;
	/**
	* @brief 在线请求历史复权信息，不读本地历史数据DB
	* @praram nSerialNo 包序列号
	* @param stRsp 回包，具体字段请参考Qot_RequestRehab.proto协议
	*/
	virtual void OnReply_RequestRehab(Moomoo::u32_t nSerialNo, const Qot_RequestRehab::Response &stRsp) = 0;
	/**
	* @brief 在线请求历史K线，不读本地历史数据DB
	* @praram nSerialNo 包序列号
	* @param stRsp 回包，具体字段请参考Qot_RequestHistoryKL.proto协议
	*/
	virtual void OnReply_RequestHistoryKL(Moomoo::u32_t nSerialNo, const Qot_RequestHistoryKL::Response &stRsp) = 0;
	/**
	* @brief 获取历史K线已经用掉的额度 
	* @praram nSerialNo 包序列号
	* @param stRsp 回包，具体字段请参考Qot_RequestHistoryKLQuota.proto协议
	*/
	virtual void OnReply_RequestHistoryKLQuota(Moomoo::u32_t nSerialNo, const Qot_RequestHistoryKLQuota::Response &stRsp) = 0;
	/**
	* @brief 获取静态信息
	* @praram nSerialNo 包序列号
	* @param stRsp 回包，具体字段请参考Qot_GetStaticInfo.proto协议
	*/
	virtual void OnReply_GetStaticInfo(Moomoo::u32_t nSerialNo, const Qot_GetStaticInfo::Response &stRsp) = 0;
	/**
	* @brief 获取股票快照
	* @praram nSerialNo 包序列号
	* @param stRsp 回包，具体字段请参考Qot_GetSecuritySnapshot.proto协议
	*/
	virtual void OnReply_GetSecuritySnapshot(Moomoo::u32_t nSerialNo, const Qot_GetSecuritySnapshot::Response &stRsp) = 0;
	/**
	* @brief 获取板块集合下的板块
	* @praram nSerialNo 包序列号
	* @param stRsp 回包，具体字段请参考Qot_GetPlateSet.proto协议
	*/
	virtual void OnReply_GetPlateSet(Moomoo::u32_t nSerialNo, const Qot_GetPlateSet::Response &stRsp) = 0;
	/**
	* @brief 获取板块下的股票
	* @praram nSerialNo 包序列号
	* @param stRsp 回包，具体字段请参考Qot_GetPlateSecurity.proto协议
	*/
	virtual void OnReply_GetPlateSecurity(Moomoo::u32_t nSerialNo, const Qot_GetPlateSecurity::Response &stRsp) = 0;
	/**
	* @brief 获取相关股票
	* @praram nSerialNo 包序列号
	* @param stRsp 回包，具体字段请参考Qot_GetReference.proto协议
	*/
	virtual void OnReply_GetReference(Moomoo::u32_t nSerialNo, const Qot_GetReference::Response &stRsp) = 0;
	/**
	* @brief 获取股票所属的板块
	* @praram nSerialNo 包序列号
	* @param stRsp 回包，具体字段请参考Qot_GetOwnerPlate.proto协议
	*/
	virtual void OnReply_GetOwnerPlate(Moomoo::u32_t nSerialNo, const Qot_GetOwnerPlate::Response &stRsp) = 0;
	/**
	* @brief 获取大股东持股变化列表
	* @praram nSerialNo 包序列号
	* @param stRsp 回包，具体字段请参考Qot_GetHoldingChangeList.proto协议
	*/
	virtual void OnReply_GetHoldingChangeList(Moomoo::u32_t nSerialNo, const Qot_GetHoldingChangeList::Response &stRsp) = 0;
	/**
	* @brief 筛选期权
	* @praram nSerialNo 包序列号
	* @param stRsp 回包，具体字段请参考Qot_GetOptionChain.proto协议
	*/
	virtual void OnReply_GetOptionChain(Moomoo::u32_t nSerialNo, const Qot_GetOptionChain::Response &stRsp) = 0;
	/**
	* @brief 筛选窝轮
	* @praram nSerialNo 包序列号
	* @param stRsp 回包，具体字段请参考Qot_GetWarrant.proto协议
	*/
	virtual void OnReply_GetWarrant(Moomoo::u32_t nSerialNo, const Qot_GetWarrant::Response &stRsp) = 0;
	/**
	* @brief 获取资金流向
	* @praram nSerialNo 包序列号
	* @param stRsp 回包，具体字段请参考Qot_GetCapitalFlow.proto协议
	*/
	virtual void OnReply_GetCapitalFlow(Moomoo::u32_t nSerialNo, const Qot_GetCapitalFlow::Response &stRsp) = 0;
	/**
	* @brief 获取资金分布
	* @praram nSerialNo 包序列号
	* @param stRsp 回包，具体字段请参考Qot_GetCapitalDistribution.proto协议
	*/
	virtual void OnReply_GetCapitalDistribution(Moomoo::u32_t nSerialNo, const Qot_GetCapitalDistribution::Response &stRsp) = 0;
	/**
	* @brief 获取自选股分组下的股票
	* @praram nSerialNo 包序列号
	* @param stRsp 回包，具体字段请参考Qot_GetUserSecurity.proto协议
	*/
	virtual void OnReply_GetUserSecurity(Moomoo::u32_t nSerialNo, const Qot_GetUserSecurity::Response &stRsp) = 0;
	/**
	* @brief 修改自选股分组下的股票
	* @praram nSerialNo 包序列号
	* @param stRsp 回包，具体字段请参考Qot_ModifyUserSecurity.proto协议
	*/
	virtual void OnReply_ModifyUserSecurity(Moomoo::u32_t nSerialNo, const Qot_ModifyUserSecurity::Response &stRsp) = 0;
	
	/**
	* @brief 条件选股
	* @praram nSerialNo 包序列号
	* @param stRsp 回包，具体字段请参考Qot_StockFilter.proto协议
	*/
	virtual void OnReply_StockFilter(Moomoo::u32_t nSerialNo, const Qot_StockFilter::Response &stRsp) = 0;
	/**
	* @brief 获取股票代码变化信息
	* @praram nSerialNo 包序列号
	* @param stRsp 回包，具体字段请参考Qot_GetCodeChange.proto协议
	*/
	virtual void OnReply_GetCodeChange(Moomoo::u32_t nSerialNo, const Qot_GetCodeChange::Response &stRsp) = 0;
	/**
	* @brief 新股IPO
	* @praram nSerialNo 包序列号
	* @param stRsp 回包，具体字段请参考Qot_GetIpoList.proto协议
	*/
	virtual void OnReply_GetIpoList(Moomoo::u32_t nSerialNo, const Qot_GetIpoList::Response &stRsp) = 0;
	/**
	* @brief 期货合约资料
	* @praram nSerialNo 包序列号
	* @param stRsp 回包，具体字段请参考Qot_GetFutureInfo.proto协议
	*/
	virtual void OnReply_GetFutureInfo(Moomoo::u32_t nSerialNo, const Qot_GetFutureInfo::Response &stRsp) = 0;
	/**
	* @brief 获取市场交易日，在线拉取不在本地计算
	* @praram nSerialNo 包序列号
	* @param stRsp 回包，具体字段请参考Qot_RequestTradeDate.proto协议
	*/
	virtual void OnReply_RequestTradeDate(Moomoo::u32_t nSerialNo, const Qot_RequestTradeDate::Response &stRsp) = 0;

	/**
	* @brief 设置到价提醒
	* @praram nSerialNo 包序列号
	* @param stRsp 回包，具体字段请参考Qot_SetPriceReminder.proto协议
	*/
	virtual void OnReply_SetPriceReminder(Moomoo::u32_t nSerialNo, const Qot_SetPriceReminder::Response &stRsp) = 0;

	/**
	* @brief 获取到价提醒
	* @praram nSerialNo 包序列号
	* @param stRsp 回包，具体字段请参考Qot_GetPriceReminder.proto协议
	*/
	virtual void OnReply_GetPriceReminder(Moomoo::u32_t nSerialNo, const Qot_GetPriceReminder::Response &stRsp) = 0;

	/**
	* @brief 获取自选股分组列表
	* @praram nSerialNo 包序列号
	* @param stRsp 回包，具体字段请参考Qot_GetUserSecurityGroup.proto协议
	*/
	virtual void OnReply_GetUserSecurityGroup(Moomoo::u32_t nSerialNo, const Qot_GetUserSecurityGroup::Response &stRsp) = 0;

	/**
	* @brief 获取市场状态
	* @praram nSerialNo 包序列号
	* @param stRsp 回包，具体字段请参考Qot_GetMarketState.proto协议
	*/
	virtual void OnReply_GetMarketState(Moomoo::u32_t nSerialNo, const Qot_GetMarketState::Response &stRsp) = 0;

	/**
	* @brief 获取期权链到期日
	* @praram nSerialNo 包序列号
	* @param stRsp 回包，具体字段请参考Qot_GetOptionExpirationDate.proto协议
	*/
	virtual void OnReply_GetOptionExpirationDate(Moomoo::u32_t nSerialNo, const Qot_GetOptionExpirationDate::Response &stRsp) = 0;
	/**
	* @brief 获取期权行情
	* @praram nSerialNo 包序列号
	* @param stRsp 回包，具体字段请参考Qot_GetOptionQuote.proto协议
	*/
	virtual void OnReply_GetOptionQuote(Moomoo::u32_t nSerialNo, const Qot_GetOptionQuote::Response &stRsp) = 0;
	/**
	* @brief 获取期权策略
	* @praram nSerialNo 包序列号
	* @param stRsp 回包，具体字段请参考Qot_GetOptionStrategy.proto协议
	*/
	virtual void OnReply_GetOptionStrategy(Moomoo::u32_t nSerialNo, const Qot_GetOptionStrategy::Response &stRsp) = 0;
	/**
	* @brief 获取期权策略分析
	* @praram nSerialNo 包序列号
	* @param stRsp 回包，具体字段请参考Qot_GetOptionStrategyAnalysis.proto协议
	*/
	virtual void OnReply_GetOptionStrategyAnalysis(Moomoo::u32_t nSerialNo, const Qot_GetOptionStrategyAnalysis::Response &stRsp) = 0;
	/**
	* @brief 获取期权策略价差
	* @praram nSerialNo 包序列号
	* @param stRsp 回包，具体字段请参考Qot_GetOptionStrategySpread.proto协议
	*/
	virtual void OnReply_GetOptionStrategySpread(Moomoo::u32_t nSerialNo, const Qot_GetOptionStrategySpread::Response &stRsp) = 0;
	/**
	* @brief 获取个股财报日前后价格涨跌幅表现
	* @praram nSerialNo 包序列号
	* @param stRsp 回包，具体字段请参考Qot_GetFinancialsEarningsPriceMove.proto协议
	*/
	virtual void OnReply_GetFinancialsEarningsPriceMove(Moomoo::u32_t nSerialNo, const Qot_GetFinancialsEarningsPriceMove::Response &stRsp) = 0;
	/**
	* @brief 获取个股财报日前后股价历史
	* @praram nSerialNo 包序列号
	* @param stRsp 回包，具体字段请参考Qot_GetFinancialsEarningsPriceHistory.proto协议
	*/
	virtual void OnReply_GetFinancialsEarningsPriceHistory(Moomoo::u32_t nSerialNo, const Qot_GetFinancialsEarningsPriceHistory::Response &stRsp) = 0;
	/**
	* @brief 获取财务报表
	* @praram nSerialNo 包序列号
	* @param stRsp 回包，具体字段请参考Qot_GetFinancialsStatements.proto协议
	*/
	virtual void OnReply_GetFinancialsStatements(Moomoo::u32_t nSerialNo, const Qot_GetFinancialsStatements::Response &stRsp) = 0;
	/**
	* @brief 获取主营构成
	* @praram nSerialNo 包序列号
	* @param stRsp 回包，具体字段请参考Qot_GetFinancialsRevenueBreakdown.proto协议
	*/
	virtual void OnReply_GetFinancialsRevenueBreakdown(Moomoo::u32_t nSerialNo, const Qot_GetFinancialsRevenueBreakdown::Response &stRsp) = 0;
	/**
	* @brief 获取分析师评级概述
	* @praram nSerialNo 包序列号
	* @param stRsp 回包，具体字段请参考Qot_GetResearchAnalystConsensus.proto协议
	*/
	virtual void OnReply_GetResearchAnalystConsensus(Moomoo::u32_t nSerialNo, const Qot_GetResearchAnalystConsensus::Response &stRsp) = 0;
	/**
	* @brief 获取评级汇总
	* @praram nSerialNo 包序列号
	* @param stRsp 回包，具体字段请参考Qot_GetResearchRatingSummary.proto协议
	*/
	virtual void OnReply_GetResearchRatingSummary(Moomoo::u32_t nSerialNo, const Qot_GetResearchRatingSummary::Response &stRsp) = 0;
	/**
	* @brief 获取晨星研究报告
	* @praram nSerialNo 包序列号
	* @param stRsp 回包，具体字段请参考Qot_GetResearchMorningstarReport.proto协议
	*/
	virtual void OnReply_GetResearchMorningstarReport(Moomoo::u32_t nSerialNo, const Qot_GetResearchMorningstarReport::Response &stRsp) = 0;
	/**
	* @brief 获取估值详情
	* @praram nSerialNo 包序列号
	* @param stRsp 回包，具体字段请参考Qot_GetValuationDetail.proto协议
	*/
	virtual void OnReply_GetValuationDetail(Moomoo::u32_t nSerialNo, const Qot_GetValuationDetail::Response &stRsp) = 0;
	/**
	* @brief 获取板块/指数成分股估值
	* @praram nSerialNo 包序列号
	* @param stRsp 回包，具体字段请参考Qot_GetValuationPlateStockList.proto协议
	*/
	virtual void OnReply_GetValuationPlateStockList(Moomoo::u32_t nSerialNo, const Qot_GetValuationPlateStockList::Response &stRsp) = 0;
	/**
	* @brief 获取分红派息
	* @praram nSerialNo 包序列号
	* @param stRsp 回包，具体字段请参考Qot_GetCorporateActionsDividends.proto协议
	*/
	virtual void OnReply_GetCorporateActionsDividends(Moomoo::u32_t nSerialNo, const Qot_GetCorporateActionsDividends::Response &stRsp) = 0;
	/**
	* @brief 获取回购
	* @praram nSerialNo 包序列号
	* @param stRsp 回包，具体字段请参考Qot_GetCorporateActionsBuybacks.proto协议
	*/
	virtual void OnReply_GetCorporateActionsBuybacks(Moomoo::u32_t nSerialNo, const Qot_GetCorporateActionsBuybacks::Response &stRsp) = 0;
	/**
	* @brief 获取拆合股
	* @praram nSerialNo 包序列号
	* @param stRsp 回包，具体字段请参考Qot_GetCorporateActionsStockSplits.proto协议
	*/
	virtual void OnReply_GetCorporateActionsStockSplits(Moomoo::u32_t nSerialNo, const Qot_GetCorporateActionsStockSplits::Response &stRsp) = 0;
	/**
	* @brief 获取持股统计
	* @praram nSerialNo 包序列号
	* @param stRsp 回包，具体字段请参考Qot_GetShareholdersOverview.proto协议
	*/
	virtual void OnReply_GetShareholdersOverview(Moomoo::u32_t nSerialNo, const Qot_GetShareholdersOverview::Response &stRsp) = 0;
	/**
	* @brief 获取持股变动
	* @praram nSerialNo 包序列号
	* @param stRsp 回包，具体字段请参考Qot_GetShareholdersHoldingChanges.proto协议
	*/
	virtual void OnReply_GetShareholdersHoldingChanges(Moomoo::u32_t nSerialNo, const Qot_GetShareholdersHoldingChanges::Response &stRsp) = 0;
	/**
	* @brief 获取持股明细
	* @praram nSerialNo 包序列号
	* @param stRsp 回包，具体字段请参考Qot_GetShareholdersHolderDetail.proto协议
	*/
	virtual void OnReply_GetShareholdersHolderDetail(Moomoo::u32_t nSerialNo, const Qot_GetShareholdersHolderDetail::Response &stRsp) = 0;
	/**
	* @brief 获取机构持股
	* @praram nSerialNo 包序列号
	* @param stRsp 回包，具体字段请参考Qot_GetShareholdersInstitutional.proto协议
	*/
	virtual void OnReply_GetShareholdersInstitutional(Moomoo::u32_t nSerialNo, const Qot_GetShareholdersInstitutional::Response &stRsp) = 0;
	/**
	* @brief 获取内部人持股列表
	* @praram nSerialNo 包序列号
	* @param stRsp 回包，具体字段请参考Qot_GetInsiderHolderList.proto协议
	*/
	virtual void OnReply_GetInsiderHolderList(Moomoo::u32_t nSerialNo, const Qot_GetInsiderHolderList::Response &stRsp) = 0;
	/**
	* @brief 获取内部人交易列表
	* @praram nSerialNo 包序列号
	* @param stRsp 回包，具体字段请参考Qot_GetInsiderTradeList.proto协议
	*/
	virtual void OnReply_GetInsiderTradeList(Moomoo::u32_t nSerialNo, const Qot_GetInsiderTradeList::Response &stRsp) = 0;
	/**
	* @brief 获取公司详情
	* @praram nSerialNo 包序列号
	* @param stRsp 回包，具体字段请参考Qot_GetCompanyProfile.proto协议
	*/
	virtual void OnReply_GetCompanyProfile(Moomoo::u32_t nSerialNo, const Qot_GetCompanyProfile::Response &stRsp) = 0;
	/**
	* @brief 获取公司高管信息
	* @praram nSerialNo 包序列号
	* @param stRsp 回包，具体字段请参考Qot_GetCompanyExecutives.proto协议
	*/
	virtual void OnReply_GetCompanyExecutives(Moomoo::u32_t nSerialNo, const Qot_GetCompanyExecutives::Response &stRsp) = 0;
	/**
	* @brief 获取公司高管背景
	* @praram nSerialNo 包序列号
	* @param stRsp 回包，具体字段请参考Qot_GetCompanyExecutiveBackground.proto协议
	*/
	virtual void OnReply_GetCompanyExecutiveBackground(Moomoo::u32_t nSerialNo, const Qot_GetCompanyExecutiveBackground::Response &stRsp) = 0;
	/**
	* @brief 获取公司经营效率
	* @praram nSerialNo 包序列号
	* @param stRsp 回包，具体字段请参考Qot_GetCompanyOperationalEfficiency.proto协议
	*/
	virtual void OnReply_GetCompanyOperationalEfficiency(Moomoo::u32_t nSerialNo, const Qot_GetCompanyOperationalEfficiency::Response &stRsp) = 0;
	/**
	* @brief 获取十大买卖经纪商
	* @praram nSerialNo 包序列号
	* @param stRsp 回包，具体字段请参考Qot_GetTopTenBuySellBrokers.proto协议
	*/
	virtual void OnReply_GetTopTenBuySellBrokers(Moomoo::u32_t nSerialNo, const Qot_GetTopTenBuySellBrokers::Response &stRsp) = 0;
	/**
	* @brief 获取每日卖空
	* @praram nSerialNo 包序列号
	* @param stRsp 回包，具体字段请参考Qot_GetDailyShortVolume.proto协议
	*/
	virtual void OnReply_GetDailyShortVolume(Moomoo::u32_t nSerialNo, const Qot_GetDailyShortVolume::Response &stRsp) = 0;
	/**
	* @brief 获取空头持仓
	* @praram nSerialNo 包序列号
	* @param stRsp 回包，具体字段请参考Qot_GetShortInterest.proto协议
	*/
	virtual void OnReply_GetShortInterest(Moomoo::u32_t nSerialNo, const Qot_GetShortInterest::Response &stRsp) = 0;
	/**
	* @brief 获取期权波动率分析
	* @praram nSerialNo 包序列号
	* @param stRsp 回包，具体字段请参考Qot_GetOptionVolatility.proto协议
	*/
	virtual void OnReply_GetOptionVolatility(Moomoo::u32_t nSerialNo, const Qot_GetOptionVolatility::Response &stRsp) = 0;
	/**
	* @brief 获取期权行权概率
	* @praram nSerialNo 包序列号
	* @param stRsp 回包，具体字段请参考Qot_GetOptionExerciseProbability.proto协议
	*/
	virtual void OnReply_GetOptionExerciseProbability(Moomoo::u32_t nSerialNo, const Qot_GetOptionExerciseProbability::Response &stRsp) = 0;

	/**
	* @brief 条件选股V2
	* @praram nSerialNo 包序列号
	* @param stRsp 回包，具体字段请参考Qot_StockScreen.proto协议
	*/
	virtual void OnReply_StockScreen(Moomoo::u32_t nSerialNo, const Qot_StockScreen::Response &stRsp) = 0;

	/**
	* @brief 期权选股
	* @praram nSerialNo 包序列号
	* @param stRsp 回包，具体字段请参考Qot_OptionScreen.proto协议
	*/
	virtual void OnReply_OptionScreen(Moomoo::u32_t nSerialNo, const Qot_OptionScreen::Response &stRsp) = 0;

	/**
	* @brief 窝轮筛选V2
	* @praram nSerialNo 包序列号
	* @param stRsp 回包，具体字段请参考Qot_WarrantScreen.proto协议
	*/
	virtual void OnReply_WarrantScreen(Moomoo::u32_t nSerialNo, const Qot_WarrantScreen::Response &stRsp) = 0;

	/**
	* @brief 获取期权市场统计
	* @praram nSerialNo 包序列号
	* @param stRsp 回包，具体字段请参考Qot_GetOptionMarketStatistic.proto协议
	*/
	virtual void OnReply_GetOptionMarketStatistic(Moomoo::u32_t nSerialNo, const Qot_GetOptionMarketStatistic::Response &stRsp) = 0;
	/**
	* @brief 获取期权标的历史统计
	* @praram nSerialNo 包序列号
	* @param stRsp 回包，具体字段请参考Qot_GetOptionUnderlyingHisStatistic.proto协议
	*/
	virtual void OnReply_GetOptionUnderlyingHisStatistic(Moomoo::u32_t nSerialNo, const Qot_GetOptionUnderlyingHisStatistic::Response &stRsp) = 0;
	/**
	* @brief 获取批量标的最新数据
	* @praram nSerialNo 包序列号
	* @param stRsp 回包，具体字段请参考Qot_GetOptionUnderlyingOverview.proto协议
	*/
	virtual void OnReply_GetOptionUnderlyingOverview(Moomoo::u32_t nSerialNo, const Qot_GetOptionUnderlyingOverview::Response &stRsp) = 0;
	/**
	* @brief 获取历史波动率
	* @praram nSerialNo 包序列号
	* @param stRsp 回包，具体字段请参考Qot_GetOptionUnderlyingHisVolatility.proto协议
	*/
	virtual void OnReply_GetOptionUnderlyingHisVolatility(Moomoo::u32_t nSerialNo, const Qot_GetOptionUnderlyingHisVolatility::Response &stRsp) = 0;
	/**
	* @brief 获取标的排行
	* @praram nSerialNo 包序列号
	* @param stRsp 回包，具体字段请参考Qot_GetOptionUnderlyingRank.proto协议
	*/
	virtual void OnReply_GetOptionUnderlyingRank(Moomoo::u32_t nSerialNo, const Qot_GetOptionUnderlyingRank::Response &stRsp) = 0;
	/**
	* @brief 获取期权合约排行
	* @praram nSerialNo 包序列号
	* @param stRsp 回包，具体字段请参考Qot_GetOptionRank.proto协议
	*/
	virtual void OnReply_GetOptionRank(Moomoo::u32_t nSerialNo, const Qot_GetOptionRank::Response &stRsp) = 0;
	/**
	* @brief 获取期权异动列表
	* @praram nSerialNo 包序列号
	* @param stRsp 回包，具体字段请参考Qot_GetOptionEvent.proto协议
	*/
	virtual void OnReply_GetOptionEvent(Moomoo::u32_t nSerialNo, const Qot_GetOptionEvent::Response &stRsp) = 0;
	/**
	* @brief 获取期权异动告警设置
	* @praram nSerialNo 包序列号
	* @param stRsp 回包，具体字段请参考Qot_GetOptionEventAlert.proto协议
	*/
	virtual void OnReply_GetOptionEventAlert(Moomoo::u32_t nSerialNo, const Qot_GetOptionEventAlert::Response &stRsp) = 0;
	/**
	* @brief 修改期权异动告警条件
	* @praram nSerialNo 包序列号
	* @param stRsp 回包，具体字段请参考Qot_SetOptionEventAlert.proto协议
	*/
	virtual void OnReply_SetOptionEventAlert(Moomoo::u32_t nSerialNo, const Qot_SetOptionEventAlert::Response &stRsp) = 0;
	/**
	* @brief 获取末日期权标的列表
	* @praram nSerialNo 包序列号
	* @param stRsp 回包，具体字段请参考Qot_GetOptionZeroDteScreener.proto协议
	*/
	virtual void OnReply_GetOptionZeroDteScreener(Moomoo::u32_t nSerialNo, const Qot_GetOptionZeroDteScreener::Response &stRsp) = 0;
	/**
	* @brief 获取末日期权合约列表
	* @praram nSerialNo 包序列号
	* @param stRsp 回包，具体字段请参考Qot_GetOptionZeroDteContract.proto协议
	*/
	virtual void OnReply_GetOptionZeroDteContract(Moomoo::u32_t nSerialNo, const Qot_GetOptionZeroDteContract::Response &stRsp) = 0;
	/**
	* @brief 获取财报期权标的列表
	* @praram nSerialNo 包序列号
	* @param stRsp 回包，具体字段请参考Qot_GetOptionEarningsScreener.proto协议
	*/
	virtual void OnReply_GetOptionEarningsScreener(Moomoo::u32_t nSerialNo, const Qot_GetOptionEarningsScreener::Response &stRsp) = 0;
	/**
	* @brief 获取期权卖方策略列表
	* @praram nSerialNo 包序列号
	* @param stRsp 回包，具体字段请参考Qot_GetOptionSellerScreener.proto协议
	*/
	virtual void OnReply_GetOptionSellerScreener(Moomoo::u32_t nSerialNo, const Qot_GetOptionSellerScreener::Response &stRsp) = 0;
	/**
	* @brief 获取指标列表
	* @praram nSerialNo 包序列号
	* @param stRsp 回包，具体字段请参考Qot_GetIndicatorList.proto协议
	*/
	virtual void OnReply_GetIndicatorList(Moomoo::u32_t nSerialNo, const Qot_GetIndicatorList::Response &stRsp) = 0;
	/**
	* @brief 异步发起指标计算
	* @praram nSerialNo 包序列号
	* @param stRsp 回包，具体字段请参考Qot_RequestIndicatorCalc.proto协议
	*/
	virtual void OnReply_RequestIndicatorCalc(Moomoo::u32_t nSerialNo, const Qot_RequestIndicatorCalc::Response &stRsp) = 0;
	/**
	* @brief 搜索行情
	* @praram nSerialNo 包序列号
	* @param stRsp 回包，具体字段请参考Qot_GetSearchQuote.proto协议
	*/
	virtual void OnReply_GetSearchQuote(Moomoo::u32_t nSerialNo, const Qot_GetSearchQuote::Response &stRsp) = 0;
	/**
	* @brief 搜索资讯
	* @praram nSerialNo 包序列号
	* @param stRsp 回包，具体字段请参考Qot_GetSearchNews.proto协议
	*/
	virtual void OnReply_GetSearchNews(Moomoo::u32_t nSerialNo, const Qot_GetSearchNews::Response &stRsp) = 0;

	/**
	* @brief 获取财报日历
	* @praram nSerialNo 包序列号
	* @param stRsp 回包，具体字段请参考Qot_GetEarningsCalendar.proto协议
	*/
	virtual void OnReply_GetEarningsCalendar(Moomoo::u32_t nSerialNo, const Qot_GetEarningsCalendar::Response &stRsp) = 0;
	/**
	* @brief 获取宏观指标列表
	* @praram nSerialNo 包序列号
	* @param stRsp 回包，具体字段请参考Qot_GetMacroIndicatorList.proto协议
	*/
	virtual void OnReply_GetMacroIndicatorList(Moomoo::u32_t nSerialNo, const Qot_GetMacroIndicatorList::Response &stRsp) = 0;
	/**
	* @brief 获取宏观指标历史数据
	* @praram nSerialNo 包序列号
	* @param stRsp 回包，具体字段请参考Qot_GetMacroIndicatorHistory.proto协议
	*/
	virtual void OnReply_GetMacroIndicatorHistory(Moomoo::u32_t nSerialNo, const Qot_GetMacroIndicatorHistory::Response &stRsp) = 0;
	/**
	* @brief 获取美联储利率预测(FedWatch概率)
	* @praram nSerialNo 包序列号
	* @param stRsp 回包，具体字段请参考Qot_GetFedWatchTargetRate.proto协议
	*/
	virtual void OnReply_GetFedWatchTargetRate(Moomoo::u32_t nSerialNo, const Qot_GetFedWatchTargetRate::Response &stRsp) = 0;
	/**
	* @brief 获取CME利率点阵图
	* @praram nSerialNo 包序列号
	* @param stRsp 回包，具体字段请参考Qot_GetFedWatchDotPlot.proto协议
	*/
	virtual void OnReply_GetFedWatchDotPlot(Moomoo::u32_t nSerialNo, const Qot_GetFedWatchDotPlot::Response &stRsp) = 0;
	/**
	* @brief 获取盈利超预期排行
	* @praram nSerialNo 包序列号
	* @param stRsp 回包，具体字段请参考Qot_GetEarningsBeatRank.proto协议
	*/
	virtual void OnReply_GetEarningsBeatRank(Moomoo::u32_t nSerialNo, const Qot_GetEarningsBeatRank::Response &stRsp) = 0;
	/**
	* @brief 获取股息排行
	* @praram nSerialNo 包序列号
	* @param stRsp 回包，具体字段请参考Qot_GetDividendRank.proto协议
	*/
	virtual void OnReply_GetDividendRank(Moomoo::u32_t nSerialNo, const Qot_GetDividendRank::Response &stRsp) = 0;
	/**
	* @brief 获取派息日历
	* @praram nSerialNo 包序列号
	* @param stRsp 回包，具体字段请参考Qot_GetDividendCalendar.proto协议
	*/
	virtual void OnReply_GetDividendCalendar(Moomoo::u32_t nSerialNo, const Qot_GetDividendCalendar::Response &stRsp) = 0;
	/**
	* @brief 获取财经日历
	* @praram nSerialNo 包序列号
	* @param stRsp 回包，具体字段请参考Qot_GetEconomicCalendar.proto协议
	*/
	virtual void OnReply_GetEconomicCalendar(Moomoo::u32_t nSerialNo, const Qot_GetEconomicCalendar::Response &stRsp) = 0;
	/**
	* @brief 获取盘前榜(美股)
	* @praram nSerialNo 包序列号
	* @param stRsp 回包，具体字段请参考Qot_GetUSPreMarketRank.proto协议
	*/
	virtual void OnReply_GetUSPreMarketRank(Moomoo::u32_t nSerialNo, const Qot_GetUSPreMarketRank::Response &stRsp) = 0;
	/**
	* @brief 获取盘后榜(美股)
	* @praram nSerialNo 包序列号
	* @param stRsp 回包，具体字段请参考Qot_GetUSAfterHoursRank.proto协议
	*/
	virtual void OnReply_GetUSAfterHoursRank(Moomoo::u32_t nSerialNo, const Qot_GetUSAfterHoursRank::Response &stRsp) = 0;
	/**
	* @brief 获取夜盘榜(美股)
	* @praram nSerialNo 包序列号
	* @param stRsp 回包，具体字段请参考Qot_GetUSOvernightRank.proto协议
	*/
	virtual void OnReply_GetUSOvernightRank(Moomoo::u32_t nSerialNo, const Qot_GetUSOvernightRank::Response &stRsp) = 0;
	/**
	* @brief 获取领涨/领跌榜
	* @praram nSerialNo 包序列号
	* @param stRsp 回包，具体字段请参考Qot_GetTopMoversRank.proto协议
	*/
	virtual void OnReply_GetTopMoversRank(Moomoo::u32_t nSerialNo, const Qot_GetTopMoversRank::Response &stRsp) = 0;
	/**
	* @brief 获取热议榜
	* @praram nSerialNo 包序列号
	* @param stRsp 回包，具体字段请参考Qot_GetHotList.proto协议
	*/
	virtual void OnReply_GetHotList(Moomoo::u32_t nSerialNo, const Qot_GetHotList::Response &stRsp) = 0;
	/**
	* @brief 获取卖空异动榜(美股)
	* @praram nSerialNo 包序列号
	* @param stRsp 回包，具体字段请参考Qot_GetShortSellingRank.proto协议
	*/
	virtual void OnReply_GetShortSellingRank(Moomoo::u32_t nSerialNo, const Qot_GetShortSellingRank::Response &stRsp) = 0;
	/**
	* @brief 获取区间涨跌幅
	* @praram nSerialNo 包序列号
	* @param stRsp 回包，具体字段请参考Qot_GetPeriodChangeRank.proto协议
	*/
	virtual void OnReply_GetPeriodChangeRank(Moomoo::u32_t nSerialNo, const Qot_GetPeriodChangeRank::Response &stRsp) = 0;
	/**
	* @brief 获取破净高股息国央企(港股)
	* @praram nSerialNo 包序列号
	* @param stRsp 回包，具体字段请参考Qot_GetHighDividendSOERank.proto协议
	*/
	virtual void OnReply_GetHighDividendSOERank(Moomoo::u32_t nSerialNo, const Qot_GetHighDividendSOERank::Response &stRsp) = 0;
	/**
	* @brief 获取机构持仓列表
	* @praram nSerialNo 包序列号
	* @param stRsp 回包，具体字段请参考Qot_GetInstitutionList.proto协议
	*/
	virtual void OnReply_GetInstitutionList(Moomoo::u32_t nSerialNo, const Qot_GetInstitutionList::Response &stRsp) = 0;
	/**
	* @brief 获取机构概况
	* @praram nSerialNo 包序列号
	* @param stRsp 回包，具体字段请参考Qot_GetInstitutionProfile.proto协议
	*/
	virtual void OnReply_GetInstitutionProfile(Moomoo::u32_t nSerialNo, const Qot_GetInstitutionProfile::Response &stRsp) = 0;
	/**
	* @brief 获取机构持仓行业分布
	* @praram nSerialNo 包序列号
	* @param stRsp 回包，具体字段请参考Qot_GetInstitutionDistribution.proto协议
	*/
	virtual void OnReply_GetInstitutionDistribution(Moomoo::u32_t nSerialNo, const Qot_GetInstitutionDistribution::Response &stRsp) = 0;
	/**
	* @brief 获取机构持仓变动
	* @praram nSerialNo 包序列号
	* @param stRsp 回包，具体字段请参考Qot_GetInstitutionHoldingChange.proto协议
	*/
	virtual void OnReply_GetInstitutionHoldingChange(Moomoo::u32_t nSerialNo, const Qot_GetInstitutionHoldingChange::Response &stRsp) = 0;
	/**
	* @brief 获取机构持股列表
	* @praram nSerialNo 包序列号
	* @param stRsp 回包，具体字段请参考Qot_GetInstitutionHoldingList.proto协议
	*/
	virtual void OnReply_GetInstitutionHoldingList(Moomoo::u32_t nSerialNo, const Qot_GetInstitutionHoldingList::Response &stRsp) = 0;
	/**
	* @brief 获取ARK基金持仓
	* @praram nSerialNo 包序列号
	* @param stRsp 回包，具体字段请参考Qot_GetArkFundHolding.proto协议
	*/
	virtual void OnReply_GetArkFundHolding(Moomoo::u32_t nSerialNo, const Qot_GetArkFundHolding::Response &stRsp) = 0;
	/**
	* @brief 获取ARK个股交易动态
	* @praram nSerialNo 包序列号
	* @param stRsp 回包，具体字段请参考Qot_GetArkStockDynamic.proto协议
	*/
	virtual void OnReply_GetArkStockDynamic(Moomoo::u32_t nSerialNo, const Qot_GetArkStockDynamic::Response &stRsp) = 0;
	/**
	* @brief 获取ARK主动交易聚合
	* @praram nSerialNo 包序列号
	* @param stRsp 回包，具体字段请参考Qot_GetArkActiveTransaction.proto协议
	*/
	virtual void OnReply_GetArkActiveTransaction(Moomoo::u32_t nSerialNo, const Qot_GetArkActiveTransaction::Response &stRsp) = 0;
	/**
	* @brief 获取评级变动
	* @praram nSerialNo 包序列号
	* @param stRsp 回包，具体字段请参考Qot_GetRatingChange.proto协议
	*/
	virtual void OnReply_GetRatingChange(Moomoo::u32_t nSerialNo, const Qot_GetRatingChange::Response &stRsp) = 0;
	/**
	* @brief 获取产业链列表
	* @praram nSerialNo 包序列号
	* @param stRsp 回包，具体字段请参考Qot_GetIndustrialChainList.proto协议
	*/
	virtual void OnReply_GetIndustrialChainList(Moomoo::u32_t nSerialNo, const Qot_GetIndustrialChainList::Response &stRsp) = 0;
	/**
	* @brief 获取产业链详情
	* @praram nSerialNo 包序列号
	* @param stRsp 回包，具体字段请参考Qot_GetIndustrialChainDetail.proto协议
	*/
	virtual void OnReply_GetIndustrialChainDetail(Moomoo::u32_t nSerialNo, const Qot_GetIndustrialChainDetail::Response &stRsp) = 0;
	/**
	* @brief 获取板块关联产业链
	* @praram nSerialNo 包序列号
	* @param stRsp 回包，具体字段请参考Qot_GetIndustrialChainByPlate.proto协议
	*/
	virtual void OnReply_GetIndustrialChainByPlate(Moomoo::u32_t nSerialNo, const Qot_GetIndustrialChainByPlate::Response &stRsp) = 0;
	/**
	* @brief 获取产业板块信息
	* @praram nSerialNo 包序列号
	* @param stRsp 回包，具体字段请参考Qot_GetIndustrialPlateInfo.proto协议
	*/
	virtual void OnReply_GetIndustrialPlateInfo(Moomoo::u32_t nSerialNo, const Qot_GetIndustrialPlateInfo::Response &stRsp) = 0;
	/**
	* @brief 获取产业板块成分股
	* @praram nSerialNo 包序列号
	* @param stRsp 回包，具体字段请参考Qot_GetIndustrialPlateStock.proto协议
	*/
	virtual void OnReply_GetIndustrialPlateStock(Moomoo::u32_t nSerialNo, const Qot_GetIndustrialPlateStock::Response &stRsp) = 0;
	/**
	* @brief 获取热力图数据
	* @praram nSerialNo 包序列号
	* @param stRsp 回包，具体字段请参考Qot_GetHeatMapData.proto协议
	*/
	virtual void OnReply_GetHeatMapData(Moomoo::u32_t nSerialNo, const Qot_GetHeatMapData::Response &stRsp) = 0;
	/**
	* @brief 获取涨跌分布
	* @praram nSerialNo 包序列号
	* @param stRsp 回包，具体字段请参考Qot_GetRiseFallDistribution.proto协议
	*/
	virtual void OnReply_GetRiseFallDistribution(Moomoo::u32_t nSerialNo, const Qot_GetRiseFallDistribution::Response &stRsp) = 0;
	/**
	* @brief 推送通知
	* @praram nSerialNo 包序列号
	* @param stRsp 回包，具体字段请参考Notify.proto协议
	*/
	virtual void OnPush_Notify(const Notify::Response &stRsp) = 0;
	/**
	* @brief 推送逐笔
	* @praram nSerialNo 包序列号
	* @param stRsp 回包，具体字段请参考Qot_UpdateTicker.proto协议
	*/
	virtual void OnPush_UpdateTicker(const Qot_UpdateTicker::Response &stRsp) = 0;
	/**
	* @brief 推送报价
	* @praram nSerialNo 包序列号
	* @param stRsp 回包，具体字段请参考Qot_UpdateBasicQot.proto协议
	*/
	virtual void OnPush_UpdateBasicQot(const Qot_UpdateBasicQot::Response &stRsp) = 0;
	/**
	* @brief 推送摆盘
	* @praram nSerialNo 包序列号
	* @param stRsp 回包，具体字段请参考Qot_UpdateOrderBook.proto协议
	*/
	virtual void OnPush_UpdateOrderBook(const Qot_UpdateOrderBook::Response &stRsp) = 0;
	/**
	* @brief 推送K线
	* @praram nSerialNo 包序列号
	* @param stRsp 回包，具体字段请参考Qot_UpdateKL.proto协议
	*/
	virtual void OnPush_UpdateKL(const Qot_UpdateKL::Response &stRsp) = 0;
	/**
	* @brief 推送分时
	* @praram nSerialNo 包序列号
	* @param stRsp 回包，具体字段请参考Qot_UpdateRT.proto协议
	*/
	virtual void OnPush_UpdateRT(const Qot_UpdateRT::Response &stRsp) = 0;
	/**
	* @brief 推送经纪队列
	* @praram nSerialNo 包序列号
	* @param stRsp 回包，具体字段请参考Qot_UpdateBroker.proto协议
	*/
	virtual void OnPush_UpdateBroker(const Qot_UpdateBroker::Response &stRsp) = 0;
	/**
	* @brief 推送到价提醒通知
	* @praram nSerialNo 包序列号
	* @param stRsp 回包，具体字段请参考Qot_UpdatePriceReminder.proto协议
	*/
	virtual void OnPush_UpdatePriceReminder(const Qot_UpdatePriceReminder::Response &stRsp) = 0;
	/**
	* @brief 推送期权异动
	* @praram nSerialNo 包序列号
	* @param stRsp 回包，具体字段请参考Qot_UpdateOptionEvent.proto协议
	*/
	virtual void OnPush_UpdateOptionEvent(const Qot_UpdateOptionEvent::Response &stRsp) = 0;
	/**
	* @brief 推送指标异步计算结果
	* @praram nSerialNo 包序列号
	* @param stRsp 回包，具体字段请参考Qot_PushIndicatorCalc.proto协议
	*/
	virtual void OnPush_PushIndicatorCalc(const Qot_PushIndicatorCalc::Response &stRsp) = 0;
};

class MMSPI_Trd
{
public:
	/**
	* @brief 获取交易账户列表
	* @praram nSerialNo 包序列号
	* @param stRsp 回包，具体字段请参考Trd_GetAccList.proto协议
	*/
	virtual void OnReply_GetAccList(Moomoo::u32_t nSerialNo, const Trd_GetAccList::Response &stRsp) = 0;
	/**
	* @brief 解锁
	* @praram nSerialNo 包序列号
	* @param stRsp 回包，具体字段请参考Trd_UnlockTrade.proto协议
	*/
	virtual void OnReply_UnlockTrade(Moomoo::u32_t nSerialNo, const Trd_UnlockTrade::Response &stRsp) = 0;
	/**
	* @brief 订阅接收推送数据的交易账户
	* @praram nSerialNo 包序列号
	* @param stRsp 回包，具体字段请参考Trd_SubAccPush.proto协议
	*/
	virtual void OnReply_SubAccPush(Moomoo::u32_t nSerialNo, const Trd_SubAccPush::Response &stRsp) = 0;
	/**
	* @brief 获取账户资金
	* @praram nSerialNo 包序列号
	* @param stRsp 回包，具体字段请参考Trd_GetFunds.proto协议
	*/
	virtual void OnReply_GetFunds(Moomoo::u32_t nSerialNo, const Trd_GetFunds::Response &stRsp) = 0;
	/**
	* @brief 获取账户持仓
	* @praram nSerialNo 包序列号
	* @param stRsp 回包，具体字段请参考Trd_GetPositionList.proto协议
	*/
	virtual void OnReply_GetPositionList(Moomoo::u32_t nSerialNo, const Trd_GetPositionList::Response &stRsp) = 0;
	/**
	* @brief 获取最大交易数量
	* @praram nSerialNo 包序列号
	* @param stRsp 回包，具体字段请参考Trd_GetMaxTrdQtys.proto协议
	*/
	virtual void OnReply_GetMaxTrdQtys(Moomoo::u32_t nSerialNo, const Trd_GetMaxTrdQtys::Response &stRsp) = 0;
	/**
	* @brief 获取组合的可买卖信息
	* @praram nSerialNo 包序列号
	* @param stRsp 回包，具体字段请参考Trd_GetComboMaxTrdQtys.proto协议
	*/
	virtual void OnReply_GetComboMaxTrdQtys(Moomoo::u32_t nSerialNo, const Trd_GetComboMaxTrdQtys::Response &stRsp) = 0;
	/**
	* @brief 获取当日订单列表
	* @praram nSerialNo 包序列号
	* @param stRsp 回包，具体字段请参考Trd_GetOrderList.proto协议
	*/
	virtual void OnReply_GetOrderList(Moomoo::u32_t nSerialNo, const Trd_GetOrderList::Response &stRsp) = 0;
	/**
	* @brief 下单
	* @praram nSerialNo 包序列号
	* @param stRsp 回包，具体字段请参考Trd_PlaceOrder.proto协议
	*/
	virtual void OnReply_PlaceOrder(Moomoo::u32_t nSerialNo, const Trd_PlaceOrder::Response &stRsp) = 0;
	/**
	* @brief 组合期权下单
	* @praram nSerialNo 包序列号
	* @param stRsp 回包，具体字段请参考Trd_PlaceComboOrder.proto协议
	*/
	virtual void OnReply_PlaceComboOrder(Moomoo::u32_t nSerialNo, const Trd_PlaceComboOrder::Response &stRsp) = 0;
	/**
	* @brief 修改订单
	* @praram nSerialNo 包序列号
	* @param stRsp 回包，具体字段请参考Trd_ModifyOrder.proto协议
	*/
	virtual void OnReply_ModifyOrder(Moomoo::u32_t nSerialNo, const Trd_ModifyOrder::Response &stRsp) = 0;
	/**
	* @brief 获取当日成交列表
	* @praram nSerialNo 包序列号
	* @param stRsp 回包，具体字段请参考Trd_GetOrderFillList.proto协议
	*/
	virtual void OnReply_GetOrderFillList(Moomoo::u32_t nSerialNo, const Trd_GetOrderFillList::Response &stRsp) = 0;
	/**
	* @brief 获取历史订单列表
	* @praram nSerialNo 包序列号
	* @param stRsp 回包，具体字段请参考Trd_GetHistoryOrderList.proto协议
	*/
	virtual void OnReply_GetHistoryOrderList(Moomoo::u32_t nSerialNo, const Trd_GetHistoryOrderList::Response &stRsp) = 0;
	/**
	* @brief 获取融资融券数据
	* @praram nSerialNo 包序列号
	* @param stRsp 回包，具体字段请参考Trd_GetMarginRatio.proto协议
	*/
	virtual void OnReply_GetMarginRatio(Moomoo::u32_t nSerialNo, const Trd_GetMarginRatio::Response &stRsp) = 0;
	/**
	* @brief 获取历史成交列表
	* @praram nSerialNo 包序列号
	* @param stRsp 回包，具体字段请参考Trd_GetHistoryOrderFillList.proto协议
	*/
	virtual void OnReply_GetHistoryOrderFillList(Moomoo::u32_t nSerialNo, const Trd_GetHistoryOrderFillList::Response &stRsp) = 0;
	/**
	* @brief 获取订单费用数据
    * @praram nSerialNo 包序列号
    * @param stRsp 回包，Trd_GetOrderFee.proto协议
    */
    virtual void OnReply_GetOrderFee(Moomoo::u32_t nSerialNo, const Trd_GetOrderFee::Response & stRsp) = 0;
	/**
	* @brief 获取现价流水
	* @praram nSerialNo 包序列号
    * @param stRsp 回包，Trd_FlowSummary.proto协议
	*/
    virtual void OnReply_GetFlowSummary(Moomoo::u32_t nSerialNo, const Trd_FlowSummary::Response& stRsp) = 0;
	/**
	* @brief 推送订单变化
	* @praram nSerialNo 包序列号
	* @param stRsp 回包，具体字段请参考Trd_UpdateOrder.proto协议
	*/
	virtual void OnPush_UpdateOrder(const Trd_UpdateOrder::Response &stRsp) = 0;
	/**
	* @brief 订单成交推送
	* @praram nSerialNo 包序列号
	* @param stRsp 回包，具体字段请参考Trd_UpdateOrderFill.proto协议
	*/
	virtual void OnPush_UpdateOrderFill(const Trd_UpdateOrderFill::Response &stRsp) = 0;
};
}
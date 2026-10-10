// Copyright 2026 Moomoo
#pragma once
#include "MMAPI_Define.h"

class MMAPIImp;
namespace Moomoo {
class MMSPI_Conn;
class MMSPI_Qot;
class MMSPI_Trd;
class  MMAPI_Conn
{
public:
	MMAPI_Conn();
	virtual ~MMAPI_Conn();

public:
	/**
	* @brief 设置客户端信息
	* @param [in] strClientID 客户端标识
	* @param [in] nClientVer 客户端版本
	*/
	void SetClientInfo(const char* szClientID, Moomoo::i32_t nClientVer);

	/**
	* @brief 设置密钥
	* @param [in] strRSAPrivateKey 密钥
	*/
	void SetRSAPrivateKey(const char* szRSAPrivateKey);
	
	/**
	* @brief 初始化连接，连接并初始化
	* @param [in] szIPAddr 地址
	* @param [in] nPort 端口
	* @param [in] bEnableEncrypt 启用加密
	* @return bool 是否启动了执行，不代表连接结果，结果通过OnInitConnect回调
	*/
	bool InitConnect(const char* szIPAddr, Moomoo::u16_t nPort, bool bEnableEncrypt);

	/**
	* @brief 此连接的连接ID，连接的唯一标识，InitConnect协议返回，没有初始化前为0
	* @return 连接ID
	*/
	Moomoo::u64_t GetConnectID();

	/**
	* @brief 关闭连接
	* @return 是否成功
	*/
	bool Close();

	/**
	* @brief 注册回调
	* @param [in] pSpi 回调，该对象没有反注册前不可销毁
	*/
	void RegisterConnSpi(MMSPI_Conn* pSpi);

	/**
	* @brief 反注册回调
	*/
	void UnregisterConnSpi();

protected:
	MMAPIImp *m_pImp{ nullptr };
};

/**
* @brief 行情接口
*/
class  MMAPI_Qot : public MMAPI_Conn
{
public:
	MMAPI_Qot();
	virtual ~MMAPI_Qot();

public:
	/**
	* @brief 注册回调
	* @param [in] pSpi 回调，该对象没有反注册前不可销毁
	*/
	void RegisterQotSpi(MMSPI_Qot* pSpi);

	/**
	* @brief 反注册回调
	*/
	void UnregisterQotSpi();

	/**
	* @brief 订阅，反订阅
	* @param [in] stReq 请求包，具体字段请参考Qot_Sub.proto协议
	* @return Moomoo::u32_t 包序列号， 0表示请求发送失败
	*/
	Moomoo::u32_t Sub(const Qot_Sub::Request &stReq);
	/**
	* @brief 获取全局信息
	* @param [in] stReq 请求包，具体字段请参考GetGlobalState.proto协议
	* @return Moomoo::u32_t 包序列号， 0表示请求发送失败
	*/
	Moomoo::u32_t GetGlobalState(const GetGlobalState::Request &stReq);
	/**
	* @brief 注册推送，用于当前连接订阅，但是在其他连接获取推送的场景
	* @param [in] stReq 请求包，具体字段请参考Qot_RegQotPush.proto协议
	* @return Moomoo::u32_t 包序列号， 0表示请求发送失败
	*/
	Moomoo::u32_t RegQotPush(const Qot_RegQotPush::Request &stReq);
	/**
	* @brief 获取订阅信息
	* @param [in] stReq 请求包，具体字段请参考Qot_GetSubInfo.proto协议
	* @return Moomoo::u32_t 包序列号， 0表示请求发送失败
	*/
	Moomoo::u32_t GetSubInfo(const Qot_GetSubInfo::Request &stReq);
	/**
	* @brief 获取逐笔，调用该接口前需要先订阅(订阅位：Qot_Common.SubType_Ticker)
	* @param [in] stReq 请求包，具体字段请参考Qot_GetTicker.proto协议
	* @return Moomoo::u32_t 包序列号， 0表示请求发送失败
	*/
	Moomoo::u32_t GetTicker(const Qot_GetTicker::Request &stReq);
	/**
	* @brief 获取报价，调用该接口前需要先订阅(订阅位：Qot_Common.SubType_Basic)
	* @param [in] stReq 请求包，具体字段请参考Qot_GetBasicQot.proto协议
	* @return Moomoo::u32_t 包序列号， 0表示请求发送失败
	*/
	Moomoo::u32_t GetBasicQot(const Qot_GetBasicQot::Request &stReq);
	/**
	* @brief 获取摆盘，调用该接口前需要先订阅(订阅位：Qot_Common.SubType_OrderBook)
	* @param [in] stReq 请求包，具体字段请参考Qot_GetOrderBook.proto协议
	* @return Moomoo::u32_t 包序列号， 0表示请求发送失败
	*/
	Moomoo::u32_t GetOrderBook(const Qot_GetOrderBook::Request &stReq);
	/**
	* @brief 获取K线，调用该接口前需要先订阅(订阅位：Qot_Common.SubType_KL_XXX)
	* @param [in] stReq 请求包，具体字段请参考Qot_GetKL.proto协议
	* @return Moomoo::u32_t 包序列号， 0表示请求发送失败
	*/
	Moomoo::u32_t GetKL(const Qot_GetKL::Request &stReq);
	/**
	* @brief 获取分时，调用该接口前需要先订阅(订阅位：Qot_Common.SubType_RT)
	* @param [in] stReq 请求包，具体字段请参考GetRT.proto协议
	* @return Moomoo::u32_t 包序列号， 0表示请求发送失败
	*/
	Moomoo::u32_t GetRT(const Qot_GetRT::Request &stReq);
	/**
	* @brief 获取经纪队列，调用该接口前需要先订阅(订阅位：Qot_Common.SubType_Broker)
	* @param [in] stReq 请求包，具体字段请参考Qot_GetBroker.proto协议
	* @return Moomoo::u32_t 包序列号， 0表示请求发送失败
	*/
	Moomoo::u32_t GetBroker(const Qot_GetBroker::Request &stReq);
	/**
	* @brief 在线请求历史复权信息，不读本地历史数据DB
	* @param [in] stReq 请求包，具体字段请参考Qot_RequestRehab.proto协议
	* @return Moomoo::u32_t 包序列号， 0表示请求发送失败
	*/
	Moomoo::u32_t RequestRehab(const Qot_RequestRehab::Request &stReq);
	/**
	* @brief 在线请求历史K线，不读本地历史数据DB
	* @param [in] stReq 请求包，具体字段请参考Qot_RequestHistoryKL.proto协议
	* @return Moomoo::u32_t 包序列号， 0表示请求发送失败
	*/
	Moomoo::u32_t RequestHistoryKL(const Qot_RequestHistoryKL::Request &stReq);
	/**
	* @brief 获取历史K线已经用掉的额度 
	* @param [in] stReq 请求包，具体字段请参考Qot_RequestHistoryKLQuota.proto协议
	* @return Moomoo::u32_t 包序列号， 0表示请求发送失败
	*/
	Moomoo::u32_t RequestHistoryKLQuota(const Qot_RequestHistoryKLQuota::Request &stReq);
	/**
	* @brief 获取静态信息
	* @param [in] stReq 请求包，具体字段请参考Qot_GetStaticInfo.proto协议
	* @return Moomoo::u32_t 包序列号， 0表示请求发送失败
	*/
	Moomoo::u32_t GetStaticInfo(const Qot_GetStaticInfo::Request &stReq);
	/**
	* @brief 获取股票快照
	* @param [in] stReq 请求包，具体字段请参考Qot_GetSecuritySnapshot.proto协议
	* @return Moomoo::u32_t 包序列号， 0表示请求发送失败
	*/
	Moomoo::u32_t GetSecuritySnapshot(const Qot_GetSecuritySnapshot::Request &stReq);
	/**
	* @brief 获取板块集合下的板块
	* @param [in] stReq 请求包，具体字段请参考Qot_GetPlateSet.proto协议
	* @return Moomoo::u32_t 包序列号， 0表示请求发送失败
	*/
	Moomoo::u32_t GetPlateSet(const Qot_GetPlateSet::Request &stReq);
	/**
	* @brief 获取板块下的股票
	* @param [in] stReq 请求包，具体字段请参考Qot_GetPlateSecurity.proto协议
	* @return Moomoo::u32_t 包序列号， 0表示请求发送失败
	*/
	Moomoo::u32_t GetPlateSecurity(const Qot_GetPlateSecurity::Request &stReq);
	/**
	* @brief 获取相关股票
	* @param [in] stReq 请求包，具体字段请参考Qot_GetReference.proto协议
	* @return Moomoo::u32_t 包序列号， 0表示请求发送失败
	*/
	Moomoo::u32_t GetReference(const Qot_GetReference::Request &stReq);
	/**
	* @brief 获取股票所属的板块
	* @param [in] stReq 请求包，具体字段请参考Qot_GetOwnerPlate.proto协议
	* @return Moomoo::u32_t 包序列号， 0表示请求发送失败
	*/
	Moomoo::u32_t GetOwnerPlate(const Qot_GetOwnerPlate::Request &stReq);
	/**
	* @brief 获取大股东持股变化列表
	* @param [in] stReq 请求包，具体字段请参考Qot_GetHoldingChangeList.proto协议
	* @return Moomoo::u32_t 包序列号， 0表示请求发送失败
	*/
	Moomoo::u32_t GetHoldingChangeList(const Qot_GetHoldingChangeList::Request &stReq);
	/**
	* @brief 筛选期权
	* @param [in] stReq 请求包，具体字段请参考Qot_GetOptionChain.proto协议
	* @return Moomoo::u32_t 包序列号， 0表示请求发送失败
	*/
	Moomoo::u32_t GetOptionChain(const Qot_GetOptionChain::Request &stReq);
	/**
	* @brief 筛选窝轮
	* @param [in] stReq 请求包，具体字段请参考Qot_GetWarrant.proto协议
	* @return Moomoo::u32_t 包序列号， 0表示请求发送失败
	*/
	Moomoo::u32_t GetWarrant(const Qot_GetWarrant::Request &stReq);
	/**
	* @brief 获取资金流向
	* @param [in] stReq 请求包，具体字段请参考Qot_GetCapitalFlow.proto协议
	* @return Moomoo::u32_t 包序列号， 0表示请求发送失败
	*/
	Moomoo::u32_t GetCapitalFlow(const Qot_GetCapitalFlow::Request &stReq);
	/**
	* @brief 获取资金分布
	* @param [in] stReq 请求包，具体字段请参考Qot_GetCapitalDistribution.proto协议
	* @return Moomoo::u32_t 包序列号， 0表示请求发送失败
	*/
	Moomoo::u32_t GetCapitalDistribution(const Qot_GetCapitalDistribution::Request &stReq);
	/**
	* @brief 获取自选股分组下的股票
	* @param [in] stReq 请求包，具体字段请参考Qot_GetUserSecurity.proto协议
	* @return Moomoo::u32_t 包序列号， 0表示请求发送失败
	*/
	Moomoo::u32_t GetUserSecurity(const Qot_GetUserSecurity::Request &stReq);
	/**
	* @brief 修改自选股分组下的股票
	* @param [in] stReq 请求包，具体字段请参考Qot_ModifyUserSecurity.proto协议
	* @return Moomoo::u32_t 包序列号， 0表示请求发送失败
	*/
	Moomoo::u32_t ModifyUserSecurity(const Qot_ModifyUserSecurity::Request &stReq);
	/**
	* @brief 条件选股
	* @param [in] stReq 请求包，具体字段请参考Qot_StockFilter.proto协议
	* @return Moomoo::u32_t 包序列号， 0表示请求发送失败
	*/
	Moomoo::u32_t StockFilter(const Qot_StockFilter::Request &stReq);

	/**
	* @brief 获取股票代码变化
	* @param [in] stReq 请求包，具体字段请参考Qot_GetCodeChange.proto协议
	* @return Moomoo::u32_t 包序列号， 0表示请求发送失败
	*/
	Moomoo::u32_t GetCodeChange(const Qot_GetCodeChange::Request &stReq);

	/**
	* @brief 新股IPO
	* @param [in] stReq 请求包，具体字段请参考Qot_GetIpoList.proto协议
	* @return Moomoo::u32_t 包序列号， 0表示请求发送失败
	*/
	Moomoo::u32_t GetIpoList(const Qot_GetIpoList::Request &stReq);

	/**
	* @brief 期货合约资料
	* @param [in] stReq 请求包，具体字段请参考Qot_GetFutureInfo.proto协议
	* @return Moomoo::u32_t 包序列号， 0表示请求发送失败
	*/
	Moomoo::u32_t GetFutureInfo(const Qot_GetFutureInfo::Request &stReq);

	/**
	* @brief 获取市场交易日，在线拉取不在本地计算
	* @param [in] stReq 请求包，具体字段请参考Qot_RequestTradeDate.proto协议
	* @return Moomoo::u32_t 包序列号， 0表示请求发送失败
	*/
	Moomoo::u32_t RequestTradeDate(const Qot_RequestTradeDate::Request &stReq);

	/**
	* @brief 设置到价提醒
	* @param [in] stReq 请求包，具体字段请参考Qot_SetPriceReminder.proto协议
	* @return Moomoo::u32_t 包序列号， 0表示请求发送失败
	*/
	Moomoo::u32_t SetPriceReminder(const Qot_SetPriceReminder::Request &stReq);

	/**
	* @brief 获取到价提醒
	* @param [in] stReq 请求包，具体字段请参考Qot_GetPriceReminder.proto协议
	* @return Moomoo::u32_t 包序列号， 0表示请求发送失败
	*/
	Moomoo::u32_t GetPriceReminder(const Qot_GetPriceReminder::Request &stReq);

	/**
	* @brief 获取自选股分组列表
	* @param [in] stReq 请求包，具体字段请参考Qot_GetUserSecurityGroup.proto协议
	* @return Moomoo::u32_t 包序列号， 0表示请求发送失败
	*/
	Moomoo::u32_t GetUserSecurityGroup(const Qot_GetUserSecurityGroup::Request &stReq);
	
	/**
	* @brief 获取市场状态
	* @param [in] stReq 请求包，具体字段请参考Qot_GetMarketState.proto协议
	* @return Moomoo::u32_t 包序列号， 0表示请求发送失败
	*/
	Moomoo::u32_t GetMarketState(const Qot_GetMarketState::Request &stReq);

	/**
	* @brief 获取期权链到期日
	* @param [in] stReq 请求包，具体字段请参考Qot_GetOptionExpirationDate.proto协议
	* @return Moomoo::u32_t 包序列号， 0表示请求发送失败
	*/
	Moomoo::u32_t GetOptionExpirationDate(const Qot_GetOptionExpirationDate::Request &stReq);

	/**
	* @brief 获取期权行情
	* @param [in] stReq 请求包，具体字段请参考Qot_GetOptionQuote.proto协议
	* @return Moomoo::u32_t 包序列号， 0表示请求发送失败
	*/
	Moomoo::u32_t GetOptionQuote(const Qot_GetOptionQuote::Request &stReq);
	/**
	* @brief 获取期权策略
	* @param [in] stReq 请求包，具体字段请参考Qot_GetOptionStrategy.proto协议
	* @return Moomoo::u32_t 包序列号， 0表示请求发送失败
	*/
	Moomoo::u32_t GetOptionStrategy(const Qot_GetOptionStrategy::Request &stReq);
	/**
	* @brief 获取期权策略分析
	* @param [in] stReq 请求包，具体字段请参考Qot_GetOptionStrategyAnalysis.proto协议
	* @return Moomoo::u32_t 包序列号， 0表示请求发送失败
	*/
	Moomoo::u32_t GetOptionStrategyAnalysis(const Qot_GetOptionStrategyAnalysis::Request &stReq);
	/**
	* @brief 获取期权策略价差
	* @param [in] stReq 请求包，具体字段请参考Qot_GetOptionStrategySpread.proto协议
	* @return Moomoo::u32_t 包序列号， 0表示请求发送失败
	*/
	Moomoo::u32_t GetOptionStrategySpread(const Qot_GetOptionStrategySpread::Request &stReq);

	/**
	* @brief 获取个股财报日前后价格涨跌幅表现
	* @param [in] stReq 请求包，具体字段请参考Qot_GetFinancialsEarningsPriceMove.proto协议
	* @return Moomoo::u32_t 包序列号， 0表示请求发送失败
	*/
	Moomoo::u32_t GetFinancialsEarningsPriceMove(const Qot_GetFinancialsEarningsPriceMove::Request &stReq);
	/**
	* @brief 获取个股财报日前后股价历史
	* @param [in] stReq 请求包，具体字段请参考Qot_GetFinancialsEarningsPriceHistory.proto协议
	* @return Moomoo::u32_t 包序列号， 0表示请求发送失败
	*/
	Moomoo::u32_t GetFinancialsEarningsPriceHistory(const Qot_GetFinancialsEarningsPriceHistory::Request &stReq);
	/**
	* @brief 获取财务报表
	* @param [in] stReq 请求包，具体字段请参考Qot_GetFinancialsStatements.proto协议
	* @return Moomoo::u32_t 包序列号， 0表示请求发送失败
	*/
	Moomoo::u32_t GetFinancialsStatements(const Qot_GetFinancialsStatements::Request &stReq);
	/**
	* @brief 获取主营构成
	* @param [in] stReq 请求包，具体字段请参考Qot_GetFinancialsRevenueBreakdown.proto协议
	* @return Moomoo::u32_t 包序列号， 0表示请求发送失败
	*/
	Moomoo::u32_t GetFinancialsRevenueBreakdown(const Qot_GetFinancialsRevenueBreakdown::Request &stReq);
	/**
	* @brief 获取分析师评级概述
	* @param [in] stReq 请求包，具体字段请参考Qot_GetResearchAnalystConsensus.proto协议
	* @return Moomoo::u32_t 包序列号， 0表示请求发送失败
	*/
	Moomoo::u32_t GetResearchAnalystConsensus(const Qot_GetResearchAnalystConsensus::Request &stReq);
	/**
	* @brief 获取评级汇总
	* @param [in] stReq 请求包，具体字段请参考Qot_GetResearchRatingSummary.proto协议
	* @return Moomoo::u32_t 包序列号， 0表示请求发送失败
	*/
	Moomoo::u32_t GetResearchRatingSummary(const Qot_GetResearchRatingSummary::Request &stReq);
	/**
	* @brief 获取晨星研究报告
	* @param [in] stReq 请求包，具体字段请参考Qot_GetResearchMorningstarReport.proto协议
	* @return Moomoo::u32_t 包序列号， 0表示请求发送失败
	*/
	Moomoo::u32_t GetResearchMorningstarReport(const Qot_GetResearchMorningstarReport::Request &stReq);
	/**
	* @brief 获取估值详情
	* @param [in] stReq 请求包，具体字段请参考Qot_GetValuationDetail.proto协议
	* @return Moomoo::u32_t 包序列号， 0表示请求发送失败
	*/
	Moomoo::u32_t GetValuationDetail(const Qot_GetValuationDetail::Request &stReq);
	/**
	* @brief 获取板块/指数成分股估值
	* @param [in] stReq 请求包，具体字段请参考Qot_GetValuationPlateStockList.proto协议
	* @return Moomoo::u32_t 包序列号， 0表示请求发送失败
	*/
	Moomoo::u32_t GetValuationPlateStockList(const Qot_GetValuationPlateStockList::Request &stReq);
	/**
	* @brief 获取分红派息
	* @param [in] stReq 请求包，具体字段请参考Qot_GetCorporateActionsDividends.proto协议
	* @return Moomoo::u32_t 包序列号， 0表示请求发送失败
	*/
	Moomoo::u32_t GetCorporateActionsDividends(const Qot_GetCorporateActionsDividends::Request &stReq);
	/**
	* @brief 获取回购
	* @param [in] stReq 请求包，具体字段请参考Qot_GetCorporateActionsBuybacks.proto协议
	* @return Moomoo::u32_t 包序列号， 0表示请求发送失败
	*/
	Moomoo::u32_t GetCorporateActionsBuybacks(const Qot_GetCorporateActionsBuybacks::Request &stReq);
	/**
	* @brief 获取拆合股
	* @param [in] stReq 请求包，具体字段请参考Qot_GetCorporateActionsStockSplits.proto协议
	* @return Moomoo::u32_t 包序列号， 0表示请求发送失败
	*/
	Moomoo::u32_t GetCorporateActionsStockSplits(const Qot_GetCorporateActionsStockSplits::Request &stReq);
	/**
	* @brief 获取持股统计
	* @param [in] stReq 请求包，具体字段请参考Qot_GetShareholdersOverview.proto协议
	* @return Moomoo::u32_t 包序列号， 0表示请求发送失败
	*/
	Moomoo::u32_t GetShareholdersOverview(const Qot_GetShareholdersOverview::Request &stReq);
	/**
	* @brief 获取持股变动
	* @param [in] stReq 请求包，具体字段请参考Qot_GetShareholdersHoldingChanges.proto协议
	* @return Moomoo::u32_t 包序列号， 0表示请求发送失败
	*/
	Moomoo::u32_t GetShareholdersHoldingChanges(const Qot_GetShareholdersHoldingChanges::Request &stReq);
	/**
	* @brief 获取持股明细
	* @param [in] stReq 请求包，具体字段请参考Qot_GetShareholdersHolderDetail.proto协议
	* @return Moomoo::u32_t 包序列号， 0表示请求发送失败
	*/
	Moomoo::u32_t GetShareholdersHolderDetail(const Qot_GetShareholdersHolderDetail::Request &stReq);
	/**
	* @brief 获取机构持股
	* @param [in] stReq 请求包，具体字段请参考Qot_GetShareholdersInstitutional.proto协议
	* @return Moomoo::u32_t 包序列号， 0表示请求发送失败
	*/
	Moomoo::u32_t GetShareholdersInstitutional(const Qot_GetShareholdersInstitutional::Request &stReq);
	/**
	* @brief 获取内部人持股列表
	* @param [in] stReq 请求包，具体字段请参考Qot_GetInsiderHolderList.proto协议
	* @return Moomoo::u32_t 包序列号， 0表示请求发送失败
	*/
	Moomoo::u32_t GetInsiderHolderList(const Qot_GetInsiderHolderList::Request &stReq);
	/**
	* @brief 获取内部人交易列表
	* @param [in] stReq 请求包，具体字段请参考Qot_GetInsiderTradeList.proto协议
	* @return Moomoo::u32_t 包序列号， 0表示请求发送失败
	*/
	Moomoo::u32_t GetInsiderTradeList(const Qot_GetInsiderTradeList::Request &stReq);
	/**
	* @brief 获取公司详情
	* @param [in] stReq 请求包，具体字段请参考Qot_GetCompanyProfile.proto协议
	* @return Moomoo::u32_t 包序列号， 0表示请求发送失败
	*/
	Moomoo::u32_t GetCompanyProfile(const Qot_GetCompanyProfile::Request &stReq);
	/**
	* @brief 获取公司高管信息
	* @param [in] stReq 请求包，具体字段请参考Qot_GetCompanyExecutives.proto协议
	* @return Moomoo::u32_t 包序列号， 0表示请求发送失败
	*/
	Moomoo::u32_t GetCompanyExecutives(const Qot_GetCompanyExecutives::Request &stReq);
	/**
	* @brief 获取公司高管背景
	* @param [in] stReq 请求包，具体字段请参考Qot_GetCompanyExecutiveBackground.proto协议
	* @return Moomoo::u32_t 包序列号， 0表示请求发送失败
	*/
	Moomoo::u32_t GetCompanyExecutiveBackground(const Qot_GetCompanyExecutiveBackground::Request &stReq);
	/**
	* @brief 获取公司经营效率
	* @param [in] stReq 请求包，具体字段请参考Qot_GetCompanyOperationalEfficiency.proto协议
	* @return Moomoo::u32_t 包序列号， 0表示请求发送失败
	*/
	Moomoo::u32_t GetCompanyOperationalEfficiency(const Qot_GetCompanyOperationalEfficiency::Request &stReq);
	/**
	* @brief 获取十大买卖经纪商
	* @param [in] stReq 请求包，具体字段请参考Qot_GetTopTenBuySellBrokers.proto协议
	* @return Moomoo::u32_t 包序列号， 0表示请求发送失败
	*/
	Moomoo::u32_t GetTopTenBuySellBrokers(const Qot_GetTopTenBuySellBrokers::Request &stReq);
	/**
	* @brief 获取每日卖空
	* @param [in] stReq 请求包，具体字段请参考Qot_GetDailyShortVolume.proto协议
	* @return Moomoo::u32_t 包序列号， 0表示请求发送失败
	*/
	Moomoo::u32_t GetDailyShortVolume(const Qot_GetDailyShortVolume::Request &stReq);
	/**
	* @brief 获取空头持仓
	* @param [in] stReq 请求包，具体字段请参考Qot_GetShortInterest.proto协议
	* @return Moomoo::u32_t 包序列号， 0表示请求发送失败
	*/
	Moomoo::u32_t GetShortInterest(const Qot_GetShortInterest::Request &stReq);
	/**
	* @brief 获取期权波动率分析
	* @param [in] stReq 请求包，具体字段请参考Qot_GetOptionVolatility.proto协议
	* @return Moomoo::u32_t 包序列号， 0表示请求发送失败
	*/
	Moomoo::u32_t GetOptionVolatility(const Qot_GetOptionVolatility::Request &stReq);
	/**
	* @brief 获取期权行权概率
	* @param [in] stReq 请求包，具体字段请参考Qot_GetOptionExerciseProbability.proto协议
	* @return Moomoo::u32_t 包序列号， 0表示请求发送失败
	*/
	Moomoo::u32_t GetOptionExerciseProbability(const Qot_GetOptionExerciseProbability::Request &stReq);

	/**
	* @brief 条件选股V2
	* @param [in] stReq 请求包，具体字段请参考Qot_StockScreen.proto协议
	* @return Moomoo::u32_t 包序列号， 0表示请求发送失败
	*/
	Moomoo::u32_t StockScreen(const Qot_StockScreen::Request &stReq);

	/**
	* @brief 期权选股
	* @param [in] stReq 请求包，具体字段请参考Qot_OptionScreen.proto协议
	* @return Moomoo::u32_t 包序列号， 0表示请求发送失败
	*/
	Moomoo::u32_t OptionScreen(const Qot_OptionScreen::Request &stReq);

	/**
	* @brief 窝轮筛选V2
	* @param [in] stReq 请求包，具体字段请参考Qot_WarrantScreen.proto协议
	* @return Moomoo::u32_t 包序列号， 0表示请求发送失败
	*/
	Moomoo::u32_t WarrantScreen(const Qot_WarrantScreen::Request &stReq);

	/**
	* @brief 获取期权市场统计
	* @param [in] stReq 请求包，具体字段请参考Qot_GetOptionMarketStatistic.proto协议
	* @return Moomoo::u32_t 包序列号， 0表示请求发送失败
	*/
	Moomoo::u32_t GetOptionMarketStatistic(const Qot_GetOptionMarketStatistic::Request &stReq);
	/**
	* @brief 获取期权标的历史统计
	* @param [in] stReq 请求包，具体字段请参考Qot_GetOptionUnderlyingHisStatistic.proto协议
	* @return Moomoo::u32_t 包序列号， 0表示请求发送失败
	*/
	Moomoo::u32_t GetOptionUnderlyingHisStatistic(const Qot_GetOptionUnderlyingHisStatistic::Request &stReq);
	/**
	* @brief 获取批量标的最新数据
	* @param [in] stReq 请求包，具体字段请参考Qot_GetOptionUnderlyingOverview.proto协议
	* @return Moomoo::u32_t 包序列号， 0表示请求发送失败
	*/
	Moomoo::u32_t GetOptionUnderlyingOverview(const Qot_GetOptionUnderlyingOverview::Request &stReq);
	/**
	* @brief 获取历史波动率
	* @param [in] stReq 请求包，具体字段请参考Qot_GetOptionUnderlyingHisVolatility.proto协议
	* @return Moomoo::u32_t 包序列号， 0表示请求发送失败
	*/
	Moomoo::u32_t GetOptionUnderlyingHisVolatility(const Qot_GetOptionUnderlyingHisVolatility::Request &stReq);
	/**
	* @brief 获取标的排行
	* @param [in] stReq 请求包，具体字段请参考Qot_GetOptionUnderlyingRank.proto协议
	* @return Moomoo::u32_t 包序列号， 0表示请求发送失败
	*/
	Moomoo::u32_t GetOptionUnderlyingRank(const Qot_GetOptionUnderlyingRank::Request &stReq);
	/**
	* @brief 获取期权合约排行
	* @param [in] stReq 请求包，具体字段请参考Qot_GetOptionRank.proto协议
	* @return Moomoo::u32_t 包序列号， 0表示请求发送失败
	*/
	Moomoo::u32_t GetOptionRank(const Qot_GetOptionRank::Request &stReq);
	/**
	* @brief 获取期权异动列表
	* @param [in] stReq 请求包，具体字段请参考Qot_GetOptionEvent.proto协议
	* @return Moomoo::u32_t 包序列号， 0表示请求发送失败
	*/
	Moomoo::u32_t GetOptionEvent(const Qot_GetOptionEvent::Request &stReq);
	/**
	* @brief 获取期权异动告警设置
	* @param [in] stReq 请求包，具体字段请参考Qot_GetOptionEventAlert.proto协议
	* @return Moomoo::u32_t 包序列号， 0表示请求发送失败
	*/
	Moomoo::u32_t GetOptionEventAlert(const Qot_GetOptionEventAlert::Request &stReq);
	/**
	* @brief 修改期权异动告警条件
	* @param [in] stReq 请求包，具体字段请参考Qot_SetOptionEventAlert.proto协议
	* @return Moomoo::u32_t 包序列号， 0表示请求发送失败
	*/
	Moomoo::u32_t SetOptionEventAlert(const Qot_SetOptionEventAlert::Request &stReq);
	/**
	* @brief 获取末日期权标的列表
	* @param [in] stReq 请求包，具体字段请参考Qot_GetOptionZeroDteScreener.proto协议
	* @return Moomoo::u32_t 包序列号， 0表示请求发送失败
	*/
	Moomoo::u32_t GetOptionZeroDteScreener(const Qot_GetOptionZeroDteScreener::Request &stReq);
	/**
	* @brief 获取末日期权合约列表
	* @param [in] stReq 请求包，具体字段请参考Qot_GetOptionZeroDteContract.proto协议
	* @return Moomoo::u32_t 包序列号， 0表示请求发送失败
	*/
	Moomoo::u32_t GetOptionZeroDteContract(const Qot_GetOptionZeroDteContract::Request &stReq);
	/**
	* @brief 获取财报期权标的列表
	* @param [in] stReq 请求包，具体字段请参考Qot_GetOptionEarningsScreener.proto协议
	* @return Moomoo::u32_t 包序列号， 0表示请求发送失败
	*/
	Moomoo::u32_t GetOptionEarningsScreener(const Qot_GetOptionEarningsScreener::Request &stReq);
	/**
	* @brief 获取期权卖方策略列表
	* @param [in] stReq 请求包，具体字段请参考Qot_GetOptionSellerScreener.proto协议
	* @return Moomoo::u32_t 包序列号， 0表示请求发送失败
	*/
	Moomoo::u32_t GetOptionSellerScreener(const Qot_GetOptionSellerScreener::Request &stReq);
	/**
	* @brief 获取指标列表
	* @param [in] stReq 请求包，具体字段请参考Qot_GetIndicatorList.proto协议
	* @return Moomoo::u32_t 包序列号， 0表示请求发送失败
	*/
	Moomoo::u32_t GetIndicatorList(const Qot_GetIndicatorList::Request &stReq);
	/**
	* @brief 异步发起指标计算
	* @param [in] stReq 请求包，具体字段请参考Qot_RequestIndicatorCalc.proto协议
	* @return Moomoo::u32_t 包序列号， 0表示请求发送失败
	*/
	Moomoo::u32_t RequestIndicatorCalc(const Qot_RequestIndicatorCalc::Request &stReq);
	/**
	* @brief 搜索行情
	* @param [in] stReq 请求包，具体字段请参考Qot_GetSearchQuote.proto协议
	* @return Moomoo::u32_t 包序列号， 0表示请求发送失败
	*/
	Moomoo::u32_t GetSearchQuote(const Qot_GetSearchQuote::Request &stReq);
	/**
	* @brief 搜索资讯
	* @param [in] stReq 请求包，具体字段请参考Qot_GetSearchNews.proto协议
	* @return Moomoo::u32_t 包序列号， 0表示请求发送失败
	*/
	Moomoo::u32_t GetSearchNews(const Qot_GetSearchNews::Request &stReq);
	/**
	* @brief 获取财报日历
	* @param [in] stReq 请求包，具体字段请参考Qot_GetEarningsCalendar.proto协议
	* @return Moomoo::u32_t 包序列号， 0表示请求发送失败
	*/
	Moomoo::u32_t GetEarningsCalendar(const Qot_GetEarningsCalendar::Request &stReq);
	/**
	* @brief 获取宏观指标列表
	* @param [in] stReq 请求包，具体字段请参考Qot_GetMacroIndicatorList.proto协议
	* @return Moomoo::u32_t 包序列号， 0表示请求发送失败
	*/
	Moomoo::u32_t GetMacroIndicatorList(const Qot_GetMacroIndicatorList::Request &stReq);
	/**
	* @brief 获取宏观指标历史数据
	* @param [in] stReq 请求包，具体字段请参考Qot_GetMacroIndicatorHistory.proto协议
	* @return Moomoo::u32_t 包序列号， 0表示请求发送失败
	*/
	Moomoo::u32_t GetMacroIndicatorHistory(const Qot_GetMacroIndicatorHistory::Request &stReq);
	/**
	* @brief 获取美联储利率预测(FedWatch概率)
	* @param [in] stReq 请求包，具体字段请参考Qot_GetFedWatchTargetRate.proto协议
	* @return Moomoo::u32_t 包序列号， 0表示请求发送失败
	*/
	Moomoo::u32_t GetFedWatchTargetRate(const Qot_GetFedWatchTargetRate::Request &stReq);
	/**
	* @brief 获取CME利率点阵图
	* @param [in] stReq 请求包，具体字段请参考Qot_GetFedWatchDotPlot.proto协议
	* @return Moomoo::u32_t 包序列号， 0表示请求发送失败
	*/
	Moomoo::u32_t GetFedWatchDotPlot(const Qot_GetFedWatchDotPlot::Request &stReq);
	/**
	* @brief 获取盈利超预期排行
	* @param [in] stReq 请求包，具体字段请参考Qot_GetEarningsBeatRank.proto协议
	* @return Moomoo::u32_t 包序列号， 0表示请求发送失败
	*/
	Moomoo::u32_t GetEarningsBeatRank(const Qot_GetEarningsBeatRank::Request &stReq);
	/**
	* @brief 获取股息排行
	* @param [in] stReq 请求包，具体字段请参考Qot_GetDividendRank.proto协议
	* @return Moomoo::u32_t 包序列号， 0表示请求发送失败
	*/
	Moomoo::u32_t GetDividendRank(const Qot_GetDividendRank::Request &stReq);
	/**
	* @brief 获取派息日历
	* @param [in] stReq 请求包，具体字段请参考Qot_GetDividendCalendar.proto协议
	* @return Moomoo::u32_t 包序列号， 0表示请求发送失败
	*/
	Moomoo::u32_t GetDividendCalendar(const Qot_GetDividendCalendar::Request &stReq);
	/**
	* @brief 获取财经日历
	* @param [in] stReq 请求包，具体字段请参考Qot_GetEconomicCalendar.proto协议
	* @return Moomoo::u32_t 包序列号， 0表示请求发送失败
	*/
	Moomoo::u32_t GetEconomicCalendar(const Qot_GetEconomicCalendar::Request &stReq);
	/**
	* @brief 获取盘前榜(美股)
	* @param [in] stReq 请求包，具体字段请参考Qot_GetUSPreMarketRank.proto协议
	* @return Moomoo::u32_t 包序列号， 0表示请求发送失败
	*/
	Moomoo::u32_t GetUSPreMarketRank(const Qot_GetUSPreMarketRank::Request &stReq);
	/**
	* @brief 获取盘后榜(美股)
	* @param [in] stReq 请求包，具体字段请参考Qot_GetUSAfterHoursRank.proto协议
	* @return Moomoo::u32_t 包序列号， 0表示请求发送失败
	*/
	Moomoo::u32_t GetUSAfterHoursRank(const Qot_GetUSAfterHoursRank::Request &stReq);
	/**
	* @brief 获取夜盘榜(美股)
	* @param [in] stReq 请求包，具体字段请参考Qot_GetUSOvernightRank.proto协议
	* @return Moomoo::u32_t 包序列号， 0表示请求发送失败
	*/
	Moomoo::u32_t GetUSOvernightRank(const Qot_GetUSOvernightRank::Request &stReq);
	/**
	* @brief 获取领涨/领跌榜
	* @param [in] stReq 请求包，具体字段请参考Qot_GetTopMoversRank.proto协议
	* @return Moomoo::u32_t 包序列号， 0表示请求发送失败
	*/
	Moomoo::u32_t GetTopMoversRank(const Qot_GetTopMoversRank::Request &stReq);
	/**
	* @brief 获取热议榜
	* @param [in] stReq 请求包，具体字段请参考Qot_GetHotList.proto协议
	* @return Moomoo::u32_t 包序列号， 0表示请求发送失败
	*/
	Moomoo::u32_t GetHotList(const Qot_GetHotList::Request &stReq);
	/**
	* @brief 获取卖空异动榜(美股)
	* @param [in] stReq 请求包，具体字段请参考Qot_GetShortSellingRank.proto协议
	* @return Moomoo::u32_t 包序列号， 0表示请求发送失败
	*/
	Moomoo::u32_t GetShortSellingRank(const Qot_GetShortSellingRank::Request &stReq);
	/**
	* @brief 获取区间涨跌幅
	* @param [in] stReq 请求包，具体字段请参考Qot_GetPeriodChangeRank.proto协议
	* @return Moomoo::u32_t 包序列号， 0表示请求发送失败
	*/
	Moomoo::u32_t GetPeriodChangeRank(const Qot_GetPeriodChangeRank::Request &stReq);
	/**
	* @brief 获取破净高股息国央企(港股)
	* @param [in] stReq 请求包，具体字段请参考Qot_GetHighDividendSOERank.proto协议
	* @return Moomoo::u32_t 包序列号， 0表示请求发送失败
	*/
	Moomoo::u32_t GetHighDividendSOERank(const Qot_GetHighDividendSOERank::Request &stReq);
	/**
	* @brief 获取机构持仓列表
	* @param [in] stReq 请求包，具体字段请参考Qot_GetInstitutionList.proto协议
	* @return Moomoo::u32_t 包序列号， 0表示请求发送失败
	*/
	Moomoo::u32_t GetInstitutionList(const Qot_GetInstitutionList::Request &stReq);
	/**
	* @brief 获取机构概况
	* @param [in] stReq 请求包，具体字段请参考Qot_GetInstitutionProfile.proto协议
	* @return Moomoo::u32_t 包序列号， 0表示请求发送失败
	*/
	Moomoo::u32_t GetInstitutionProfile(const Qot_GetInstitutionProfile::Request &stReq);
	/**
	* @brief 获取机构持仓行业分布
	* @param [in] stReq 请求包，具体字段请参考Qot_GetInstitutionDistribution.proto协议
	* @return Moomoo::u32_t 包序列号， 0表示请求发送失败
	*/
	Moomoo::u32_t GetInstitutionDistribution(const Qot_GetInstitutionDistribution::Request &stReq);
	/**
	* @brief 获取机构持仓变动
	* @param [in] stReq 请求包，具体字段请参考Qot_GetInstitutionHoldingChange.proto协议
	* @return Moomoo::u32_t 包序列号， 0表示请求发送失败
	*/
	Moomoo::u32_t GetInstitutionHoldingChange(const Qot_GetInstitutionHoldingChange::Request &stReq);
	/**
	* @brief 获取机构持股列表
	* @param [in] stReq 请求包，具体字段请参考Qot_GetInstitutionHoldingList.proto协议
	* @return Moomoo::u32_t 包序列号， 0表示请求发送失败
	*/
	Moomoo::u32_t GetInstitutionHoldingList(const Qot_GetInstitutionHoldingList::Request &stReq);
	/**
	* @brief 获取ARK基金持仓
	* @param [in] stReq 请求包，具体字段请参考Qot_GetArkFundHolding.proto协议
	* @return Moomoo::u32_t 包序列号， 0表示请求发送失败
	*/
	Moomoo::u32_t GetArkFundHolding(const Qot_GetArkFundHolding::Request &stReq);
	/**
	* @brief 获取ARK个股交易动态
	* @param [in] stReq 请求包，具体字段请参考Qot_GetArkStockDynamic.proto协议
	* @return Moomoo::u32_t 包序列号， 0表示请求发送失败
	*/
	Moomoo::u32_t GetArkStockDynamic(const Qot_GetArkStockDynamic::Request &stReq);
	/**
	* @brief 获取ARK主动交易聚合
	* @param [in] stReq 请求包，具体字段请参考Qot_GetArkActiveTransaction.proto协议
	* @return Moomoo::u32_t 包序列号， 0表示请求发送失败
	*/
	Moomoo::u32_t GetArkActiveTransaction(const Qot_GetArkActiveTransaction::Request &stReq);
	/**
	* @brief 获取评级变动
	* @param [in] stReq 请求包，具体字段请参考Qot_GetRatingChange.proto协议
	* @return Moomoo::u32_t 包序列号， 0表示请求发送失败
	*/
	Moomoo::u32_t GetRatingChange(const Qot_GetRatingChange::Request &stReq);
	/**
	* @brief 获取产业链列表
	* @param [in] stReq 请求包，具体字段请参考Qot_GetIndustrialChainList.proto协议
	* @return Moomoo::u32_t 包序列号， 0表示请求发送失败
	*/
	Moomoo::u32_t GetIndustrialChainList(const Qot_GetIndustrialChainList::Request &stReq);
	/**
	* @brief 获取产业链详情
	* @param [in] stReq 请求包，具体字段请参考Qot_GetIndustrialChainDetail.proto协议
	* @return Moomoo::u32_t 包序列号， 0表示请求发送失败
	*/
	Moomoo::u32_t GetIndustrialChainDetail(const Qot_GetIndustrialChainDetail::Request &stReq);
	/**
	* @brief 获取板块关联产业链
	* @param [in] stReq 请求包，具体字段请参考Qot_GetIndustrialChainByPlate.proto协议
	* @return Moomoo::u32_t 包序列号， 0表示请求发送失败
	*/
	Moomoo::u32_t GetIndustrialChainByPlate(const Qot_GetIndustrialChainByPlate::Request &stReq);
	/**
	* @brief 获取产业板块信息
	* @param [in] stReq 请求包，具体字段请参考Qot_GetIndustrialPlateInfo.proto协议
	* @return Moomoo::u32_t 包序列号， 0表示请求发送失败
	*/
	Moomoo::u32_t GetIndustrialPlateInfo(const Qot_GetIndustrialPlateInfo::Request &stReq);
	/**
	* @brief 获取产业板块成分股
	* @param [in] stReq 请求包，具体字段请参考Qot_GetIndustrialPlateStock.proto协议
	* @return Moomoo::u32_t 包序列号， 0表示请求发送失败
	*/
	Moomoo::u32_t GetIndustrialPlateStock(const Qot_GetIndustrialPlateStock::Request &stReq);
	/**
	* @brief 获取热力图数据
	* @param [in] stReq 请求包，具体字段请参考Qot_GetHeatMapData.proto协议
	* @return Moomoo::u32_t 包序列号， 0表示请求发送失败
	*/
	Moomoo::u32_t GetHeatMapData(const Qot_GetHeatMapData::Request &stReq);
	/**
	* @brief 获取涨跌分布
	* @param [in] stReq 请求包，具体字段请参考Qot_GetRiseFallDistribution.proto协议
	* @return Moomoo::u32_t 包序列号， 0表示请求发送失败
	*/
	Moomoo::u32_t GetRiseFallDistribution(const Qot_GetRiseFallDistribution::Request &stReq);
};

/**
* @brief 交易接口
*/
class  MMAPI_Trd : public MMAPI_Conn
{
public:
	MMAPI_Trd();
	virtual ~MMAPI_Trd();

public:
	/**
	* @brief 注册回调
	* @param [in] pSpi 回调，该对象没有反注册前不可销毁
	*/
	void RegisterTrdSpi(MMSPI_Trd* pSpi);

	/**
	* @brief 反注册回调
	*/
	void UnregisterTrdSpi();

	/**
	* @brief 获取交易包标识
	* @param [out] 获取到的交易包标识
	* @return bool  是否成功，没有初始化前调用会返回失败
	*/
	bool GetPacketID(Common::PacketID &stPacketID);
	
	/**
	* @brief 获取交易帐号列表
	* @param [in] stReq 请求包，具体字段请参考Trd_GetAccList.proto协议
	* @return Moomoo::u32_t 包序列号， 0表示请求发送失败
	*/
	Moomoo::u32_t GetAccList(const Trd_GetAccList::Request &stReq);
	/**
	* @brief 解锁，针对OpenD解锁一次即可
	* @param [in] stReq 请求包，具体字段请参考Trd_UnlockTrade.proto协议
	* @return Moomoo::u32_t 包序列号， 0表示请求发送失败
	*/
	Moomoo::u32_t UnlockTrade(const Trd_UnlockTrade::Request &stReq);
	/**
	* @brief 订阅接收推送数据的交易账户
	* @param [in] stReq 请求包，具体字段请参考Trd_SubAccPush.proto协议
	* @return Moomoo::u32_t 包序列号， 0表示请求发送失败
	*/
	Moomoo::u32_t SubAccPush(const Trd_SubAccPush::Request &stReq);
	/**
	* @brief 获取账户资金
	* @param [in] stReq 请求包，具体字段请参考Trd_GetFunds.proto协议
	* @return Moomoo::u32_t 包序列号， 0表示请求发送失败
	*/
	Moomoo::u32_t GetFunds(const Trd_GetFunds::Request &stReq);
	/**
	* @brief 获取账户持仓
	* @param [in] stReq 请求包，具体字段请参考Trd_GetPositionList.proto协议
	* @return Moomoo::u32_t 包序列号， 0表示请求发送失败
	*/
	Moomoo::u32_t GetPositionList(const Trd_GetPositionList::Request &stReq);
	/**
	* @brief 获取最大交易数量
	* @param [in] stReq 请求包，具体字段请参考Trd_GetMaxTrdQtys.proto协议
	* @return Moomoo::u32_t 包序列号， 0表示请求发送失败
	*/
	Moomoo::u32_t GetMaxTrdQtys(const Trd_GetMaxTrdQtys::Request &stReq);
	/**
	* @brief 获取组合的可买卖信息
	* @param [in] stReq 请求包，具体字段请参考Trd_GetComboMaxTrdQtys.proto协议
	* @return Moomoo::u32_t 包序列号， 0表示请求发送失败
	*/
	Moomoo::u32_t GetComboMaxTrdQtys(const Trd_GetComboMaxTrdQtys::Request &stReq);
	/**
	* @brief 获取当日订单列表
	* @param [in] stReq 请求包，具体字段请参考Trd_GetOrderList.proto协议
	* @return Moomoo::u32_t 包序列号， 0表示请求发送失败
	*/
	Moomoo::u32_t GetOrderList(const Trd_GetOrderList::Request &stReq);
	/**
	* @brief 下单
	* @param [in] stReq 请求包，具体字段请参考Trd_PlaceOrder.proto协议，PacketID不需填写，发送时接口会填
	* @return Moomoo::u32_t 包序列号， 0表示请求发送失败
	*/
	Moomoo::u32_t PlaceOrder(const Trd_PlaceOrder::Request &stReq);
	/**
	* @brief 组合期权下单
	* @param [in] stReq 请求包，具体字段请参考Trd_PlaceComboOrder.proto协议，PacketID不需填写，发送时接口会填
	* @return Moomoo::u32_t 包序列号， 0表示请求发送失败
	*/
	Moomoo::u32_t PlaceComboOrder(const Trd_PlaceComboOrder::Request &stReq);
	/**
	* @brief 修改订单
	* @param [in] stReq 请求包，具体字段请参考Trd_ModifyOrder.proto协议，PacketID不需填写，发送时接口会填
	* @return Moomoo::u32_t 包序列号， 0表示请求发送失败
	*/
	Moomoo::u32_t ModifyOrder(const Trd_ModifyOrder::Request &stReq);
	/**
	* @brief 获取当日成交列表
	* @param [in] stReq 请求包，具体字段请参考Trd_GetOrderFillList.proto协议
	* @return Moomoo::u32_t 包序列号， 0表示请求发送失败
	*/
	Moomoo::u32_t GetOrderFillList(const Trd_GetOrderFillList::Request &stReq);
	/**
	* @brief 获取历史订单列表
	* @param [in] stReq 请求包，具体字段请参考Trd_GetHistoryOrderList.proto协议
	* @return Moomoo::u32_t 包序列号， 0表示请求发送失败
	*/
	Moomoo::u32_t GetHistoryOrderList(const Trd_GetHistoryOrderList::Request &stReq);
	/**
	* @brief 获取历史成交列表
	* @param [in] stReq 请求包，具体字段请参考Trd_GetHistoryOrderFillList.proto协议
	* @return Moomoo::u32_t 包序列号， 0表示请求发送失败
	*/
	Moomoo::u32_t GetHistoryOrderFillList(const Trd_GetHistoryOrderFillList::Request &stReq);
	/**
	* @brief 获取融资融券数据
	* @param [in] stReq 请求包，具体字段请参考Trd_GetMarginRatio.proto协议
	* @return Moomoo::u32_t 包序列号， 0表示请求发送失败
	*/
	Moomoo::u32_t GetMarginRatio(const Trd_GetMarginRatio::Request &stReq);
	/**
	* @brief 获取订单费用数据
	* @param [in] stReq 请求包，Trd_GetOrderFee.proto协议
	* @return Moomoo::u32_t 包序列号， 0表示请求发送失败
	*/
	Moomoo::u32_t GetOrderFee(const Trd_GetOrderFee::Request& stReq);
	/**
	* @brief 获取现价流水数据
    * @param [in] stReq 请求包，Trd_FlowSummary.proto协议
	* @return Moomoo::u32_t 包序列号， 0表示请求发送失败
	*/
	Moomoo::u32_t GetFlowSummary(const Trd_FlowSummary::Request& stReq);
};

/**
* @brief 全局工具接口
*/
class MMAPI
{
public:
	static MMAPI_Qot* CreateQotApi();
	static void ReleaseQotApi(MMAPI_Qot* pQot);

	static MMAPI_Trd* CreateTrdApi();
	static void ReleaseTrdApi(MMAPI_Trd* pTrd);

	static void Init();
	static void UnInit();
};

}
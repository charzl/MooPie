// Copyright 2026 Moomoo
#pragma once

#include "MMAPIChannel_Define.h"

/** 交易、行情号段范围预留定义 */
#define MMAPI_ProtoID_Trd_Begin										2000 /**< 交易相关协议号段开始 */
#define MMAPI_ProtoID_Trd_End										2999 /**< 交易相关协议号段结束 */
#define MMAPI_ProtoID_Qot_Begin										3000 /**< 行情相关协议号段开始 */
#define MMAPI_ProtoID_Qot_End										3999 /**< 行情相关协议号段结束 */

// 全句协议
#define MMAPI_ProtoID_InitConnect									1001 /**< 初始化连接 */
#define MMAPI_ProtoID_GetGlobalState								1002 /**< 获取全局状态 */
#define MMAPI_ProtoID_Notify										1003 /**< 推送通知 */
#define MMAPI_ProtoID_KeepAlive										1004 /**< 心跳 */
#define MMAPI_ProtoID_GetUserInfo									1005 /**< 获取用户信息 */
#define MMAPI_ProtoID_Verification									1006 /**< 请求或输入验证码 */
#define MMAPI_ProtoID_GetDelayStatistics							1007 /**< 获取延迟统计 */
#define MMAPI_ProtoID_TestCmd										1008 /**< 测试命令 */

// 交易协议
#define MMAPI_ProtoID_Trd_GetAccList								2001 /**< 获取交易账户列表 */
#define MMAPI_ProtoID_Trd_UnlockTrade							    2005 /**< 解锁或锁定交易 */
#define MMAPI_ProtoID_Trd_SubAccPush							    2008 /**< 订阅接收推送数据的交易账户 */

#define MMAPI_ProtoID_Trd_GetFunds								    2101 /**< 获取账户资金 */
#define MMAPI_ProtoID_Trd_GetPositionList						    2102 /**< 获取账户持仓 */

#define MMAPI_ProtoID_Trd_GetMaxTrdQtys						        2111 /**< 获取最大交易数量 */
#define MMAPI_ProtoID_Trd_GetComboMaxTrdQtys				        2112 /**< 获取组合的可买卖信息 */

#define MMAPI_ProtoID_Trd_GetOrderList							    2201 /**< 获取订单列表 */
#define MMAPI_ProtoID_Trd_PlaceOrder								2202 /**< 下单 */
#define MMAPI_ProtoID_Trd_ModifyOrder							    2205 /**< 修改订单 */
#define MMAPI_ProtoID_Trd_UpdateOrder							    2208 /**< 订单状态变动通知(推送) */

#define MMAPI_ProtoID_Trd_GetOrderFillList						    2211 /**< 获取成交列表 */
#define MMAPI_ProtoID_Trd_UpdateOrderFill						    2218 /**< 成交通知(推送) */

#define MMAPI_ProtoID_Trd_GetHistoryOrderList				        2221 /**< 获取历史订单列表 */
#define MMAPI_ProtoID_Trd_GetHistoryOrderFillList			        2222 /**< 获取历史成交列表 */
#define MMAPI_ProtoID_Trd_GetMarginRatio                            2223 /**< 获取融资融券数据 */

#define MMAPI_ProtoID_Trd_GetOrderFee                               2225 /**< 获取订单费用数据 */
#define MMAPI_ProtoID_Trd_FlowSummary                               2226 /**< 获取资金流水 */
#define MMAPI_ProtoID_Trd_PlaceComboOrder                           2227 /**< 组合期权下单 */

// 行情-实时数据协议
#define MMAPI_ProtoID_Qot_Sub										3001 /**< 订阅或者反订阅 */
#define MMAPI_ProtoID_Qot_RegQotPush							    3002 /**< 注册推送 */
#define MMAPI_ProtoID_Qot_GetSubInfo							    3003 /**< 获取订阅信息 */
#define MMAPI_ProtoID_Qot_GetBasicQot							    3004 /**< 获取基本行情 */
#define MMAPI_ProtoID_Qot_UpdateBasicQot						    3005 /**< 推送基本行情 */
#define MMAPI_ProtoID_Qot_GetKL									    3006 /**< 获取K线 */
#define MMAPI_ProtoID_Qot_UpdateKL								    3007 /**< 推送K线 */
#define MMAPI_ProtoID_Qot_GetRT									    3008 /**< 获取分时 */
#define MMAPI_ProtoID_Qot_UpdateRT								    3009 /**< 推送分时 */
#define MMAPI_ProtoID_Qot_GetTicker								    3010 /**< 获取逐笔 */
#define MMAPI_ProtoID_Qot_UpdateTicker							    3011 /**< 推送逐笔 */
#define MMAPI_ProtoID_Qot_GetOrderBook						        3012 /**< 获取买卖盘 */
#define MMAPI_ProtoID_Qot_UpdateOrderBook					        3013 /**< 推送买卖盘 */
#define MMAPI_ProtoID_Qot_GetBroker								    3014 /**< 获取经纪队列 */
#define MMAPI_ProtoID_Qot_UpdateBroker						        3015 /**< 推送经纪队列 */
#define MMAPI_ProtoID_Qot_GetOrderDetail						    3016 /**< 获取委托明细 */
#define MMAPI_ProtoID_Qot_UpdateOrderDetail					        3017 /**< 推送委托明细 */

#define MMAPI_ProtoID_Qot_UpdatePriceReminder					    3019 /**< 到价提醒推送 */

//	行情-历史数据协议
#define MMAPI_ProtoID_Qot_GetHistoryKL							    3100 /**< 获取历史K线 */
#define MMAPI_ProtoID_Qot_GetHistoryKLPoints					    3101 /**< 获取多只股票历史单点K线 */
#define MMAPI_ProtoID_Qot_GetRehab								    3102 /**< 获取复权信息 */
#define MMAPI_ProtoID_Qot_RequestHistoryKL						    3103 /**< 拉取历史K线，不读本地历史数据DB */
#define MMAPI_ProtoID_Qot_RequestHistoryKLQuota					    3104 /**< 拉取历史K线已经用掉的额度 */
#define MMAPI_ProtoID_Qot_RequestRehab							    3105 /**< 拉取复权信息，不读本地历史数据DB */

// 行情-其他数据协议											        
#define MMAPI_ProtoID_Qot_GetTradeDate							    3200 /**< 获取市场交易日 */
#define MMAPI_ProtoID_Qot_GetSuspend							    3201 /**< 获取股票停牌信息 */
#define MMAPI_ProtoID_Qot_GetStaticInfo							    3202 /**< 获取股票静态信息 */
#define MMAPI_ProtoID_Qot_GetSecuritySnapshot					    3203 /**< 获取股票快照 */
#define MMAPI_ProtoID_Qot_GetPlateSet							    3204 /**< 获取板块集合下的板块 */
#define MMAPI_ProtoID_Qot_GetPlateSecurity						    3205 /**< 获取板块下的股票 */
#define MMAPI_ProtoID_Qot_GetReference							    3206 /**< 获取正股相关股票，包括窝轮和期货 */
#define MMAPI_ProtoID_Qot_GetOwnerPlate							    3207 /**< 获取股票所属板块 */
#define MMAPI_ProtoID_Qot_GetHoldingChangeList					    3208 /**< 获取大股东持股变化列表 */
#define MMAPI_ProtoID_Qot_GetOptionChain						    3209 /**< 获取期权链 */
#define MMAPI_ProtoID_Qot_GetWarrant							    3210 /**< 获取窝轮 */
#define MMAPI_ProtoID_Qot_GetCapitalFlow						    3211 /**< 获取资金流向 */
#define MMAPI_ProtoID_Qot_GetCapitalDistribution				    3212 /**< 获取资金分布 */
#define MMAPI_ProtoID_Qot_GetUserSecurity						    3213 /**< 获取自选股分组下的股票 */
#define MMAPI_ProtoID_Qot_ModifyUserSecurity					    3214 /**< 修改自选股分组下的股票 */
#define MMAPI_ProtoID_Qot_StockFilter							    3215 /**< 条件选股 */
#define MMAPI_ProtoID_Qot_GetCodeChange							    3216 /**< 获取股票代码变化信息*/
#define MMAPI_ProtoID_Qot_GetIpoList							    3217 /**< 获取新股IPO */
#define MMAPI_ProtoID_Qot_GetFutureInfo						        3218 /**< 获取期货合约资料 */
#define MMAPI_ProtoID_Qot_RequestTradeDate							3219 /**< 获取市场交易日，在线拉取不在本地计算 */
#define MMAPI_ProtoID_Qot_SetPriceReminder							3220 /**< 设置到价提醒 */
#define MMAPI_ProtoID_Qot_GetPriceReminder							3221 /**< 获取到价提醒 */
#define MMAPI_ProtoID_Qot_GetUserSecurityGroup						3222 /**< 获取自选股分组列表 */
#define MMAPI_ProtoID_Qot_GetMarketState						    3223 /**< 获取市场状态 */
#define MMAPI_ProtoID_Qot_GetOptionExpirationDate					3224 /**< 获取期权到期日 */
#define MMAPI_ProtoID_Qot_GetFinancialsEarningsPriceMove		    3225 /**< 获取个股财报日前后价格涨跌幅表现 */
#define MMAPI_ProtoID_Qot_GetFinancialsEarningsPriceHistory		    3226 /**< 获取个股财报日前后股价历史 */
#define MMAPI_ProtoID_Qot_GetFinancialsStatements				    3227 /**< 获取财务报表 */
#define MMAPI_ProtoID_Qot_GetFinancialsRevenueBreakdown			    3228 /**< 获取主营构成 */
#define MMAPI_ProtoID_Qot_GetResearchAnalystConsensus			    3229 /**< 获取分析师评级概述 */
#define MMAPI_ProtoID_Qot_GetResearchRatingSummary				    3230 /**< 获取评级汇总 */
#define MMAPI_ProtoID_Qot_GetResearchMorningstarReport			    3231 /**< 获取晨星研究报告 */
#define MMAPI_ProtoID_Qot_GetValuationDetail					    3232 /**< 获取估值详情 */
#define MMAPI_ProtoID_Qot_GetValuationPlateStockList			    3233 /**< 获取板块/指数成分股估值 */
#define MMAPI_ProtoID_Qot_GetCorporateActionsDividends			    3234 /**< 获取分红派息 */
#define MMAPI_ProtoID_Qot_GetCorporateActionsBuybacks			    3235 /**< 获取回购 */
#define MMAPI_ProtoID_Qot_GetCorporateActionsStockSplits		    3236 /**< 获取拆合股 */
#define MMAPI_ProtoID_Qot_GetShareholdersOverview				    3237 /**< 获取持股统计 */
#define MMAPI_ProtoID_Qot_GetShareholdersHoldingChanges			    3238 /**< 获取持股变动 */
#define MMAPI_ProtoID_Qot_GetShareholdersHolderDetail			    3239 /**< 获取持股明细 */
#define MMAPI_ProtoID_Qot_GetShareholdersInstitutional			    3240 /**< 获取机构持股 */
#define MMAPI_ProtoID_Qot_GetInsiderHolderList					    3241 /**< 获取内部人持股列表 */
#define MMAPI_ProtoID_Qot_GetInsiderTradeList					    3242 /**< 获取内部人交易列表 */
#define MMAPI_ProtoID_Qot_GetCompanyProfile						    3243 /**< 获取公司详情 */
#define MMAPI_ProtoID_Qot_GetCompanyExecutives					    3244 /**< 获取公司高管信息 */
#define MMAPI_ProtoID_Qot_GetCompanyExecutiveBackground			    3245 /**< 获取公司高管背景 */
#define MMAPI_ProtoID_Qot_GetCompanyOperationalEfficiency		    3246 /**< 获取公司经营效率 */
#define MMAPI_ProtoID_Qot_GetTopTenBuySellBrokers				    3247 /**< 获取十大买卖经纪商 */
#define MMAPI_ProtoID_Qot_GetDailyShortVolume					    3248 /**< 获取每日卖空 */
#define MMAPI_ProtoID_Qot_GetShortInterest						    3249 /**< 获取空头持仓 */
#define MMAPI_ProtoID_Qot_GetOptionVolatility					    3250 /**< 获取期权波动率分析 */
#define MMAPI_ProtoID_Qot_GetOptionExerciseProbability			    3251 /**< 获取期权行权概率 */
#define MMAPI_ProtoID_Qot_StockScreen							    3252 /**< 条件选股V2 */
#define MMAPI_ProtoID_Qot_OptionScreen							    3253 /**< 期权选股 */
#define MMAPI_ProtoID_Qot_WarrantScreen							    3254 /**< 窝轮筛选V2 */
#define MMAPI_ProtoID_Qot_GetOptionQuote						    3255 /**< 获取期权行情 */
#define MMAPI_ProtoID_Qot_GetOptionStrategy						    3256 /**< 获取期权策略 */
#define MMAPI_ProtoID_Qot_GetOptionStrategyAnalysis				    3257 /**< 获取期权策略分析 */
#define MMAPI_ProtoID_Qot_GetOptionStrategySpread				    3258 /**< 获取期权策略价差 */

#define MMAPI_ProtoID_Qot_GetOptionMarketStatistic                  3301 /**< 获取期权市场统计 */
#define MMAPI_ProtoID_Qot_GetOptionUnderlyingHisStatistic           3302 /**< 获取期权标的历史统计 */
#define MMAPI_ProtoID_Qot_GetOptionUnderlyingOverview               3303 /**< 获取批量标的最新数据 */
#define MMAPI_ProtoID_Qot_GetOptionUnderlyingHisVolatility          3304 /**< 获取历史波动率 */
#define MMAPI_ProtoID_Qot_GetOptionUnderlyingRank                   3305 /**< 获取标的排行 */
#define MMAPI_ProtoID_Qot_GetOptionRank                             3306 /**< 获取期权合约排行 */
#define MMAPI_ProtoID_Qot_GetOptionEvent                            3307 /**< 获取期权异动列表 */
#define MMAPI_ProtoID_Qot_GetOptionEventAlert                       3308 /**< 获取期权异动告警设置 */
#define MMAPI_ProtoID_Qot_SetOptionEventAlert                       3309 /**< 修改期权异动告警条件 */
#define MMAPI_ProtoID_Qot_UpdateOptionEvent                         3310 /**< 期权异动推送 */
#define MMAPI_ProtoID_Qot_GetOptionZeroDteScreener                  3311 /**< 获取末日期权标的列表 */
#define MMAPI_ProtoID_Qot_GetOptionZeroDteContract                  3312 /**< 获取末日期权合约列表 */
#define MMAPI_ProtoID_Qot_GetOptionEarningsScreener                 3313 /**< 获取财报期权标的列表 */
#define MMAPI_ProtoID_Qot_GetOptionSellerScreener                   3314 /**< 获取期权卖方策略列表 */

#define MMAPI_ProtoID_Qot_GetIndicatorList                          3259 /**< 获取指标列表 */
#define MMAPI_ProtoID_Qot_RequestIndicatorCalc                      3260 /**< 异步发起指标计算 */
#define MMAPI_ProtoID_Qot_PushIndicatorCalc                         3261 /**< 指标异步计算结果推送 */
#define MMAPI_ProtoID_Qot_GetSearchQuote                            3262 /**< 搜索行情 */
#define MMAPI_ProtoID_Qot_GetSearchNews                             3263 /**< 搜索资讯 */
#define MMAPI_ProtoID_Qot_GetEarningsCalendar                          3401 /**< 获取财报日历 */
#define MMAPI_ProtoID_Qot_GetMacroIndicatorList                        3402 /**< 获取宏观指标列表 */
#define MMAPI_ProtoID_Qot_GetMacroIndicatorHistory                     3403 /**< 获取宏观指标历史数据 */
#define MMAPI_ProtoID_Qot_GetFedWatchTargetRate                        3404 /**< 获取美联储利率预测(FedWatch概率) */
#define MMAPI_ProtoID_Qot_GetFedWatchDotPlot                           3405 /**< 获取CME利率点阵图 */
#define MMAPI_ProtoID_Qot_GetEarningsBeatRank                          3406 /**< 获取盈利超预期排行 */
#define MMAPI_ProtoID_Qot_GetDividendRank                              3407 /**< 获取股息排行 */
#define MMAPI_ProtoID_Qot_GetDividendCalendar                          3408 /**< 获取派息日历 */
#define MMAPI_ProtoID_Qot_GetEconomicCalendar                          3409 /**< 获取财经日历 */
#define MMAPI_ProtoID_Qot_GetUSPreMarketRank                           3410 /**< 获取盘前榜(美股) */
#define MMAPI_ProtoID_Qot_GetUSAfterHoursRank                          3411 /**< 获取盘后榜(美股) */
#define MMAPI_ProtoID_Qot_GetUSOvernightRank                           3412 /**< 获取夜盘榜(美股) */
#define MMAPI_ProtoID_Qot_GetTopMoversRank                             3413 /**< 获取领涨/领跌榜 */
#define MMAPI_ProtoID_Qot_GetHotList                                   3414 /**< 获取热议榜 */
#define MMAPI_ProtoID_Qot_GetShortSellingRank                          3415 /**< 获取卖空异动榜(美股) */
#define MMAPI_ProtoID_Qot_GetPeriodChangeRank                          3416 /**< 获取区间涨跌幅 */
#define MMAPI_ProtoID_Qot_GetHighDividendSOERank                       3417 /**< 获取破净高股息国央企(港股) */
#define MMAPI_ProtoID_Qot_GetInstitutionList                           3418 /**< 获取机构持仓列表 */
#define MMAPI_ProtoID_Qot_GetInstitutionProfile                        3419 /**< 获取机构概况 */
#define MMAPI_ProtoID_Qot_GetInstitutionDistribution                   3420 /**< 获取机构持仓行业分布 */
#define MMAPI_ProtoID_Qot_GetInstitutionHoldingChange                  3421 /**< 获取机构持仓变动 */
#define MMAPI_ProtoID_Qot_GetInstitutionHoldingList                    3422 /**< 获取机构持股列表 */
#define MMAPI_ProtoID_Qot_GetArkFundHolding                            3423 /**< 获取ARK基金持仓 */
#define MMAPI_ProtoID_Qot_GetArkStockDynamic                           3424 /**< 获取ARK个股交易动态 */
#define MMAPI_ProtoID_Qot_GetArkActiveTransaction                      3425 /**< 获取ARK主动交易聚合 */
#define MMAPI_ProtoID_Qot_GetRatingChange                              3426 /**< 获取评级变动 */
#define MMAPI_ProtoID_Qot_GetIndustrialChainList                       3427 /**< 获取产业链列表 */
#define MMAPI_ProtoID_Qot_GetIndustrialChainDetail                     3428 /**< 获取产业链详情 */
#define MMAPI_ProtoID_Qot_GetIndustrialChainByPlate                    3429 /**< 获取板块关联产业链 */
#define MMAPI_ProtoID_Qot_GetIndustrialPlateInfo                       3430 /**< 获取产业板块信息 */
#define MMAPI_ProtoID_Qot_GetIndustrialPlateStock                      3431 /**< 获取产业板块成分股 */
#define MMAPI_ProtoID_Qot_GetHeatMapData                               3432 /**< 获取热力图数据 */
#define MMAPI_ProtoID_Qot_GetRiseFallDistribution                      3433 /**< 获取涨跌分布 */

/**
* 根据协议号判断是否是推送协议
* @param [in] u32_t nProtoID 协议号
* @return bool 是否是推送协议，true是，false否
*/
static inline bool FAPI_IsPushProto(Moomoo::u32_t nProtoID)
{
	switch (nProtoID)
	{
	case MMAPI_ProtoID_Notify:
	case MMAPI_ProtoID_Trd_UpdateOrder:
	case MMAPI_ProtoID_Trd_UpdateOrderFill:
	case MMAPI_ProtoID_Qot_UpdateBasicQot:
	case MMAPI_ProtoID_Qot_UpdateKL:
	case MMAPI_ProtoID_Qot_UpdateRT:
	case MMAPI_ProtoID_Qot_UpdateTicker:
	case MMAPI_ProtoID_Qot_UpdateOrderBook:
	case MMAPI_ProtoID_Qot_UpdateBroker:
	case MMAPI_ProtoID_Qot_UpdateOrderDetail:
	case MMAPI_ProtoID_Qot_UpdatePriceReminder:
		return true;
		break;
	}

	return false;
};
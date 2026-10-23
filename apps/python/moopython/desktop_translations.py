"""English presentation catalog. Raw inputs, rules and exported evidence stay intact."""
import re

CATALOG = '''
MooPie · 股票研究	MooPie · Stock Research
找到值得研究的下一张 Put。	Find your next Put to research.
先明确风险边界，再按收益、风险、到期时长或担保成本比较。	Set risk boundaries, then compare income, risk, time to expiry and collateral.
输入代码 / 公司名 / 别名，支持 * 和 ?；留空查看 Watchlist	Ticker / company / alias; supports * and ?. Leave blank for Watchlist.
美股 · 未来三个月期权 · 现金担保 Put	US stocks · Next three months · Cash-secured puts
筛选卖出 Put	Screen Puts
分析走势	Analyze Trend
更新行情	Update Quotes
强制刷新全部	Force Refresh All
启动 OpenD	Launch OpenD
收益优先	Highest Return
低风险优先	Lowest Risk
到期时长：短到长	Expiry: Soonest First
担保成本：低到高	Collateral: Lowest First
收益 / 风险综合	Return / Risk Balance
表头排序	Column Sort
Filter / 评分设置	Filters / Scoring
OpenD 端口	OpenD Port
候选排行榜	Candidate Rankings
现金担保 PUT	CASH-SECURED PUT
现金担保 Put	Cash-secured Put
等待查询	Ready to Search
查看 Watchlist	View Watchlist
加入 Watchlist	Add to Watchlist
管理 Watchlist	Manage Watchlist
更新股票目录	Update Symbol Directory
将输入的股票加入名单；只核验证券资料，不抓取期权行情。	Add the entered ticker after identity validation; no option quotes are fetched.
连接 OpenD 同步美股和 ETF 的代码、公司名；不抓取报价。	Sync US stock and ETF tickers and company names from OpenD; no quotes.
查看、添加、管理 Watchlist，或更新股票目录。	View, add to or manage your Watchlist, or update the symbol directory.
增量更新：复用有效缓存，只抓缺失或过期股票。盘中缓存60秒；右侧菜单可强制刷新全部。	Reuse valid cache and fetch only missing or stale data. Intraday cache: 60 seconds. Use the arrow to force a full refresh.
点击选中合约，双击查看评分与筛选依据。	Select a contract; double-click for scoring and filter evidence.
查看所选合约 →	View Selected Contract →
收益按 Bid 与全额现金担保计算，未扣费用。蓝色条表示综合分；财报未验证或事件风险以琥珀色标注。	Returns use Bid and full cash collateral, before costs. Blue bars show the composite score; amber marks earnings uncertainty or event risk.
候选列表	Candidates
合约详情 / 筛选依据	Contract Details / Filters
走势分析	Trend Analysis
价格信号	Price Signals
盘中读取 OpenD 并保存，盘后读取本地数据库。首次无数据时请登录 OpenD 并点击「更新行情」。	Read and save OpenD data during trading hours; use the database after hours. For missing data, sign in to OpenD and select Update Quotes.
取消	Cancel
导出结果	Export Results
设置	Settings
语言 / Language	Language / 语言
外观	Appearance
跟随系统	Follow System
深色	Dark
浅色	Light
（需检查）	 (needs attention)
先过滤完整合约，再排序并选取 Top 数量。	Filter the full chain, rank candidates, then select the requested Top count.
输入代码搜索单股，或留空查看默认 Watchlist。	Enter a ticker, or leave blank to view the default Watchlist.
先按 Filter 过滤，再按到期时长、担保成本、收益、风险或综合得分排序。	Filter first, then rank by expiry, collateral, return, risk or composite score.
点击表头切换排序方向；设置页调整 Filter 和评分参数。	Click column headers to sort; adjust filters and scoring in Settings.
均线 · RSI · MACD · 成交量	Moving averages · RSI · MACD · Volume
显示趋势、关键价位和改判条件。数据来自已完成日线。	Trend, key levels and conditions for reassessment, based on completed daily bars.
没有符合当前 Filter 的 Put。请查看「合约详情 / 筛选依据」，再自行决定是否调整条件。	No puts pass the current filters. Review Contract Details / Filters before changing your criteria.
没有可复用的数据，请先抓取。	No saved input is available. Fetch data first.
请先输入要加入 Watchlist 的股票代码。	Enter a ticker to add to the Watchlist.
正在分析价格信号…	Analyzing price signals…
正在抓取和分析…	Fetching and analyzing…
正在用已有数据重新过滤和排序…	Filtering and ranking saved data…
正在按交易时段读取行情并筛选合约…	Loading session data and screening contracts…
正在用已采集的数据重新过滤和排序，不重新抓取行情。	Filtering and ranking saved inputs; no new quotes are fetched.
正在判断交易时段；盘后读取 SQLite，盘中抓取并保存…	Checking the session: SQLite after hours, live fetch and save during trading…
正在刷新 OpenD 并保存数据库…	Refreshing OpenD and saving to the database…
正在核验证券基本资料并加入 Watchlist…	Validating the ticker and adding it to the Watchlist…
正在逐股检查缓存，只补抓缺失或过期股票，再合并 Top 20…	Checking each ticker cache, updating missing or stale data, then merging Top 20…
正在更新股票和 ETF 目录；不抓取期权或股票报价…	Updating stock and ETF identities; no stock or option quotes are fetched…
已停止操作；以当前保存的 Watchlist / 股票目录为准。	Stopped. The saved Watchlist / symbol directory remains authoritative.
本次分析已取消，没有生成候选。	Analysis canceled; no candidates generated.
本次分析已取消，未生成价格信号。	Analysis canceled; no price signals generated.
本次分析已取消。可以重新输入股票并开始查询。	Analysis canceled. Enter a ticker to start again.
已取消；没有生成本次分析结果。	Canceled; no new analysis results.
本次查询未完成，未生成价格信号。	The query did not finish; no price signals generated.
分析未完成。请到「合约详情 / 筛选依据」查看数据缺失或连接错误。	Analysis incomplete. See Contract Details / Filters for missing data or connection errors.
本次查询失败	Query Failed
分析未完成；没有生成候选或走势结论。	Analysis incomplete; no candidates or trend conclusion generated.
没有符合当前 Filter 的 Put	No Puts Pass the Current Filters
可打开 Filter / 评分设置，自行关闭条件或调整阈值；程序不会自动放宽。	Open Filters / Scoring to change criteria; rules are never relaxed automatically.
设置已保存；尚未重新抓取行情。	Settings saved; quotes have not been refreshed.
仅供研究；交易前需核对上述风险并刷新报价。	For research. Review these risks and refresh quotes before trading.
日均毛收益率假设完整保留权利金，不是实际每天到账的收益，股价下跌可产生亏损。	Daily gross return assumes the full premium is retained; it is not daily income. A stock decline can cause losses.
查看评分与筛选依据	View scoring and filter evidence
双击查看依据	Double-click for evidence
股票代码	Ticker
股票	Stock
到期日	Expiration
天数	Days
行权价 / 担保	Strike / Collateral
每张权利金（费用前）	Premium per Contract (Before Costs)
每张权利金	Premium
盈亏平衡价	Breakeven Price
盈亏平衡缓冲	Breakeven Buffer
盈亏平衡	Breakeven
日均毛收益率	Daily Gross Return
日均毛收益	Daily Return
简单年化	Annualized
缓冲	Buffer
财报列示日期	Listed Earnings Date
财报	Earnings
风险分（越低越好）	Risk Score (Lower Is Better)
风险分	Risk Score
收益分	Return Score
综合分	Composite Score
未知 / 缺失	Unknown / Missing
未验证	Unverified
未知	Unknown
到期前 / 同日	Before / On Expiry
当前完整排序中的名次。	Rank in the full candidate ordering.
点击对完整候选重新排序，再取所选 Top 数量；再次点击切换方向。	Rerank all candidates, then select Top N; click again to reverse.
按行权价数值排序；标准100股合约的担保成本与行权价同比例。	Sort by strike; collateral for standard 100-share contracts is proportional to strike.
点击按 Bid 数值排序；再次点击切换方向。Ask 作为参考显示。	Sort by Bid; click again to reverse. Ask is shown for reference.
按列示的财报日期排序；日期缺失时始终排在最后，未验证状态继续保留。	Sort by listed earnings date; missing dates stay last and remain unverified.
完整保留 Bid 权利金时的毛收益比较，未扣费用；不是实际到账或预期净收益。	Gross return if the full Bid premium is retained, before costs; not realized income or expected profit.
现价到费用前盈亏平衡价的距离，由规则引擎计算；不代表不会跌破。	Distance from spot to breakeven before costs; not a guarantee that the level will hold.
风险分 0–100，越低越好；不是亏损概率。	Risk score: 0–100, lower is better; not a loss probability.
券商日历列示日期；未验证不等于没有财报。	Broker-listed date; unverified does not mean no earnings event.
越高越好；使用当前收益和风险权重。	Higher is better; uses the current return and risk weights.
纽约时间	New York time
合约快照	Contract Snapshot
日期	Date
价格位置与择时信号	Price Location & Timing Signals
独立展示，暂不参与 Filter、收益分、风险分、综合分或排序。	Shown independently; excluded from filters, return, risk, composite scores and rankings.
暂无价格信号，请先查询股票或 Watchlist。	No price signals yet. Query a ticker or Watchlist first.
价格信号数据不足	Insufficient Price-Signal Data
短期动能转弱，宜等待企稳证据	Short-term momentum is weakening; wait for stabilization evidence
接近潜在阻力，宜等待更好的价格位置	Near potential resistance; wait for a better price location
价格更靠近潜在阻力，可等待回落后的承接依据	Closer to potential resistance; watch for support after a pullback
接近潜在支撑，仍需确认承接	Near potential support; buying support still needs confirmation
当前缺少明确的价格位置优势	No clear price-location advantage yet
下方潜在支撑	Potential Support Below
上方潜在阻力	Potential Resistance Above
暂无已确认区间	No confirmed zone
等待后续日线确认	Awaiting later daily bars
价格区域	Price Zone
距区域边缘	Distance to Zone Edge
历史转折证据	Historical Pivot Evidence
当前历史范围内没有足够的转折依据，不推测具体价位。	No sufficient pivot evidence in this history window; no level inferred.
日线已通过验证；分析窗口内未找到位于参考价下方的转折低点且已得到后续日线确认的区域，因此暂无可确认价位。	Daily history is valid, but no pivot low below the reference price has been confirmed by later bars in this window; no support zone is reported.
日线已通过验证；分析窗口内未找到位于参考价上方的转折高点且已得到后续日线确认的区域，因此暂无可确认价位。	Daily history is valid, but no pivot high above the reference price has been confirmed by later bars in this window; no resistance zone is reported.
单次转折，依据有限	Single pivot; limited evidence
多次转折	Repeated pivots
下一步观察	What to Watch Next
盘口承接 / 买卖盘比例：未验证。	Order-flow support / buy-sell ratio: unverified.
这些价位是历史转折推断，不是正在等待成交的买单或卖单。	These zones are inferred from historical pivots, not current resting buy or sell orders.
潜在支撑 / 阻力来自历史日线转折，不代表当前挂单、真实持仓成本或买卖盘比例。	Potential support / resistance comes from daily pivots, not current orders, actual cost bases or buy-sell ratios.
未验证盘口承接、逐笔方向、成交量按价分布和做市商 Gamma 仓位。	Order-book absorption, trade direction, volume by price and dealer Gamma positions are unverified.
属于日线价格位置参考，不是涨跌概率、估值结论或期权期望收益；支撑可能失效。	Daily price-location context, not directional probabilities, valuation or expected option returns. Support can fail.
条件判断未经回测，不代表胜率。	Conditions are not backtested and do not represent win rates.
观察回落后是否在支撑区企稳；若放量突破阻力，应重新评估价位。	Watch for stabilization near support after a pullback; reassess after a high-volume resistance breakout.
比较支撑与阻力距离，并观察回落是否企稳；这些距离不是期权盈亏比。	Compare distances to support and resistance and watch for stabilization; these distances are not option payoff ratios.
观察支撑能否守住、价格与动能是否改善；跌破后重新评估。	Watch whether support holds and price and momentum improve; reassess after a breakdown.
观察是否止跌、回收失地或形成反弹；触及支撑本身不是开仓依据。	Watch for stabilization, recovery or a rebound; touching support alone is not an entry signal.
等待价格接近有依据的区域，并观察实际价格反应。	Wait for price to approach an evidenced zone and observe its reaction.
标的 last_price（不替换为盘后价）	Underlying last_price (not replaced with after-hours price)
已完成日线收盘	Completed Daily Close
快照更新时间（纽约）	Snapshot Updated (New York)
日线日期	Daily Bar Date
报价未提供时间	Quote time unavailable
分析最近	Analyzing the last
根日线	 daily bars
信号版本	Signal Version
选择股票后点「删除选中」，再点「确认保存」生效；取消则保留原名单。	Select tickers, choose Remove Selected, then Confirm & Save. Cancel keeps the original list.
删除选中	Remove Selected
确认保存	Confirm & Save
Watchlist 股票名单	Watchlist Tickers
公司名暂未收录	Company name unavailable
待删除	Pending Removal
。点击「确认保存」后生效。	. Changes take effect only after Confirm & Save.
保存失败，尚未确认删除	Save failed; removal not confirmed
股票代码及公司名称候选	Ticker and Company Suggestions
别名	Alias
尚未建立股票目录，请点击「更新股票目录」。	No symbol directory yet. Choose Update Symbol Directory.
没有匹配项。可尝试名称前缀或 *关键词*；仍可输入完整股票代码。	No match. Try a name prefix or *keyword*, or enter the full ticker.
目录查询失败	Directory search failed
已选择	Selected
请先从输入框下方选择具体股票，再查询或加入 Watchlist。	Select a specific stock from the suggestions before searching or adding it.
请输入完整股票代码，或从下方候选中选择股票。	Enter a full ticker or select a stock from the suggestions.
Filter 是不可越过的风险边界；Sort 比较边界内的收益。初始数值仅作研究示例，请按自己的承受范围调整。趋势和财报默认作为风险提示，可勾选升级为硬限制。	Filters set hard risk boundaries; sorting compares eligible candidates. Defaults are research examples. Trend and earnings are warnings unless enabled as hard filters.
关闭全部可选 Filter	Disable Optional Filters
恢复默认 Filter	Restore Default Filters
基础校验始终执行：计算所需数据有效、合约身份一致、未过期、标准100股合约、未停牌。	Always checked: valid required data, consistent contract identity, unexpired standard 100-share contracts and no suspension.
合约 Filter	Contract Filters
趋势 Filter（由“标的通过全部趋势检查”开关控制）	Trend Filters (controlled by the underlying-trend filter)
Filter 过滤	Filters
收益 / 风险评分	Return / Risk Scoring
恢复示例评分参数	Restore Example Scoring
风险维度权重（至少一项大于0）	Risk Weights (At Least One Must Be Positive)
评分尺度和收益 / 风险取舍	Scoring Scales and Return / Risk Tradeoff
应用并重新筛选（已有数据）	Apply & Rescreen Saved Data
保存设置	Save Settings
设置无效	Invalid Settings
最小值不能大于最大值，请检查到期天数或 Delta 范围。	The minimum cannot exceed the maximum. Check DTE and Delta ranges.
至少一项风险维度的权重需要大于0。	At least one risk weight must be positive.
标准美股合约（每张 100 股）	Standard US Contract (100 Shares)
未停牌	Not Suspended
报价属于当前交易日	Quote Belongs to the Reference Trading Day
剩余到期天数（自然日）	Days to Expiry (Calendar Days)
价外幅度	Out-of-the-Money Distance
Bid（每股美元）	Bid (USD / Share)
Ask（每股美元）	Ask (USD / Share)
买方报价数量	Bid Size
未平仓量	Open Interest
当日成交量	Daily Volume
买卖价差 / 中间价	Bid–Ask Spread / Midpoint
已知下次财报日且日历抓取完整	Known Next Earnings Date and Complete Calendar
到期早于财报的天数	Days from Expiry to Earnings
标的通过全部趋势检查	Underlying Passes All Trend Checks
收盘相对 MA50 的幅度	Close vs MA50
MA50 五日斜率	MA50 Five-Day Slope
收盘跌破此前 20 日低点	Close Below Prior 20-Day Low
MACD 柱较前日变化	MACD Histogram Change
现金担保（美元）	Cash Collateral (USD)
现金担保权利金简单年化	Simple Annualized Collateral Return
日均权利金毛收益率	Daily Gross Premium Return
权利金 / 担保本金	Premium / Collateral
Delta 敏感度	Delta Sensitivity
下跌情景亏损	Downside Scenario Loss
股票趋势	Stock Trend
流动性	Liquidity
财报事件	Earnings Event
Delta 达到满风险分的参考值	Delta Reference for Maximum Risk Score
到期股价下跌情景（%）	Expiry Stock-Decline Scenario (%)
情景亏损占本金达到满分的参考值（%）	Scenario Loss / Collateral Reference for Maximum Risk (%)
价差达到满风险分的参考值（%）	Spread Reference for Maximum Risk (%)
未平仓量参考目标	Open Interest Reference Target
买盘数量参考目标	Bid Size Reference Target
到期与财报的间隔参考天数	Expiry-to-Earnings Reference Gap (Days)
缺失趋势 / 财报的风险惩罚分	Missing Trend / Earnings Risk Penalty
收益分达到100分的日均毛收益率（%）	Daily Gross Return for a 100 Return Score (%)
综合分中收益的权重（0–1，其余为风险权重）	Return Weight in Composite (0–1; Remainder Is Risk)
关键价位	Key Levels
什么会改变判断	Reassessment Conditions
此前 20 日低点	Prior 20-Day Low
此前 60 日低点	Prior 60-Day Low
方向分歧，暂未形成一致趋势	Mixed Signals; No Consistent Trend Yet
下行压力仍在，暂不支持止跌判断	Downward Pressure Persists; Stabilization Unconfirmed
趋势相对偏强，但不是上涨保证	Relatively Strong Trend; Further Gains Are Not Guaranteed
未来 5–20 个交易日的条件判断	Conditional Outlook for the Next 5–20 Trading Days
站上 MA50、均线止跌且 MACD 动能改善时，趋势才有转强依据；跌破前低则下行压力增加。	A move above MA50, stabilizing averages and improving MACD would support recovery; a break of prior lows adds downside pressure.
基于已完成日线，不覆盖盘中变化、新闻与估值，也不提供经过校准的涨跌概率。	Based on completed daily bars; excludes intraday changes, news and valuation, and provides no calibrated directional probabilities.
尚未跌破此前 20 日低点	The prior 20-day low has not been broken
已跌破此前 20 日低点	The prior 20-day low has been broken
成交量为此前 20 日均量的	Volume vs the prior 20-day average:
日线截至	Daily Bars Through
采集时间	Collected At
数据采集	Data Collected
原始采集时间	Original Collection Time
离线重新排序不会刷新行情。	Offline reranking does not refresh quotes.
已保存数据	Saved Data
混合来源	Mixed Sources
数据库保存的原始快照；不是当前可成交报价。	Original database snapshot; not a currently executable quote.
Watchlist 合并研究；各股票保留自己的采集时间，不代表同时报价。	Combined Watchlist research; each ticker retains its own collection time, not simultaneous quotes.
合约详情	Contract Details
参考 Bid / Ask	Reference Bid / Ask
行权价	Strike
现金担保要求	Cash Collateral Required
日均毛收益率（完整保留权利金）	Daily Gross Return (Full Premium Retained)
最大亏损（股价归零）	Maximum Loss (Stock Falls to Zero)
所选合约的评分依据	Selected Contract Scoring Evidence
风险维度	Risk Component
贡献分	Contribution
权重	Weight
分数	Score
选择理由与取舍	Reasons and Tradeoffs
需复核	Review Required
信息缺失	Missing Data
分析完成	Analysis Complete
分析未完成	Analysis Incomplete
部分结果	Partial Results
查询失败	Query Failed
股票目录更新失败，保留原目录	Symbol directory update failed; previous data retained
未加入 Watchlist	Not Added to Watchlist
无法打开 Watchlist	Cannot Open Watchlist
没有匹配项	No Matches
现金预算	Cash Budget
未提供	Not Provided
筛选依据与排除原因	Filter Evidence and Exclusions
筛选条件	Filter Criteria
标的趋势	Underlying Trend
合约条件	Contract Criteria
通过后的排序	Ranking After Filtering
已关闭的 Filter	Disabled Filters
这些条件不参与排除，相关风险仍需复核。	These conditions do not exclude candidates; associated risks still require review.
趋势 Filter 已关闭（以下仅作参考）	Trend Filter Disabled (Evidence for Reference)
已选趋势 Filter 通过	Selected Trend Filters Passed
已选趋势 Filter 未通过	Selected Trend Filters Failed
日线数据无法验证	Daily History Could Not Be Validated
趋势条件	Trend Condition
实际值	Actual Value
结果	Result
未通过	Failed
通过	Passed
未启用	Disabled
合约条件逐项检查	Contract Filter Checks
未通过 / 已评估	Failed / Evaluated
放宽预览（尚未应用）	Relaxation Preview (Not Applied)
下面只展示模拟数量，不会替你修改 Filter。基础数据无效的合约不会被放回。	Counts are simulated; filters are not changed. Contracts with invalid required data remain excluded.
如果关闭这一项	If This Filter Is Disabled
预计候选数	Estimated Candidates
组合模拟	Combined Preview
关闭整个趋势 Filter	Disable All Trend Filters
同时关闭两项财报 Filter	Disable Both Earnings Filters
同时关闭趋势与财报 Filter	Disable Trend and Earnings Filters
基础数据问题	Required Data Issues
原因	Reason
合约数	Contracts
没有生成候选或走势结论。	No candidates or trend conclusion generated.
以下为待验证的研究参数，不代表亏损概率。	Research parameters awaiting validation; not loss probabilities.
股票研究	Stock Research
导出研究结果	Export Research Results
导出完成	Export Complete
要求	Required
排序	Sort
从高到低	 (Descending)
从低到高	 (Ascending)
已选	Selected
日线收盘	Daily close
日线	Daily Bars
收盘	Close
MACD 柱	MACD histogram
较前日变化	change vs previous day
交易日	Trading Day
纽约	New York
只股票	stocks
个合约	 contracts
个候选	 candidates
个通过 Filter	 passed Filters
显示	Showing
检查	Checked
复用	Reused
抓取	Fetched
到期	Expiry
日期缺失	Date Missing
盘后 / 休市	After Hours / Closed
倍	 times
条证券	 securities
个别名	 aliases
已加入 Watchlist。	Added to Watchlist.
已在 Watchlist 中，没有重复添加。	Already in Watchlist; no duplicate added.
Watchlist 已保存	Watchlist Saved
点击「搜索 Watchlist」查看最新结果。	Choose View Watchlist for updated results.
从菜单选择「查看 Watchlist」查看最新结果。	Choose View Watchlist from the menu for updated results.
尚未提供单张现金预算，未判断担保资金是否适合个人账户	No per-contract cash budget supplied; account suitability has not been assessed
合约跨越或临近已知财报日	Contract crosses or is near known earnings
标的未通过默认趋势检查	Underlying failed the baseline trend checks
历史日线无法验证	Daily history could not be validated
仅按采集时点研究比较；交易前需复核风险并刷新报价	Research comparison at collection time; review risks and refresh quotes before trading
缺少可验证日线，使用未知风险惩罚分。	No validated daily history; applying the missing-data risk penalty.
下次财报或日历完整性未知，使用未知风险惩罚分。	Next earnings or calendar completeness unknown; applying the missing-data risk penalty.
衡量敏感度，不是指派概率。	Measures sensitivity, not assignment probability.
风险分是相对研究指标，不是亏损概率；部分维度相关，不代表独立风险。	Risk scores are research heuristics, not loss probabilities; components may be correlated.
评分为未校准的研究模型。	Scoring uses an uncalibrated research model.
未回测校准。	Not calibrated by backtesting.
未知状态仍会显示。	Unknown status remains visible.
不含费用。	Excludes costs.
费用前	Before Costs
未扣费用	Before Costs
每张	Per Contract
期权	Options
权利金	Premium
担保本金	Collateral
担保成本	Collateral
规则	Rules
排名	Rank
合约	Contract
阈值	Threshold
条件	Condition
成交量	Volume
最低	Minimum
最高	Maximum
已启用	Enabled
未启用	Disabled
天	 days
次	 times
只	 tickers
项	 items
个	 items
'''

CATALOG += """
偏弱，仍有继续下跌的压力	Weak; Further Downside Pressure Remains
趋势偏强，关注回调后的承接	Strong Trend; Watch Support on Pullbacks
若跌破前低、失守 MA50，且均线和 MACD 同时转弱，当前偏强判断需要下调。	Reassess the bullish outlook if prior lows and MA50 break while averages and MACD weaken.
（跌破后关注收复）	 (watch for recovery after a breakdown)
个通过当前 Filter。	pass the current filters.
MA20 / MA50 / MA200 为	MA20 / MA50 / MA200:
走势	Trend
导出失败	Export Failed
成本上下限、最低日均毛收益率、最高风险分和到期截止日可组合启用；先过滤完整数据，再取Top数量。< / > 为严格不等式，到期截止日不含当天。收益门槛以百分数输入，例如0.05表示0.05%/天。财报未知时，启用的财报条件无法通过；关闭后仍保留风险提示。	Combine cost bounds, minimum daily return, maximum risk and expiry cutoff. Filter the full input before selecting Top N. Comparisons are strict; the cutoff date is excluded. Return thresholds use percentage points: 0.05 means 0.05% per day. Unknown earnings fail enabled earnings filters and remain flagged when filters are disabled.
风险分0–100，越高越危险；收益分和综合分越高越好。以下为待验证的研究参数，不代表亏损概率。权重自动归一化，缺失信息有单独惩罚。修改评分不更改 Filter 设置；启用最高风险分限制时，评分变化会影响是否通过。	Risk: 0–100, higher is riskier. Higher return and composite scores are better. These unvalidated research parameters are not probabilities. Weights are normalized and missing data is penalized. Scoring does not change filter settings, but can affect eligibility when the maximum-risk filter is enabled.
按一张标准合约全额现金担保计算；未校验个人资金预算。收益不含费用、不保证成交，规则尚未经回测。	Assumes one standard contract with full cash collateral. Personal budgets are not checked. Returns exclude costs, quotes are not fill guarantees, and rules are not backtested.
点「Filter / 评分设置」调整条件；点击候选表头排序。导出 JSON 可查看原始数据、配置及每个合约的实际值、阈值和未通过项。	Use Filters / Scoring to change criteria and column headers to sort. Export JSON for raw inputs, settings, values, thresholds and failed checks.
缺少有效双边报价，或 Bid/Ask 倒挂	Missing valid two-sided quotes, or crossed Bid/Ask
日线不可用	Daily history unavailable
数据不足	Insufficient Data
权利金 / 本金 · 简单年化	Premium / Collateral · Simple Annualized
买卖价差 / 未平仓量	Bid–Ask Spread / Open Interest
关闭某一项仍可能为0，因为同一合约可能同时违反多项。可参考结果中的放宽预览，再自行决定。	Disabling one condition may still leave no candidates because contracts can fail several checks. Review the relaxation preview before making changes.
离线重算不会刷新原始快照。	Offline analysis does not refresh the original snapshot.
要求：是	Required: Yes
要求：否	Required: No
标准美股合约（每张 100 股）：是	Standard US Contract (100 Shares): Yes
未停牌：是	Not Suspended: Yes
报价属于当前交易日：是	Quote Belongs to the Reference Trading Day: Yes
收盘跌破此前 20 日低点：否	Close Below Prior 20-Day Low: No
收盘跌破此前 20 日低点：是	Close Below Prior 20-Day Low: Yes
排除	Excluded
本次数据	Current Input
符合已启用 Filter	pass the enabled filters
有数据支持的风险权重覆盖率	Risk weight with available evidence
未知项按设置计惩罚分。	Missing components use the configured penalty.
不随 Filter 开关变化。	Independent of filter switches.
默认趋势参考	Baseline Trend Checks
项未通过	failed checks
满分参考	maximum-score reference
价差分	Spread score
未平仓量不足分	Open interest shortfall score
买盘数量不足分	Bid size shortfall score
报价数量不保证成交。	Quoted size does not guarantee execution.
到期股价下跌	Expiry stock decline
时，费用前损益	, P/L before costs
亏损占担保本金	loss / collateral
财报在到期后	Earnings days after expiry
财报在	Earnings:
跨财报为100分，间隔达到	Crossing earnings scores 100; a gap of at least
天为0分。	days scores 0.
通过当前全部风险边界，在	Passes all enabled risk boundaries; among
个候选中排序第	candidates, rank
担保现金	cash collateral
较现价低	below spot by
买卖价差为中间价的	Bid–Ask spread / midpoint
越高越危险	higher is riskier
以下统计针对	Counts cover
个基础数据有效的合约；同一合约可同时违反多个条件，不能将各项数量相加。	contracts with valid required data. A contract can fail multiple checks; counts cannot be summed.
最大权利金收益	Maximum premium gain
股票归零时最大亏损	maximum loss if the stock falls to zero
未来 5–20 个交易日的条件判断	Conditional Outlook for the Next 5–20 Trading Days
上行结构较完整，关注回撤是否守住	Constructive Uptrend; Watch Whether Pullbacks Hold
下行压力较大，优先等待企稳	Downside Pressure; Watch for Stabilization
只	 tickers
"""

CATALOG += '''
模拟盘	Paper Trading
相同股票池、相同单股投入，比较三个策略与买入持有基线。前向模拟与历史回测分别记录。	Compare three strategies and a buy-and-hold baseline using the same universe and per-stock budget. Forward runs and backtests are recorded separately.
每5分钟更新（程序运行期间）	Update every 5 minutes while the app is open
读取账本	Read Ledger
更新模拟盘	Update Paper Accounts
实验名称（可留空）	Experiment name (optional)
虚拟客户	Virtual Clients
单股投入 $	Per Stock $
以 Watchlist 创建前向模拟	Start Forward Run from Watchlist
历史开始日期	Historical Start
历史回测（独立实验）	Backtest (Separate Run)
创建时冻结当前 Watchlist；复制客户不增加独立样本。	The Watchlist is frozen at creation. Duplicate clients are not independent samples.
尚未创建模拟实验。	No paper experiment yet.
客户 / 策略	Client / Strategy
净收益率	Net Return
最大回撤	Max Drawdown
净损益 $	Net P&L $
持仓比例	Exposure
成交数	Fills
换手率	Turnover
超额收益	Excess Return
1个月	1 Month
3个月	3 Months
6个月	6 Months
前向模拟	Forward Run
历史回测	Backtest
200日趋势	200-Day Trend
12–1个月动量	12–1 Month Momentum
趋势中短期反转	Pullback Reversal
等额买入持有基线	Equal-Notional Buy & Hold
等待	Pending
换手率 = 累计买卖成交额 / 平均每日净资产；收益率剔除追加资金。	Turnover = total traded notional / average daily NAV; return excludes contributions.
最新决策 / 退出条件	Latest Decision / Exit Rules
最近成交（最多20笔）	Latest Fills (up to 20)
漏过的决策日	Missed Decision Dates
正在更新模拟账本…	Updating paper ledger…
'''

CATALOG += '\n股票池：留空使用 Watchlist，或输入 AVGO,NVDA,AAPL；每只需要253个交易日历史\tUniverse: blank for Watchlist, or AVGO,NVDA,AAPL; each ticker needs 253 trading days\n'

CATALOG += '\n创建前向模拟\tStart Forward Run\n'

CATALOG += '\n新建实验\tNew Experiment\n开始\tStarted\n数据截至\tData As Of\n'

CATALOG += """
盘中抓取并保存，盘后优先读库；没有缓存的股票会自动从 OpenD 抓取。	Fetch and save during trading; use cached data after hours and automatically fetch uncached stocks from OpenD.
正在判断交易时段；盘后优先读库，缺少缓存时自动抓取…	Checking session: cache first after hours; automatically fetching missing data…
没有缓存时会自动请求 OpenD。请确认 OpenD 已登录，并检查端口、股票代码和行情权限。	Missing data is requested from OpenD automatically. Check OpenD sign-in, port, ticker and market-data permissions.
本地没有匹配快照，已自动抓取 OpenD 并保存；之后相同查询优先读库。	No matching local snapshot: fetched and saved OpenD data automatically. Repeated queries use the cache.
盘后逐项读库，缺少的股票自动抓取；成员保留各自采集时间。	Read cached members after hours and fetch missing stocks; each member keeps its own timestamp.
三个策略与股票池买入持有，并列比较 QQQ 和 SPY 大盘基线。各账户起始资金、成交时点与费用口径一致。	Compare three strategies, stock-pool buy and hold, QQQ and SPY benchmarks, using the same starting capital, execution timing and cost assumptions.
QQQ 买入持有基线	QQQ Buy & Hold
SPY 大盘买入持有基线	SPY Market Buy & Hold
相对 SPY	Excess vs SPY
"""

CATALOG += '''
分析	Analysis
OpenD 连接	OpenD Connection
研究范围	Research Scope
全部 Watchlist	Entire Watchlist
选择标的 → 比较首选候选 → 查看依据 → 模拟盘评估	Choose a ticker → Compare the first choice → Review evidence → Evaluate with paper trading
比较候选	Compare Candidates
推荐与候选	Recommendation & Candidates
当前排序 No.1 · 卖出 Put	No.1 in Current Ranking · Sell Put
查看推荐依据	Review Recommendation
暂无首选候选	No First Choice Yet
先选择标的并分析；没有符合条件的合约时，不自动放宽 Filter。	Choose a ticker and analyze. Filters are never relaxed automatically to create a candidate.
现金担保	Cash Collateral
按当前 Filter / Sort 选取	Selected using current Filters / Sort
技术面依据	Technical Evidence
已完成日线 · 趋势、支撑压力与价格位置	Completed daily bars · Trend, support, resistance and price position
默认查看已保存的收盘结果；点击「更新行情」刷新。首次查询新股票会自动抓取。	Show saved closing results by default. Select Update Quotes to refresh. New tickers are fetched on first query.
正在读取已保存的收盘结果…	Loading saved closing results…
正在读取已保存的收盘结果；首次查询新股票时自动抓取…	Loading saved closing results; fetching new tickers on first query…
读取已保存的收盘结果；点击「更新行情」才刷新已有行情。	Reading saved closing results. Select Update Quotes to refresh existing data.
读取已保存的收盘数据；点击「更新行情」才刷新已有行情。	Reading saved closing inputs. Select Update Quotes to refresh existing data.
最近完成交易日	Latest completed session
当前显示更早的结果，请点击「更新行情」获取最近收盘数据。	Showing older results. Select Update Quotes to obtain the latest closing data.
收盘结果	Closing Results
正在加入 Watchlist…	Adding to Watchlist…
已在 Watchlist 中；可在「管理 Watchlist」中移除。	Already in Watchlist; use Manage Watchlist to remove.
历史日线不足：现有	Insufficient history: available
根，完整趋势分析需要至少 205 根已完成日线。	 bars; full trend analysis requires at least 205 completed daily bars.
暂不提供完整趋势判断；Put 排名仍遵循当前 Filter。	Full trend analysis is unavailable. Put rankings still follow your filters.
日线校验未通过	Daily history validation failed
'''

CATALOG += '''
首页 · Watchlist	Home · Watchlist
Watchlist · 股价和涨跌	Watchlist · Price and Change
股票	Stock
股价	Price
涨跌	Change
Watchlist · 股票价格与基本信息	Watchlist · Prices and Company Details
个股依据 · 支撑阻力、买卖盘与趋势	Stock Evidence · Price Zones, Order Book and Trend
代码	Ticker
名称	Name
类型	Type
最新价	Last Price
较昨收	Vs Previous Close
报价时间（纽约）	Quote Time (New York)
买卖盘价位	Order Book Levels
买盘挂单量较集中的价位	Largest Visible Bid Levels
卖盘挂单量较集中的价位	Largest Visible Ask Levels
可见挂单量	Visible Size
档位	Level
买盘服务器时间	Bid Server Time
卖盘服务器时间	Ask Server Time
未提供，无法核对交易所更新时间	Unavailable; exchange update time cannot be checked
没有可见档位。	No visible levels.
盘口不可用	Order book unavailable
历史转折	Historical pivots
'''

CATALOG += '''
持仓效率 · 不考虑风险	Position Efficiency · Risk Excluded
持仓效率	Position Efficiency
指标已计算 · 平仓阈值尚未设置	Indicator calculated · No exit threshold configured
未触发设定的效率退出条件	Configured efficiency exit condition is not triggered
低于设定阈值 · 考虑买回平仓	Below the configured threshold · Consider buying to close
平仓阈值	Exit Threshold
开仓效率基准不等于退出阈值。退出阈值由后续模拟盘策略单独指定，80%仅是待测试候选。	The entry benchmark is separate from the exit threshold. Future paper strategies will configure their own threshold; 80% is a candidate to test.
手动计算 · 现金担保 Put	Manual Calculation · Cash-Secured Put
填写真实开仓信息。开仓权利金和当前回购价均为每股价格，按一张100股标准合约计算。	Enter the actual entry information. Entry premium and buyback price are per share, for one standard 100-share contract.
开仓日期	Opening Date
评估日期	Assessment Date
开仓权利金／股 $	Entry Premium / Share $
当前回购价／股 $	Buyback Price / Share $
请输入价格	Enter a price
回购价参考所选合约 Ask，报价时间	Buyback price uses the selected contract's Ask. Quote timestamp
纽约时间。请核对可成交价格。	New York time. Verify the executable price.
当前回购价请填写可成交买价；不要使用卖出时参考的 Bid。	Enter an executable buyback price, rather than the Bid used for selling.
补齐开仓日期、开仓权利金和其他输入后，自动计算。	Complete the entry date, entry premium and other inputs to calculate automatically.
请核对输入：日期使用YYYY-MM-DD，开仓早于到期、评估不早于开仓；权利金与行权价大于0，回购价不小于0。	Check inputs: use YYYY-MM-DD dates; opening precedes expiry and assessment is on or after opening. Entry premium and strike must be positive; buyback price must be nonnegative.
保留率	Efficiency Retained
效率不低于开仓基准 · 倾向继续持有	Efficiency meets or exceeds the entry benchmark · Holding favored
效率低于开仓基准 · 评估提前平仓	Efficiency is below the entry benchmark · Review early close
尚未盈利 · 不适用止盈判断	Not profitable · Profit-taking assessment does not apply
开仓当天 · 暂不提供持有或止盈倾向	Opening day · No hold or profit-taking indication yet
已到期 · 不适用剩余效率判断	Expired · Remaining-efficiency assessment does not apply
已获利	Profit Captured
已用时间	Time Elapsed
剩余	Remaining
开仓最大日均收益率	Initial Maximum Daily Return
剩余最大日均收益率	Remaining Maximum Daily Return
保留率 =（回购价 ÷ 剩余天数）÷（开仓权利金 ÷ 原始期限）×100%。	Efficiency Retained = (buyback price / remaining days) / (entry premium / initial days) × 100%.
100%为开仓效率基准；低于100%表示效率下降，高于100%表示剩余效率更高。	100% is the entry benchmark. Below 100% means lower efficiency; above 100% means higher remaining efficiency.
仅比较最大收益上限与时间，忽略风险、费用和利息，不改变当前 Put 排名，也不自动交易。	Compares maximum return and time only, excluding risk, fees and interest. Does not affect Put rankings or execute trades.
关闭	Close
'''

CATALOG += '''
三个策略与股票池买入持有，并列比较 QQQ 和 SPY 大盘基线。默认各账户本金相同，也可独立设置。	Compare three strategies, stock-universe buy-and-hold, QQQ and SPY. Accounts start with equal capital by default; individual amounts are configurable.
每个客户的起始资金	Starting Capital by Client
每个账户独立使用自己的资金；留相同本金便于比较策略。修改仅用于新实验。	Each account has its own funds. Equal starting amounts help compare strategies. Changes apply to new experiments only.
起始资金 $	Starting Capital $
默认起始资金 $	Default Starting Capital $
单独设置资金…	Customize Client Capital…
全部使用默认本金	Use Default for All
资金模式	Funding Mode
固定资金	Fixed Capital
自动追加资金	Automatic Deposits
固定资金不自动补资，现金不足时等额缩小新买单。单股投入决定策略资金利用率；QQQ / SPY 以各自本金建仓。	Fixed capital never adds funds; new buys share available cash when needed. Per-stock budgets determine strategy exposure; QQQ / SPY invest their respective starting capital.
'''

TRANSLATIONS=dict(line.split('\t',1) for line in CATALOG.strip().splitlines() if '\t' in line)
# One pass prevents translated output from being translated again. Single Chinese
# characters are translated only as whole values, never inside company names.
PHRASES=re.compile('|'.join(re.escape(k) for k in sorted(TRANSLATIONS,key=len,reverse=True) if len(k)>1))
VALUES={'是':'Yes','否':'No'}


def english(text):
    def node(value):
        stripped=value.strip()
        if stripped in VALUES: return value.replace(stripped,VALUES[stripped])
        value=re.sub(r'到期后 (\d+) 天',r'\1 days after expiry',value)
        value=PHRASES.sub(lambda m:TRANSLATIONS[m[0]],value)
        value=re.sub(r'(?<=[0-9])\s*天', ' days', value)
        value=re.sub(r'(?<=[0-9])\s*次', ' times', value)
        value=re.sub(r'(?<=[0-9])\s*个', ' items', value)
        value=re.sub(r'(?<=[0-9])\s*项', ' checks', value)
        value=re.sub(r'(?<=[0-9])\s*倍', ' times', value)
        value=re.sub(r'([：:])是(?=$|[。；])',r'\1Yes',value)
        value=re.sub(r'([：:])否(?=$|[。；])',r'\1No',value)
        return value.translate(str.maketrans({'：':':','，':',','。':'.','；':';','、':',','（':' (','）':')'}))
    # Keep HTML tags, attributes, URLs, CSS and embedded data untouched.
    return ''.join(part if re.match(r'</?[a-zA-Z]',part) else node(part)
                   for part in re.split(r'(</?[a-zA-Z][^>]*>)',str(text)))

#include "tool.h"
#include "GetSecuritySnapshotDemo.h"
#include "StockFilterDemo.h"
#include "PlaceOrderDemo.h"
#include "QuotePushDemo.h"
#include "MACDStrategy.h"

enum DemoName {
	DEMO_UNKNOWN = 0,
	DEMO_GET_SECURITY_SNAPSHOT,
	DEMO_STOCK_FILTER,
	DEMO_QUOTE_PUSH,
	DEMO_PLACE_ORDER,
	DEMO_MACD_STRATEGY
};

vector<string> demoNames{ "Unknown", "GetSecuritySnapshot", "StockFilter", "QuotePush", "PlaceOrder", "MACDStrategy" };

// 不传参数时，默认运行的demo
#define DEFAULT_DEMO_NAME DEMO_GET_SECURITY_SNAPSHOT

//范例仅供参考，不考虑协议失败，线程安全等因素，如使用到实际项目，请自行完善。
int32_t main(int32_t argc, char** argv)
{
	MMAPI::Init();

	// 解析参数中的demo名称运行指定demo，如果没有指定，运行默认demo
	string demoName = "Unknown";
	DemoName emDemo = DEMO_UNKNOWN;
	if (argc > 1) {
		// 只支持一个参数并且仅为要运行的demo名称
		demoName = argv[1];
	}

	for (size_t i = 0; i < demoNames.size(); i++) {
		if (demoNames[i] == demoName) {
			emDemo = static_cast<DemoName>(i);
		}
	}

	if (emDemo == DEMO_UNKNOWN) {
		emDemo = DEFAULT_DEMO_NAME;
	}

	switch (emDemo)
	{
	case DEMO_GET_SECURITY_SNAPSHOT:
		{
			//拉取股票快照
			GetSecuritySnapshotDemo demoGetSecuritySnapshot;
			demoGetSecuritySnapshot.Run();
		}
		break;
	case DEMO_STOCK_FILTER:
		{
			//股票筛选
			StockFilterDemo demoStockFilter;
			demoStockFilter.Run();
		}
		break;
	case DEMO_QUOTE_PUSH:
		{
			//行情推送，请在盘中运行
			QuotePushDemo demoQuote;
			demoQuote.Run();
		}
		break;
	case DEMO_PLACE_ORDER:
		{
			//下单
			PlaceOrderDemo demoStockSell;
			demoStockSell.Run();
		}
		break;
	case DEMO_MACD_STRATEGY:
		{
			//简单的MACD买卖策略
			MACDStrategy demoMACD;
			demoMACD.Run();
		}
		break;
	default:
		break;
	}

	CPSleep(1);
	
	protobuf::ShutdownProtobufLibrary();
	MMAPI::UnInit();
	return 0;
}

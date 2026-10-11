"""Read-only account access. Account IDs remain integers/strings, never floats."""
def records(sdk, result):
    ret, data = result
    if ret != sdk.RET_OK:
        raise RuntimeError(str(data))
    return data.to_dict('records')


def query_accounts(sdk, host, port, command):
    market = getattr(sdk.TrdMarket, command['market'])
    firm = getattr(sdk.SecurityFirm, command['firm'])
    context = sdk.OpenSecTradeContext(host=host, port=port, filter_trdmarket=market, security_firm=firm)
    try:
        accounts = records(sdk, context.get_acc_list())
        if command['op'] == 'accounts':
            for row in accounts: row['acc_id'] = str(row['acc_id'])
            return dict(accounts=accounts)
        selected = next((a for a in accounts if str(a['acc_id']) == command['acc_id']), None)
        if selected is None:
            raise ValueError('账户不存在或不属于所选券商和市场，请重新获取账户列表')
        currency = getattr(sdk.Currency, command['currency'])
        parameters = dict(acc_id=int(selected['acc_id']), trd_env=selected['trd_env'], refresh_cache=False, currency=currency)
        funds = records(sdk, context.accinfo_query(**parameters))
        positions = records(sdk, context.position_list_query(**parameters))
        return dict(acc_id=str(selected['acc_id']), currency=command['currency'], funds=funds, positions=positions)
    finally:
        context.close()

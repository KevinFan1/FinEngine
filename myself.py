import json

print(
    json.dumps(
        "结算单号	订单码	关联订单号	关联运单号	费用项	服务商	QIC仓	结算金额	计费参数	计费完成时间	业务节点	业务发生时间	结算时间	状态	动账账户	动账流水号	备注	是否木带宝	是否子单".split(
            "\t"
        ),
        ensure_ascii=False,
    )
)

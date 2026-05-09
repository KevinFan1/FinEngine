datas = """创建时间	交易类型描述	收入（元）	支出（元）	账户余额（元）	业务单号	备注"""

import json

print(json.dumps(datas.split("\t"), ensure_ascii=False))

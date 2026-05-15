"""Seed platforms and file specifications.

Usage:
    cd backend && python -m scripts.seed_file_specs
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.database import async_session_factory
from app.models.file_spec import FileSpec
from app.models.platform import Platform
from app.tasks.processors.alipay import ALIPAY_DONGZHANG_HEADERS
from app.tasks.processors.douyin import DOUYIN_ORDER_HEADERS, DOUYIN_SHIPPING_INSURANCE_HEADERS
from app.tasks.processors.qianniu import QIANNIU_DONGZHANG_HEADERS, QIANNIU_ORDER_HEADERS
from app.tasks.processors.weixin_video import WEIXIN_VIDEO_BIC_HEADERS, WEIXIN_VIDEO_DONGZHANG_HEADERS, WEIXIN_VIDEO_ORDER_HEADERS
from app.tasks.processors.xiaohongshu import (
    XIAOHONGSHU_DONGZHANG_HEADERS,
    XIAOHONGSHU_GMV_HEADERS,
    XIAOHONGSHU_ORDER_HEADERS,
    XIAOHONGSHU_OTHER_SERVICE_HEADERS,
)
from sqlalchemy import select

# ── Platform definitions ─────────────────────────────────────────────────────
PLATFORMS = [
    {"code": "douyin", "name": "抖音", "sort_order": 1, "parent_code": "douyin", "processor_code": "douyin", "order_scope_code": "douyin"},
    {"code": "kuaishou", "name": "快手", "sort_order": 2, "parent_code": "kuaishou", "processor_code": "kuaishou", "order_scope_code": "kuaishou"},
    {"code": "xiaohongshu", "name": "小红书", "sort_order": 3, "parent_code": "xiaohongshu", "processor_code": "xiaohongshu", "order_scope_code": "xiaohongshu"},
    {"code": "weixin_video", "name": "微信小店", "sort_order": 4, "parent_code": "weixin_video", "processor_code": "weixin_video", "order_scope_code": "weixin_video"},
    {"code": "taobao", "name": "淘宝", "sort_order": 5, "parent_code": "taobao", "processor_code": "taobao", "order_scope_code": "taobao"},
    {"code": "alipay", "name": "支付宝", "sort_order": 6, "parent_code": "taobao", "processor_code": "alipay", "order_scope_code": "taobao"},
    {"code": "qianniu", "name": "千牛", "sort_order": 7, "parent_code": "taobao", "processor_code": "qianniu", "order_scope_code": "taobao"},
    {"code": "tmall", "name": "天猫", "sort_order": 8, "parent_code": "taobao", "processor_code": "tmall", "order_scope_code": "taobao"},
    {"code": "miniprogram", "name": "小程序", "sort_order": 9, "parent_code": "miniprogram", "processor_code": "miniprogram", "order_scope_code": "miniprogram"},
]

# ── File spec definitions ────────────────────────────────────────────────────
FILE_SPECS = [
    {
        "platform_code": "douyin",
        "type_code": "订单",
        "name": "抖音订单",
        "match_threshold": 5,
        "headers": DOUYIN_ORDER_HEADERS,
    },
    {
        "platform_code": "douyin",
        "type_code": "动账",
        "name": "抖音动账",
        "match_threshold": 5,
        "headers": [
            "动账时间",
            "动帐流水号",
            "动账方向",
            "动账金额",
            "动账账户",
            "动账场景",
            "计费类型",
            "子订单号",
            "订单号",
            "售后编号",
            "下单时间",
            "商品ID",
            "商品名称",
            "达人ID",
            "达人名称",
            "订单类型",
            "订单实付应结",
            "运费实付",
            "实际平台补贴_运费",
            "实际平台补贴",
            "其他平台补贴",
            "以旧换新抵扣",
            "政府补贴平台垫资",
            "实际达人补贴",
            "实际抖音支付补贴",
            "实际抖音月付营销补贴",
            "银行补贴",
            "订单退款",
            "平台服务费",
            "佣金",
            "服务商佣金",
            "渠道分成",
            "招商服务费",
            "站外推广费",
            "其他分成",
            "是否免佣",
            "免佣金额",
            "备注",
        ],
    },
    {
        "platform_code": "douyin",
        "type_code": "bic",
        "name": "抖音BIC",
        "match_threshold": 5,
        "headers": [
            "结算单号",
            "订单码",
            "关联订单号",
            "关联运单号",
            "费用项",
            "服务商",
            "QIC仓",
            "结算金额",
            "计费参数",
            "计费完成时间",
            "业务节点",
            "业务发生时间",
            "结算时间",
            "状态",
            "动账账户",
            "动账流水号",
            "备注",
            "是否木带宝",
            "是否子单",
        ],
    },
    {
        "platform_code": "douyin",
        "type_code": "运费险",
        "name": "抖音运费险",
        "match_threshold": 5,
        "headers": DOUYIN_SHIPPING_INSURANCE_HEADERS,
    },
    {
        "platform_code": "kuaishou",
        "type_code": "gmv",
        "name": "快手GMV",
        "match_threshold": 5,
        "headers": [
            "商家ID",
            "订单号",
            "商品ID",
            "商品名称",
            "商品数量",
            "订单创建时间",
            "订单实付(元)",
            "政府补贴",
            "支付营销补贴",
            "平台补贴",
            "商家补贴(元)",
            "达人补贴",
            "达人补贴明细",
            "合计收入(元)",
            "订单退款(元)",
            "支付营销回退（元）",
            "技术服务费(元)",
            "预售增收技术服务费（元）",
            "达人ID",
            "MCN机构ID",
            "达人佣金(元)",
            "团长id",
            "团长佣金(元)",
            "佣金模式",
            "快赚客ID",
            "快赚客佣金(元)",
            "服务商ID",
            "服务商佣金(元)",
            "分账基数",
            "其他收费",
            "其他收费明细",
            "合计支出(元)",
            "实际结算金额(元)",
            "实际结算时间",
            "结算规则",
            "资金渠道",
            "账户名称",
            "结算商户号",
            "备注",
            "消费金信息",
        ],
    },
    {
        "platform_code": "kuaishou",
        "type_code": "动账",
        "name": "快手动账",
        "match_threshold": 5,
        "headers": [
            "账务流水号",
            "关联业务单号",
            "入账时间",
            "账务方向",
            "发生额（元）",
            "期末余额（元）",
            "业务类型",
            "描述",
            "备注",
        ],
    },
    {
        "platform_code": "kuaishou",
        "type_code": "运费险",
        "name": "快手运费险",
        "match_threshold": 5,
        "headers": [
            "订单编号",
            "服务费用（元）",
            "商家承担服务费用（元）",
            "平台补贴费用（元）",
            "生效时间",
            "收费编号",
        ],
    },
    {
        "platform_code": "kuaishou",
        "type_code": "订单",
        "name": "快手订单",
        "match_threshold": 5,
        "headers": [
            "订单号",
            "赠品订单号",
            "活动订单编号",
            "订单创建时间",
            "订单支付时间",
            "预售定金支付时间",
            "订单状态",
            "实付款",
            "快递费",
            "店铺优惠",
            "平台补贴",
            "主播补贴",
            "混资活动优惠",
            "支付优惠",
            "支付方式",
            "成交数量",
            "买家留言",
            "账号类型",
            "账号明细",
            "订单备注",
            "旗帜颜色",
            "售后状态",
            "活动订单",
            "预售/承诺发货时间",
            "订单载体",
            "商品名称",
            "商品ID",
            "商品规格",
            "SKU编码",
            "商品单价",
            "渠道",
            "CPS达人ID",
            "CPS达人昵称",
            "预估推广佣金",
            "预估推广者分佣比例",
            "团长ID",
            "团长昵称",
            "快赚客ID",
            "快赚客昵称",
            "授权推广者ID",
            "授权推广者昵称",
            "收货人姓名",
            "收货人电话",
            "收货地址-省",
            "收货地址-市",
            "收货地址-区",
            "收货地址-街道",
            "收货地址",
            "发货时间",
            "快递公司",
            "快递单号",
            "物流信息",
            "集运类型",
            "直邮类型",
            "仓库名称",
            "仓库地址",
            "实名姓名",
            "服务门店ID",
            "服务门店名称",
            "服务门店地址",
            "国补/类国补/消费券",
        ],
    },
    {
        "platform_code": "weixin_video",
        "type_code": "订单",
        "name": "微信小店订单",
        "match_threshold": 5,
        "headers": WEIXIN_VIDEO_ORDER_HEADERS,
    },
    {
        "platform_code": "weixin_video",
        "type_code": "动账",
        "name": "微信小店动账",
        "match_threshold": 5,
        "headers": WEIXIN_VIDEO_DONGZHANG_HEADERS,
    },
    {
        "platform_code": "weixin_video",
        "type_code": "bic",
        "name": "微信小店BIC",
        "match_threshold": 5,
        "headers": WEIXIN_VIDEO_BIC_HEADERS,
    },
    {
        "platform_code": "xiaohongshu",
        "type_code": "gmv",
        "name": "小红书GMV",
        "match_threshold": 5,
        "headers": XIAOHONGSHU_GMV_HEADERS,
    },
    {
        "platform_code": "xiaohongshu",
        "type_code": "其他服务款",
        "name": "小红书其他服务款",
        "match_threshold": 5,
        "headers": XIAOHONGSHU_OTHER_SERVICE_HEADERS,
    },
    {
        "platform_code": "xiaohongshu",
        "type_code": "动账",
        "name": "小红书动账",
        "match_threshold": 5,
        "headers": XIAOHONGSHU_DONGZHANG_HEADERS,
    },
    {
        "platform_code": "xiaohongshu",
        "type_code": "订单",
        "name": "小红书订单",
        "match_threshold": 5,
        "headers": XIAOHONGSHU_ORDER_HEADERS,
    },
    {
        "platform_code": "alipay",
        "type_code": "动账",
        "name": "支付宝动账",
        "match_threshold": 5,
        "headers": ALIPAY_DONGZHANG_HEADERS,
    },
    {
        "platform_code": "qianniu",
        "type_code": "订单",
        "name": "千牛订单",
        "match_threshold": 5,
        "headers": QIANNIU_ORDER_HEADERS,
    },
    {
        "platform_code": "qianniu",
        "type_code": "动账",
        "name": "千牛动账",
        "match_threshold": 5,
        "headers": QIANNIU_DONGZHANG_HEADERS,
    },
]


async def seed():
    async with async_session_factory() as db:
        # ── 1. Upsert platforms ──────────────────────────────────────────
        platform_id_map: dict[str, int] = {}
        for p in PLATFORMS:
            stmt = select(Platform).where(Platform.code == p["code"])
            result = await db.execute(stmt)
            platform = result.scalar_one_or_none()

            if platform is None:
                platform = Platform(
                    code=p["code"],
                    name=p["name"],
                    parent_code=p["parent_code"],
                    processor_code=p["processor_code"],
                    order_scope_code=p["order_scope_code"],
                    sort_order=p["sort_order"],
                    status=1,
                )
                db.add(platform)
                await db.flush()
                print(f"[+] Created platform: id={platform.id} code={p['code']}")
            else:
                platform.name = p["name"]
                platform.parent_code = p["parent_code"]
                platform.processor_code = p["processor_code"]
                platform.order_scope_code = p["order_scope_code"]
                platform.sort_order = p["sort_order"]
                await db.flush()
                print(f"[=] Platform exists: id={platform.id} code={p['code']}")

            platform_id_map[p["code"]] = platform.id

        # ── 2. Upsert file specs ─────────────────────────────────────────
        for fs in FILE_SPECS:
            pid = platform_id_map.get(fs["platform_code"])
            if pid is None:
                print(f"[!] Platform [{fs['platform_code']}] not found, skipping file spec [{fs['name']}]")
                continue

            stmt = select(FileSpec).where(
                FileSpec.platform_id == pid,
                FileSpec.type_code == fs["type_code"],
            )
            result = await db.execute(stmt)
            spec = result.scalar_one_or_none()

            if spec is None:
                spec = FileSpec(
                    platform_id=pid,
                    type_code=fs["type_code"],
                    name=fs["name"],
                    headers=fs["headers"],
                    match_threshold=fs["match_threshold"],
                    status=1,
                )
                db.add(spec)
                await db.flush()
                print(f"[+] Created file spec: id={spec.id} name={fs['name']} headers={len(fs['headers'])}")
            else:
                spec.headers = fs["headers"]
                spec.match_threshold = fs["match_threshold"]
                spec.name = fs["name"]
                spec.status = 1
                await db.flush()
                print(f"[=] File spec exists: id={spec.id} name={fs['name']} — updated")

        await db.commit()
        print("[OK] Seed file specs complete.")


if __name__ == "__main__":
    asyncio.run(seed())

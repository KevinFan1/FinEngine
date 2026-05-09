"""Seed category dictionaries for 备注 matching.

Usage:
    cd backend && python -m scripts.seed_category_dicts

Edit the CATEGORY_DICTS list below to add/modify dictionaries.
Each entry maps a platform_code + type_code to a dict of {category_name: [keywords]}.
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.database import async_session_factory
from app.models.category_dict import CategoryDict
from app.models.platform import Platform
from sqlalchemy import select

# ── Category dictionary definitions ──────────────────────────────────────────
# Edit this list to add your own category dictionaries.
# Each {category_name: [keywords]} means: if 备注 contains any keyword,
# the row is classified into that category.
CATEGORY_DICTS = [
    {
        "platform_code": "douyin",
        "type_code": "动账",
        "name": "抖音动账赔付分类",
        "categories": {
            "小额打款": [
                "先行赔付失败退回",
                "晚发立赔",
                "商家向消费者小额打款其他",
                "打款订单号",
                "小额打款",
                "商家向消费者小额打款补差价",
                "商家打款补偿",
                "商家",
                "因商家商品存在商家承诺后未退款问题对消费者进行赔付",
                "售后单仲裁申诉通过打款",
                "商家向消费者小额打款运费补偿",
                "支付宝转账小额打款",
                "商家向消费者小额打款商品补偿",
            ],
            "商家责任赔付": [
                "先行赔付失败退回",
                "因商家责任导致消费者申请售后扣除商家相应金额进行运费赔付订单售后单运单",
                "商家客服未及时回复售后咨询扣除商家相应金额进行运费赔付订单售后单运单",
                "晚揽立赔平台追回",
                "商家客服未及时回复售后咨询扣除商家相应金额进行运费赔付",
                "因商家存在消极服务或态度差的行为扣除商家相应金额进行运费赔订单售后单运单",
                "商责退运费",
                "因商家商品存在未按时完成消费者开票问题对消费者进行赔付",
                "因商家责任导致消费者申请售后扣除商家相应金额进行运费赔付",
                "晚发立赔售后商责延迟发货等违约金扣款",
                "快手商品赔付",
                "因商家商品存在线下协商一致退货退款仅退款问题对消费者进行赔付",
                "因商家商品存在缺货无货投诉问题对消费者进行赔付",
                "订单存在欺诈发货问题对消费者进行赔付",
            ],
            "退率严重赔付": [
                "商品品退率偏高扣除商家相应金额进行运费赔付订单售后单运单",
                "因商品品退率严重异常扣除商家相应金额进行运费赔付",
                "商品品退率偏高扣除商家相应金额进行运费赔付",
                "因商品品退率严重异常扣除商家相应金额进行运费赔付订单售后单运单",
            ],
            "月付贴息费用": ["先用后付", "抖音月付联合补贴费用返还", "支付宝余额在线充值推广费", "营销费用", "抖音月付联合贴息费用划扣", "抖音月付联合贴息费用返还"],
            "差评赔付": [
                "因商品差评率严重异常扣除商家相应金额进行运费赔付",
                "商品差评率偏高扣除商家相应金额进行运费赔付",
                "商品差评率偏高扣除商家相应金额进行运费赔付订单售后单运单",
                "因商品差评率严重异常扣除商家相应金额进行运费赔付订单售后单运单",
            ],
            "商品违规赔付": [
                "虚假宣传虚构商品信息违规管理罚单编号",
                "因商品或店铺存在违规问题扣除商家相应金额进行运费赔付",
                "因商品存在虚假宣传问题扣除商家相应金额进行运费赔付",
                "因商品存在虚假宣传问题扣除商家相应金额进行运费赔付订单售后单运单",
                "因商品或店铺存在违规问题扣除商家相应金额进行运费赔付订单售后单运单",
                "发布违禁商品信息奖惩中心罚单编号",
                "订单存在欺诈发货问题对消费者进行赔付",
            ],
            "虚假宣传赔付": ["因商品存在虚假宣传问题扣除商家相应金额进行运费赔付", "因商品存在虚假宣传问题扣除商家相应金额进行运费赔付订单售后单运单"],
            "罚款": [
                "平台补贴发票违约金扣款",
                "商家虚假交易违规违规管理罚单编号",
                "延迟发货扣违约金",
                "违约金罚单扣款",
                "在申诉举报报备等环节提供虚假凭证违规管理罚单编号",
                "假冒材质成分违规管理罚单编号",
            ],
            "赔付": [
                "发货异常用户体验赔付",
                "晚揽立赔平台追回",
                "因商家商品存在超未发货问题对消费者进行赔付",
                "因订单存在发货超时问题对消费者进行赔付",
                "因订单存在非消费者意愿私自召回包裹问题对消费者进行赔付",
                "退货包运费垫资追款",
                "商品差评率偏高扣除商家相应金额进行运费赔付订单售后单运单",
                "因商家商品存在物流轨迹异常问题对消费者进行赔付",
                "因商品存在品质问题扣除商家相应金额进行运费赔付",
                "因商家责任导致消费者申请售后扣除商家相应金额进行运费赔付",
                "因商家飞鸽承诺承担退换货运费扣除商家相应金额进行运费赔付",
                "平台赔付商家",
                "天猫保证金充值代扣",
                "退货包运费服务扣款",
                "售后已由平台处理完成消费者退款费用由平台出资赔付商家详情至售后工作台查看",
                "因商家商品存在退运费问题对消费者进行赔付",
                "快手商品赔付赔券扣款",
                "保证金淘宝扣除转移",
                "因商品存在品质问题扣除商家相应金额进行运费赔付订单售后单运单",
                "晚发立赔",
                "因商家商品存在商家承诺后未退款问题对消费者进行赔付",
                "快手商品赔付现金补偿",
                "因订单存在发货违规等问题扣除商家相应金额进行运费赔付",
                "商品差评率偏高扣除商家相应金额进行运费赔付",
                "因商家责任导致消费者申请售后扣除商家相应金额进行运费赔付订单售后单运单",
                "赔付红包",
                "保证金点淘缴存",
                "店铺或所售商品存在违规扣除商家相应金额进行运费赔付",
                "保证金淘宝出账缴存",
                "因商家飞鸽承诺承担退换货运费扣除商家相应金额进行运费赔付订单售后单运单",
                "因商品存在虚假宣传问题扣除商家相应金额进行运费赔付",
                "运费报销赔付",
                "集运扣款冻结",
                "因商家商品存在售后入口关闭退货款问题对消费者进行赔付",
                "因订单存在订单未及时发货问题对消费者进行赔付",
                "商家换货未履约体验赔付",
                "因商家商品问题对消费者进行赔付",
                "因商家商品存在商家服务问题辱骂问题对消费者进行赔付",
                "商品好评率低于扣除商家相应金额进行运费赔付",
                "因订单存在发货后小时未揽收问题对消费者进行赔付",
                "结算单号供应链快递拦截费用货物类赔付",
                "保证金淘宝额度补齐缴存",
                "先行赔付失败退回",
                "保证金淘宝缴存退款锁定",
                "集运扣款",
                "因订单存在揽收后小时无分拨记录问题对消费者进行赔付",
                "因订单存在发运超时问题对消费者进行赔付",
                "换货超期发货主动赔付",
                "因商品存在虚假宣传问题扣除商家相应金额进行运费赔付订单售后单运单",
                "撤销因订单存在订单缺货无货问题对消费者进行赔付",
                "因商家商品存在缺货无货投诉问题对消费者进行赔付",
                "因订单存在中转超时问题对消费者进行赔付",
                "揽收超时主动赔付",
                "因平台仲裁判定为商家责任扣除商家相应金额进行运费赔付订单售后单运单",
                "因商品品退率严重异常扣除商家相应金额进行运费赔付订单售后单运单",
                "因订单存在长时间未入质检仓问题对消费者进行赔付",
                "体验赔付",
                "因平台仲裁判定为商家责任扣除商家相应金额进行运费赔付",
                "因订单存在发货违规等问题扣除商家相应金额进行运费赔付订单售后单运单",
                "快手商品赔付",
                "因订单存在订单缺货无货问题对消费者进行赔付",
                "保证金点淘保证金扣除",
                "商品好评率低于扣除商家相应金额进行运费赔付订单售后单运单",
                "因订单存在揽收超时问题对消费者进行赔付",
                "撤销因订单存在发货超时问题对消费者进行赔付",
                "商品品退率偏高扣除商家相应金额进行运费赔付订单售后单运单",
                "晚发立赔售后商责延迟发货等违约金扣款",
                "非消费者原因运费报销",
                "店铺或所售商品存在违规扣除商家相应金额进行运费赔付订单售后单运单",
                "仲裁结算订单号",
                "商品品退率偏高扣除商家相应金额进行运费赔付",
                "因订单存在超过应发货时间仍未发货问题对消费者进行赔付",
                "商家向消费者小额打款运费补偿",
                "因商家商品存在物流轨迹超时问题对消费者进行赔付",
                "订单存在欺诈发货问题对消费者进行赔付",
                "赔付单扣款",
                "撤销赔付单扣款揽收超时主动赔付订单编号",
            ],
            "好评率低赔付": ["商品好评率低于扣除商家相应金额进行运费赔付订单售后单运单", "商品好评率低于扣除商家相应金额进行运费赔付"],
            "赔付2": ["商家开票发票补偿金扣款提交批次号查询路径商家开票历史处理记录提交批次号"],
            "捐赠": ["公益捐款支出中国妇女发展基金会", "公益商家佣金捐赠"],
        },
    },
    {
        "platform_code": "kuaishou",
        "type_code": "动账",
        "name": "快手动账赔付分类",
        "categories": {
            "其他费用": [
                "晚揽立赔平台追回",
                "晚发立赔售后商责延迟发货等违约金扣款",
                "退款快手电商订单编号",
                "平台赔付商家",
                "发货异常用户体验赔付",
                "分账追回超售后期平台服务费退款单号",
                "分账追回超售后期推广者三方分佣户退款单号",
                "小额打款",
                "商责退运费垫资追回",
            ],
        },
    },
]


async def seed():
    async with async_session_factory() as db:
        # Build platform code -> id map
        stmt = select(Platform)
        result = await db.execute(stmt)
        platforms = {p.code: p.id for p in result.scalars().all()}

        for cd in CATEGORY_DICTS:
            pid = platforms.get(cd["platform_code"])
            if pid is None:
                print(f"[!] Platform [{cd['platform_code']}] not found, skipping [{cd['name']}]")
                continue

            # Find existing
            existing_stmt = select(CategoryDict).where(
                CategoryDict.platform_id == pid,
                CategoryDict.type_code == cd["type_code"],
            )
            existing_result = await db.execute(existing_stmt)
            existing = existing_result.scalar_one_or_none()

            if existing is None:
                cat = CategoryDict(
                    platform_id=pid,
                    type_code=cd["type_code"],
                    name=cd["name"],
                    categories=cd["categories"],
                    status=1,
                )
                db.add(cat)
                await db.flush()
                cats_count = len(cd["categories"])
                kw_count = sum(len(v) for v in cd["categories"].values())
                print(f"[+] Created category dict: id={cat.id} name={cd['name']} categories={cats_count} keywords={kw_count}")
            else:
                existing.categories = cd["categories"]
                existing.name = cd["name"]
                await db.flush()
                print(f"[=] Category dict exists: id={existing.id} name={cd['name']} — updated")

        await db.commit()
        print("[OK] Seed category dicts complete.")


if __name__ == "__main__":
    asyncio.run(seed())

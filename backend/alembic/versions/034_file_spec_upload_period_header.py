"""add upload period header to file specs

Revision ID: 034
Revises: 033
Create Date: 2026-05-29 00:00:00.000000

"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "034"
down_revision: Union[str, None] = "033"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "fin_file_specs",
        sa.Column("upload_period_header", sa.String(length=100), nullable=True, comment="上传所属年月取数表头"),
    )
    op.execute(
        """
        UPDATE fin_file_specs AS fs
        SET upload_period_header = rules.header_name
        FROM fin_platforms AS p
        JOIN (
            VALUES
                ('douyin', '动账', '动账时间'),
                ('douyin', '运费险', '承保时间'),
                ('douyin', 'bic', '结算时间'),
                ('douyin', '订单', '订单提交时间'),
                ('xiaohongshu', '动账', '创建时间'),
                ('xiaohongshu', '运费险', '结算时间'),
                ('xiaohongshu', 'gmv', '结算时间'),
                ('xiaohongshu', '其他服务款', '结算时间'),
                ('xiaohongshu', 'bic', '结算时间'),
                ('xiaohongshu', '订单', '订单创建时间'),
                ('weixin_video', '动账', '记账时间'),
                ('weixin_video', 'bic', '结算时间'),
                ('weixin_video', '运费险', '开始时间'),
                ('weixin_video', '订单', '订单下单时间'),
                ('kuaishou', '订单', '订单创建时间'),
                ('kuaishou', 'gmv', '实际结算时间'),
                ('kuaishou', '运费险', '生效时间'),
                ('kuaishou', '动账', '入账时间'),
                ('qianniu', '动账', '数据创建时间'),
                ('qianniu', '订单', '订单创建时间'),
                ('taobao', '动账', '数据创建时间'),
                ('taobao', '订单', '订单创建时间'),
                ('alipay', '动账', '入账时间'),
                ('alipay', '订单', '创建时间')
        ) AS rules(platform_code, type_code, header_name)
            ON rules.platform_code = p.code
        WHERE fs.platform_id = p.id
          AND fs.type_code = rules.type_code
          AND fs.upload_period_header IS NULL
        """
    )


def downgrade() -> None:
    op.drop_column("fin_file_specs", "upload_period_header")

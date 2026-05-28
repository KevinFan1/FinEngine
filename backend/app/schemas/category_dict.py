from datetime import datetime

from pydantic import BaseModel, Field


class CategoryDictCreate(BaseModel):
    platform_id: int = Field(..., description="平台ID")
    type_code: str = Field(..., description="业务类型: 动账/gmv/bic/运费险/订单")
    name: str = Field(..., max_length=100, description="字典名称")
    categories: dict[str, list[str]] = Field(..., description='分类字典: {"分类名": ["关键词1", "关键词2"]}')
    status: int = Field(1, description="状态: 1=启用 0=禁用")


class CategoryDictUpdate(BaseModel):
    platform_id: int | None = Field(None, description="平台ID")
    type_code: str | None = Field(None, description="业务类型")
    name: str | None = Field(None, max_length=100, description="字典名称")
    categories: dict[str, list[str]] | None = Field(None, description="分类字典")
    status: int | None = Field(None, description="状态: 1=启用 0=禁用")


class CategoryDictOut(BaseModel):
    id: int
    platform_id: int
    type_code: str
    name: str
    categories: dict
    status: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ClassifyRequest(BaseModel):
    """单条文本分类请求"""

    text: str = Field(..., description="待分类的文本")
    platform_id: int = Field(..., description="平台ID")
    type_code: str = Field("动账", description="业务类型")


class ClassifyBatchRequest(BaseModel):
    """批量文本分类请求"""

    texts: list[str] = Field(..., description="待分类的文本列表")
    platform_id: int = Field(..., description="平台ID")
    type_code: str = Field("动账", description="业务类型")


class ClassifyResult(BaseModel):
    text: str = Field(description="原始文本")
    chinese_text: str = Field(description="提取后的中文文本")
    category: str | None = Field(None, description="匹配到的分类")
    matched_keyword: str | None = Field(None, description="命中的关键词")
    match_type: str = Field("none", description="匹配方式: exact=精确 / none=未匹配")
    match_score: float = Field(0.0, description="匹配分数，0~100")

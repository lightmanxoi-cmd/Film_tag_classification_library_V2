"""
标签数据模型模块

本模块定义了标签相关的数据模型，包括：
- Tag: SQLAlchemy ORM 模型，对应数据库中的 tags 表
- TagCreate: Pydantic 模型，用于创建标签时的数据验证
- TagUpdate: Pydantic 模型，用于更新标签时的数据验证
- TagResponse: Pydantic 模型，用于 API 响应的数据序列化
- TagTreeResponse: Pydantic 模型，用于标签树的响应
- TagMergeRequest: Pydantic 模型，用于标签合并请求

数据库表结构 (tags):
    - id: 主键，自增整数
    - name: 标签名称
    - parent_id: 父标签ID（支持层级结构）
    - description: 标签描述
    - sort_order: 排序顺序
    - created_at: 创建时间
    - updated_at: 更新时间

标签层级说明：
    本系统支持两级标签结构：
    - 一级标签：parent_id 为 NULL
    - 二级标签：parent_id 指向一级标签

使用示例：
    # 创建一级标签
    tag_data = TagCreate(name="电影类型")
    parent_tag = tag_repo.create(tag_data)
    
    # 创建二级标签
    child_data = TagCreate(name="动作", parent_id=parent_tag.id)
    child_tag = tag_repo.create(child_data)
"""
from datetime import datetime
from typing import Optional, List
from sqlalchemy import String, DateTime, Integer, ForeignKey, UniqueConstraint, func, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from video_tag_system.core.database import Base


class Tag(Base):
    """
    标签 ORM 模型
    
    对应数据库中的 tags 表，存储标签的基本信息。
    支持层级结构（父子关系），与 VideoTag 建立一对多关系。
    
    Attributes:
        id: 主键，自增整数
        name: 标签名称，最大50字符，不能为空
        parent_id: 父标签ID，NULL 表示一级标签
        description: 标签描述，最大200字符
        sort_order: 排序顺序，数值越小越靠前，默认为0
        created_at: 记录创建时间，自动设置
        updated_at: 记录更新时间，自动更新
        parent: 父标签对象（自引用关系）
        children: 子标签列表（自引用关系）
        videos: 关联的视频列表（通过 VideoTag 中间表）
    
    Constraints:
        - uq_tag_name_parent: 同一父标签下标签名称唯一
    
    Indexes:
        - idx_tags_sort_order: 排序顺序索引
        - idx_tags_name_parent: 名称和父标签组合索引
    
    Note:
        删除父标签时，子标签的 parent_id 会被设为 NULL（变为一级标签）
        删除标签时，关联的 VideoTag 记录会被级联删除
    """
    __tablename__ = "tags"
    __table_args__ = (
        UniqueConstraint("name", "parent_id", name="uq_tag_name_parent"),
        Index('idx_tags_sort_order', 'sort_order'),
        Index('idx_tags_name_parent', 'name', 'parent_id'),
    )
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    parent_id: Mapped[Optional[int]] = mapped_column(
        Integer, 
        ForeignKey("tags.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    description: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, 
        default=func.now(),
        nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, 
        default=func.now(),
        onupdate=func.now(),
        nullable=False
    )
    
    parent: Mapped[Optional["Tag"]] = relationship(
        "Tag",
        remote_side=[id],
        back_populates="children"
    )
    children: Mapped[List["Tag"]] = relationship(
        "Tag",
        back_populates="parent",
        cascade="all, delete-orphan",
        single_parent=True
    )
    videos: Mapped[List["VideoTag"]] = relationship(
        "VideoTag",
        back_populates="tag",
        cascade="all, delete-orphan"
    )
    
    @property
    def level(self) -> int:
        """
        获取标签层级
        
        根据是否有父标签判断层级：
        - 无父标签：返回 1（一级标签）
        - 有父标签：返回 2（二级标签）
        
        Returns:
            int: 标签层级（1 或 2）
        """
        if self.parent_id is None:
            return 1
        return 2
    
    def __repr__(self) -> str:
        """
        返回对象的字符串表示
        
        Returns:
            str: 格式化的对象信息
        """
        return f"<Tag(id={self.id}, name='{self.name}', parent_id={self.parent_id})>"


from pydantic import BaseModel, Field, field_validator


class TagCreate(BaseModel):
    """
    创建标签的数据模型
    
    用于验证创建标签时的请求数据。
    所有字段都有类型验证和约束检查。
    
    Attributes:
        name: 标签名称，必填，最大50字符
        parent_id: 父标签ID，可选，用于创建二级标签
        description: 标签描述，可选，最大200字符
        sort_order: 排序顺序，默认为0，必须 >= 0
    
    Example:
        # 创建一级标签
        tag_data = TagCreate(name="电影类型", description="电影分类")
        
        # 创建二级标签
        child_data = TagCreate(name="动作", parent_id=1)
    """
    name: str = Field(..., max_length=50, description="标签名称")
    parent_id: Optional[int] = Field(None, description="父标签ID")
    description: Optional[str] = Field(None, max_length=200, description="标签描述")
    sort_order: int = Field(0, ge=0, description="排序顺序")
    
    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """
        验证标签名称
        
        确保标签名称非空且去除首尾空白。
        
        Args:
            v: 待验证的标签名称
        
        Returns:
            str: 验证后的标签名称
        
        Raises:
            ValueError: 标签名称为空时抛出
        """
        if not v or not v.strip():
            raise ValueError("标签名称不能为空")
        return v.strip()


class TagUpdate(BaseModel):
    """
    更新标签的数据模型
    
    用于验证更新标签时的请求数据。
    所有字段都是可选的，只更新提供的字段。
    
    Attributes:
        name: 新的标签名称，可选
        parent_id: 新的父标签ID，可选（设为 None 可将标签提升为一级标签）
        description: 新的标签描述，可选
        sort_order: 新的排序顺序，可选
    
    Example:
        update_data = TagUpdate(name="新名称", sort_order=10)
        # 只更新名称和排序，其他字段保持不变
    """
    name: Optional[str] = Field(None, max_length=50, description="标签名称")
    parent_id: Optional[int] = Field(None, description="父标签ID")
    description: Optional[str] = Field(None, max_length=200, description="标签描述")
    sort_order: Optional[int] = Field(None, ge=0, description="排序顺序")


class TagResponse(BaseModel):
    """
    标签响应数据模型
    
    用于 API 响应的标签数据序列化。
    包含标签的所有基本信息和子标签列表。
    
    Attributes:
        id: 标签ID
        name: 标签名称
        parent_id: 父标签ID
        description: 标签描述
        sort_order: 排序顺序
        level: 标签层级（1 或 2）
        created_at: 创建时间
        updated_at: 更新时间
        children: 子标签列表（用于构建标签树）
    
    Config:
        from_attributes: 允许从 ORM 模型直接转换
    """
    id: int
    name: str
    parent_id: Optional[int] = None
    description: Optional[str] = None
    sort_order: int = 0
    level: int = 1
    created_at: datetime
    updated_at: datetime
    children: List["TagResponse"] = []
    
    class Config:
        from_attributes = True


class TagTreeResponse(BaseModel):
    """
    标签树响应模型
    
    用于返回完整的标签树结构，包含所有一级标签及其子标签。
    
    Attributes:
        items: 一级标签列表（每个一级标签包含其子标签）
        total: 标签总数
    
    Example:
        response = TagTreeResponse(
            items=[
                TagResponse(id=1, name="电影类型", children=[...]),
                TagResponse(id=2, name="地区", children=[...])
            ],
            total=20
        )
    """
    items: List[TagResponse]
    total: int


class TagMergeRequest(BaseModel):
    """
    标签合并请求模型
    
    用于将一个标签的所有关联转移到另一个标签，然后删除源标签。
    
    Attributes:
        source_tag_id: 源标签ID（将被合并并删除的标签）
        target_tag_id: 目标标签ID（合并到的标签）
    
    Note:
        - 合并后，源标签的所有视频关联会转移到目标标签
        - 源标签会被删除
        - 不能将自己合并到自己
    
    Example:
        merge_request = TagMergeRequest(
            source_tag_id=5,  # 将被删除
            target_tag_id=3   # 保留并接收关联
        )
    """
    source_tag_id: int = Field(..., description="要合并的源标签ID")
    target_tag_id: int = Field(..., description="目标标签ID")

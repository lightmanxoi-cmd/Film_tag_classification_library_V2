"""
标签数据模型
"""
from datetime import datetime
from typing import Optional, List
from sqlalchemy import String, DateTime, Integer, ForeignKey, UniqueConstraint, func, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from video_tag_system.core.database import Base


class Tag(Base):
    """标签ORM模型"""
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
        """获取标签层级"""
        if self.parent_id is None:
            return 1
        return 2
    
    def __repr__(self) -> str:
        return f"<Tag(id={self.id}, name='{self.name}', parent_id={self.parent_id})>"


from pydantic import BaseModel, Field, field_validator


class TagCreate(BaseModel):
    """创建标签的数据模型"""
    name: str = Field(..., max_length=50, description="标签名称")
    parent_id: Optional[int] = Field(None, description="父标签ID")
    description: Optional[str] = Field(None, max_length=200, description="标签描述")
    sort_order: int = Field(0, ge=0, description="排序顺序")
    
    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("标签名称不能为空")
        return v.strip()


class TagUpdate(BaseModel):
    """更新标签的数据模型"""
    name: Optional[str] = Field(None, max_length=50, description="标签名称")
    parent_id: Optional[int] = Field(None, description="父标签ID")
    description: Optional[str] = Field(None, max_length=200, description="标签描述")
    sort_order: Optional[int] = Field(None, ge=0, description="排序顺序")


class TagResponse(BaseModel):
    """标签响应数据模型"""
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
    """标签树响应"""
    items: List[TagResponse]
    total: int


class TagMergeRequest(BaseModel):
    """标签合并请求"""
    source_tag_id: int = Field(..., description="要合并的源标签ID")
    target_tag_id: int = Field(..., description="目标标签ID")

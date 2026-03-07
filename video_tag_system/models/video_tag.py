"""
视频-标签关联数据模型模块

本模块定义了视频与标签之间多对多关系的数据模型，包括：
- VideoTag: SQLAlchemy ORM 模型，对应数据库中的 video_tags 关联表
- VideoTagCreate: Pydantic 模型，用于创建关联时的数据验证
- BatchTagOperation: Pydantic 模型，用于批量标签操作

数据库表结构 (video_tags):
    - id: 主键，自增整数
    - video_id: 视频ID（外键）
    - tag_id: 标签ID（外键）
    - created_at: 创建时间

关系说明：
    - Video 与 Tag 通过 VideoTag 建立多对多关系
    - 一个视频可以有多个标签
    - 一个标签可以应用于多个视频
    - 同一视频-标签组合只能存在一次（唯一约束）

使用示例：
    # 为视频添加标签
    video_tag = VideoTagCreate(video_id=1, tag_id=5)
    result = video_tag_repo.create(video_tag)
    
    # 批量操作
    batch_op = BatchTagOperation(
        video_ids=[1, 2, 3],
        tag_ids=[5, 6]
    )
"""
from datetime import datetime
from typing import Optional, List
from sqlalchemy import DateTime, Integer, ForeignKey, UniqueConstraint, func, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from pydantic import BaseModel, Field

from video_tag_system.core.database import Base


class VideoTag(Base):
    """
    视频-标签关联 ORM 模型
    
    对应数据库中的 video_tags 表，实现视频与标签的多对多关系。
    作为中间表，存储视频和标签的关联关系。
    
    Attributes:
        id: 主键，自增整数
        video_id: 视频ID，外键关联 videos 表
        tag_id: 标签ID，外键关联 tags 表
        created_at: 关联创建时间，自动设置
        video: 关联的视频对象
        tag: 关联的标签对象
    
    Constraints:
        - uq_video_tag: 视频ID和标签ID组合唯一，防止重复关联
    
    Indexes:
        - idx_video_tags_video_tag: 视频ID和标签ID组合索引
        - idx_video_tags_tag_video: 标签ID和视频ID组合索引
        - idx_video_tags_created_at: 创建时间索引
    
    Cascade:
        - 删除视频时，自动删除相关的 VideoTag 记录
        - 删除标签时，自动删除相关的 VideoTag 记录
    """
    __tablename__ = "video_tags"
    __table_args__ = (
        UniqueConstraint("video_id", "tag_id", name="uq_video_tag"),
        Index('idx_video_tags_video_tag', 'video_id', 'tag_id'),
        Index('idx_video_tags_tag_video', 'tag_id', 'video_id'),
        Index('idx_video_tags_created_at', 'created_at'),
    )
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    video_id: Mapped[int] = mapped_column(
        Integer, 
        ForeignKey("videos.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    tag_id: Mapped[int] = mapped_column(
        Integer, 
        ForeignKey("tags.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, 
        default=func.now(),
        nullable=False
    )
    
    video: Mapped["Video"] = relationship("Video", back_populates="tags")
    tag: Mapped["Tag"] = relationship("Tag", back_populates="videos")
    
    def __repr__(self) -> str:
        """
        返回对象的字符串表示
        
        Returns:
            str: 格式化的对象信息
        """
        return f"<VideoTag(video_id={self.video_id}, tag_id={self.tag_id})>"


class VideoTagCreate(BaseModel):
    """
    创建视频-标签关联的数据模型
    
    用于验证创建关联时的请求数据。
    确保视频ID和标签ID都有效且不为空。
    
    Attributes:
        video_id: 视频ID，必填
        tag_id: 标签ID，必填
    
    Example:
        # 为视频ID为1的视频添加标签ID为5的标签
        video_tag = VideoTagCreate(video_id=1, tag_id=5)
    """
    video_id: int = Field(..., description="视频ID")
    tag_id: int = Field(..., description="标签ID")


class BatchTagOperation(BaseModel):
    """
    批量标签操作数据模型
    
    用于批量添加或删除视频标签。
    支持同时对多个视频和多个标签进行操作。
    
    操作逻辑：
    - 批量添加：为每个视频添加每个标签
    - 批量删除：从每个视频移除每个标签
    
    Attributes:
        video_ids: 视频ID列表，必填
        tag_ids: 标签ID列表，必填
    
    Example:
        # 为视频1、2、3添加标签5、6
        batch_op = BatchTagOperation(
            video_ids=[1, 2, 3],
            tag_ids=[5, 6]
        )
        # 结果：创建 3 * 2 = 6 个关联
    
    Note:
        - 如果关联已存在，添加操作会跳过（不报错）
        - 如果关联不存在，删除操作会跳过（不报错）
    """
    video_ids: List[int] = Field(..., description="视频ID列表")
    tag_ids: List[int] = Field(..., description="标签ID列表")

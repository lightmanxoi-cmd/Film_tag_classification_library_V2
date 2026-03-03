"""
视频-标签关联数据模型
"""
from datetime import datetime
from typing import Optional, List
from sqlalchemy import DateTime, Integer, ForeignKey, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from pydantic import BaseModel, Field

from video_tag_system.core.database import Base


class VideoTag(Base):
    """视频-标签关联ORM模型"""
    __tablename__ = "video_tags"
    __table_args__ = (
        UniqueConstraint("video_id", "tag_id", name="uq_video_tag"),
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
        return f"<VideoTag(video_id={self.video_id}, tag_id={self.tag_id})>"


class VideoTagCreate(BaseModel):
    """创建视频-标签关联的数据模型"""
    video_id: int = Field(..., description="视频ID")
    tag_id: int = Field(..., description="标签ID")


class BatchTagOperation(BaseModel):
    """批量标签操作"""
    video_ids: List[int] = Field(..., description="视频ID列表")
    tag_ids: List[int] = Field(..., description="标签ID列表")

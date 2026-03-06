"""
视频数据模型
"""
from datetime import datetime
from typing import Optional, List
from sqlalchemy import String, Text, DateTime, Integer, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from video_tag_system.core.database import Base


class Video(Base):
    """视频ORM模型"""
    __tablename__ = "videos"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    file_path: Mapped[str] = mapped_column(String(500), unique=True, nullable=False, index=True)
    title: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    duration: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    file_size: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    file_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    gif_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
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
    
    tags: Mapped[List["VideoTag"]] = relationship(
        "VideoTag", 
        back_populates="video",
        cascade="all, delete-orphan"
    )
    
    def __repr__(self) -> str:
        return f"<Video(id={self.id}, file_path='{self.file_path}', title='{self.title}')>"


from pydantic import BaseModel, Field, field_validator
from video_tag_system.models.tag import TagResponse


class VideoCreate(BaseModel):
    """创建视频的数据模型"""
    file_path: str = Field(..., max_length=500, description="视频文件路径")
    title: Optional[str] = Field(None, max_length=200, description="视频标题")
    description: Optional[str] = Field(None, description="视频描述")
    duration: Optional[int] = Field(None, ge=0, description="视频时长(秒)")
    file_size: Optional[int] = Field(None, ge=0, description="文件大小(字节)")
    file_hash: Optional[str] = Field(None, max_length=64, description="文件哈希值")
    
    @field_validator("file_path")
    @classmethod
    def validate_file_path(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("文件路径不能为空")
        return v.strip()


class VideoUpdate(BaseModel):
    """更新视频的数据模型"""
    title: Optional[str] = Field(None, max_length=200, description="视频标题")
    description: Optional[str] = Field(None, description="视频描述")
    duration: Optional[int] = Field(None, ge=0, description="视频时长(秒)")
    file_size: Optional[int] = Field(None, ge=0, description="文件大小(字节)")
    file_hash: Optional[str] = Field(None, max_length=64, description="文件哈希值")


class VideoResponse(BaseModel):
    """视频响应数据模型"""
    id: int
    file_path: str
    title: Optional[str] = None
    description: Optional[str] = None
    duration: Optional[int] = None
    file_size: Optional[int] = None
    file_hash: Optional[str] = None
    gif_path: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    tags: List[TagResponse] = []
    
    class Config:
        from_attributes = True


class VideoListResponse(BaseModel):
    """视频列表响应"""
    items: List[VideoResponse]
    total: int
    page: int
    page_size: int
    total_pages: int

"""
视频数据模型模块

本模块定义了视频相关的数据模型，包括：
- Video: SQLAlchemy ORM 模型，对应数据库中的 videos 表
- VideoCreate: Pydantic 模型，用于创建视频时的数据验证
- VideoUpdate: Pydantic 模型，用于更新视频时的数据验证
- VideoResponse: Pydantic 模型，用于 API 响应的数据序列化
- VideoListResponse: Pydantic 模型，用于视频列表的分页响应

数据库表结构 (videos):
    - id: 主键，自增整数
    - file_path: 视频文件路径，唯一约束
    - title: 视频标题
    - description: 视频描述
    - duration: 视频时长（秒）
    - file_size: 文件大小（字节）
    - file_hash: 文件哈希值（用于去重）
    - gif_path: GIF 预览路径
    - created_at: 创建时间
    - updated_at: 更新时间

使用示例：
    # 创建视频
    video_data = VideoCreate(file_path="/path/to/video.mp4", title="测试视频")
    video = video_repo.create(video_data)
    
    # 转换为响应格式
    response = VideoResponse.model_validate(video)
"""
from datetime import datetime
from typing import Optional, List
from sqlalchemy import String, Text, DateTime, Integer, func, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from video_tag_system.core.database import Base


class Video(Base):
    """
    视频 ORM 模型
    
    对应数据库中的 videos 表，存储视频的基本信息和元数据。
    与 VideoTag 建立一对多关系，支持标签关联。
    
    Attributes:
        id: 主键，自增整数
        file_path: 视频文件的完整路径，唯一约束，不能为空
        title: 视频标题，用于显示，可为空（为空时使用文件名）
        description: 视频描述，支持长文本
        duration: 视频时长，单位为秒
        file_size: 文件大小，单位为字节
        file_hash: 文件的 SHA256 哈希值，用于检测重复文件
        gif_path: GIF 动态预览图的存储路径
        created_at: 记录创建时间，自动设置
        updated_at: 记录更新时间，自动更新
        tags: 关联的标签列表（通过 VideoTag 中间表）
    
    Indexes:
        - idx_videos_title: 标题索引，加速标题搜索
        - idx_videos_created_at: 创建时间索引，加速按时间排序
        - idx_videos_updated_at: 更新时间索引
        - idx_videos_duration: 时长索引，支持按时长筛选
        - idx_videos_file_size: 文件大小索引
    """
    __tablename__ = "videos"
    __table_args__ = (
        Index('idx_videos_title', 'title'),
        Index('idx_videos_created_at', 'created_at'),
        Index('idx_videos_updated_at', 'updated_at'),
        Index('idx_videos_duration', 'duration'),
        Index('idx_videos_file_size', 'file_size'),
    )
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    file_path: Mapped[str] = mapped_column(String(500), unique=True, nullable=False, index=True)
    title: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    duration: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    file_size: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    file_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    gif_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    thumbnail_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    gif_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
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
        """
        返回对象的字符串表示
        
        Returns:
            str: 格式化的对象信息
        """
        return f"<Video(id={self.id}, file_path='{self.file_path}', title='{self.title}')>"


from pydantic import BaseModel, Field, field_validator
from video_tag_system.models.tag import TagResponse


class VideoCreate(BaseModel):
    """
    创建视频的数据模型
    
    用于验证创建视频时的请求数据。
    所有字段都有类型验证和约束检查。
    
    Attributes:
        file_path: 视频文件路径，必填，最大500字符
        title: 视频标题，可选，最大200字符
        description: 视频描述，可选，无长度限制
        duration: 视频时长（秒），可选，必须 >= 0
        file_size: 文件大小（字节），可选，必须 >= 0
        file_hash: 文件哈希值，可选，最大64字符
    
    Example:
        video_data = VideoCreate(
            file_path="/videos/example.mp4",
            title="示例视频",
            duration=120,
            file_size=10485760
        )
    """
    file_path: str = Field(..., max_length=500, description="视频文件路径")
    title: Optional[str] = Field(None, max_length=200, description="视频标题")
    description: Optional[str] = Field(None, description="视频描述")
    duration: Optional[int] = Field(None, ge=0, description="视频时长(秒)")
    file_size: Optional[int] = Field(None, ge=0, description="文件大小(字节)")
    file_hash: Optional[str] = Field(None, max_length=64, description="文件哈希值")
    
    @field_validator("file_path")
    @classmethod
    def validate_file_path(cls, v: str) -> str:
        """
        验证文件路径
        
        确保文件路径非空且去除首尾空白。
        
        Args:
            v: 待验证的文件路径
        
        Returns:
            str: 验证后的文件路径
        
        Raises:
            ValueError: 文件路径为空时抛出
        """
        if not v or not v.strip():
            raise ValueError("文件路径不能为空")
        return v.strip()


class VideoUpdate(BaseModel):
    """
    更新视频的数据模型
    
    用于验证更新视频时的请求数据。
    所有字段都是可选的，只更新提供的字段。
    
    Attributes:
        title: 新的视频标题，可选
        description: 新的视频描述，可选
        duration: 新的视频时长，可选
        file_size: 新的文件大小，可选
        file_hash: 新的文件哈希值，可选
    
    Example:
        update_data = VideoUpdate(title="新标题")
        # 只更新标题，其他字段保持不变
    """
    title: Optional[str] = Field(None, max_length=200, description="视频标题")
    description: Optional[str] = Field(None, description="视频描述")
    duration: Optional[int] = Field(None, ge=0, description="视频时长(秒)")
    file_size: Optional[int] = Field(None, ge=0, description="文件大小(字节)")
    file_hash: Optional[str] = Field(None, max_length=64, description="文件哈希值")


class VideoResponse(BaseModel):
    """
    视频响应数据模型
    
    用于 API 响应的视频数据序列化。
    包含视频的所有基本信息和关联的标签列表。
    
    Attributes:
        id: 视频ID
        file_path: 视频文件路径
        title: 视频标题
        description: 视频描述
        duration: 视频时长（秒）
        file_size: 文件大小（字节）
        file_hash: 文件哈希值
        gif_path: GIF 预览路径
        created_at: 创建时间
        updated_at: 更新时间
        tags: 关联的标签列表
    
    Config:
        from_attributes: 允许从 ORM 模型直接转换
    """
    id: int
    file_path: str
    title: Optional[str] = None
    description: Optional[str] = None
    duration: Optional[int] = None
    file_size: Optional[int] = None
    file_hash: Optional[str] = None
    gif_path: Optional[str] = None
    thumbnail_url: Optional[str] = None
    gif_url: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    tags: List[TagResponse] = []
    
    class Config:
        from_attributes = True


class VideoListResponse(BaseModel):
    """
    视频列表响应模型
    
    用于分页返回视频列表，包含分页信息和数据列表。
    
    Attributes:
        items: 视频数据列表
        total: 总记录数
        page: 当前页码
        page_size: 每页记录数
        total_pages: 总页数
    
    Example:
        response = VideoListResponse(
            items=[video1, video2],
            total=100,
            page=1,
            page_size=20,
            total_pages=5
        )
    """
    items: List[VideoResponse]
    total: int
    page: int
    page_size: int
    total_pages: int

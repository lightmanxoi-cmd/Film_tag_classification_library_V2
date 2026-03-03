"""
视频标签分类库管理系统
"""
from video_tag_system.exceptions import (
    VideoTagSystemError,
    VideoNotFoundError,
    TagNotFoundError,
    DuplicateVideoError,
    DuplicateTagError,
    DatabaseError,
    ValidationError,
)
from video_tag_system.core.database import DatabaseManager
from video_tag_system.services.video_service import VideoService
from video_tag_system.services.tag_service import TagService
from video_tag_system.services.video_tag_service import VideoTagService

__version__ = "1.0.0"
__all__ = [
    "VideoTagSystemError",
    "VideoNotFoundError",
    "TagNotFoundError",
    "DuplicateVideoError",
    "DuplicateTagError",
    "DatabaseError",
    "ValidationError",
    "DatabaseManager",
    "VideoService",
    "TagService",
    "VideoTagService",
]

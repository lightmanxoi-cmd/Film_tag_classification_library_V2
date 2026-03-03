"""
业务逻辑层
"""
from video_tag_system.services.video_service import VideoService
from video_tag_system.services.tag_service import TagService
from video_tag_system.services.video_tag_service import VideoTagService

__all__ = [
    "VideoService",
    "TagService",
    "VideoTagService",
]

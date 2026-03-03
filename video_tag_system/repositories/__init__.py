"""
数据访问层
"""
from video_tag_system.repositories.video_repository import VideoRepository
from video_tag_system.repositories.tag_repository import TagRepository
from video_tag_system.repositories.video_tag_repository import VideoTagRepository

__all__ = [
    "VideoRepository",
    "TagRepository",
    "VideoTagRepository",
]

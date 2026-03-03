"""
数据模型层
"""
from video_tag_system.models.video import Video, VideoCreate, VideoUpdate, VideoResponse
from video_tag_system.models.tag import Tag, TagCreate, TagUpdate, TagResponse
from video_tag_system.models.video_tag import VideoTag, VideoTagCreate

__all__ = [
    "Video",
    "VideoCreate",
    "VideoUpdate",
    "VideoResponse",
    "Tag",
    "TagCreate",
    "TagUpdate",
    "TagResponse",
    "VideoTag",
    "VideoTagCreate",
]

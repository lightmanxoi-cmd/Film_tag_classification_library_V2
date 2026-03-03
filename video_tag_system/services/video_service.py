"""
视频业务逻辑层
"""
import math
from typing import Optional, List

from sqlalchemy.orm import Session

from video_tag_system.models.video import (
    Video, VideoCreate, VideoUpdate, VideoResponse, VideoListResponse
)
from video_tag_system.models.tag import TagResponse
from video_tag_system.repositories.video_repository import VideoRepository
from video_tag_system.repositories.video_tag_repository import VideoTagRepository
from video_tag_system.exceptions import (
    VideoNotFoundError,
    DuplicateVideoError,
    ValidationError,
)


class VideoService:
    """视频业务逻辑类"""
    
    def __init__(self, session: Session):
        self.session = session
        self.video_repo = VideoRepository(session)
        self.video_tag_repo = VideoTagRepository(session)
    
    def create_video(self, video_data: VideoCreate) -> VideoResponse:
        """创建视频"""
        if self.video_repo.exists_by_file_path(video_data.file_path):
            existing = self.video_repo.get_by_file_path(video_data.file_path)
            raise DuplicateVideoError(video_data.file_path, existing.id if existing else None)
        
        video = self.video_repo.create(video_data)
        return self._to_response(video)
    
    def get_video(self, video_id: int) -> VideoResponse:
        """获取视频详情"""
        video = self.video_repo.get_by_id_with_tags(video_id)
        if not video:
            raise VideoNotFoundError(video_id=video_id)
        return self._to_response(video)
    
    def get_video_by_path(self, file_path: str) -> VideoResponse:
        """根据文件路径获取视频"""
        video = self.video_repo.get_by_file_path(file_path)
        if not video:
            raise VideoNotFoundError(file_path=file_path)
        return self._to_response(video)
    
    def update_video(self, video_id: int, video_data: VideoUpdate) -> VideoResponse:
        """更新视频"""
        video = self.video_repo.get_by_id(video_id)
        if not video:
            raise VideoNotFoundError(video_id=video_id)
        
        video = self.video_repo.update(video, video_data)
        return self._to_response(video)
    
    def delete_video(self, video_id: int) -> bool:
        """删除视频"""
        video = self.video_repo.get_by_id(video_id)
        if not video:
            raise VideoNotFoundError(video_id=video_id)
        
        self.video_repo.delete(video)
        return True
    
    def list_videos(
        self,
        page: int = 1,
        page_size: int = 20,
        search: Optional[str] = None
    ) -> VideoListResponse:
        """获取视频列表"""
        if page < 1:
            page = 1
        if page_size < 1 or page_size > 100:
            page_size = 20
        
        videos, total = self.video_repo.list_all(
            page=page,
            page_size=page_size,
            search=search
        )
        
        items = [self._to_response(v) for v in videos]
        total_pages = math.ceil(total / page_size) if total > 0 else 1
        
        return VideoListResponse(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages
        )
    
    def list_videos_by_tags(
        self,
        tag_ids: List[int],
        page: int = 1,
        page_size: int = 20,
        match_all: bool = False
    ) -> VideoListResponse:
        """根据标签筛选视频"""
        if not tag_ids:
            return VideoListResponse(
                items=[],
                total=0,
                page=page,
                page_size=page_size,
                total_pages=0
            )
        
        if page < 1:
            page = 1
        if page_size < 1 or page_size > 100:
            page_size = 20
        
        videos, total = self.video_repo.list_by_tag_ids(
            tag_ids=tag_ids,
            page=page,
            page_size=page_size,
            match_all=match_all
        )
        
        items = [self._to_response(v) for v in videos]
        total_pages = math.ceil(total / page_size) if total > 0 else 1
        
        return VideoListResponse(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages
        )
    
    def get_video_tags(self, video_id: int) -> List[TagResponse]:
        """获取视频的所有标签"""
        video = self.video_repo.get_by_id(video_id)
        if not video:
            raise VideoNotFoundError(video_id=video_id)
        
        tags = self.video_tag_repo.list_tags_by_video(video_id)
        return [TagResponse.model_validate(tag) for tag in tags]
    
    def search_videos(
        self,
        keyword: str,
        page: int = 1,
        page_size: int = 20
    ) -> VideoListResponse:
        """搜索视频"""
        return self.list_videos(
            page=page,
            page_size=page_size,
            search=keyword
        )
    
    def count_videos(self) -> int:
        """获取视频总数"""
        return self.video_repo.count_all()
    
    def check_video_exists(self, video_id: int) -> bool:
        """检查视频是否存在"""
        return self.video_repo.get_by_id(video_id) is not None
    
    def _to_response(self, video: Video) -> VideoResponse:
        """将ORM模型转换为响应模型"""
        tags = []
        if hasattr(video, 'tags') and video.tags:
            for vt in video.tags:
                if vt.tag:
                    tags.append(TagResponse.model_validate(vt.tag))
        
        return VideoResponse(
            id=video.id,
            file_path=video.file_path,
            title=video.title,
            description=video.description,
            duration=video.duration,
            file_size=video.file_size,
            file_hash=video.file_hash,
            created_at=video.created_at,
            updated_at=video.updated_at,
            tags=tags
        )

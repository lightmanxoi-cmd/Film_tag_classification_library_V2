"""
视频-标签关联业务逻辑层
"""
from typing import List, Set

from sqlalchemy.orm import Session

from video_tag_system.models.video_tag import VideoTagCreate, BatchTagOperation
from video_tag_system.models.tag import TagResponse
from video_tag_system.repositories.video_repository import VideoRepository
from video_tag_system.repositories.tag_repository import TagRepository
from video_tag_system.repositories.video_tag_repository import VideoTagRepository
from video_tag_system.exceptions import (
    VideoNotFoundError,
    TagNotFoundError,
    ValidationError,
)


class VideoTagService:
    """视频-标签关联业务逻辑类"""
    
    def __init__(self, session: Session):
        self.session = session
        self.video_repo = VideoRepository(session)
        self.tag_repo = TagRepository(session)
        self.video_tag_repo = VideoTagRepository(session)
    
    def add_tag_to_video(self, video_id: int, tag_id: int) -> dict:
        """为视频添加标签"""
        video = self.video_repo.get_by_id(video_id)
        if not video:
            raise VideoNotFoundError(video_id=video_id)
        
        tag = self.tag_repo.get_by_id(tag_id)
        if not tag:
            raise TagNotFoundError(tag_id=tag_id)
        
        if self.video_tag_repo.exists(video_id, tag_id):
            return {
                "video_id": video_id,
                "tag_id": tag_id,
                "added": False,
                "message": "标签已存在"
            }
        
        self.video_tag_repo.create(VideoTagCreate(video_id=video_id, tag_id=tag_id))
        
        return {
            "video_id": video_id,
            "tag_id": tag_id,
            "added": True,
            "message": "标签添加成功"
        }
    
    def remove_tag_from_video(self, video_id: int, tag_id: int) -> dict:
        """从视频移除标签"""
        video = self.video_repo.get_by_id(video_id)
        if not video:
            raise VideoNotFoundError(video_id=video_id)
        
        tag = self.tag_repo.get_by_id(tag_id)
        if not tag:
            raise TagNotFoundError(tag_id=tag_id)
        
        removed = self.video_tag_repo.delete_by_video_and_tag(video_id, tag_id)
        
        return {
            "video_id": video_id,
            "tag_id": tag_id,
            "removed": removed,
            "message": "标签移除成功" if removed else "标签不存在"
        }
    
    def get_video_tags(self, video_id: int) -> List[TagResponse]:
        """获取视频的所有标签"""
        video = self.video_repo.get_by_id(video_id)
        if not video:
            raise VideoNotFoundError(video_id=video_id)
        
        tags = self.video_tag_repo.list_tags_by_video(video_id)
        return [TagResponse.model_validate(tag) for tag in tags]
    
    def get_video_tag_ids(self, video_id: int) -> Set[int]:
        """获取视频的所有标签ID"""
        video = self.video_repo.get_by_id(video_id)
        if not video:
            raise VideoNotFoundError(video_id=video_id)
        
        return self.video_tag_repo.list_tag_ids_by_video(video_id)
    
    def set_video_tags(self, video_id: int, tag_ids: List[int]) -> dict:
        """设置视频的标签（替换现有标签）"""
        video = self.video_repo.get_by_id(video_id)
        if not video:
            raise VideoNotFoundError(video_id=video_id)
        
        tags = self.tag_repo.get_by_ids(tag_ids)
        if len(tags) != len(tag_ids):
            found_ids = {tag.id for tag in tags}
            missing_ids = set(tag_ids) - found_ids
            raise TagNotFoundError(tag_id=next(iter(missing_ids)))
        
        existing_tag_ids = self.video_tag_repo.list_tag_ids_by_video(video_id)
        
        tags_to_add = set(tag_ids) - existing_tag_ids
        tags_to_remove = existing_tag_ids - set(tag_ids)
        
        added_count = 0
        removed_count = 0
        
        if tags_to_add:
            added_count = len(self.video_tag_repo.add_tags_to_video(
                video_id, list(tags_to_add)
            ))
        
        if tags_to_remove:
            removed_count = self.video_tag_repo.remove_tags_from_video(
                video_id, list(tags_to_remove)
            )
        
        return {
            "video_id": video_id,
            "tags_added": added_count,
            "tags_removed": removed_count,
            "current_tag_count": len(tag_ids)
        }
    
    def batch_add_tags(self, operation: BatchTagOperation) -> dict:
        """批量为视频添加标签"""
        videos = []
        missing_video_ids = []
        for video_id in operation.video_ids:
            video = self.video_repo.get_by_id(video_id)
            if video:
                videos.append(video)
            else:
                missing_video_ids.append(video_id)
        
        if missing_video_ids:
            raise VideoNotFoundError(video_id=missing_video_ids[0])
        
        tags = self.tag_repo.get_by_ids(operation.tag_ids)
        if len(tags) != len(operation.tag_ids):
            found_ids = {tag.id for tag in tags}
            missing_ids = set(operation.tag_ids) - found_ids
            raise TagNotFoundError(tag_id=next(iter(missing_ids)))
        
        added_count = self.video_tag_repo.add_tags_to_videos(
            operation.video_ids,
            operation.tag_ids
        )
        
        return {
            "videos_affected": len(operation.video_ids),
            "tags_added": added_count,
            "message": f"成功为 {len(operation.video_ids)} 个视频添加了 {added_count} 个标签关联"
        }
    
    def batch_remove_tags(self, operation: BatchTagOperation) -> dict:
        """批量从视频移除标签"""
        for video_id in operation.video_ids:
            if not self.video_repo.get_by_id(video_id):
                raise VideoNotFoundError(video_id=video_id)
        
        for tag_id in operation.tag_ids:
            if not self.tag_repo.get_by_id(tag_id):
                raise TagNotFoundError(tag_id=tag_id)
        
        removed_count = self.video_tag_repo.remove_tags_from_videos(
            operation.video_ids,
            operation.tag_ids
        )
        
        return {
            "videos_affected": len(operation.video_ids),
            "tags_removed": removed_count,
            "message": f"成功从 {len(operation.video_ids)} 个视频移除了 {removed_count} 个标签关联"
        }
    
    def get_videos_by_tags(
        self,
        tag_ids: List[int],
        match_all: bool = False
    ) -> List[int]:
        """根据标签获取视频ID列表"""
        for tag_id in tag_ids:
            if not self.tag_repo.get_by_id(tag_id):
                raise TagNotFoundError(tag_id=tag_id)
        
        from sqlalchemy import select
        from video_tag_system.models.video_tag import VideoTag
        from sqlalchemy import func
        
        if match_all:
            subquery = (
                select(VideoTag.video_id)
                .where(VideoTag.tag_id.in_(tag_ids))
                .group_by(VideoTag.video_id)
                .having(func.count(VideoTag.tag_id) == len(tag_ids))
            )
            result = self.session.execute(subquery).scalars().all()
        else:
            stmt = (
                select(VideoTag.video_id)
                .where(VideoTag.tag_id.in_(tag_ids))
                .distinct()
            )
            result = self.session.execute(stmt).scalars().all()
        
        return list(result)
    
    def get_tag_video_count(self, tag_id: int) -> int:
        """获取标签关联的视频数量"""
        if not self.tag_repo.get_by_id(tag_id):
            raise TagNotFoundError(tag_id=tag_id)
        
        return self.video_tag_repo.count_by_tag(tag_id)
    
    def get_video_tag_count(self, video_id: int) -> int:
        """获取视频关联的标签数量"""
        if not self.video_repo.get_by_id(video_id):
            raise VideoNotFoundError(video_id=video_id)
        
        return self.video_tag_repo.count_by_video(video_id)
    
    def check_video_has_tag(self, video_id: int, tag_id: int) -> bool:
        """检查视频是否有指定标签"""
        if not self.video_repo.get_by_id(video_id):
            raise VideoNotFoundError(video_id=video_id)
        if not self.tag_repo.get_by_id(tag_id):
            raise TagNotFoundError(tag_id=tag_id)
        
        return self.video_tag_repo.exists(video_id, tag_id)
    
    def count_associations(self) -> int:
        """获取所有视频-标签关联总数"""
        from sqlalchemy import func
        from video_tag_system.models.video_tag import VideoTag
        
        result = self.session.execute(
            select(func.count()).select_from(VideoTag)
        ).scalar()
        
        return result or 0

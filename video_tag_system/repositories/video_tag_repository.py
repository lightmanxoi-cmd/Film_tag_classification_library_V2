"""
视频-标签关联数据访问层
"""
from typing import List, Optional, Set
from sqlalchemy import select, delete, and_
from sqlalchemy.orm import Session

from video_tag_system.models.video_tag import VideoTag, VideoTagCreate
from video_tag_system.models.tag import Tag


class VideoTagRepository:
    """视频-标签关联数据访问类"""
    
    def __init__(self, session: Session):
        self.session = session
    
    def create(self, data: VideoTagCreate) -> VideoTag:
        """创建关联"""
        video_tag = VideoTag(**data.model_dump())
        self.session.add(video_tag)
        self.session.flush()
        return video_tag
    
    def create_batch(self, data_list: List[VideoTagCreate]) -> List[VideoTag]:
        """批量创建关联"""
        video_tags = [VideoTag(**data.model_dump()) for data in data_list]
        self.session.add_all(video_tags)
        self.session.flush()
        return video_tags
    
    def get_by_video_and_tag(self, video_id: int, tag_id: int) -> Optional[VideoTag]:
        """根据视频ID和标签ID获取关联"""
        stmt = select(VideoTag).where(
            VideoTag.video_id == video_id,
            VideoTag.tag_id == tag_id
        )
        return self.session.execute(stmt).scalar_one_or_none()
    
    def delete(self, video_tag: VideoTag) -> None:
        """删除关联"""
        self.session.delete(video_tag)
        self.session.flush()
    
    def delete_by_video_and_tag(self, video_id: int, tag_id: int) -> bool:
        """根据视频ID和标签ID删除关联"""
        video_tag = self.get_by_video_and_tag(video_id, tag_id)
        if video_tag:
            self.delete(video_tag)
            return True
        return False
    
    def delete_by_video_id(self, video_id: int) -> int:
        """删除视频的所有标签关联"""
        stmt = delete(VideoTag).where(VideoTag.video_id == video_id)
        result = self.session.execute(stmt)
        self.session.flush()
        return result.rowcount
    
    def delete_by_tag_id(self, tag_id: int) -> int:
        """删除标签的所有视频关联"""
        stmt = delete(VideoTag).where(VideoTag.tag_id == tag_id)
        result = self.session.execute(stmt)
        self.session.flush()
        return result.rowcount
    
    def list_tags_by_video(self, video_id: int) -> List[Tag]:
        """获取视频的所有标签"""
        stmt = (
            select(Tag)
            .join(VideoTag, Tag.id == VideoTag.tag_id)
            .where(VideoTag.video_id == video_id)
            .order_by(Tag.sort_order, Tag.created_at)
        )
        return list(self.session.execute(stmt).scalars().all())
    
    def list_tag_ids_by_video(self, video_id: int) -> Set[int]:
        """获取视频的所有标签ID"""
        stmt = select(VideoTag.tag_id).where(VideoTag.video_id == video_id)
        return set(self.session.execute(stmt).scalars().all())
    
    def exists(self, video_id: int, tag_id: int) -> bool:
        """检查关联是否存在"""
        stmt = select(VideoTag.id).where(
            VideoTag.video_id == video_id,
            VideoTag.tag_id == tag_id
        )
        return self.session.execute(stmt).scalar_one_or_none() is not None
    
    def count_by_video(self, video_id: int) -> int:
        """获取视频的标签数量"""
        from sqlalchemy import func
        stmt = select(func.count(VideoTag.id)).where(VideoTag.video_id == video_id)
        return self.session.execute(stmt).scalar()
    
    def count_by_tag(self, tag_id: int) -> int:
        """获取标签的视频数量"""
        from sqlalchemy import func
        stmt = select(func.count(VideoTag.id)).where(VideoTag.tag_id == tag_id)
        return self.session.execute(stmt).scalar()
    
    def add_tags_to_video(
        self, 
        video_id: int, 
        tag_ids: List[int]
    ) -> List[VideoTag]:
        """为视频添加多个标签"""
        existing_tag_ids = self.list_tag_ids_by_video(video_id)
        new_tag_ids = set(tag_ids) - existing_tag_ids
        
        new_video_tags = []
        for tag_id in new_tag_ids:
            video_tag = VideoTag(video_id=video_id, tag_id=tag_id)
            self.session.add(video_tag)
            new_video_tags.append(video_tag)
        
        if new_video_tags:
            self.session.flush()
        
        return new_video_tags
    
    def remove_tags_from_video(
        self, 
        video_id: int, 
        tag_ids: List[int]
    ) -> int:
        """从视频移除多个标签"""
        stmt = delete(VideoTag).where(
            and_(
                VideoTag.video_id == video_id,
                VideoTag.tag_id.in_(tag_ids)
            )
        )
        result = self.session.execute(stmt)
        self.session.flush()
        return result.rowcount
    
    def add_tags_to_videos(
        self, 
        video_ids: List[int], 
        tag_ids: List[int]
    ) -> int:
        """批量为多个视频添加多个标签"""
        count = 0
        for video_id in video_ids:
            existing_tag_ids = self.list_tag_ids_by_video(video_id)
            new_tag_ids = set(tag_ids) - existing_tag_ids
            
            for tag_id in new_tag_ids:
                video_tag = VideoTag(video_id=video_id, tag_id=tag_id)
                self.session.add(video_tag)
                count += 1
        
        if count > 0:
            self.session.flush()
        
        return count
    
    def remove_tags_from_videos(
        self, 
        video_ids: List[int], 
        tag_ids: List[int]
    ) -> int:
        """批量从多个视频移除多个标签"""
        stmt = delete(VideoTag).where(
            and_(
                VideoTag.video_id.in_(video_ids),
                VideoTag.tag_id.in_(tag_ids)
            )
        )
        result = self.session.execute(stmt)
        self.session.flush()
        return result.rowcount
    
    def transfer_video_tags(
        self, 
        source_tag_id: int, 
        target_tag_id: int
    ) -> int:
        """将源标签的视频关联转移到目标标签"""
        stmt = select(VideoTag.video_id).where(VideoTag.tag_id == source_tag_id)
        source_video_ids = list(self.session.execute(stmt).scalars().all())
        
        count = 0
        for video_id in source_video_ids:
            existing = self.get_by_video_and_tag(video_id, target_tag_id)
            if existing:
                self.delete_by_video_and_tag(video_id, source_tag_id)
            else:
                stmt = (
                    delete(VideoTag)
                    .where(
                        VideoTag.video_id == video_id,
                        VideoTag.tag_id == source_tag_id
                    )
                )
                self.session.execute(stmt)
                video_tag = VideoTag(video_id=video_id, tag_id=target_tag_id)
                self.session.add(video_tag)
            count += 1
        
        if count > 0:
            self.session.flush()
        
        return count

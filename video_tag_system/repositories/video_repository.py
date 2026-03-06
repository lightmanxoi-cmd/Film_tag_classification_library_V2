"""
视频数据访问层
"""
import random
from typing import Optional, List, Tuple
from sqlalchemy import select, func, or_
from sqlalchemy.orm import Session, joinedload, selectinload

from video_tag_system.models.video import Video, VideoCreate, VideoUpdate
from video_tag_system.models.tag import Tag
from video_tag_system.models.video_tag import VideoTag


class VideoRepository:
    """视频数据访问类"""
    
    def __init__(self, session: Session):
        self.session = session
    
    def create(self, video_data: VideoCreate) -> Video:
        """创建视频"""
        video = Video(**video_data.model_dump())
        self.session.add(video)
        self.session.flush()
        return video
    
    def create_batch(self, videos_data: List[VideoCreate]) -> List[Video]:
        """批量创建视频"""
        videos = [Video(**data.model_dump()) for data in videos_data]
        self.session.add_all(videos)
        self.session.flush()
        return videos
    
    def get_by_id(self, video_id: int) -> Optional[Video]:
        """根据ID获取视频"""
        return self.session.get(Video, video_id)
    
    def get_by_id_with_tags(self, video_id: int) -> Optional[Video]:
        """根据ID获取视频（包含标签）"""
        stmt = (
            select(Video)
            .options(selectinload(Video.tags).selectinload(VideoTag.tag))
            .where(Video.id == video_id)
        )
        return self.session.execute(stmt).unique().scalar_one_or_none()
    
    def get_by_file_path(self, file_path: str) -> Optional[Video]:
        """根据文件路径获取视频"""
        stmt = select(Video).where(Video.file_path == file_path)
        return self.session.execute(stmt).scalar_one_or_none()
    
    def get_by_file_hash(self, file_hash: str) -> Optional[Video]:
        """根据文件哈希获取视频"""
        stmt = select(Video).where(Video.file_hash == file_hash)
        return self.session.execute(stmt).scalar_one_or_none()
    
    def get_by_ids(self, video_ids: List[int]) -> List[Video]:
        """根据ID列表批量获取视频"""
        if not video_ids:
            return []
        stmt = select(Video).where(Video.id.in_(video_ids))
        return list(self.session.execute(stmt).scalars().all())
    
    def update(self, video: Video, video_data: VideoUpdate) -> Video:
        """更新视频"""
        update_data = video_data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(video, key, value)
        self.session.flush()
        return video
    
    def delete(self, video: Video) -> None:
        """删除视频"""
        self.session.delete(video)
        self.session.flush()
    
    def delete_by_id(self, video_id: int) -> bool:
        """根据ID删除视频"""
        video = self.get_by_id(video_id)
        if video:
            self.delete(video)
            return True
        return False
    
    def delete_by_ids(self, video_ids: List[int]) -> int:
        """批量删除视频"""
        if not video_ids:
            return 0
        stmt = select(Video).where(Video.id.in_(video_ids))
        videos = self.session.execute(stmt).scalars().all()
        count = 0
        for video in videos:
            self.session.delete(video)
            count += 1
        self.session.flush()
        return count
    
    def list_all(
        self,
        page: int = 1,
        page_size: int = 20,
        search: Optional[str] = None,
        random_order: bool = False,
        random_seed: Optional[int] = None
    ) -> Tuple[List[Video], int]:
        """获取视频列表"""
        stmt = select(Video)
        count_stmt = select(func.count(Video.id))
        
        if search:
            search_pattern = f"%{search}%"
            search_filter = or_(
                Video.title.ilike(search_pattern),
                Video.description.ilike(search_pattern),
                Video.file_path.ilike(search_pattern)
            )
            stmt = stmt.where(search_filter)
            count_stmt = count_stmt.where(search_filter)
        
        total = self.session.execute(count_stmt).scalar()
        
        if random_order and random_seed is not None:
            random.seed(random_seed)
            all_ids_stmt = select(Video.id)
            if search:
                all_ids_stmt = all_ids_stmt.where(search_filter)
            all_ids = [row[0] for row in self.session.execute(all_ids_stmt).all()]
            random.shuffle(all_ids)
            
            start_idx = (page - 1) * page_size
            end_idx = start_idx + page_size
            page_ids = all_ids[start_idx:end_idx]
            
            if not page_ids:
                return [], total
            
            stmt = select(Video).where(Video.id.in_(page_ids))
            videos = list(self.session.execute(stmt).scalars().all())
            
            id_to_video = {v.id: v for v in videos}
            ordered_videos = [id_to_video[vid] for vid in page_ids if vid in id_to_video]
            
            return ordered_videos, total
        else:
            stmt = stmt.order_by(Video.created_at.desc())
            stmt = stmt.offset((page - 1) * page_size).limit(page_size)
            videos = list(self.session.execute(stmt).scalars().all())
            return videos, total
    
    def list_by_tag_ids(
        self,
        tag_ids: List[int],
        page: int = 1,
        page_size: int = 20,
        match_all: bool = False
    ) -> Tuple[List[Video], int]:
        """根据标签ID列表获取视频"""
        from video_tag_system.models.video_tag import VideoTag
        
        if not tag_ids:
            return [], 0
        
        if match_all:
            subquery = (
                select(VideoTag.video_id)
                .where(VideoTag.tag_id.in_(tag_ids))
                .group_by(VideoTag.video_id)
                .having(func.count(VideoTag.tag_id) == len(tag_ids))
            )
            stmt = select(Video).where(Video.id.in_(subquery))
            count_stmt = select(func.count()).select_from(stmt.subquery())
        else:
            stmt = (
                select(Video)
                .join(VideoTag, Video.id == VideoTag.video_id)
                .where(VideoTag.tag_id.in_(tag_ids))
                .distinct()
            )
            count_stmt = select(func.count()).select_from(stmt.subquery())
        
        total = self.session.execute(count_stmt).scalar()
        
        stmt = stmt.order_by(Video.created_at.desc())
        stmt = stmt.offset((page - 1) * page_size).limit(page_size)
        
        videos = list(self.session.execute(stmt).scalars().all())
        
        return videos, total
    
    def list_by_tags_advanced(
        self,
        tags_by_category: dict,
        page: int = 1,
        page_size: int = 20
    ) -> Tuple[List[Video], int]:
        """
        高级标签筛选
        同一分类下的标签为OR关系，不同分类间为AND关系
        
        Args:
            tags_by_category: {category_id: [tag_id1, tag_id2, ...], ...}
            page: 页码
            page_size: 每页数量
            
        Returns:
            (videos, total)
        """
        from video_tag_system.models.video_tag import VideoTag
        from sqlalchemy import and_
        
        if not tags_by_category:
            return [], 0
        
        conditions = []
        for category_id, tag_ids in tags_by_category.items():
            if tag_ids:
                subquery = (
                    select(VideoTag.video_id)
                    .where(VideoTag.tag_id.in_(tag_ids))
                )
                conditions.append(Video.id.in_(subquery))
        
        if not conditions:
            return [], 0
        
        stmt = select(Video).where(and_(*conditions)).distinct()
        count_stmt = select(func.count()).select_from(stmt.subquery())
        
        total = self.session.execute(count_stmt).scalar()
        
        stmt = stmt.order_by(Video.created_at.desc())
        stmt = stmt.offset((page - 1) * page_size).limit(page_size)
        
        videos = list(self.session.execute(stmt).scalars().all())
        
        return videos, total
    
    def exists_by_file_path(self, file_path: str) -> bool:
        """检查文件路径是否存在"""
        stmt = select(func.count(Video.id)).where(Video.file_path == file_path)
        return self.session.execute(stmt).scalar() > 0
    
    def count_all(self) -> int:
        """获取视频总数"""
        return self.session.execute(select(func.count(Video.id))).scalar()
    
    def count_by_tag_ids(self, tag_ids: List[int], match_all: bool = False) -> int:
        """根据标签ID统计视频数量"""
        from video_tag_system.models.video_tag import VideoTag
        
        if not tag_ids:
            return 0
        
        if match_all:
            subquery = (
                select(VideoTag.video_id)
                .where(VideoTag.tag_id.in_(tag_ids))
                .group_by(VideoTag.video_id)
                .having(func.count(VideoTag.tag_id) == len(tag_ids))
            )
            stmt = select(func.count()).select_from(subquery.subquery())
        else:
            stmt = (
                select(func.count(func.distinct(VideoTag.video_id)))
                .where(VideoTag.tag_id.in_(tag_ids))
            )
        
        return self.session.execute(stmt).scalar()

"""
视频数据访问层
"""
from typing import Optional, List, Tuple
from sqlalchemy import select, func, or_
from sqlalchemy.orm import Session, joinedload

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
    
    def get_by_id(self, video_id: int) -> Optional[Video]:
        """根据ID获取视频"""
        return self.session.get(Video, video_id)
    
    def get_by_id_with_tags(self, video_id: int) -> Optional[Video]:
        """根据ID获取视频（包含标签）"""
        stmt = (
            select(Video)
            .options(joinedload(Video.tags).joinedload(VideoTag.tag))
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
    
    def list_all(
        self,
        page: int = 1,
        page_size: int = 20,
        search: Optional[str] = None
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
    
    def exists_by_file_path(self, file_path: str) -> bool:
        """检查文件路径是否存在"""
        stmt = select(func.count(Video.id)).where(Video.file_path == file_path)
        return self.session.execute(stmt).scalar() > 0
    
    def count_all(self) -> int:
        """获取视频总数"""
        return self.session.execute(select(func.count(Video.id))).scalar()

"""
视频数据访问层模块

本模块提供视频数据的持久化操作，封装了所有与视频相关的数据库操作。
采用 Repository 模式，将数据访问逻辑与业务逻辑分离。

主要功能：
- 视频的 CRUD 操作（创建、读取、更新、删除）
- 视频列表查询（支持分页、搜索、随机排序）
- 根据标签筛选视频
- 视频去重检测（通过文件路径或哈希值）

使用示例：
    from video_tag_system.repositories.video_repository import VideoRepository
    from video_tag_system.core.database import get_session
    
    with get_session() as session:
        repo = VideoRepository(session)
        
        # 创建视频
        video = repo.create(VideoCreate(file_path="/path/to/video.mp4"))
        
        # 分页查询
        videos, total = repo.list_all(page=1, page_size=20)
        
        # 按标签筛选
        videos, total = repo.list_by_tag_ids([1, 2, 3])

Note:
    所有方法都需要传入 SQLAlchemy Session 对象。
    方法内部使用 flush() 而非 commit()，事务管理由调用方控制。
"""
import random
from typing import Optional, List, Tuple
from sqlalchemy import select, func, or_
from sqlalchemy.orm import Session, joinedload, selectinload

from video_tag_system.models.video import Video, VideoCreate, VideoUpdate
from video_tag_system.models.tag import Tag
from video_tag_system.models.video_tag import VideoTag


class VideoRepository:
    """
    视频数据访问类
    
    提供视频数据的增删改查操作，封装所有与 videos 表相关的数据库操作。
    
    Attributes:
        session: SQLAlchemy 数据库会话对象
    
    Thread Safety:
        本类不是线程安全的，每个线程应使用独立的 Session 和 Repository 实例。
    
    Example:
        repo = VideoRepository(session)
        video = repo.get_by_id(1)
    """
    
    def __init__(self, session: Session):
        """
        初始化视频数据访问对象
        
        Args:
            session: SQLAlchemy 数据库会话对象
        """
        self.session = session
    
    def create(self, video_data: VideoCreate) -> Video:
        """
        创建视频记录
        
        将视频数据插入数据库，返回创建的视频对象。
        
        Args:
            video_data: 视频创建数据模型，包含必填的 file_path
        
        Returns:
            Video: 创建的视频 ORM 对象，包含自动生成的 id 和时间戳
        
        Note:
            调用后需要 commit 才能持久化到数据库
        """
        video = Video(**video_data.model_dump())
        self.session.add(video)
        self.session.flush()
        return video
    
    def create_batch(self, videos_data: List[VideoCreate]) -> List[Video]:
        """
        批量创建视频记录
        
        一次性插入多个视频记录，比循环调用 create() 更高效。
        
        Args:
            videos_data: 视频创建数据模型列表
        
        Returns:
            List[Video]: 创建的视频对象列表
        
        Performance:
            使用 add_all() 批量插入，性能优于循环单条插入
        """
        videos = [Video(**data.model_dump()) for data in videos_data]
        self.session.add_all(videos)
        self.session.flush()
        return videos
    
    def get_by_id(self, video_id: int) -> Optional[Video]:
        """
        根据ID获取视频
        
        通过主键快速查找视频记录。
        
        Args:
            video_id: 视频ID
        
        Returns:
            Optional[Video]: 视频对象，不存在时返回 None
        
        Performance:
            使用 session.get() 直接通过主键查询，性能最优
        """
        return self.session.get(Video, video_id)
    
    def get_by_id_with_tags(self, video_id: int) -> Optional[Video]:
        """
        根据ID获取视频（包含关联的标签）
        
        使用预加载策略一次性获取视频及其所有标签，
        避免 N+1 查询问题。
        
        Args:
            video_id: 视频ID
        
        Returns:
            Optional[Video]: 包含标签的视频对象
        
        Performance:
            使用 selectinload 预加载标签，减少数据库查询次数
        """
        stmt = (
            select(Video)
            .options(selectinload(Video.tags).selectinload(VideoTag.tag))
            .where(Video.id == video_id)
        )
        return self.session.execute(stmt).unique().scalar_one_or_none()
    
    def get_by_file_path(self, file_path: str) -> Optional[Video]:
        """
        根据文件路径获取视频
        
        用于检查视频是否已存在（文件路径唯一）。
        
        Args:
            file_path: 视频文件的完整路径
        
        Returns:
            Optional[Video]: 视频对象，不存在时返回 None
        """
        stmt = select(Video).where(Video.file_path == file_path)
        return self.session.execute(stmt).scalar_one_or_none()
    
    def get_by_file_hash(self, file_hash: str) -> Optional[Video]:
        """
        根据文件哈希获取视频
        
        用于检测重复文件（相同哈希的视频）。
        
        Args:
            file_hash: 文件的 SHA256 哈希值
        
        Returns:
            Optional[Video]: 视频对象，不存在时返回 None
        """
        stmt = select(Video).where(Video.file_hash == file_hash)
        return self.session.execute(stmt).scalar_one_or_none()
    
    def get_by_ids(self, video_ids: List[int]) -> List[Video]:
        """
        根据ID列表批量获取视频
        
        一次性获取多个视频记录。
        
        Args:
            video_ids: 视频ID列表
        
        Returns:
            List[Video]: 视频对象列表（只返回存在的视频）
        """
        if not video_ids:
            return []
        stmt = select(Video).where(Video.id.in_(video_ids))
        return list(self.session.execute(stmt).scalars().all())
    
    def update(self, video: Video, video_data: VideoUpdate) -> Video:
        """
        更新视频信息
        
        只更新提供的字段，未提供的字段保持不变。
        
        Args:
            video: 要更新的视频对象
            video_data: 更新数据模型（所有字段可选）
        
        Returns:
            Video: 更新后的视频对象
        
        Note:
            updated_at 字段会自动更新
        """
        update_data = video_data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(video, key, value)
        self.session.flush()
        return video
    
    def delete(self, video: Video) -> None:
        """
        删除视频
        
        删除视频记录及其所有关联的标签关系。
        
        Args:
            video: 要删除的视频对象
        
        Note:
            关联的 VideoTag 记录会被级联删除
        """
        self.session.delete(video)
        self.session.flush()
    
    def delete_by_id(self, video_id: int) -> bool:
        """
        根据ID删除视频
        
        Args:
            video_id: 视频ID
        
        Returns:
            bool: 删除成功返回 True，视频不存在返回 False
        """
        video = self.get_by_id(video_id)
        if video:
            self.delete(video)
            return True
        return False
    
    def delete_by_ids(self, video_ids: List[int]) -> int:
        """
        批量删除视频
        
        Args:
            video_ids: 视频ID列表
        
        Returns:
            int: 实际删除的视频数量
        """
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
        """
        获取视频列表
        
        支持分页、搜索和随机排序。
        
        Args:
            page: 页码，从1开始
            page_size: 每页记录数
            search: 搜索关键词，匹配标题、描述、文件路径
            random_order: 是否随机排序
            random_seed: 随机种子，用于复现随机排序结果
        
        Returns:
            Tuple[List[Video], int]: (视频列表, 总记录数)
        
        Performance:
            随机排序时需要获取所有ID后内存排序，大数据量时性能较低
        """
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
        """
        根据标签ID列表获取视频
        
        支持两种匹配模式：
        - match_all=False: 视频包含任意一个标签即可（OR）
        - match_all=True: 视频必须包含所有标签（AND）
        
        Args:
            tag_ids: 标签ID列表
            page: 页码
            page_size: 每页记录数
            match_all: 是否必须匹配所有标签
        
        Returns:
            Tuple[List[Video], int]: (视频列表, 总记录数)
        """
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
        
        支持按标签分类进行组合筛选：
        - 同一分类下的标签为 OR 关系（满足任一即可）
        - 不同分类间为 AND 关系（必须都满足）
        
        例如：筛选"动作片或喜剧片"且"中国大陆或香港"的视频
        
        Args:
            tags_by_category: 分类标签字典
                格式: {category_id: [tag_id1, tag_id2, ...], ...}
            page: 页码
            page_size: 每页数量
            
        Returns:
            Tuple[List[Video], int]: (视频列表, 总记录数)
        
        Example:
            videos, total = repo.list_by_tags_advanced({
                1: [1, 2],  # 分类1：动作或喜剧
                2: [5, 6]   # 分类2：大陆或香港
            })
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
        """
        检查文件路径是否已存在
        
        用于导入视频时去重。
        
        Args:
            file_path: 视频文件路径
        
        Returns:
            bool: 存在返回 True，不存在返回 False
        """
        stmt = select(func.count(Video.id)).where(Video.file_path == file_path)
        return self.session.execute(stmt).scalar() > 0
    
    def count_all(self) -> int:
        """
        获取视频总数
        
        Returns:
            int: 视频总记录数
        """
        return self.session.execute(select(func.count(Video.id))).scalar()
    
    def count_by_tag_ids(self, tag_ids: List[int], match_all: bool = False) -> int:
        """
        根据标签ID统计视频数量
        
        Args:
            tag_ids: 标签ID列表
            match_all: 是否必须匹配所有标签
        
        Returns:
            int: 符合条件的视频数量
        """
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

"""
视频-标签关联数据访问层模块

本模块提供视频与标签关联关系的持久化操作，封装了所有与 video_tags 表相关的数据库操作。
采用 Repository 模式，将数据访问逻辑与业务逻辑分离。

主要功能：
- 关联的 CRUD 操作（创建、读取、删除）
- 批量操作（批量添加、批量删除）
- 关联查询（获取视频的标签、获取标签的视频）
- 标签转移（合并标签时转移关联）

使用示例：
    from video_tag_system.repositories.video_tag_repository import VideoTagRepository
    from video_tag_system.core.database import get_session
    
    with get_session() as session:
        repo = VideoTagRepository(session)
        
        # 为视频添加标签
        repo.add_tags_to_video(video_id=1, tag_ids=[1, 2, 3])
        
        # 获取视频的所有标签
        tags = repo.list_tags_by_video(video_id=1)
        
        # 批量操作
        repo.add_tags_to_videos([1, 2, 3], [5, 6])

Note:
    所有方法都需要传入 SQLAlchemy Session 对象。
    方法内部使用 flush() 而非 commit()，事务管理由调用方控制。
"""
from typing import List, Optional, Set
from sqlalchemy import select, delete, and_
from sqlalchemy.orm import Session

from video_tag_system.models.video_tag import VideoTag, VideoTagCreate
from video_tag_system.models.tag import Tag


class VideoTagRepository:
    """
    视频-标签关联数据访问类
    
    提供视频与标签关联关系的增删改查操作，封装所有与 video_tags 表相关的数据库操作。
    作为多对多关系的中间表访问层，支持复杂的关联操作。
    
    Attributes:
        session: SQLAlchemy 数据库会话对象
    
    Thread Safety:
        本类不是线程安全的，每个线程应使用独立的 Session 和 Repository 实例。
    
    Example:
        repo = VideoTagRepository(session)
        tags = repo.list_tags_by_video(video_id=1)
    """
    
    def __init__(self, session: Session):
        """
        初始化视频-标签关联数据访问对象
        
        Args:
            session: SQLAlchemy 数据库会话对象
        """
        self.session = session
    
    def create(self, data: VideoTagCreate) -> VideoTag:
        """
        创建视频-标签关联
        
        建立视频与标签的关联关系。
        
        Args:
            data: 关联创建数据模型，包含 video_id 和 tag_id
        
        Returns:
            VideoTag: 创建的关联对象
        
        Raises:
            IntegrityError: 关联已存在时抛出（唯一约束冲突）
        """
        video_tag = VideoTag(**data.model_dump())
        self.session.add(video_tag)
        self.session.flush()
        return video_tag
    
    def create_batch(self, data_list: List[VideoTagCreate]) -> List[VideoTag]:
        """
        批量创建视频-标签关联
        
        一次性创建多个关联关系，比循环调用 create() 更高效。
        
        Args:
            data_list: 关联创建数据模型列表
        
        Returns:
            List[VideoTag]: 创建的关联对象列表
        
        Note:
            如果列表中有重复关联，会抛出 IntegrityError
        """
        video_tags = [VideoTag(**data.model_dump()) for data in data_list]
        self.session.add_all(video_tags)
        self.session.flush()
        return video_tags
    
    def get_by_video_and_tag(self, video_id: int, tag_id: int) -> Optional[VideoTag]:
        """
        根据视频ID和标签ID获取关联
        
        查询特定的视频-标签关联是否存在。
        
        Args:
            video_id: 视频ID
            tag_id: 标签ID
        
        Returns:
            Optional[VideoTag]: 关联对象，不存在时返回 None
        """
        stmt = select(VideoTag).where(
            VideoTag.video_id == video_id,
            VideoTag.tag_id == tag_id
        )
        return self.session.execute(stmt).scalar_one_or_none()
    
    def delete(self, video_tag: VideoTag) -> None:
        """
        删除视频-标签关联
        
        Args:
            video_tag: 要删除的关联对象
        """
        self.session.delete(video_tag)
        self.session.flush()
    
    def delete_by_video_and_tag(self, video_id: int, tag_id: int) -> bool:
        """
        根据视频ID和标签ID删除关联
        
        Args:
            video_id: 视频ID
            tag_id: 标签ID
        
        Returns:
            bool: 删除成功返回 True，关联不存在返回 False
        """
        video_tag = self.get_by_video_and_tag(video_id, tag_id)
        if video_tag:
            self.delete(video_tag)
            return True
        return False
    
    def delete_by_video_id(self, video_id: int) -> int:
        """
        删除视频的所有标签关联
        
        删除指定视频与所有标签的关联关系。
        通常在删除视频时调用。
        
        Args:
            video_id: 视频ID
        
        Returns:
            int: 删除的关联数量
        """
        stmt = delete(VideoTag).where(VideoTag.video_id == video_id)
        result = self.session.execute(stmt)
        self.session.flush()
        return result.rowcount
    
    def delete_by_tag_id(self, tag_id: int) -> int:
        """
        删除标签的所有视频关联
        
        删除指定标签与所有视频的关联关系。
        通常在删除标签时调用。
        
        Args:
            tag_id: 标签ID
        
        Returns:
            int: 删除的关联数量
        """
        stmt = delete(VideoTag).where(VideoTag.tag_id == tag_id)
        result = self.session.execute(stmt)
        self.session.flush()
        return result.rowcount
    
    def list_tags_by_video(self, video_id: int) -> List[Tag]:
        """
        获取视频的所有标签
        
        查询与指定视频关联的所有标签。
        
        Args:
            video_id: 视频ID
        
        Returns:
            List[Tag]: 标签对象列表，按 sort_order 和创建时间排序
        """
        stmt = (
            select(Tag)
            .join(VideoTag, Tag.id == VideoTag.tag_id)
            .where(VideoTag.video_id == video_id)
            .order_by(Tag.sort_order, Tag.created_at)
        )
        return list(self.session.execute(stmt).scalars().all())
    
    def list_tag_ids_by_video(self, video_id: int) -> Set[int]:
        """
        获取视频的所有标签ID
        
        只返回标签ID集合，比 list_tags_by_video 更轻量。
        用于快速判断视频是否有特定标签。
        
        Args:
            video_id: 视频ID
        
        Returns:
            Set[int]: 标签ID集合
        """
        stmt = select(VideoTag.tag_id).where(VideoTag.video_id == video_id)
        return set(self.session.execute(stmt).scalars().all())
    
    def exists(self, video_id: int, tag_id: int) -> bool:
        """
        检查关联是否存在
        
        快速判断视频是否已关联指定标签。
        
        Args:
            video_id: 视频ID
            tag_id: 标签ID
        
        Returns:
            bool: 存在返回 True，不存在返回 False
        """
        stmt = select(VideoTag.id).where(
            VideoTag.video_id == video_id,
            VideoTag.tag_id == tag_id
        )
        return self.session.execute(stmt).scalar_one_or_none() is not None
    
    def count_by_video(self, video_id: int) -> int:
        """
        获取视频的标签数量
        
        统计与指定视频关联的标签数量。
        
        Args:
            video_id: 视频ID
        
        Returns:
            int: 标签数量
        """
        from sqlalchemy import func
        stmt = select(func.count(VideoTag.id)).where(VideoTag.video_id == video_id)
        return self.session.execute(stmt).scalar()
    
    def count_by_tag(self, tag_id: int) -> int:
        """
        获取标签的视频数量
        
        统计与指定标签关联的视频数量。
        
        Args:
            tag_id: 标签ID
        
        Returns:
            int: 视频数量
        """
        from sqlalchemy import func
        stmt = select(func.count(VideoTag.id)).where(VideoTag.tag_id == tag_id)
        return self.session.execute(stmt).scalar()
    
    def add_tags_to_video(
        self, 
        video_id: int, 
        tag_ids: List[int]
    ) -> List[VideoTag]:
        """
        为视频添加多个标签
        
        批量为指定视频添加标签，自动跳过已存在的关联。
        
        Args:
            video_id: 视频ID
            tag_ids: 标签ID列表
        
        Returns:
            List[VideoTag]: 新创建的关联对象列表（不包含已存在的）
        
        Note:
            此方法不会抛出重复关联异常，会自动跳过已存在的关联
        """
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
        """
        从视频移除多个标签
        
        批量移除指定视频的标签关联。
        
        Args:
            video_id: 视频ID
            tag_ids: 标签ID列表
        
        Returns:
            int: 实际删除的关联数量
        """
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
        """
        批量为多个视频添加多个标签
        
        为每个视频添加每个标签，自动跳过已存在的关联。
        适用于批量标签操作场景。
        
        Args:
            video_ids: 视频ID列表
            tag_ids: 标签ID列表
        
        Returns:
            int: 新创建的关联数量
        
        Example:
            # 为视频1、2、3添加标签5、6
            count = repo.add_tags_to_videos([1, 2, 3], [5, 6])
            # 最多创建 3 * 2 = 6 个关联
        """
        if not video_ids or not tag_ids:
            return 0
        
        existing_stmt = select(VideoTag).where(
            VideoTag.video_id.in_(video_ids),
            VideoTag.tag_id.in_(tag_ids)
        )
        existing = self.session.execute(existing_stmt).scalars().all()
        existing_set = {(vt.video_id, vt.tag_id) for vt in existing}
        
        new_video_tags = []
        for video_id in video_ids:
            for tag_id in tag_ids:
                if (video_id, tag_id) not in existing_set:
                    new_video_tags.append(VideoTag(video_id=video_id, tag_id=tag_id))
        
        if new_video_tags:
            self.session.add_all(new_video_tags)
            self.session.flush()
        
        return len(new_video_tags)
    
    def remove_tags_from_videos(
        self, 
        video_ids: List[int], 
        tag_ids: List[int]
    ) -> int:
        """
        批量从多个视频移除多个标签
        
        从每个视频移除每个指定的标签关联。
        
        Args:
            video_ids: 视频ID列表
            tag_ids: 标签ID列表
        
        Returns:
            int: 实际删除的关联数量
        """
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
        """
        将源标签的视频关联转移到目标标签
        
        用于标签合并操作，将源标签的所有视频关联转移到目标标签。
        如果视频已有目标标签的关联，则只删除源标签的关联。
        
        Args:
            source_tag_id: 源标签ID（将被删除的标签）
            target_tag_id: 目标标签ID（合并到的标签）
        
        Returns:
            int: 处理的视频数量
        
        Example:
            # 将标签1的视频全部转移到标签2
            count = repo.transfer_video_tags(source_tag_id=1, target_tag_id=2)
            # 之后可以安全删除标签1
        """
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

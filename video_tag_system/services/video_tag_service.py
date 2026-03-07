"""
视频-标签关联业务逻辑层模块

本模块提供视频与标签关联关系的业务逻辑处理，是表现层和数据访问层之间的桥梁。
负责协调多个 Repository 完成复杂的业务操作，处理业务规则验证。

主要功能：
- 视频-标签关联的增删操作
- 批量标签操作（批量添加、批量删除）
- 视频标签设置（替换现有标签）
- 根据标签查询视频
- 关联统计信息

业务规则：
- 添加标签前验证视频和标签是否存在
- 添加已存在的标签不会报错，返回提示信息
- 删除不存在的标签关联不会报错，返回提示信息
- 批量操作时验证所有视频和标签是否存在

使用示例：
    from video_tag_system.services.video_tag_service import VideoTagService
    from video_tag_system.core.database import get_session
    
    with get_session() as session:
        service = VideoTagService(session)
        
        # 为视频添加标签
        result = service.add_tag_to_video(video_id=1, tag_id=5)
        
        # 批量操作
        result = service.batch_add_tags(BatchTagOperation(
            video_ids=[1, 2, 3],
            tag_ids=[5, 6]
        ))
        
        # 获取视频的标签
        tags = service.get_video_tags(video_id=1)

Note:
    服务层方法通常不直接提交事务，事务管理由调用方控制。
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
    """
    视频-标签关联业务逻辑类
    
    提供视频与标签关联关系的业务操作，封装业务规则和数据访问逻辑。
    协调 VideoRepository、TagRepository 和 VideoTagRepository 完成复杂操作。
    
    Attributes:
        session: SQLAlchemy 数据库会话对象
        video_repo: 视频数据访问对象
        tag_repo: 标签数据访问对象
        video_tag_repo: 视频-标签关联数据访问对象
    
    Example:
        service = VideoTagService(session)
        tags = service.get_video_tags(video_id=1)
    """
    
    def __init__(self, session: Session):
        """
        初始化视频-标签关联业务逻辑对象
        
        Args:
            session: SQLAlchemy 数据库会话对象
        """
        self.session = session
        self.video_repo = VideoRepository(session)
        self.tag_repo = TagRepository(session)
        self.video_tag_repo = VideoTagRepository(session)
    
    def add_tag_to_video(self, video_id: int, tag_id: int) -> dict:
        """
        为视频添加标签
        
        建立视频与标签的关联关系，包含以下业务规则：
        1. 验证视频是否存在
        2. 验证标签是否存在
        3. 检查关联是否已存在
        4. 创建新的关联
        
        Args:
            video_id: 视频ID
            tag_id: 标签ID
        
        Returns:
            dict: 操作结果字典
                - video_id: 视频ID
                - tag_id: 标签ID
                - added: 是否添加成功
                - message: 结果消息
        
        Raises:
            VideoNotFoundError: 视频不存在时抛出
            TagNotFoundError: 标签不存在时抛出
        """
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
        """
        从视频移除标签
        
        删除视频与标签的关联关系。
        
        Args:
            video_id: 视频ID
            tag_id: 标签ID
        
        Returns:
            dict: 操作结果字典
                - video_id: 视频ID
                - tag_id: 标签ID
                - removed: 是否移除成功
                - message: 结果消息
        
        Raises:
            VideoNotFoundError: 视频不存在时抛出
            TagNotFoundError: 标签不存在时抛出
        """
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
        """
        获取视频的所有标签
        
        获取与指定视频关联的所有标签信息。
        
        Args:
            video_id: 视频ID
        
        Returns:
            List[TagResponse]: 标签响应对象列表
        
        Raises:
            VideoNotFoundError: 视频不存在时抛出
        """
        video = self.video_repo.get_by_id(video_id)
        if not video:
            raise VideoNotFoundError(video_id=video_id)
        
        tags = self.video_tag_repo.list_tags_by_video(video_id)
        return [TagResponse.model_validate(tag) for tag in tags]
    
    def get_video_tag_ids(self, video_id: int) -> Set[int]:
        """
        获取视频的所有标签ID
        
        只返回标签ID集合，比 get_video_tags 更轻量。
        用于快速判断视频是否有特定标签。
        
        Args:
            video_id: 视频ID
        
        Returns:
            Set[int]: 标签ID集合
        
        Raises:
            VideoNotFoundError: 视频不存在时抛出
        """
        video = self.video_repo.get_by_id(video_id)
        if not video:
            raise VideoNotFoundError(video_id=video_id)
        
        return self.video_tag_repo.list_tag_ids_by_video(video_id)
    
    def set_video_tags(self, video_id: int, tag_ids: List[int]) -> dict:
        """
        设置视频的标签（替换现有标签）
        
        将视频的标签设置为指定的标签列表，会：
        1. 移除不在新列表中的标签
        2. 添加新列表中缺少的标签
        
        Args:
            video_id: 视频ID
            tag_ids: 新的标签ID列表
        
        Returns:
            dict: 操作结果字典
                - video_id: 视频ID
                - tags_added: 添加的标签数量
                - tags_removed: 移除的标签数量
                - current_tag_count: 当前标签总数
        
        Raises:
            VideoNotFoundError: 视频不存在时抛出
            TagNotFoundError: 标签不存在时抛出
        """
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
        """
        批量为视频添加标签
        
        为多个视频同时添加多个标签，自动跳过已存在的关联。
        
        Args:
            operation: 批量操作数据模型
                - video_ids: 视频ID列表
                - tag_ids: 标签ID列表
        
        Returns:
            dict: 操作结果字典
                - videos_affected: 受影响的视频数量
                - tags_added: 添加的关联数量
                - message: 结果消息
        
        Raises:
            VideoNotFoundError: 视频不存在时抛出
            TagNotFoundError: 标签不存在时抛出
        
        Example:
            result = service.batch_add_tags(BatchTagOperation(
                video_ids=[1, 2, 3],
                tag_ids=[5, 6]
            ))
            # 最多创建 3 * 2 = 6 个关联
        """
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
        """
        批量从视频移除标签
        
        从多个视频同时移除多个标签。
        
        Args:
            operation: 批量操作数据模型
                - video_ids: 视频ID列表
                - tag_ids: 标签ID列表
        
        Returns:
            dict: 操作结果字典
                - videos_affected: 受影响的视频数量
                - tags_removed: 移除的关联数量
                - message: 结果消息
        
        Raises:
            VideoNotFoundError: 视频不存在时抛出
            TagNotFoundError: 标签不存在时抛出
        """
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
        """
        根据标签获取视频ID列表
        
        查询包含指定标签的视频ID列表，支持两种匹配模式：
        - match_all=False: 视频包含任意一个标签即可（OR 关系）
        - match_all=True: 视频必须包含所有标签（AND 关系）
        
        Args:
            tag_ids: 标签ID列表
            match_all: 是否必须匹配所有标签
        
        Returns:
            List[int]: 视频ID列表
        
        Raises:
            TagNotFoundError: 标签不存在时抛出
        """
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
        """
        获取标签关联的视频数量
        
        统计与指定标签关联的视频数量。
        
        Args:
            tag_id: 标签ID
        
        Returns:
            int: 视频数量
        
        Raises:
            TagNotFoundError: 标签不存在时抛出
        """
        if not self.tag_repo.get_by_id(tag_id):
            raise TagNotFoundError(tag_id=tag_id)
        
        return self.video_tag_repo.count_by_tag(tag_id)
    
    def get_video_tag_count(self, video_id: int) -> int:
        """
        获取视频关联的标签数量
        
        统计与指定视频关联的标签数量。
        
        Args:
            video_id: 视频ID
        
        Returns:
            int: 标签数量
        
        Raises:
            VideoNotFoundError: 视频不存在时抛出
        """
        if not self.video_repo.get_by_id(video_id):
            raise VideoNotFoundError(video_id=video_id)
        
        return self.video_tag_repo.count_by_video(video_id)
    
    def check_video_has_tag(self, video_id: int, tag_id: int) -> bool:
        """
        检查视频是否有指定标签
        
        快速判断视频是否已关联指定标签。
        
        Args:
            video_id: 视频ID
            tag_id: 标签ID
        
        Returns:
            bool: 存在关联返回 True，不存在返回 False
        
        Raises:
            VideoNotFoundError: 视频不存在时抛出
            TagNotFoundError: 标签不存在时抛出
        """
        if not self.video_repo.get_by_id(video_id):
            raise VideoNotFoundError(video_id=video_id)
        if not self.tag_repo.get_by_id(tag_id):
            raise TagNotFoundError(tag_id=tag_id)
        
        return self.video_tag_repo.exists(video_id, tag_id)
    
    def count_associations(self) -> int:
        """
        获取所有视频-标签关联总数
        
        统计数据库中所有关联记录的数量。
        
        Returns:
            int: 关联总数
        """
        from sqlalchemy import func
        from video_tag_system.models.video_tag import VideoTag
        
        result = self.session.execute(
            select(func.count()).select_from(VideoTag)
        ).scalar()
        
        return result or 0

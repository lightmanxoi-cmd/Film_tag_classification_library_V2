"""
视频业务逻辑层模块

本模块提供视频相关的业务逻辑处理，是表现层和数据访问层之间的桥梁。
负责协调多个 Repository 完成复杂的业务操作，处理业务规则验证。

主要功能：
- 视频的 CRUD 业务操作（创建、读取、更新、删除）
- 视频列表查询（支持分页、搜索、随机排序）
- 根据标签筛选视频（支持简单筛选和高级筛选）
- 视频数据格式转换（ORM 模型转响应模型）

业务规则：
- 创建视频时检查文件路径是否重复
- 删除视频时级联删除相关的标签关联
- 分页参数有默认值和边界限制

使用示例：
    from video_tag_system.services.video_service import VideoService
    from video_tag_system.core.database import get_session
    
    with get_session() as session:
        service = VideoService(session)
        
        # 创建视频
        video = service.create_video(VideoCreate(file_path="/path/to/video.mp4"))
        
        # 分页查询
        result = service.list_videos(page=1, page_size=20)
        
        # 按标签筛选
        result = service.list_videos_by_tags([1, 2, 3])

Note:
    服务层方法通常不直接提交事务，事务管理由调用方控制。
    这允许在单个事务中执行多个操作，支持回滚。
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
    """
    视频业务逻辑类
    
    提供视频相关的业务操作，封装业务规则和数据访问逻辑。
    协调 VideoRepository 和 VideoTagRepository 完成复杂操作。
    
    Attributes:
        session: SQLAlchemy 数据库会话对象
        video_repo: 视频数据访问对象
        video_tag_repo: 视频-标签关联数据访问对象
    
    Example:
        service = VideoService(session)
        video = service.get_video(1)
    """
    
    def __init__(self, session: Session):
        """
        初始化视频业务逻辑对象
        
        Args:
            session: SQLAlchemy 数据库会话对象
        """
        self.session = session
        self.video_repo = VideoRepository(session)
        self.video_tag_repo = VideoTagRepository(session)
    
    def create_video(self, video_data: VideoCreate) -> VideoResponse:
        """
        创建视频
        
        创建新的视频记录，包含以下业务规则：
        1. 检查文件路径是否已存在（防止重复）
        2. 创建视频记录
        3. 返回包含标签的响应对象
        
        Args:
            video_data: 视频创建数据模型
        
        Returns:
            VideoResponse: 创建的视频响应对象
        
        Raises:
            DuplicateVideoError: 文件路径已存在时抛出
        """
        if self.video_repo.exists_by_file_path(video_data.file_path):
            existing = self.video_repo.get_by_file_path(video_data.file_path)
            raise DuplicateVideoError(video_data.file_path, existing.id if existing else None)
        
        video = self.video_repo.create(video_data)
        return self._to_response(video)
    
    def get_video(self, video_id: int) -> VideoResponse:
        """
        获取视频详情
        
        获取指定视频的详细信息，包括关联的标签列表。
        
        Args:
            video_id: 视频ID
        
        Returns:
            VideoResponse: 视频响应对象，包含标签列表
        
        Raises:
            VideoNotFoundError: 视频不存在时抛出
        """
        video = self.video_repo.get_by_id_with_tags(video_id)
        if not video:
            raise VideoNotFoundError(video_id=video_id)
        return self._to_response(video)
    
    def get_video_by_path(self, file_path: str) -> VideoResponse:
        """
        根据文件路径获取视频
        
        通过文件路径查找视频，用于检查视频是否已导入。
        
        Args:
            file_path: 视频文件路径
        
        Returns:
            VideoResponse: 视频响应对象
        
        Raises:
            VideoNotFoundError: 视频不存在时抛出
        """
        video = self.video_repo.get_by_file_path(file_path)
        if not video:
            raise VideoNotFoundError(file_path=file_path)
        return self._to_response(video)
    
    def update_video(self, video_id: int, video_data: VideoUpdate) -> VideoResponse:
        """
        更新视频信息
        
        更新指定视频的信息，只更新提供的字段。
        
        Args:
            video_id: 视频ID
            video_data: 更新数据模型（所有字段可选）
        
        Returns:
            VideoResponse: 更新后的视频响应对象
        
        Raises:
            VideoNotFoundError: 视频不存在时抛出
        """
        video = self.video_repo.get_by_id(video_id)
        if not video:
            raise VideoNotFoundError(video_id=video_id)
        
        video = self.video_repo.update(video, video_data)
        return self._to_response(video)
    
    def delete_video(self, video_id: int) -> bool:
        """
        删除视频
        
        删除指定视频及其所有关联的标签关系。
        
        Args:
            video_id: 视频ID
        
        Returns:
            bool: 删除成功返回 True
        
        Raises:
            VideoNotFoundError: 视频不存在时抛出
        
        Note:
            关联的 VideoTag 记录会被级联删除
        """
        video = self.video_repo.get_by_id(video_id)
        if not video:
            raise VideoNotFoundError(video_id=video_id)
        
        self.video_repo.delete(video)
        return True
    
    def list_videos(
        self,
        page: int = 1,
        page_size: int = 20,
        search: Optional[str] = None,
        random_order: bool = False,
        random_seed: Optional[int] = None
    ) -> VideoListResponse:
        """
        获取视频列表
        
        分页获取视频列表，支持搜索和随机排序。
        
        Args:
            page: 页码，从1开始，小于1时自动设为1
            page_size: 每页记录数，范围1-100，超出范围时设为默认值20
            search: 搜索关键词，匹配标题、描述、文件路径
            random_order: 是否随机排序
            random_seed: 随机种子，用于复现随机排序结果
        
        Returns:
            VideoListResponse: 分页响应对象，包含视频列表和分页信息
        """
        if page < 1:
            page = 1
        if page_size < 1 or page_size > 50000:
            page_size = 20
        
        videos, total = self.video_repo.list_all(
            page=page,
            page_size=page_size,
            search=search,
            random_order=random_order,
            random_seed=random_seed
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
        match_all: bool = False,
        random_order: bool = False,
        random_seed: Optional[int] = None
    ) -> VideoListResponse:
        """
        根据标签筛选视频
        
        获取包含指定标签的视频列表，支持两种匹配模式：
        - match_all=False: 视频包含任意一个标签即可（OR 关系）
        - match_all=True: 视频必须包含所有标签（AND 关系）
        
        Args:
            tag_ids: 标签ID列表
            page: 页码
            page_size: 每页记录数
            match_all: 是否必须匹配所有标签
            random_order: 是否随机排序
            random_seed: 随机种子，用于复现随机排序结果
        
        Returns:
            VideoListResponse: 分页响应对象
        """
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
        if page_size < 1 or page_size > 50000:
            page_size = 20
        
        videos, total = self.video_repo.list_by_tag_ids(
            tag_ids=tag_ids,
            page=page,
            page_size=page_size,
            match_all=match_all,
            random_order=random_order,
            random_seed=random_seed
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
    
    def list_videos_by_tags_advanced(
        self,
        tags_by_category: dict,
        page: int = 1,
        page_size: int = 20,
        random_order: bool = False,
        random_seed: Optional[int] = None
    ) -> VideoListResponse:
        """
        高级标签筛选视频
        
        支持按标签分类进行组合筛选：
        - 同一分类下的标签为 OR 关系（满足任一即可）
        - 不同分类间为 AND 关系（必须都满足）
        
        例如：筛选"动作片或喜剧片"且"中国大陆或香港"的视频
        
        Args:
            tags_by_category: 分类标签字典
                格式: {category_id: [tag_id1, tag_id2, ...], ...}
            page: 页码
            page_size: 每页数量
            random_order: 是否随机排序
            random_seed: 随机种子，用于复现随机排序结果
        
        Returns:
            VideoListResponse: 分页响应对象
        
        Example:
            result = service.list_videos_by_tags_advanced({
                1: [1, 2],  # 分类1：动作或喜剧
                2: [5, 6]   # 分类2：大陆或香港
            })
        """
        if not tags_by_category:
            return VideoListResponse(
                items=[],
                total=0,
                page=page,
                page_size=page_size,
                total_pages=0
            )
        
        if page < 1:
            page = 1
        if page_size < 1 or page_size > 50000:
            page_size = 20
        
        videos, total = self.video_repo.list_by_tags_advanced(
            tags_by_category=tags_by_category,
            page=page,
            page_size=page_size,
            random_order=random_order,
            random_seed=random_seed
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
        """
        获取视频的所有标签
        
        获取与指定视频关联的所有标签。
        
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
    
    def search_videos(
        self,
        keyword: str,
        page: int = 1,
        page_size: int = 20
    ) -> VideoListResponse:
        """
        搜索视频
        
        根据关键词搜索视频，匹配标题、描述和文件路径。
        
        Args:
            keyword: 搜索关键词
            page: 页码
            page_size: 每页记录数
        
        Returns:
            VideoListResponse: 分页响应对象
        """
        return self.list_videos(
            page=page,
            page_size=page_size,
            search=keyword
        )
    
    def count_videos(self) -> int:
        """
        获取视频总数
        
        Returns:
            int: 视频总记录数
        """
        return self.video_repo.count_all()
    
    def check_video_exists(self, video_id: int) -> bool:
        """
        检查视频是否存在
        
        Args:
            video_id: 视频ID
        
        Returns:
            bool: 存在返回 True，不存在返回 False
        """
        return self.video_repo.get_by_id(video_id) is not None
    
    def _to_response(self, video: Video) -> VideoResponse:
        """
        将 ORM 模型转换为响应模型
        
        提取视频数据并加载关联的标签，转换为 API 响应格式。
        
        Args:
            video: 视频 ORM 对象
        
        Returns:
            VideoResponse: 视频响应对象
        """
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

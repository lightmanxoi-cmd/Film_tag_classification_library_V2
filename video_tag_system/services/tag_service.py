"""
标签业务逻辑层模块

本模块提供标签相关的业务逻辑处理，是表现层和数据访问层之间的桥梁。
负责协调多个 Repository 完成复杂的业务操作，处理业务规则验证。

主要功能：
- 标签的 CRUD 业务操作（创建、读取、更新、删除）
- 标签树结构管理（支持两级标签）
- 标签合并功能
- 标签统计信息

业务规则：
- 标签层级最多支持两级（一级标签和二级标签）
- 同一父标签下标签名称不能重复
- 有子标签的标签不能直接删除
- 有子标签的标签不能变为二级标签
- 标签合并只能合并同级标签

使用示例：
    from video_tag_system.services.tag_service import TagService
    from video_tag_system.core.database import get_session
    
    with get_session() as session:
        service = TagService(session)
        
        # 创建一级标签
        tag = service.create_tag(TagCreate(name="电影类型"))
        
        # 创建二级标签
        child = service.create_tag(TagCreate(name="动作", parent_id=tag.id))
        
        # 获取标签树
        tree = service.get_tag_tree()

Note:
    服务层方法通常不直接提交事务，事务管理由调用方控制。
"""
import math
from typing import Optional, List

from sqlalchemy.orm import Session

from video_tag_system.models.tag import (
    Tag, TagCreate, TagUpdate, TagResponse, TagTreeResponse, TagMergeRequest
)
from video_tag_system.repositories.tag_repository import TagRepository
from video_tag_system.repositories.video_tag_repository import VideoTagRepository
from video_tag_system.exceptions import (
    TagNotFoundError,
    DuplicateTagError,
    TagMergeError,
    ValidationError,
)


class TagService:
    """
    标签业务逻辑类
    
    提供标签相关的业务操作，封装业务规则和数据访问逻辑。
    协调 TagRepository 和 VideoTagRepository 完成复杂操作。
    
    Attributes:
        session: SQLAlchemy 数据库会话对象
        tag_repo: 标签数据访问对象
        video_tag_repo: 视频-标签关联数据访问对象
        MAX_LEVEL: 最大标签层级（当前为2级）
    
    Example:
        service = TagService(session)
        tag = service.get_tag(1)
    """
    
    MAX_LEVEL = 2
    
    def __init__(self, session: Session):
        """
        初始化标签业务逻辑对象
        
        Args:
            session: SQLAlchemy 数据库会话对象
        """
        self.session = session
        self.tag_repo = TagRepository(session)
        self.video_tag_repo = VideoTagRepository(session)
    
    def create_tag(self, tag_data: TagCreate) -> TagResponse:
        """
        创建标签
        
        创建新的标签，包含以下业务规则：
        1. 如果指定了父标签，验证父标签存在且为一级标签
        2. 检查同一父标签下是否已存在同名标签
        3. 创建标签记录
        
        Args:
            tag_data: 标签创建数据模型
        
        Returns:
            TagResponse: 创建的标签响应对象
        
        Raises:
            TagNotFoundError: 父标签不存在时抛出
            ValidationError: 父标签是二级标签（不支持三级标签）时抛出
            DuplicateTagError: 同一父标签下已存在同名标签时抛出
        """
        if tag_data.parent_id:
            parent = self.tag_repo.get_by_id(tag_data.parent_id)
            if not parent:
                raise TagNotFoundError(tag_id=tag_data.parent_id)
            if parent.parent_id is not None:
                raise ValidationError(
                    "parent_id",
                    tag_data.parent_id,
                    "不支持超过两级的标签结构"
                )
        
        if self.tag_repo.exists_by_name_and_parent(tag_data.name, tag_data.parent_id):
            raise DuplicateTagError(tag_data.name, tag_data.parent_id)
        
        tag = self.tag_repo.create(tag_data)
        return self._to_response(tag)
    
    def get_tag(self, tag_id: int) -> TagResponse:
        """
        获取标签详情
        
        获取指定标签的详细信息，包括子标签列表。
        
        Args:
            tag_id: 标签ID
        
        Returns:
            TagResponse: 标签响应对象，包含子标签列表
        
        Raises:
            TagNotFoundError: 标签不存在时抛出
        """
        tag = self.tag_repo.get_by_id_with_children(tag_id)
        if not tag:
            raise TagNotFoundError(tag_id=tag_id)
        return self._to_response(tag)
    
    def get_tag_by_name(
        self, 
        name: str, 
        parent_id: Optional[int] = None,
        parent_name: Optional[str] = None
    ) -> TagResponse:
        """
        根据名称获取标签
        
        通过标签名称和父标签ID或名称查找标签。
        
        Args:
            name: 标签名称
            parent_id: 父标签ID，None 表示一级标签
            parent_name: 父标签名称，与 parent_id 二选一
        
        Returns:
            TagResponse: 标签响应对象
        
        Raises:
            TagNotFoundError: 标签不存在时抛出
        """
        if parent_name and not parent_id:
            parent_tag = self.tag_repo.get_by_name_and_parent(parent_name, None)
            if parent_tag:
                parent_id = parent_tag.id
        
        tag = self.tag_repo.get_by_name_and_parent(name, parent_id)
        if not tag:
            raise TagNotFoundError(tag_name=name)
        return self._to_response(tag)
    
    def update_tag(self, tag_id: int, tag_data: TagUpdate) -> TagResponse:
        """
        更新标签信息
        
        更新指定标签的信息，包含以下业务规则：
        1. 不能将标签的父标签设为自己
        2. 新的父标签必须存在且为一级标签
        3. 有子标签的标签不能变为二级标签
        4. 更新名称时检查是否与同级标签重复
        
        Args:
            tag_id: 标签ID
            tag_data: 更新数据模型（所有字段可选）
        
        Returns:
            TagResponse: 更新后的标签响应对象
        
        Raises:
            TagNotFoundError: 标签或父标签不存在时抛出
            ValidationError: 违反业务规则时抛出
            DuplicateTagError: 名称与同级标签重复时抛出
        """
        tag = self.tag_repo.get_by_id(tag_id)
        if not tag:
            raise TagNotFoundError(tag_id=tag_id)
        
        update_data = tag_data.model_dump(exclude_unset=True)
        
        if "parent_id" in update_data:
            new_parent_id = update_data["parent_id"]
            if new_parent_id is not None:
                if new_parent_id == tag_id:
                    raise ValidationError(
                        "parent_id",
                        new_parent_id,
                        "标签不能以自己为父标签"
                    )
                
                parent = self.tag_repo.get_by_id(new_parent_id)
                if not parent:
                    raise TagNotFoundError(tag_id=new_parent_id)
                
                if parent.parent_id is not None:
                    raise ValidationError(
                        "parent_id",
                        new_parent_id,
                        "不支持超过两级的标签结构"
                    )
                
                if self.tag_repo.count_children(tag_id) > 0:
                    raise ValidationError(
                        "parent_id",
                        new_parent_id,
                        "有子标签的标签不能变为二级标签"
                    )
        
        if "name" in update_data:
            parent_id = update_data.get("parent_id", tag.parent_id)
            if self.tag_repo.exists_by_name_and_parent(update_data["name"], parent_id):
                existing = self.tag_repo.get_by_name_and_parent(update_data["name"], parent_id)
                if existing and existing.id != tag_id:
                    raise DuplicateTagError(update_data["name"], parent_id)
        
        tag = self.tag_repo.update(tag, tag_data)
        return self._to_response(tag)
    
    def delete_tag(self, tag_id: int) -> bool:
        """
        删除标签
        
        删除指定标签，包含以下业务规则：
        1. 标签必须存在
        2. 标签不能有子标签（需要先删除子标签）
        
        Args:
            tag_id: 标签ID
        
        Returns:
            bool: 删除成功返回 True
        
        Raises:
            TagNotFoundError: 标签不存在时抛出
            ValidationError: 标签有子标签时抛出
        
        Note:
            关联的 VideoTag 记录会被级联删除
        """
        tag = self.tag_repo.get_by_id(tag_id)
        if not tag:
            raise TagNotFoundError(tag_id=tag_id)
        
        children_count = self.tag_repo.count_children(tag_id)
        if children_count > 0:
            raise ValidationError(
                "tag_id",
                tag_id,
                f"该标签下有 {children_count} 个子标签，请先删除子标签"
            )
        
        self.tag_repo.delete(tag)
        return True
    
    def list_tags(
        self,
        page: int = 1,
        page_size: int = 50,
        search: Optional[str] = None,
        parent_id: Optional[int] = None
    ) -> dict:
        """
        获取标签列表
        
        分页获取标签列表，支持搜索和层级筛选。
        
        Args:
            page: 页码，从1开始
            page_size: 每页记录数，范围1-200
            search: 搜索关键词，匹配名称和描述
            parent_id: 父标签ID筛选
        
        Returns:
            dict: 包含 items、total、page、page_size、total_pages 的字典
        """
        if page < 1:
            page = 1
        if page_size < 1 or page_size > 200:
            page_size = 50
        
        tags, total = self.tag_repo.list_all(
            page=page,
            page_size=page_size,
            search=search,
            parent_id=parent_id
        )
        
        items = [self._to_response(tag) for tag in tags]
        total_pages = math.ceil(total / page_size) if total > 0 else 1
        
        return {
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages
        }
    
    def get_tag_tree(self) -> TagTreeResponse:
        """
        获取完整标签树
        
        返回所有一级标签及其子标签，构建完整的标签树结构。
        
        Returns:
            TagTreeResponse: 标签树响应对象
        """
        root_tags = self.tag_repo.get_tag_tree()
        items = [self._to_response_with_children(tag) for tag in root_tags]
        total = self.tag_repo.count_all()
        
        return TagTreeResponse(items=items, total=total)
    
    def list_root_tags(self) -> List[TagResponse]:
        """
        获取所有一级标签
        
        获取所有 parent_id 为 NULL 的标签，包含子标签。
        
        Returns:
            List[TagResponse]: 一级标签响应对象列表
        """
        tags = self.tag_repo.list_root_tags()
        return [self._to_response_with_children(tag) for tag in tags]
    
    def list_children(self, parent_id: int) -> List[TagResponse]:
        """
        获取指定标签的子标签
        
        获取指定父标签下的所有二级标签。
        
        Args:
            parent_id: 父标签ID
        
        Returns:
            List[TagResponse]: 子标签响应对象列表
        
        Raises:
            TagNotFoundError: 父标签不存在时抛出
        """
        parent = self.tag_repo.get_by_id(parent_id)
        if not parent:
            raise TagNotFoundError(tag_id=parent_id)
        
        children = self.tag_repo.list_children(parent_id)
        return [self._to_response(tag) for tag in children]
    
    def merge_tags(self, merge_data: TagMergeRequest) -> dict:
        """
        合并标签
        
        将源标签的所有视频关联转移到目标标签，然后删除源标签。
        包含以下业务规则：
        1. 源标签和目标标签不能相同
        2. 两个标签必须存在
        3. 只能合并同级标签
        4. 源标签不能有子标签
        
        Args:
            merge_data: 标签合并请求数据
        
        Returns:
            dict: 包含合并结果的字典
                - source_tag_id: 源标签ID
                - target_tag_id: 目标标签ID
                - transferred_relations: 转移的关联数量
                - deleted_source_tag: 是否删除了源标签
        
        Raises:
            TagMergeError: 违反合并规则时抛出
            TagNotFoundError: 标签不存在时抛出
        """
        source_id = merge_data.source_tag_id
        target_id = merge_data.target_tag_id
        
        if source_id == target_id:
            raise TagMergeError(source_id, target_id, "源标签和目标标签不能相同")
        
        source_tag = self.tag_repo.get_by_id(source_id)
        if not source_tag:
            raise TagNotFoundError(tag_id=source_id)
        
        target_tag = self.tag_repo.get_by_id(target_id)
        if not target_tag:
            raise TagNotFoundError(tag_id=target_id)
        
        if source_tag.parent_id != target_tag.parent_id:
            raise TagMergeError(
                source_id, 
                target_id, 
                "只能合并同级标签"
            )
        
        if self.tag_repo.count_children(source_id) > 0:
            raise TagMergeError(
                source_id,
                target_id,
                "源标签有子标签，请先处理子标签"
            )
        
        transferred_count = self.video_tag_repo.transfer_video_tags(source_id, target_id)
        
        source_video_count = self.video_tag_repo.count_by_tag(source_id)
        
        self.tag_repo.delete(source_tag)
        
        return {
            "source_tag_id": source_id,
            "target_tag_id": target_id,
            "transferred_relations": transferred_count,
            "deleted_source_tag": True
        }
    
    def get_tag_statistics(self, tag_id: int) -> dict:
        """
        获取标签统计信息
        
        获取指定标签的视频数量和子标签数量。
        
        Args:
            tag_id: 标签ID
        
        Returns:
            dict: 统计信息字典
                - tag_id: 标签ID
                - tag_name: 标签名称
                - level: 标签层级
                - video_count: 关联的视频数量
                - children_count: 子标签数量
        
        Raises:
            TagNotFoundError: 标签不存在时抛出
        """
        tag = self.tag_repo.get_by_id(tag_id)
        if not tag:
            raise TagNotFoundError(tag_id=tag_id)
        
        video_count = self.video_tag_repo.count_by_tag(tag_id)
        children_count = self.tag_repo.count_children(tag_id)
        
        return {
            "tag_id": tag_id,
            "tag_name": tag.name,
            "level": tag.level,
            "video_count": video_count,
            "children_count": children_count
        }
    
    def count_tags(self) -> int:
        """
        获取标签总数
        
        Returns:
            int: 标签总记录数
        """
        return self.tag_repo.count_all()
    
    def check_tag_exists(self, tag_id: int) -> bool:
        """
        检查标签是否存在
        
        Args:
            tag_id: 标签ID
        
        Returns:
            bool: 存在返回 True，不存在返回 False
        """
        return self.tag_repo.get_by_id(tag_id) is not None
    
    def _to_response(self, tag: Tag) -> TagResponse:
        """
        将 ORM 模型转换为响应模型（不包含子标签）
        
        Args:
            tag: 标签 ORM 对象
        
        Returns:
            TagResponse: 标签响应对象
        """
        return TagResponse(
            id=tag.id,
            name=tag.name,
            parent_id=tag.parent_id,
            description=tag.description,
            sort_order=tag.sort_order,
            level=tag.level,
            created_at=tag.created_at,
            updated_at=tag.updated_at,
            children=[]
        )
    
    def _to_response_with_children(self, tag: Tag) -> TagResponse:
        """
        将 ORM 模型转换为响应模型（包含子标签）
        
        递归加载子标签，构建完整的标签树结构。
        
        Args:
            tag: 标签 ORM 对象
        
        Returns:
            TagResponse: 包含子标签的标签响应对象
        """
        children = []
        if tag.children:
            children = [self._to_response(child) for child in tag.children]
        
        return TagResponse(
            id=tag.id,
            name=tag.name,
            parent_id=tag.parent_id,
            description=tag.description,
            sort_order=tag.sort_order,
            level=tag.level,
            created_at=tag.created_at,
            updated_at=tag.updated_at,
            children=children
        )

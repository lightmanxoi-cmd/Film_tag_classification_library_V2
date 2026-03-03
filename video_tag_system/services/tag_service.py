"""
标签业务逻辑层
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
    """标签业务逻辑类"""
    
    MAX_LEVEL = 2
    
    def __init__(self, session: Session):
        self.session = session
        self.tag_repo = TagRepository(session)
        self.video_tag_repo = VideoTagRepository(session)
    
    def create_tag(self, tag_data: TagCreate) -> TagResponse:
        """创建标签"""
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
        """获取标签详情"""
        tag = self.tag_repo.get_by_id_with_children(tag_id)
        if not tag:
            raise TagNotFoundError(tag_id=tag_id)
        return self._to_response(tag)
    
    def get_tag_by_name(
        self, 
        name: str, 
        parent_id: Optional[int] = None
    ) -> TagResponse:
        """根据名称获取标签"""
        tag = self.tag_repo.get_by_name_and_parent(name, parent_id)
        if not tag:
            raise TagNotFoundError(tag_name=name)
        return self._to_response(tag)
    
    def update_tag(self, tag_id: int, tag_data: TagUpdate) -> TagResponse:
        """更新标签"""
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
        """删除标签"""
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
        """获取标签列表"""
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
        """获取完整标签树"""
        root_tags = self.tag_repo.get_tag_tree()
        items = [self._to_response_with_children(tag) for tag in root_tags]
        total = self.tag_repo.count_all()
        
        return TagTreeResponse(items=items, total=total)
    
    def list_root_tags(self) -> List[TagResponse]:
        """获取所有一级标签"""
        tags = self.tag_repo.list_root_tags()
        return [self._to_response_with_children(tag) for tag in tags]
    
    def list_children(self, parent_id: int) -> List[TagResponse]:
        """获取指定标签的子标签"""
        parent = self.tag_repo.get_by_id(parent_id)
        if not parent:
            raise TagNotFoundError(tag_id=parent_id)
        
        children = self.tag_repo.list_children(parent_id)
        return [self._to_response(tag) for tag in children]
    
    def merge_tags(self, merge_data: TagMergeRequest) -> dict:
        """合并标签"""
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
        """获取标签统计信息"""
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
        """获取标签总数"""
        return self.tag_repo.count_all()
    
    def check_tag_exists(self, tag_id: int) -> bool:
        """检查标签是否存在"""
        return self.tag_repo.get_by_id(tag_id) is not None
    
    def _to_response(self, tag: Tag) -> TagResponse:
        """将ORM模型转换为响应模型"""
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
        """将ORM模型转换为响应模型（包含子标签）"""
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

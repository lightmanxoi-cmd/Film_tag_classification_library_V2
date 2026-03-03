"""
标签数据访问层
"""
from typing import Optional, List, Tuple
from sqlalchemy import select, func, or_
from sqlalchemy.orm import Session, joinedload

from video_tag_system.models.tag import Tag, TagCreate, TagUpdate


class TagRepository:
    """标签数据访问类"""
    
    def __init__(self, session: Session):
        self.session = session
    
    def create(self, tag_data: TagCreate) -> Tag:
        """创建标签"""
        tag = Tag(**tag_data.model_dump())
        self.session.add(tag)
        self.session.flush()
        return tag
    
    def get_by_id(self, tag_id: int) -> Optional[Tag]:
        """根据ID获取标签"""
        return self.session.get(Tag, tag_id)
    
    def get_by_id_with_children(self, tag_id: int) -> Optional[Tag]:
        """根据ID获取标签（包含子标签）"""
        stmt = (
            select(Tag)
            .options(joinedload(Tag.children))
            .where(Tag.id == tag_id)
        )
        return self.session.execute(stmt).unique().scalar_one_or_none()
    
    def get_by_name_and_parent(
        self, 
        name: str, 
        parent_id: Optional[int] = None
    ) -> Optional[Tag]:
        """根据名称和父标签ID获取标签"""
        stmt = select(Tag).where(
            Tag.name == name,
            Tag.parent_id == parent_id
        )
        return self.session.execute(stmt).scalar_one_or_none()
    
    def update(self, tag: Tag, tag_data: TagUpdate) -> Tag:
        """更新标签"""
        update_data = tag_data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(tag, key, value)
        self.session.flush()
        return tag
    
    def delete(self, tag: Tag) -> None:
        """删除标签"""
        self.session.delete(tag)
        self.session.flush()
    
    def delete_by_id(self, tag_id: int) -> bool:
        """根据ID删除标签"""
        tag = self.get_by_id(tag_id)
        if tag:
            self.delete(tag)
            return True
        return False
    
    def list_all(
        self,
        page: int = 1,
        page_size: int = 50,
        search: Optional[str] = None,
        parent_id: Optional[int] = None
    ) -> Tuple[List[Tag], int]:
        """获取标签列表"""
        stmt = select(Tag)
        count_stmt = select(func.count(Tag.id))
        
        if parent_id is not None:
            stmt = stmt.where(Tag.parent_id == parent_id)
            count_stmt = count_stmt.where(Tag.parent_id == parent_id)
        
        if search:
            search_pattern = f"%{search}%"
            search_filter = or_(
                Tag.name.ilike(search_pattern),
                Tag.description.ilike(search_pattern)
            )
            stmt = stmt.where(search_filter)
            count_stmt = count_stmt.where(search_filter)
        
        total = self.session.execute(count_stmt).scalar()
        
        stmt = stmt.order_by(Tag.sort_order, Tag.created_at)
        stmt = stmt.offset((page - 1) * page_size).limit(page_size)
        
        tags = list(self.session.execute(stmt).scalars().all())
        
        return tags, total
    
    def list_root_tags(self) -> List[Tag]:
        """获取所有一级标签"""
        stmt = (
            select(Tag)
            .options(joinedload(Tag.children))
            .where(Tag.parent_id.is_(None))
            .order_by(Tag.sort_order, Tag.created_at)
        )
        return list(self.session.execute(stmt).unique().scalars().all())
    
    def list_children(self, parent_id: int) -> List[Tag]:
        """获取指定标签的子标签"""
        stmt = (
            select(Tag)
            .where(Tag.parent_id == parent_id)
            .order_by(Tag.sort_order, Tag.created_at)
        )
        return list(self.session.execute(stmt).scalars().all())
    
    def get_tag_tree(self) -> List[Tag]:
        """获取完整标签树"""
        root_tags = self.list_root_tags()
        return root_tags
    
    def exists_by_name_and_parent(
        self, 
        name: str, 
        parent_id: Optional[int] = None
    ) -> bool:
        """检查标签是否存在"""
        stmt = select(func.count(Tag.id)).where(
            Tag.name == name,
            Tag.parent_id == parent_id
        )
        return self.session.execute(stmt).scalar() > 0
    
    def count_all(self) -> int:
        """获取标签总数"""
        return self.session.execute(select(func.count(Tag.id))).scalar()
    
    def count_children(self, parent_id: int) -> int:
        """获取子标签数量"""
        stmt = select(func.count(Tag.id)).where(Tag.parent_id == parent_id)
        return self.session.execute(stmt).scalar()
    
    def get_by_ids(self, tag_ids: List[int]) -> List[Tag]:
        """根据ID列表获取标签"""
        if not tag_ids:
            return []
        stmt = select(Tag).where(Tag.id.in_(tag_ids))
        return list(self.session.execute(stmt).scalars().all())
    
    def get_siblings(
        self, 
        tag_id: int, 
        parent_id: Optional[int] = None
    ) -> List[Tag]:
        """获取同级标签"""
        stmt = (
            select(Tag)
            .where(Tag.parent_id == parent_id, Tag.id != tag_id)
            .order_by(Tag.sort_order, Tag.created_at)
        )
        return list(self.session.execute(stmt).scalars().all())

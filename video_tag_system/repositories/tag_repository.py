"""
标签数据访问层模块

本模块提供标签数据的持久化操作，封装了所有与标签相关的数据库操作。
采用 Repository 模式，将数据访问逻辑与业务逻辑分离。

主要功能：
- 标签的 CRUD 操作（创建、读取、更新、删除）
- 标签列表查询（支持分页、搜索、层级筛选）
- 标签树结构获取
- 标签存在性检查

使用示例：
    from video_tag_system.repositories.tag_repository import TagRepository
    from video_tag_system.core.database import get_session
    
    with get_session() as session:
        repo = TagRepository(session)
        
        # 创建标签
        tag = repo.create(TagCreate(name="动作"))
        
        # 获取标签树
        tree = repo.get_tag_tree()
        
        # 获取一级标签
        root_tags = repo.list_root_tags()

Note:
    所有方法都需要传入 SQLAlchemy Session 对象。
    方法内部使用 flush() 而非 commit()，事务管理由调用方控制。
"""
from typing import Optional, List, Tuple
from sqlalchemy import select, func, or_
from sqlalchemy.orm import Session, joinedload

from video_tag_system.models.tag import Tag, TagCreate, TagUpdate


class TagRepository:
    """
    标签数据访问类
    
    提供标签数据的增删改查操作，封装所有与 tags 表相关的数据库操作。
    支持标签的层级结构管理。
    
    Attributes:
        session: SQLAlchemy 数据库会话对象
    
    Thread Safety:
        本类不是线程安全的，每个线程应使用独立的 Session 和 Repository 实例。
    
    Example:
        repo = TagRepository(session)
        tag = repo.get_by_id(1)
    """
    
    def __init__(self, session: Session):
        """
        初始化标签数据访问对象
        
        Args:
            session: SQLAlchemy 数据库会话对象
        """
        self.session = session
    
    def create(self, tag_data: TagCreate) -> Tag:
        """
        创建标签记录
        
        将标签数据插入数据库，返回创建的标签对象。
        
        Args:
            tag_data: 标签创建数据模型，包含必填的 name
        
        Returns:
            Tag: 创建的标签 ORM 对象，包含自动生成的 id 和时间戳
        
        Raises:
            IntegrityError: 同一父标签下已存在同名标签时抛出
        
        Note:
            调用后需要 commit 才能持久化到数据库
        """
        tag = Tag(**tag_data.model_dump())
        self.session.add(tag)
        self.session.flush()
        return tag
    
    def get_by_id(self, tag_id: int) -> Optional[Tag]:
        """
        根据ID获取标签
        
        通过主键快速查找标签记录。
        
        Args:
            tag_id: 标签ID
        
        Returns:
            Optional[Tag]: 标签对象，不存在时返回 None
        
        Performance:
            使用 session.get() 直接通过主键查询，性能最优
        """
        return self.session.get(Tag, tag_id)
    
    def get_by_id_with_children(self, tag_id: int) -> Optional[Tag]:
        """
        根据ID获取标签（包含子标签）
        
        使用预加载策略一次性获取标签及其所有子标签，
        避免 N+1 查询问题。
        
        Args:
            tag_id: 标签ID
        
        Returns:
            Optional[Tag]: 包含子标签的标签对象
        
        Performance:
            使用 joinedload 预加载子标签，减少数据库查询次数
        """
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
        """
        根据名称和父标签ID获取标签
        
        用于检查标签是否已存在（同一父标签下名称唯一）。
        
        Args:
            name: 标签名称
            parent_id: 父标签ID，None 表示一级标签
        
        Returns:
            Optional[Tag]: 标签对象，不存在时返回 None
        """
        stmt = select(Tag).where(
            Tag.name == name,
            Tag.parent_id == parent_id
        )
        return self.session.execute(stmt).scalar_one_or_none()
    
    def update(self, tag: Tag, tag_data: TagUpdate) -> Tag:
        """
        更新标签信息
        
        只更新提供的字段，未提供的字段保持不变。
        
        Args:
            tag: 要更新的标签对象
            tag_data: 更新数据模型（所有字段可选）
        
        Returns:
            Tag: 更新后的标签对象
        
        Note:
            updated_at 字段会自动更新
        """
        update_data = tag_data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(tag, key, value)
        self.session.flush()
        return tag
    
    def delete(self, tag: Tag) -> None:
        """
        删除标签
        
        删除标签记录及其所有关联关系。
        
        Args:
            tag: 要删除的标签对象
        
        Note:
            - 关联的 VideoTag 记录会被级联删除
            - 子标签的 parent_id 会被设为 NULL（变为一级标签）
        """
        self.session.delete(tag)
        self.session.flush()
    
    def delete_by_id(self, tag_id: int) -> bool:
        """
        根据ID删除标签
        
        Args:
            tag_id: 标签ID
        
        Returns:
            bool: 删除成功返回 True，标签不存在返回 False
        """
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
        """
        获取标签列表
        
        支持分页、搜索和层级筛选。
        
        Args:
            page: 页码，从1开始
            page_size: 每页记录数
            search: 搜索关键词，匹配名称和描述
            parent_id: 父标签ID筛选
                - None: 不限制层级
                - 指定值: 只返回该父标签下的子标签
        
        Returns:
            Tuple[List[Tag], int]: (标签列表, 总记录数)
        """
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
        """
        获取所有一级标签（包含子标签）
        
        获取 parent_id 为 NULL 的所有标签，并预加载其子标签。
        用于构建标签树的第一层。
        
        Returns:
            List[Tag]: 一级标签列表，每个标签包含 children 属性
        
        Performance:
            使用 joinedload 预加载子标签，避免 N+1 查询
        """
        stmt = (
            select(Tag)
            .options(joinedload(Tag.children))
            .where(Tag.parent_id.is_(None))
            .order_by(Tag.sort_order, Tag.created_at)
        )
        return list(self.session.execute(stmt).unique().scalars().all())
    
    def list_children(self, parent_id: int) -> List[Tag]:
        """
        获取指定标签的子标签
        
        获取指定父标签下的所有二级标签。
        
        Args:
            parent_id: 父标签ID
        
        Returns:
            List[Tag]: 子标签列表，按 sort_order 和创建时间排序
        """
        stmt = (
            select(Tag)
            .where(Tag.parent_id == parent_id)
            .order_by(Tag.sort_order, Tag.created_at)
        )
        return list(self.session.execute(stmt).scalars().all())
    
    def get_tag_tree(self) -> List[Tag]:
        """
        获取完整标签树
        
        返回所有一级标签及其子标签，构建完整的标签树结构。
        
        Returns:
            List[Tag]: 一级标签列表，每个标签包含 children 属性
        
        Note:
            这是 list_root_tags() 的别名，语义更清晰
        """
        root_tags = self.list_root_tags()
        return root_tags
    
    def exists_by_name_and_parent(
        self, 
        name: str, 
        parent_id: Optional[int] = None
    ) -> bool:
        """
        检查标签是否已存在
        
        检查同一父标签下是否存在同名标签。
        
        Args:
            name: 标签名称
            parent_id: 父标签ID，None 表示一级标签
        
        Returns:
            bool: 存在返回 True，不存在返回 False
        """
        stmt = select(func.count(Tag.id)).where(
            Tag.name == name,
            Tag.parent_id == parent_id
        )
        return self.session.execute(stmt).scalar() > 0
    
    def count_all(self) -> int:
        """
        获取标签总数
        
        Returns:
            int: 标签总记录数
        """
        return self.session.execute(select(func.count(Tag.id))).scalar()
    
    def count_children(self, parent_id: int) -> int:
        """
        获取子标签数量
        
        统计指定标签下的子标签数量。
        
        Args:
            parent_id: 父标签ID
        
        Returns:
            int: 子标签数量
        """
        stmt = select(func.count(Tag.id)).where(Tag.parent_id == parent_id)
        return self.session.execute(stmt).scalar()
    
    def get_by_ids(self, tag_ids: List[int]) -> List[Tag]:
        """
        根据ID列表批量获取标签
        
        一次性获取多个标签记录。
        
        Args:
            tag_ids: 标签ID列表
        
        Returns:
            List[Tag]: 标签对象列表（只返回存在的标签）
        """
        if not tag_ids:
            return []
        stmt = select(Tag).where(Tag.id.in_(tag_ids))
        return list(self.session.execute(stmt).scalars().all())
    
    def get_siblings(
        self, 
        tag_id: int, 
        parent_id: Optional[int] = None
    ) -> List[Tag]:
        """
        获取同级标签
        
        获取与指定标签具有相同父标签的其他标签。
        用于标签排序或移动时的参考。
        
        Args:
            tag_id: 当前标签ID（排除在结果外）
            parent_id: 父标签ID，None 表示一级标签
        
        Returns:
            List[Tag]: 同级标签列表（不包含自身）
        """
        stmt = (
            select(Tag)
            .where(Tag.parent_id == parent_id, Tag.id != tag_id)
            .order_by(Tag.sort_order, Tag.created_at)
        )
        return list(self.session.execute(stmt).scalars().all())

"""
视频数据库标签管理脚本
提供标签的创建、删除、重命名、改变层级以及视频标签关联编辑等功能
"""
import argparse
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from typing import Optional, List

from video_tag_system import DatabaseManager
from video_tag_system.models.tag import TagCreate, TagUpdate, TagMergeRequest
from video_tag_system.models.video_tag import BatchTagOperation
from video_tag_system.services import TagService, VideoTagService
from video_tag_system.repositories import VideoRepository, TagRepository
from video_tag_system.exceptions import (
    TagNotFoundError,
    DuplicateTagError,
    ValidationError,
    TagMergeError,
    VideoNotFoundError,
)


class TagManagerCLI:
    """标签管理命令行工具"""
    
    def __init__(self, db_url: Optional[str] = None):
        self.db_manager = DatabaseManager(database_url=db_url, echo=False)
        self.db_manager.create_tables()
    
    def create_tag(
        self,
        name: str,
        parent_id: Optional[int] = None,
        parent_name: Optional[str] = None,
        description: Optional[str] = None,
        sort_order: int = 0
    ) -> None:
        """创建标签"""
        with self.db_manager.get_session() as session:
            tag_service = TagService(session)
            
            if parent_name is not None:
                if parent_id is not None:
                    print("✗ 错误: 不能同时指定 --parent 和 --parent-name")
                    sys.exit(1)
                
                try:
                    parent_tag = tag_service.get_tag_by_name(parent_name, parent_id=None)
                    parent_id = parent_tag.id
                except TagNotFoundError:
                    print(f"✗ 错误: 父标签不存在 (名称: '{parent_name}')")
                    sys.exit(1)
            
            tag_data = TagCreate(
                name=name,
                parent_id=parent_id,
                description=description,
                sort_order=sort_order
            )
            
            try:
                tag = tag_service.create_tag(tag_data)
                level = "一级" if tag.parent_id is None else "二级"
                print(f"✓ 成功创建{level}标签: {tag.name} (ID: {tag.id})")
                if tag.parent_id:
                    print(f"  父标签ID: {tag.parent_id}")
                if tag.description:
                    print(f"  描述: {tag.description}")
            except TagNotFoundError as e:
                print(f"✗ 错误: 父标签不存在 (ID: {e.details.get('tag_id')})")
                sys.exit(1)
            except DuplicateTagError as e:
                parent_info = f" (父标签ID: {e.details.get('parent_id')})" if e.details.get('parent_id') else ""
                print(f"✗ 错误: 标签 '{e.details.get('tag_name')}' 已存在{parent_info}")
                sys.exit(1)
            except ValidationError as e:
                print(f"✗ 验证错误: {e.message}")
                sys.exit(1)
    
    def delete_tag(self, tag_id: int, force: bool = False) -> None:
        """删除标签"""
        with self.db_manager.get_session() as session:
            tag_service = TagService(session)
            
            try:
                tag = tag_service.get_tag(tag_id)
                print(f"标签信息: {tag.name} (ID: {tag.id})")
                print(f"  层级: {'一级' if tag.level == 1 else '二级'}")
                
                stats = tag_service.get_tag_statistics(tag_id)
                print(f"  关联视频数: {stats['video_count']}")
                print(f"  子标签数: {stats['children_count']}")
                
                if stats['children_count'] > 0:
                    print(f"✗ 错误: 该标签下有 {stats['children_count']} 个子标签，请先删除子标签")
                    sys.exit(1)
                
                if stats['video_count'] > 0 and not force:
                    print(f"⚠ 警告: 该标签关联了 {stats['video_count']} 个视频")
                    print("  使用 --force 参数强制删除")
                    sys.exit(1)
                
                if force and stats['video_count'] > 0:
                    print("⚠ 警告: 强制删除将移除所有视频关联")
                
                confirm = input(f"\n确认删除标签 '{tag.name}'? (yes/no): ")
                if confirm.lower() not in ['yes', 'y']:
                    print("操作已取消")
                    return
                
                tag_service.delete_tag(tag_id)
                print(f"✓ 成功删除标签: {tag.name}")
                
            except TagNotFoundError:
                print(f"✗ 错误: 标签不存在 (ID: {tag_id})")
                sys.exit(1)
            except ValidationError as e:
                print(f"✗ 验证错误: {e.message}")
                sys.exit(1)
    
    def rename_tag(self, tag_id: int, new_name: str) -> None:
        """重命名标签"""
        with self.db_manager.get_session() as session:
            tag_service = TagService(session)
            
            try:
                tag = tag_service.get_tag(tag_id)
                print(f"当前标签: {tag.name} (ID: {tag.id})")
                
                update_data = TagUpdate(name=new_name)
                updated_tag = tag_service.update_tag(tag_id, update_data)
                
                print(f"✓ 成功重命名标签: '{tag.name}' -> '{updated_tag.name}'")
                
            except TagNotFoundError:
                print(f"✗ 错误: 标签不存在 (ID: {tag_id})")
                sys.exit(1)
            except DuplicateTagError as e:
                print(f"✗ 错误: 标签名称 '{e.tag_name}' 已存在")
                sys.exit(1)
            except ValidationError as e:
                print(f"✗ 验证错误: {e.message}")
                sys.exit(1)
    
    def move_tag(self, tag_id: int, new_parent_id: Optional[int]) -> None:
        """改变标签层级"""
        with self.db_manager.get_session() as session:
            tag_service = TagService(session)
            
            try:
                tag = tag_service.get_tag(tag_id)
                old_level = "一级" if tag.level == 1 else "二级"
                old_parent = f" (父标签ID: {tag.parent_id})" if tag.parent_id else ""
                
                print(f"当前标签: {tag.name} (ID: {tag.id})")
                print(f"  当前层级: {old_level}{old_parent}")
                
                if new_parent_id:
                    parent_tag = tag_service.get_tag(new_parent_id)
                    if parent_tag.level != 1:
                        print(f"✗ 错误: 父标签必须是一级标签")
                        sys.exit(1)
                    new_level_info = f"二级标签 (父标签: {parent_tag.name})"
                else:
                    new_level_info = "一级标签"
                
                print(f"  目标层级: {new_level_info}")
                
                update_data = TagUpdate(parent_id=new_parent_id)
                updated_tag = tag_service.update_tag(tag_id, update_data)
                
                new_level = "一级" if updated_tag.level == 1 else "二级"
                new_parent_info = f" (父标签ID: {updated_tag.parent_id})" if updated_tag.parent_id else ""
                
                print(f"✓ 成功改变标签层级: {old_level} -> {new_level}{new_parent_info}")
                
            except TagNotFoundError:
                print(f"✗ 错误: 标签不存在")
                sys.exit(1)
            except ValidationError as e:
                print(f"✗ 验证错误: {e.message}")
                sys.exit(1)
    
    def update_tag(
        self,
        tag_id: int,
        name: Optional[str] = None,
        description: Optional[str] = None,
        sort_order: Optional[int] = None
    ) -> None:
        """更新标签信息"""
        with self.db_manager.get_session() as session:
            tag_service = TagService(session)
            
            try:
                tag = tag_service.get_tag(tag_id)
                print(f"当前标签: {tag.name} (ID: {tag.id})")
                
                update_kwargs = {}
                if name is not None:
                    update_kwargs['name'] = name
                if description is not None:
                    update_kwargs['description'] = description
                if sort_order is not None:
                    update_kwargs['sort_order'] = sort_order
                
                if not update_kwargs:
                    print("✓ 标签信息无变化")
                    return
                
                update_data = TagUpdate(**update_kwargs)
                updated_tag = tag_service.update_tag(tag_id, update_data)
                
                changes = []
                if 'name' in update_kwargs and name != tag.name:
                    changes.append(f"名称: '{tag.name}' -> '{updated_tag.name}'")
                if 'description' in update_kwargs:
                    old_desc = tag.description or "无"
                    new_desc = updated_tag.description or "无"
                    changes.append(f"描述: '{old_desc}' -> '{new_desc}'")
                if 'sort_order' in update_kwargs:
                    changes.append(f"排序: {tag.sort_order} -> {updated_tag.sort_order}")
                
                if changes:
                    print("✓ 成功更新标签:")
                    for change in changes:
                        print(f"  - {change}")
                else:
                    print("✓ 标签信息无变化")
                
            except TagNotFoundError:
                print(f"✗ 错误: 标签不存在 (ID: {tag_id})")
                sys.exit(1)
            except ValidationError as e:
                print(f"✗ 验证错误: {e.message}")
                sys.exit(1)
    
    def merge_tags(self, source_id: int, target_id: int) -> None:
        """合并标签"""
        with self.db_manager.get_session() as session:
            tag_service = TagService(session)
            
            try:
                source_tag = tag_service.get_tag(source_id)
                target_tag = tag_service.get_tag(target_id)
                
                print(f"源标签: {source_tag.name} (ID: {source_tag.id})")
                print(f"目标标签: {target_tag.name} (ID: {target_tag.id})")
                
                source_stats = tag_service.get_tag_statistics(source_id)
                print(f"源标签关联视频数: {source_stats['video_count']}")
                
                merge_data = TagMergeRequest(
                    source_tag_id=source_id,
                    target_tag_id=target_id
                )
                
                result = tag_service.merge_tags(merge_data)
                
                print(f"✓ 成功合并标签:")
                print(f"  - 转移关联关系: {result['transferred_relations']} 条")
                print(f"  - 删除源标签: {result['deleted_source_tag']}")
                
            except TagNotFoundError:
                print(f"✗ 错误: 标签不存在")
                sys.exit(1)
            except TagMergeError as e:
                print(f"✗ 合并错误: {e.message}")
                sys.exit(1)
    
    def list_tags(
        self,
        parent_id: Optional[int] = None,
        search: Optional[str] = None,
        show_tree: bool = False
    ) -> None:
        """列出标签"""
        with self.db_manager.get_session() as session:
            tag_service = TagService(session)
            
            if show_tree:
                self._show_tag_tree(tag_service)
            else:
                self._show_tag_list(tag_service, parent_id, search)
    
    def _show_tag_tree(self, tag_service: TagService) -> None:
        """显示标签树"""
        tag_tree = tag_service.get_tag_tree()
        total = tag_tree.total
        
        print(f"\n标签树 (共 {total} 个标签):\n")
        
        for root_tag in tag_tree.items:
            self._print_tag_node(root_tag, 0)
        
        if total == 0:
            print("  (暂无标签)")
    
    def _print_tag_node(self, tag, level: int) -> None:
        """递归打印标签节点"""
        indent = "  " * level
        level_str = f"[{tag.level}级]" if tag.level else ""
        video_count_str = f"({tag.video_count}个视频)" if hasattr(tag, 'video_count') else ""
        
        print(f"{indent}├─ {tag.name} (ID:{tag.id}) {level_str} {video_count_str}")
        if tag.description:
            print(f"{indent}│  描述: {tag.description}")
        
        for child in tag.children:
            self._print_tag_node(child, level + 1)
    
    def _show_tag_list(
        self,
        tag_service: TagService,
        parent_id: Optional[int],
        search: Optional[str]
    ) -> None:
        """显示标签列表"""
        if parent_id:
            parent = tag_service.get_tag(parent_id)
            print(f"\n标签列表 (父标签: {parent.name}):\n")
        elif search:
            print(f"\n标签列表 (搜索: '{search}'):\n")
        else:
            print(f"\n标签列表:\n")
        
        result = tag_service.list_tags(page=1, page_size=100, parent_id=parent_id, search=search)
        
        if not result['items']:
            print("  (暂无标签)")
            return
        
        for tag in result['items']:
            level_str = "一级" if tag.level == 1 else "二级"
            parent_str = f" (父ID: {tag.parent_id})" if tag.parent_id else ""
            desc_str = f" - {tag.description}" if tag.description else ""
            
            print(f"  [{tag.id}] {tag.name} ({level_str}){parent_str}{desc_str}")
        
        print(f"\n总计: {result['total']} 个标签")
    
    def show_tag_info(self, tag_id: int) -> None:
        """显示标签详细信息"""
        with self.db_manager.get_session() as session:
            tag_service = TagService(session)
            
            try:
                tag = tag_service.get_tag(tag_id)
                stats = tag_service.get_tag_statistics(tag_id)
                
                print(f"\n标签详细信息:\n")
                print(f"  ID: {tag.id}")
                print(f"  名称: {tag.name}")
                print(f"  层级: {'一级' if tag.level == 1 else '二级'}")
                if tag.parent_id:
                    print(f"  父标签ID: {tag.parent_id}")
                if tag.description:
                    print(f"  描述: {tag.description}")
                print(f"  排序: {tag.sort_order}")
                print(f"  创建时间: {tag.created_at.strftime('%Y-%m-%d %H:%M:%S')}")
                print(f"  更新时间: {tag.updated_at.strftime('%Y-%m-%d %H:%M:%S')}")
                print(f"  关联视频数: {stats['video_count']}")
                print(f"  子标签数: {stats['children_count']}")
                
                if tag.children:
                    print(f"\n  子标签:")
                    for child in tag.children:
                        print(f"    - {child.name} (ID: {child.id})")
                
            except TagNotFoundError:
                print(f"✗ 错误: 标签不存在 (ID: {tag_id})")
                sys.exit(1)
    
    def list_videos(self, tag_ids: Optional[List[int]] = None) -> None:
        """列出视频"""
        with self.db_manager.get_session() as session:
            video_repo = VideoRepository(session)
            video_tag_service = VideoTagService(session)
            
            if tag_ids:
                video_ids = video_tag_service.get_videos_by_tags(tag_ids, match_all=False)
                videos = [video_repo.get_by_id(vid) for vid in video_ids]
                videos = [v for v in videos if v is not None]
                print(f"\n视频列表 (标签: {tag_ids}):\n")
            else:
                videos = video_repo.list_all(page=1, page_size=50)[0]
                print(f"\n视频列表:\n")
            
            if not videos:
                print("  (暂无视频)")
                return
            
            for video in videos:
                tags = video_tag_service.get_video_tags(video.id)
                tag_names = [t.name for t in tags]
                print(f"  [{video.id}] {video.title}")
                print(f"      路径: {video.file_path}")
                if tag_names:
                    print(f"      标签: {', '.join(tag_names)}")
                print()
    
    def add_video_tag(self, video_id: int, tag_id: int) -> None:
        """为视频添加标签"""
        with self.db_manager.get_session() as session:
            video_tag_service = VideoTagService(session)
            
            try:
                result = video_tag_service.add_tag_to_video(video_id, tag_id)
                if result['added']:
                    print(f"✓ 成功为视频 {video_id} 添加标签 {tag_id}")
                else:
                    print(f"✓ 视频 {video_id} 已有标签 {tag_id}")
            except VideoNotFoundError:
                print(f"✗ 错误: 视频不存在 (ID: {video_id})")
                sys.exit(1)
            except TagNotFoundError:
                print(f"✗ 错误: 标签不存在 (ID: {tag_id})")
                sys.exit(1)
    
    def remove_video_tag(self, video_id: int, tag_id: int) -> None:
        """从视频移除标签"""
        with self.db_manager.get_session() as session:
            video_tag_service = VideoTagService(session)
            
            try:
                result = video_tag_service.remove_tag_from_video(video_id, tag_id)
                if result['removed']:
                    print(f"✓ 成功从视频 {video_id} 移除标签 {tag_id}")
                else:
                    print(f"✓ 视频 {video_id} 没有标签 {tag_id}")
            except VideoNotFoundError:
                print(f"✗ 错误: 视频不存在 (ID: {video_id})")
                sys.exit(1)
            except TagNotFoundError:
                print(f"✗ 错误: 标签不存在 (ID: {tag_id})")
                sys.exit(1)
    
    def set_video_tags(self, video_id: int, tag_ids: List[int]) -> None:
        """设置视频的标签（替换现有标签）"""
        with self.db_manager.get_session() as session:
            video_tag_service = VideoTagService(session)
            
            try:
                result = video_tag_service.set_video_tags(video_id, tag_ids)
                print(f"✓ 成功设置视频 {video_id} 的标签:")
                print(f"  - 添加了 {result['tags_added']} 个标签")
                print(f"  - 移除了 {result['tags_removed']} 个标签")
                print(f"  - 当前共有 {result['current_tag_count']} 个标签")
            except VideoNotFoundError:
                print(f"✗ 错误: 视频不存在 (ID: {video_id})")
                sys.exit(1)
            except TagNotFoundError:
                print(f"✗ 错误: 标签不存在")
                sys.exit(1)
    
    def batch_add_video_tags(
        self,
        video_ids: List[int],
        tag_ids: List[int]
    ) -> None:
        """批量为视频添加标签"""
        with self.db_manager.get_session() as session:
            video_tag_service = VideoTagService(session)
            
            try:
                operation = BatchTagOperation(
                    video_ids=video_ids,
                    tag_ids=tag_ids
                )
                result = video_tag_service.batch_add_tags(operation)
                print(f"✓ {result['message']}")
            except VideoNotFoundError:
                print(f"✗ 错误: 视频不存在")
                sys.exit(1)
            except TagNotFoundError:
                print(f"✗ 错误: 标签不存在")
                sys.exit(1)
    
    def batch_remove_video_tags(
        self,
        video_ids: List[int],
        tag_ids: List[int]
    ) -> None:
        """批量从视频移除标签"""
        with self.db_manager.get_session() as session:
            video_tag_service = VideoTagService(session)
            
            try:
                operation = BatchTagOperation(
                    video_ids=video_ids,
                    tag_ids=tag_ids
                )
                result = video_tag_service.batch_remove_tags(operation)
                print(f"✓ {result['message']}")
            except VideoNotFoundError:
                print(f"✗ 错误: 视频不存在")
                sys.exit(1)
            except TagNotFoundError:
                print(f"✗ 错误: 标签不存在")
                sys.exit(1)
    
    def show_video_tags(self, video_id: int) -> None:
        """显示视频的所有标签"""
        with self.db_manager.get_session() as session:
            video_tag_service = VideoTagService(session)
            
            try:
                tags = video_tag_service.get_video_tags(video_id)
                print(f"\n视频 {video_id} 的标签:\n")
                
                if not tags:
                    print("  (暂无标签)")
                    return
                
                for tag in tags:
                    level = "一级" if tag.level == 1 else "二级"
                    parent_info = f" (父: {tag.parent_id})" if tag.parent_id else ""
                    print(f"  - {tag.name} (ID: {tag.id}) [{level}]{parent_info}")
                    if tag.description:
                        print(f"      描述: {tag.description}")
                
                print(f"\n总计: {len(tags)} 个标签")
            except VideoNotFoundError:
                print(f"✗ 错误: 视频不存在 (ID: {video_id})")
                sys.exit(1)
    
    def search_videos_by_tag(self, tag_name: str) -> None:
        """根据标签名称搜索视频"""
        with self.db_manager.get_session() as session:
            tag_service = TagService(session)
            video_tag_service = VideoTagService(session)
            
            try:
                tag = tag_service.get_tag_by_name(tag_name, parent_id=None)
            except TagNotFoundError:
                try:
                    tag_repo = TagRepository(session)
                    tag = tag_repo.get_by_name_and_parent(tag_name, parent_id=None)
                    if not tag:
                        from sqlalchemy import select
                        from video_tag_system.models.tag import Tag
                        stmt = select(Tag).where(Tag.name == tag_name)
                        tag = session.execute(stmt).scalar_one_or_none()
                        if not tag:
                            raise TagNotFoundError(tag_name=tag_name)
                except TagNotFoundError:
                    print(f"✗ 错误: 标签不存在 (名称: '{tag_name}')")
                    sys.exit(1)
            
            video_ids = video_tag_service.get_videos_by_tags([tag.id], match_all=False)
            
            print(f"\n标签 '{tag_name}' (ID: {tag.id}) 关联的视频:\n")
            
            if not video_ids:
                print("  (暂无视频)")
                return
            
            video_repo = VideoRepository(session)
            for video_id in video_ids:
                video = video_repo.get_by_id(video_id)
                if video:
                    print(f"  [{video.id}] {video.title}")
                    print(f"      路径: {video.file_path}")
                    print()
            
            print(f"总计: {len(video_ids)} 个视频")
    
    def close(self) -> None:
        """关闭数据库连接"""
        self.db_manager.close()


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="视频数据库标签管理工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  创建一级标签:
    python tools/tag_manager.py create "动作" --desc "动作类型视频"
  
  创建二级标签 (使用父标签ID):
    python tools/tag_manager.py create "武侠" --parent 1 --desc "武侠动作片"
  
  创建二级标签 (使用父标签名称):
    python tools/tag_manager.py create "武侠" --parent-name "动作" --desc "武侠动作片"
  
  删除标签:
    python tools/tag_manager.py delete 5
  
  强制删除标签:
    python tools/tag_manager.py delete 5 --force
  
  重命名标签:
    python tools/tag_manager.py rename 5 "功夫片"
  
  改变标签层级:
    python tools/tag_manager.py move 5 --parent 1
    python tools/tag_manager.py move 5 --root
  
  更新标签:
    python tools/tag_manager.py update 5 --desc "更新后的描述" --sort 10
  
  合并标签:
    python tools/tag_manager.py merge 5 6
  
  查看标签树:
    python tools/tag_manager.py list --tree
  
  查看标签详情:
    python tools/tag_manager.py info 5
  
  列出视频:
    python tools/tag_manager.py videos
  
  根据标签列出视频:
    python tools/tag_manager.py videos --tags 1 2
  
  为视频添加标签:
    python tools/tag_manager.py video-add 1 2
  
  从视频移除标签:
    python tools/tag_manager.py video-remove 1 2
  
  设置视频标签:
    python tools/tag_manager.py video-set 1 --tags 1 2 3
  
  查看视频标签:
    python tools/tag_manager.py video-tags 1
  
  批量添加标签:
    python tools/tag_manager.py batch-add --videos 1 2 3 --tags 1 2
  
  批量移除标签:
    python tools/tag_manager.py batch-remove --videos 1 2 3 --tags 1 2
  
  根据标签名搜索视频:
    python tools/tag_manager.py search "黑丝"
        """
    )
    
    parser.add_argument(
        '--db',
        type=str,
        help='数据库连接URL (默认: 使用配置文件中的设置)'
    )
    
    subparsers = parser.add_subparsers(dest='command', help='可用命令')
    
    create_parser = subparsers.add_parser('create', help='创建标签')
    create_parser.add_argument('name', type=str, help='标签名称')
    parent_group = create_parser.add_mutually_exclusive_group()
    parent_group.add_argument('--parent', type=int, help='父标签ID (可选)')
    parent_group.add_argument('--parent-name', type=str, help='父标签名称 (可选)')
    create_parser.add_argument('--desc', type=str, help='标签描述')
    create_parser.add_argument('--sort', type=int, default=0, help='排序顺序')
    
    delete_parser = subparsers.add_parser('delete', help='删除标签')
    delete_parser.add_argument('tag_id', type=int, help='标签ID')
    delete_parser.add_argument('--force', action='store_true', help='强制删除(即使有关联视频)')
    
    rename_parser = subparsers.add_parser('rename', help='重命名标签')
    rename_parser.add_argument('tag_id', type=int, help='标签ID')
    rename_parser.add_argument('new_name', type=str, help='新名称')
    
    move_parser = subparsers.add_parser('move', help='改变标签层级')
    move_parser.add_argument('tag_id', type=int, help='标签ID')
    move_group = move_parser.add_mutually_exclusive_group(required=True)
    move_group.add_argument('--parent', type=int, help='新的父标签ID')
    move_group.add_argument('--root', action='store_true', help='设为一级标签')
    
    update_parser = subparsers.add_parser('update', help='更新标签信息')
    update_parser.add_argument('tag_id', type=int, help='标签ID')
    update_parser.add_argument('--name', type=str, help='新名称')
    update_parser.add_argument('--desc', type=str, help='新描述')
    update_parser.add_argument('--sort', type=int, help='新排序')
    
    merge_parser = subparsers.add_parser('merge', help='合并标签')
    merge_parser.add_argument('source_id', type=int, help='源标签ID')
    merge_parser.add_argument('target_id', type=int, help='目标标签ID')
    
    list_parser = subparsers.add_parser('list', help='列出标签')
    list_parser.add_argument('--tree', action='store_true', help='以树形结构显示')
    list_parser.add_argument('--parent', type=int, help='只显示指定父标签的子标签')
    list_parser.add_argument('--search', type=str, help='搜索标签')
    
    info_parser = subparsers.add_parser('info', help='显示标签详细信息')
    info_parser.add_argument('tag_id', type=int, help='标签ID')
    
    videos_parser = subparsers.add_parser('videos', help='列出视频')
    videos_parser.add_argument('--tags', type=int, nargs='+', help='只显示指定标签的视频')
    
    video_add_parser = subparsers.add_parser('video-add', help='为视频添加标签')
    video_add_parser.add_argument('video_id', type=int, help='视频ID')
    video_add_parser.add_argument('tag_id', type=int, help='标签ID')
    
    video_remove_parser = subparsers.add_parser('video-remove', help='从视频移除标签')
    video_remove_parser.add_argument('video_id', type=int, help='视频ID')
    video_remove_parser.add_argument('tag_id', type=int, help='标签ID')
    
    video_set_parser = subparsers.add_parser('video-set', help='设置视频的标签（替换现有标签）')
    video_set_parser.add_argument('video_id', type=int, help='视频ID')
    video_set_parser.add_argument('--tags', type=int, nargs='+', required=True, help='标签ID列表')
    
    video_tags_parser = subparsers.add_parser('video-tags', help='查看视频的所有标签')
    video_tags_parser.add_argument('video_id', type=int, help='视频ID')
    
    batch_add_parser = subparsers.add_parser('batch-add', help='批量为视频添加标签')
    batch_add_parser.add_argument('--videos', type=int, nargs='+', required=True, help='视频ID列表')
    batch_add_parser.add_argument('--tags', type=int, nargs='+', required=True, help='标签ID列表')
    
    batch_remove_parser = subparsers.add_parser('batch-remove', help='批量从视频移除标签')
    batch_remove_parser.add_argument('--videos', type=int, nargs='+', required=True, help='视频ID列表')
    batch_remove_parser.add_argument('--tags', type=int, nargs='+', required=True, help='标签ID列表')
    
    search_parser = subparsers.add_parser('search', help='根据标签名称搜索视频')
    search_parser.add_argument('tag_name', type=str, help='标签名称')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    manager = TagManagerCLI(db_url=args.db)
    
    try:
        if args.command == 'create':
            manager.create_tag(
                name=args.name,
                parent_id=args.parent,
                parent_name=args.parent_name,
                description=args.desc,
                sort_order=args.sort
            )
        elif args.command == 'delete':
            manager.delete_tag(args.tag_id, force=args.force)
        elif args.command == 'rename':
            manager.rename_tag(args.tag_id, args.new_name)
        elif args.command == 'move':
            new_parent_id = None if args.root else args.parent
            manager.move_tag(args.tag_id, new_parent_id)
        elif args.command == 'update':
            manager.update_tag(
                tag_id=args.tag_id,
                name=args.name,
                description=args.desc,
                sort_order=args.sort
            )
        elif args.command == 'merge':
            manager.merge_tags(args.source_id, args.target_id)
        elif args.command == 'list':
            manager.list_tags(
                parent_id=args.parent,
                search=args.search,
                show_tree=args.tree
            )
        elif args.command == 'info':
            manager.show_tag_info(args.tag_id)
        elif args.command == 'videos':
            manager.list_videos(tag_ids=args.tags)
        elif args.command == 'video-add':
            manager.add_video_tag(args.video_id, args.tag_id)
        elif args.command == 'video-remove':
            manager.remove_video_tag(args.video_id, args.tag_id)
        elif args.command == 'video-set':
            manager.set_video_tags(args.video_id, args.tags)
        elif args.command == 'video-tags':
            manager.show_video_tags(args.video_id)
        elif args.command == 'batch-add':
            manager.batch_add_video_tags(args.videos, args.tags)
        elif args.command == 'batch-remove':
            manager.batch_remove_video_tags(args.videos, args.tags)
        elif args.command == 'search':
            manager.search_videos_by_tag(args.tag_name)
    finally:
        manager.close()


if __name__ == "__main__":
    main()
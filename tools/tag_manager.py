"""
标签管理工具

本模块提供交互式控制台工具，用于管理视频数据库中的标签。
支持以下功能：
- 查看标签：显示所有标签的树形结构
- 创建标签：创建一级标签或二级标签
- 删除标签：删除标签（需先处理子标签和关联）
- 重命名标签：修改标签名称
- 修改层级：将二级标签提升为一级标签，或将一级标签降为二级标签
- 合并标签：将一个标签合并到另一个标签

使用方式：
    python tools/tag_manager.py
    python tools/tag_manager.py /path/to/database.db

作者：Video Library System
创建时间：2024
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from typing import Optional, List

from video_tag_system import DatabaseManager
from video_tag_system.services import TagService, VideoTagService
from video_tag_system.repositories import TagRepository, VideoTagRepository
from video_tag_system.models.tag import TagCreate, TagUpdate, TagMergeRequest
from video_tag_system.exceptions import (
    TagNotFoundError,
    DuplicateTagError,
    ValidationError,
    TagMergeError,
)


class TagManager:
    """
    标签管理器类
    
    提供标签管理的核心功能，包括创建、删除、修改、合并标签等操作。
    
    属性：
        db_manager: 数据库管理器实例
    """
    
    def __init__(self, db_url: Optional[str] = None):
        """
        初始化标签管理器
        
        Args:
            db_url: 数据库连接字符串，默认为当前目录下的video_library.db
        """
        self.db_manager = DatabaseManager(database_url=db_url or "sqlite:///./video_library.db", echo=False)
        self.db_manager.create_tables()
    
    def get_tag_tree(self) -> List[dict]:
        """
        获取标签树结构
        
        Returns:
            标签字典列表，按层级组织
        """
        with self.db_manager.get_session() as session:
            tag_service = TagService(session)
            tag_tree = tag_service.get_tag_tree()
            
            result = []
            for root_tag in tag_tree.items:
                tag_info = {
                    "id": root_tag.id,
                    "name": root_tag.name,
                    "level": 1,
                    "parent_id": None,
                    "parent_name": None,
                    "video_count": self._get_tag_video_count(session, root_tag.id),
                    "children_count": len(root_tag.children),
                    "children": []
                }
                for child in root_tag.children:
                    tag_info["children"].append({
                        "id": child.id,
                        "name": child.name,
                        "level": 2,
                        "parent_id": root_tag.id,
                        "parent_name": root_tag.name,
                        "video_count": self._get_tag_video_count(session, child.id),
                        "children_count": 0,
                        "children": []
                    })
                result.append(tag_info)
            return result
    
    def _get_tag_video_count(self, session, tag_id: int) -> int:
        """
        获取标签关联的视频数量
        
        Args:
            session: 数据库会话
            tag_id: 标签ID
            
        Returns:
            视频数量
        """
        video_tag_repo = VideoTagRepository(session)
        return video_tag_repo.count_by_tag(tag_id)
    
    def get_all_tags_flat(self) -> List[dict]:
        """
        获取所有标签的扁平列表
        
        Returns:
            标签字典列表
        """
        with self.db_manager.get_session() as session:
            tag_service = TagService(session)
            tag_tree = tag_service.get_tag_tree()
            
            result = []
            for root_tag in tag_tree.items:
                result.append({
                    "id": root_tag.id,
                    "name": root_tag.name,
                    "level": 1,
                    "parent_id": None,
                    "parent_name": None,
                    "video_count": self._get_tag_video_count(session, root_tag.id),
                    "children_count": len(root_tag.children)
                })
                for child in root_tag.children:
                    result.append({
                        "id": child.id,
                        "name": child.name,
                        "level": 2,
                        "parent_id": root_tag.id,
                        "parent_name": root_tag.name,
                        "video_count": self._get_tag_video_count(session, child.id),
                        "children_count": 0
                    })
            return result
    
    def create_tag(self, name: str, parent_id: Optional[int] = None) -> dict:
        """
        创建标签
        
        Args:
            name: 标签名称
            parent_id: 父标签ID（创建二级标签时需要）
            
        Returns:
            操作结果字典
        """
        with self.db_manager.get_session() as session:
            tag_service = TagService(session)
            try:
                tag_data = TagCreate(name=name, parent_id=parent_id)
                tag = tag_service.create_tag(tag_data)
                session.commit()
                return {
                    "success": True,
                    "tag": {
                        "id": tag.id,
                        "name": tag.name,
                        "parent_id": tag.parent_id,
                        "level": tag.level
                    }
                }
            except (TagNotFoundError, DuplicateTagError, ValidationError) as e:
                return {"success": False, "error": str(e)}
    
    def delete_tag(self, tag_id: int) -> dict:
        """
        删除标签
        
        Args:
            tag_id: 标签ID
            
        Returns:
            操作结果字典
        """
        with self.db_manager.get_session() as session:
            tag_service = TagService(session)
            video_tag_repo = VideoTagRepository(session)
            
            try:
                video_count = video_tag_repo.count_by_tag(tag_id)
                tag = tag_service.get_tag(tag_id)
                children_count = len(tag.children) if tag.children else 0
                
                if children_count > 0:
                    return {
                        "success": False,
                        "error": f"该标签下有 {children_count} 个子标签，请先删除或移动子标签"
                    }
                
                tag_service.delete_tag(tag_id)
                session.commit()
                return {
                    "success": True,
                    "deleted_video_relations": video_count
                }
            except TagNotFoundError as e:
                return {"success": False, "error": str(e)}
            except ValidationError as e:
                return {"success": False, "error": str(e)}
    
    def rename_tag(self, tag_id: int, new_name: str) -> dict:
        """
        重命名标签
        
        Args:
            tag_id: 标签ID
            new_name: 新名称
            
        Returns:
            操作结果字典
        """
        with self.db_manager.get_session() as session:
            tag_service = TagService(session)
            try:
                tag_data = TagUpdate(name=new_name)
                tag = tag_service.update_tag(tag_id, tag_data)
                session.commit()
                return {
                    "success": True,
                    "tag": {
                        "id": tag.id,
                        "name": tag.name,
                        "parent_id": tag.parent_id,
                        "level": tag.level
                    }
                }
            except (TagNotFoundError, DuplicateTagError, ValidationError) as e:
                return {"success": False, "error": str(e)}
    
    def change_parent(self, tag_id: int, new_parent_id: Optional[int]) -> dict:
        """
        修改标签的父标签（改变层级）
        
        Args:
            tag_id: 要修改的标签ID
            new_parent_id: 新的父标签ID，None表示提升为一级标签
            
        Returns:
            操作结果字典
        """
        with self.db_manager.get_session() as session:
            tag_service = TagService(session)
            tag_repo = TagRepository(session)
            
            try:
                tag = tag_repo.get_by_id(tag_id)
                if not tag:
                    return {"success": False, "error": f"标签ID {tag_id} 不存在"}
                
                old_parent_id = tag.parent_id
                old_level = tag.level
                
                if new_parent_id == tag_id:
                    return {"success": False, "error": "标签不能以自己为父标签"}
                
                if new_parent_id is not None:
                    new_parent = tag_repo.get_by_id(new_parent_id)
                    if not new_parent:
                        return {"success": False, "error": f"父标签ID {new_parent_id} 不存在"}
                    if new_parent.parent_id is not None:
                        return {"success": False, "error": "不支持超过两级的标签结构，目标父标签必须是一级标签"}
                
                children_count = tag_repo.count_children(tag_id)
                if children_count > 0 and new_parent_id is not None:
                    return {"success": False, "error": f"该标签有 {children_count} 个子标签，不能变为二级标签"}
                
                tag_data = TagUpdate(parent_id=new_parent_id)
                updated_tag = tag_service.update_tag(tag_id, tag_data)
                session.commit()
                
                new_level = 1 if new_parent_id is None else 2
                action = "提升为一级标签" if new_parent_id is None else "降为二级标签"
                
                return {
                    "success": True,
                    "tag": {
                        "id": updated_tag.id,
                        "name": updated_tag.name,
                        "parent_id": updated_tag.parent_id,
                        "level": new_level
                    },
                    "old_level": old_level,
                    "new_level": new_level,
                    "action": action
                }
            except (TagNotFoundError, ValidationError) as e:
                return {"success": False, "error": str(e)}
    
    def merge_tags(self, source_id: int, target_id: int) -> dict:
        """
        合并标签
        
        将源标签的所有视频关联转移到目标标签，然后删除源标签。
        
        Args:
            source_id: 源标签ID（将被删除）
            target_id: 目标标签ID
            
        Returns:
            操作结果字典
        """
        with self.db_manager.get_session() as session:
            tag_service = TagService(session)
            try:
                merge_data = TagMergeRequest(source_tag_id=source_id, target_tag_id=target_id)
                result = tag_service.merge_tags(merge_data)
                session.commit()
                return {
                    "success": True,
                    "transferred_relations": result["transferred_relations"],
                    "source_tag_id": source_id,
                    "target_tag_id": target_id
                }
            except (TagNotFoundError, TagMergeError) as e:
                return {"success": False, "error": str(e)}
    
    def get_tag_statistics(self) -> dict:
        """
        获取标签统计信息
        
        Returns:
            统计信息字典
        """
        with self.db_manager.get_session() as session:
            tag_service = TagService(session)
            tag_repo = TagRepository(session)
            
            total_tags = tag_service.count_tags()
            root_tags = tag_repo.list_root_tags()
            level1_count = len(root_tags)
            level2_count = total_tags - level1_count
            
            return {
                "total_tags": total_tags,
                "level1_count": level1_count,
                "level2_count": level2_count
            }


def clear_screen():
    """清屏函数"""
    os.system('cls' if os.name == 'nt' else 'clear')


def print_separator(char='-', length=60):
    """打印分隔线"""
    print(char * length)


def show_tag_tree(manager: TagManager):
    """显示标签树"""
    tags = manager.get_tag_tree()
    stats = manager.get_tag_statistics()
    
    print("\n" + "=" * 60)
    print("  标签列表（树形结构）")
    print("=" * 60)
    print(f"  总计: {stats['total_tags']} 个标签 (一级: {stats['level1_count']}, 二级: {stats['level2_count']})")
    print_separator()
    
    if not tags:
        print("  暂无标签")
        print_separator()
        return
    
    for tag in tags:
        video_info = f"({tag['video_count']}视频)"
        children_info = f"[{tag['children_count']}子标签]" if tag['children_count'] > 0 else ""
        print(f"  [{tag['id']}] {tag['name']} {video_info} {children_info}")
        
        for child in tag.get("children", []):
            child_video_info = f"({child['video_count']}视频)"
            print(f"      └─ [{child['id']}] {child['name']} {child_video_info}")
    
    print_separator()


def create_tag_flow(manager: TagManager):
    """创建标签流程"""
    print("\n" + "=" * 60)
    print("  创建标签")
    print("=" * 60)
    
    name = input("\n请输入标签名称: ").strip()
    if not name:
        print("标签名称不能为空")
        return
    
    print("\n选择标签类型:")
    print("  [1] 一级标签")
    print("  [2] 二级标签")
    print("  [0] 取消")
    
    choice = input("\n请选择: ").strip()
    
    if choice == "0":
        return
    
    parent_id = None
    
    if choice == "2":
        tags = manager.get_tag_tree()
        if not tags:
            print("\n没有一级标签，请先创建一级标签")
            return
        
        print("\n选择父标签:")
        print_separator()
        for i, tag in enumerate(tags, 1):
            print(f"  [{i}] {tag['name']}")
        print_separator()
        print("  [0] 取消")
        
        parent_choice = input("\n请选择父标签编号: ").strip()
        if parent_choice == "0":
            return
        
        try:
            idx = int(parent_choice) - 1
            if 0 <= idx < len(tags):
                parent_id = tags[idx]["id"]
            else:
                print("无效的选择")
                return
        except ValueError:
            print("请输入有效的数字")
            return
    
    result = manager.create_tag(name, parent_id)
    
    if result["success"]:
        tag = result["tag"]
        level_str = "一级" if tag["level"] == 1 else "二级"
        print(f"\n✓ 成功创建{level_str}标签: {tag['name']} (ID: {tag['id']})")
    else:
        print(f"\n✗ 创建失败: {result['error']}")


def delete_tag_flow(manager: TagManager):
    """删除标签流程"""
    tags = manager.get_tag_tree()
    
    if not tags:
        print("\n暂无标签可删除")
        return
    
    print("\n" + "=" * 60)
    print("  删除标签")
    print("=" * 60)
    print("\n当前标签列表:")
    print_separator()
    
    all_tags = []
    for tag in tags:
        all_tags.append(tag)
        print(f"  [{tag['id']}] {tag['name']} (一级, {tag['video_count']}视频, {tag['children_count']}子标签)")
        for child in tag.get("children", []):
            all_tags.append(child)
            print(f"      └─ [{child['id']}] {child['name']} (二级, {child['video_count']}视频)")
    
    print_separator()
    print("  [0] 取消")
    print_separator()
    
    tag_id = input("\n请输入要删除的标签ID: ").strip()
    
    if tag_id == "0":
        return
    
    try:
        tag_id = int(tag_id)
    except ValueError:
        print("请输入有效的数字")
        return
    
    tag_to_delete = None
    for tag in all_tags:
        if tag["id"] == tag_id:
            tag_to_delete = tag
            break
    
    if not tag_to_delete:
        print(f"标签ID {tag_id} 不存在")
        return
    
    print(f"\n将要删除标签: {tag_to_delete['name']}")
    print(f"  - 关联视频数: {tag_to_delete['video_count']}")
    print(f"  - 子标签数: {tag_to_delete['children_count']}")
    
    confirm = input("\n确认删除？(y/n): ").strip().lower()
    if confirm != 'y':
        print("已取消")
        return
    
    result = manager.delete_tag(tag_id)
    
    if result["success"]:
        print(f"\n✓ 删除成功")
        if result.get("deleted_video_relations", 0) > 0:
            print(f"  已移除 {result['deleted_video_relations']} 个视频关联")
    else:
        print(f"\n✗ 删除失败: {result['error']}")


def rename_tag_flow(manager: TagManager):
    """重命名标签流程"""
    tags = manager.get_all_tags_flat()
    
    if not tags:
        print("\n暂无标签可重命名")
        return
    
    print("\n" + "=" * 60)
    print("  重命名标签")
    print("=" * 60)
    print("\n当前标签列表:")
    print_separator()
    
    for tag in tags:
        level_str = "一级" if tag["level"] == 1 else f"二级[{tag['parent_name']}]"
        print(f"  [{tag['id']}] {tag['name']} ({level_str})")
    
    print_separator()
    print("  [0] 取消")
    print_separator()
    
    tag_id = input("\n请输入要重命名的标签ID: ").strip()
    
    if tag_id == "0":
        return
    
    try:
        tag_id = int(tag_id)
    except ValueError:
        print("请输入有效的数字")
        return
    
    tag_to_rename = None
    for tag in tags:
        if tag["id"] == tag_id:
            tag_to_rename = tag
            break
    
    if not tag_to_rename:
        print(f"标签ID {tag_id} 不存在")
        return
    
    print(f"\n当前名称: {tag_to_rename['name']}")
    new_name = input("请输入新名称: ").strip()
    
    if not new_name:
        print("标签名称不能为空")
        return
    
    if new_name == tag_to_rename['name']:
        print("新名称与原名称相同，无需修改")
        return
    
    result = manager.rename_tag(tag_id, new_name)
    
    if result["success"]:
        print(f"\n✓ 重命名成功: {tag_to_rename['name']} -> {new_name}")
    else:
        print(f"\n✗ 重命名失败: {result['error']}")


def change_level_flow(manager: TagManager):
    """修改标签层级流程"""
    tags = manager.get_tag_tree()
    
    if not tags:
        print("\n暂无标签")
        return
    
    print("\n" + "=" * 60)
    print("  修改标签层级")
    print("=" * 60)
    print("\n说明:")
    print("  - 提升: 将二级标签变为一级标签")
    print("  - 降级: 将一级标签变为二级标签（需选择父标签）")
    print("  注意: 有子标签的一级标签不能降级")
    print_separator()
    
    all_tags = []
    for tag in tags:
        all_tags.append(tag)
        for child in tag.get("children", []):
            all_tags.append(child)
    
    print("\n当前标签列表:")
    print_separator()
    for tag in tags:
        children_info = f"[{tag['children_count']}子标签]" if tag['children_count'] > 0 else ""
        print(f"  [{tag['id']}] {tag['name']} (一级) {children_info}")
        for child in tag.get("children", []):
            print(f"      └─ [{child['id']}] {child['name']} (二级, 父: {tag['name']})")
    
    print_separator()
    print("  [0] 取消")
    print_separator()
    
    tag_id = input("\n请输入要修改的标签ID: ").strip()
    
    if tag_id == "0":
        return
    
    try:
        tag_id = int(tag_id)
    except ValueError:
        print("请输入有效的数字")
        return
    
    selected_tag = None
    for tag in all_tags:
        if tag["id"] == tag_id:
            selected_tag = tag
            break
    
    if not selected_tag:
        print(f"标签ID {tag_id} 不存在")
        return
    
    if selected_tag["level"] == 2:
        print(f"\n当前: 二级标签 [{selected_tag['parent_name']}/{selected_tag['name']}]")
        print("操作: 提升为一级标签")
        confirm = input("\n确认提升？(y/n): ").strip().lower()
        if confirm == 'y':
            result = manager.change_parent(tag_id, None)
            if result["success"]:
                print(f"\n✓ 提升成功: {selected_tag['name']} 现在是一级标签")
            else:
                print(f"\n✗ 提升失败: {result['error']}")
        else:
            print("已取消")
    else:
        if selected_tag["children_count"] > 0:
            print(f"\n该标签有 {selected_tag['children_count']} 个子标签，不能降级")
            print("请先删除或移动子标签")
            return
        
        print(f"\n当前: 一级标签 [{selected_tag['name']}]")
        print("选择新的父标签:")
        print_separator()
        
        root_tags = [t for t in tags if t["id"] != tag_id]
        if not root_tags:
            print("没有其他一级标签可作为父标签")
            return
        
        for i, tag in enumerate(root_tags, 1):
            print(f"  [{i}] {tag['name']}")
        print_separator()
        print("  [0] 取消")
        
        parent_choice = input("\n请选择父标签编号: ").strip()
        if parent_choice == "0":
            return
        
        try:
            idx = int(parent_choice) - 1
            if 0 <= idx < len(root_tags):
                new_parent_id = root_tags[idx]["id"]
                new_parent_name = root_tags[idx]["name"]
            else:
                print("无效的选择")
                return
        except ValueError:
            print("请输入有效的数字")
            return
        
        confirm = input(f"\n确认将 '{selected_tag['name']}' 降为 '{new_parent_name}' 的子标签？(y/n): ").strip().lower()
        if confirm == 'y':
            result = manager.change_parent(tag_id, new_parent_id)
            if result["success"]:
                print(f"\n✓ 降级成功: {selected_tag['name']} 现在是 {new_parent_name} 的子标签")
            else:
                print(f"\n✗ 降级失败: {result['error']}")
        else:
            print("已取消")


def merge_tags_flow(manager: TagManager):
    """合并标签流程"""
    tags = manager.get_all_tags_flat()
    
    if len(tags) < 2:
        print("\n至少需要2个标签才能合并")
        return
    
    print("\n" + "=" * 60)
    print("  合并标签")
    print("=" * 60)
    print("\n说明:")
    print("  将源标签的所有视频关联转移到目标标签，然后删除源标签")
    print("  注意: 只能合并同级标签")
    print_separator()
    
    print("\n当前标签列表:")
    print_separator()
    for tag in tags:
        level_str = "一级" if tag["level"] == 1 else f"二级[{tag['parent_name']}]"
        print(f"  [{tag['id']}] {tag['name']} ({level_str}, {tag['video_count']}视频)")
    
    print_separator()
    print("  [0] 取消")
    print_separator()
    
    source_id = input("\n请输入源标签ID（将被删除）: ").strip()
    if source_id == "0":
        return
    
    try:
        source_id = int(source_id)
    except ValueError:
        print("请输入有效的数字")
        return
    
    target_id = input("请输入目标标签ID（将保留）: ").strip()
    if target_id == "0":
        return
    
    try:
        target_id = int(target_id)
    except ValueError:
        print("请输入有效的数字")
        return
    
    source_tag = None
    target_tag = None
    for tag in tags:
        if tag["id"] == source_id:
            source_tag = tag
        if tag["id"] == target_id:
            target_tag = tag
    
    if not source_tag:
        print(f"源标签ID {source_id} 不存在")
        return
    if not target_tag:
        print(f"目标标签ID {target_id} 不存在")
        return
    
    if source_id == target_id:
        print("源标签和目标标签不能相同")
        return
    
    print(f"\n将要合并:")
    print(f"  源标签: {source_tag['name']} ({source_tag['video_count']}视频) -> 将被删除")
    print(f"  目标标签: {target_tag['name']} ({target_tag['video_count']}视频) -> 将保留")
    
    confirm = input("\n确认合并？(y/n): ").strip().lower()
    if confirm != 'y':
        print("已取消")
        return
    
    result = manager.merge_tags(source_id, target_id)
    
    if result["success"]:
        print(f"\n✓ 合并成功")
        print(f"  转移了 {result['transferred_relations']} 个视频关联")
        print(f"  源标签已删除")
    else:
        print(f"\n✗ 合并失败: {result['error']}")


def show_main_menu():
    """显示主菜单"""
    print("\n" + "=" * 60)
    print("  标签管理工具 v1.0")
    print("=" * 60)
    print("\n  请选择功能:")
    print_separator()
    print("  [1] 查看标签列表")
    print("      - 显示所有标签的树形结构")
    print()
    print("  [2] 创建标签")
    print("      - 创建一级标签或二级标签")
    print()
    print("  [3] 删除标签")
    print("      - 删除标签（需先处理子标签）")
    print()
    print("  [4] 重命名标签")
    print("      - 修改标签名称")
    print()
    print("  [5] 修改标签层级")
    print("      - 提升二级标签为一级标签")
    print("      - 降级一级标签为二级标签")
    print()
    print("  [6] 合并标签")
    print("      - 将一个标签合并到另一个标签")
    print_separator()
    print("  [0] 退出程序")
    print_separator()


def main():
    """主函数"""
    print("\n" + "=" * 60)
    print("  标签管理工具 v1.0")
    print("  用于管理视频数据库中的标签")
    print("=" * 60)
    
    db_file = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "video_library.db")
    db_path = f"sqlite:///{db_file}"
    
    if len(sys.argv) > 1:
        arg = sys.argv[1]
        if arg.endswith('.db'):
            db_path = f"sqlite:///{os.path.abspath(arg)}"
        else:
            db_path = arg
    
    try:
        manager = TagManager(db_url=db_path)
        print(f"\n✓ 数据库连接成功: {db_file}")
    except Exception as e:
        print(f"\n✗ 数据库连接失败: {e}")
        sys.exit(1)
    
    while True:
        try:
            show_main_menu()
            
            choice = input("请选择功能 (0-6): ").strip().lower()
            
            if choice == "0" or choice == "q":
                print("\n再见！")
                break
            elif choice == "1":
                show_tag_tree(manager)
                input("\n按回车键继续...")
            elif choice == "2":
                create_tag_flow(manager)
                input("\n按回车键继续...")
            elif choice == "3":
                delete_tag_flow(manager)
                input("\n按回车键继续...")
            elif choice == "4":
                rename_tag_flow(manager)
                input("\n按回车键继续...")
            elif choice == "5":
                change_level_flow(manager)
                input("\n按回车键继续...")
            elif choice == "6":
                merge_tags_flow(manager)
                input("\n按回车键继续...")
            else:
                print("无效的选择，请输入 0-6")
                input("\n按回车键继续...")
            
        except KeyboardInterrupt:
            print("\n\n操作已取消，再见！")
            break
        except Exception as e:
            print(f"\n发生错误: {e}")
            retry = input("是否继续？(y/n): ").strip().lower()
            if retry != 'y':
                break


if __name__ == "__main__":
    main()

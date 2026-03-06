"""
视频标签编辑器
交互式控制台工具，用于编辑视频标签（增加、删减、修改）
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from typing import Optional, List

from video_tag_system import DatabaseManager
from video_tag_system.services import TagService, VideoTagService
from video_tag_system.repositories import VideoRepository, TagRepository, VideoTagRepository
from video_tag_system.exceptions import VideoNotFoundError, TagNotFoundError


class VideoTagEditor:
    """视频标签编辑器"""
    
    def __init__(self, db_url: Optional[str] = None):
        self.db_manager = DatabaseManager(database_url=db_url or "sqlite:///./video_library.db", echo=False)
        self.db_manager.create_tables()
    
    def search_videos(self, keyword: str) -> List[dict]:
        """搜索视频"""
        with self.db_manager.get_session() as session:
            video_repo = VideoRepository(session)
            videos, _ = video_repo.list_all(page=1, page_size=50, search=keyword)
            
            result = []
            for video in videos:
                result.append({
                    "id": video.id,
                    "title": video.title or os.path.basename(video.file_path),
                    "file_path": video.file_path,
                    "duration": video.duration
                })
            return result
    
    def get_video_tags(self, video_id: int) -> List[dict]:
        """获取视频的标签"""
        with self.db_manager.get_session() as session:
            video_tag_repo = VideoTagRepository(session)
            tag_repo = TagRepository(session)
            tags = video_tag_repo.list_tags_by_video(video_id)
            
            result = []
            for tag in tags:
                parent_name = None
                if tag.parent_id:
                    parent = tag_repo.get_by_id(tag.parent_id)
                    parent_name = parent.name if parent else None
                result.append({
                    "id": tag.id,
                    "name": tag.name,
                    "parent_id": tag.parent_id,
                    "parent_name": parent_name
                })
            return result
    
    def get_all_tags(self) -> List[dict]:
        """获取所有标签（树形结构）"""
        with self.db_manager.get_session() as session:
            tag_service = TagService(session)
            tag_tree = tag_service.get_tag_tree()
            
            result = []
            for root_tag in tag_tree.items:
                result.append({
                    "id": root_tag.id,
                    "name": root_tag.name,
                    "level": 1,
                    "parent_id": None
                })
                for child in root_tag.children:
                    result.append({
                        "id": child.id,
                        "name": child.name,
                        "level": 2,
                        "parent_id": root_tag.id,
                        "parent_name": root_tag.name
                    })
            return result
    
    def add_tag_to_video(self, video_id: int, tag_id: int) -> dict:
        """为视频添加标签"""
        with self.db_manager.get_session() as session:
            video_tag_service = VideoTagService(session)
            return video_tag_service.add_tag_to_video(video_id, tag_id)
    
    def remove_tag_from_video(self, video_id: int, tag_id: int) -> dict:
        """从视频移除标签"""
        with self.db_manager.get_session() as session:
            video_tag_service = VideoTagService(session)
            return video_tag_service.remove_tag_from_video(video_id, tag_id)
    
    def set_video_tags(self, video_id: int, tag_ids: List[int]) -> dict:
        """设置视频标签（替换）"""
        with self.db_manager.get_session() as session:
            video_tag_service = VideoTagService(session)
            return video_tag_service.set_video_tags(video_id, tag_ids)
    
    def clear_video_tags(self, video_id: int) -> int:
        """清空视频所有标签"""
        with self.db_manager.get_session() as session:
            video_tag_repo = VideoTagRepository(session)
            return video_tag_repo.delete_by_video_id(video_id)


def clear_screen():
    """清屏"""
    os.system('cls' if os.name == 'nt' else 'clear')


def print_separator(char='-', length=60):
    """打印分隔线"""
    print(char * length)


def format_duration(seconds: Optional[int]) -> str:
    """格式化时长"""
    if not seconds:
        return "未知"
    minutes, secs = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    if hours > 0:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    return f"{minutes}:{secs:02d}"


def select_from_list(items: List[dict], prompt: str, key_name: str = "name") -> Optional[dict]:
    """从列表中选择一项"""
    if not items:
        print("\n没有可选项")
        return None
    
    print(f"\n{prompt}")
    print_separator()
    for i, item in enumerate(items, 1):
        extra_info = ""
        if "parent_name" in item and item["parent_name"]:
            extra_info = f" [{item['parent_name']}]"
        elif "duration" in item and item["duration"]:
            extra_info = f" ({format_duration(item['duration'])})"
        
        print(f"  [{i}] {item[key_name]}{extra_info}")
    
    print_separator()
    print(f"  [0] 返回/取消")
    print_separator()
    
    while True:
        try:
            choice = input("\n请选择编号: ").strip()
            if choice == "0" or choice.lower() == "q":
                return None
            
            idx = int(choice) - 1
            if 0 <= idx < len(items):
                return items[idx]
            print("无效的编号，请重新输入")
        except ValueError:
            print("请输入有效的数字")
        except KeyboardInterrupt:
            return None


def search_video_flow(editor: VideoTagEditor) -> Optional[dict]:
    """搜索视频流程"""
    while True:
        print("\n" + "=" * 60)
        print("  视频标签编辑器 - 搜索视频")
        print("=" * 60)
        
        keyword = input("\n请输入视频名称或关键词（输入 q 退出）: ").strip()
        
        if keyword.lower() == "q":
            return None
        
        if not keyword:
            print("请输入有效的搜索关键词")
            continue
        
        videos = editor.search_videos(keyword)
        
        if not videos:
            print(f"\n未找到包含 '{keyword}' 的视频")
            retry = input("是否继续搜索？(y/n): ").strip().lower()
            if retry != 'y':
                return None
            continue
        
        selected = select_from_list(videos, f"搜索结果 (共 {len(videos)} 个视频)", "title")
        if selected:
            return selected


def show_video_info(video: dict, tags: List[dict]):
    """显示视频信息和标签"""
    print("\n" + "=" * 60)
    print("  当前视频信息")
    print("=" * 60)
    print(f"  ID: {video['id']}")
    print(f"  标题: {video['title']}")
    print(f"  路径: {video['file_path']}")
    print(f"  时长: {format_duration(video.get('duration'))}")
    print_separator()
    
    if tags:
        print("  当前标签:")
        for tag in tags:
            parent_info = f" [{tag.get('parent_name', '')}]" if tag.get('parent_id') else ""
            print(f"    - [{tag['id']}] {tag['name']}{parent_info}")
    else:
        print("  当前标签: 无")
    print("=" * 60)


def add_tag_flow(editor: VideoTagEditor, video_id: int):
    """添加标签流程"""
    all_tags = editor.get_all_tags()
    
    if not all_tags:
        print("\n系统中暂无标签，请先创建标签")
        return
    
    current_tags = editor.get_video_tags(video_id)
    current_tag_ids = {t["id"] for t in current_tags}
    
    available_tags = []
    for tag in all_tags:
        if tag["id"] not in current_tag_ids:
            available_tags.append(tag)
    
    if not available_tags:
        print("\n该视频已拥有所有可用标签")
        return
    
    print(f"\n可添加的标签 (输入编号，多个用逗号分隔，如: 1,3,5):")
    print_separator()
    for i, tag in enumerate(available_tags, 1):
        parent_info = f" [{tag.get('parent_name', '')}]" if tag.get('parent_id') else ""
        print(f"  [{i}] {tag['name']}{parent_info}")
    print_separator()
    print("  [0] 取消")
    print_separator()
    
    while True:
        choice = input("\n请选择标签编号: ").strip()
        
        if choice == "0" or choice.lower() == "q":
            return
        
        try:
            indices = [int(x.strip()) for x in choice.split(",")]
            selected_tags = []
            
            for idx in indices:
                if 1 <= idx <= len(available_tags):
                    selected_tags.append(available_tags[idx - 1])
            
            if not selected_tags:
                print("无效的选择，请重新输入")
                continue
            
            print(f"\n将添加标签: {', '.join([t['name'] for t in selected_tags])}")
            confirm = input("确认添加？(y/n): ").strip().lower()
            
            if confirm == 'y':
                added_count = 0
                for tag in selected_tags:
                    result = editor.add_tag_to_video(video_id, tag["id"])
                    if result["added"]:
                        added_count += 1
                print(f"\n✓ 成功添加 {added_count} 个标签")
            return
            
        except ValueError:
            print("请输入有效的数字，多个用逗号分隔")


def remove_tag_flow(editor: VideoTagEditor, video_id: int):
    """移除标签流程"""
    current_tags = editor.get_video_tags(video_id)
    
    if not current_tags:
        print("\n该视频暂无标签")
        return
    
    print(f"\n当前标签 (输入编号，多个用逗号分隔，如: 1,3,5):")
    print_separator()
    for i, tag in enumerate(current_tags, 1):
        parent_info = f" [{tag.get('parent_name', '')}]" if tag.get('parent_name') else ""
        print(f"  [{i}] {tag['name']}{parent_info}")
    print_separator()
    print("  [0] 取消")
    print_separator()
    
    while True:
        choice = input("\n请选择要移除的标签编号: ").strip()
        
        if choice == "0" or choice.lower() == "q":
            return
        
        try:
            indices = [int(x.strip()) for x in choice.split(",")]
            selected_tags = []
            
            for idx in indices:
                if 1 <= idx <= len(current_tags):
                    selected_tags.append(current_tags[idx - 1])
            
            if not selected_tags:
                print("无效的选择，请重新输入")
                continue
            
            print(f"\n将移除标签: {', '.join([t['name'] for t in selected_tags])}")
            confirm = input("确认移除？(y/n): ").strip().lower()
            
            if confirm == 'y':
                removed_count = 0
                for tag in selected_tags:
                    result = editor.remove_tag_from_video(video_id, tag["id"])
                    if result["removed"]:
                        removed_count += 1
                print(f"\n✓ 成功移除 {removed_count} 个标签")
            return
            
        except ValueError:
            print("请输入有效的数字，多个用逗号分隔")


def replace_tags_flow(editor: VideoTagEditor, video_id: int):
    """替换标签流程"""
    all_tags = editor.get_all_tags()
    
    if not all_tags:
        print("\n系统中暂无标签，请先创建标签")
        return
    
    current_tags = editor.get_video_tags(video_id)
    current_tag_ids = {t["id"] for t in current_tags}
    
    print("\n所有标签 (输入编号，多个用逗号分隔，如: 1,3,5):")
    print_separator()
    for i, tag in enumerate(all_tags, 1):
        marker = "✓" if tag["id"] in current_tag_ids else " "
        parent_info = f" [{tag.get('parent_name', '')}]" if tag.get('parent_id') else ""
        print(f"  [{i}] [{marker}] {tag['name']}{parent_info}")
    print_separator()
    print("  [0] 取消")
    print_separator()
    
    while True:
        choice = input("\n请选择标签编号: ").strip()
        
        if choice == "0" or choice.lower() == "q":
            return
        
        try:
            indices = [int(x.strip()) for x in choice.split(",")]
            selected_tag_ids = []
            selected_names = []
            
            for idx in indices:
                if 1 <= idx <= len(all_tags):
                    tag = all_tags[idx - 1]
                    selected_tag_ids.append(tag["id"])
                    selected_names.append(tag["name"])
            
            if not selected_tag_ids:
                print("无效的选择，请重新输入")
                continue
            
            print(f"\n将设置标签: {', '.join(selected_names)}")
            confirm = input("确认替换？(y/n): ").strip().lower()
            
            if confirm == 'y':
                result = editor.set_video_tags(video_id, selected_tag_ids)
                print(f"\n✓ 标签设置成功:")
                print(f"  - 添加了 {result['tags_added']} 个标签")
                print(f"  - 移除了 {result['tags_removed']} 个标签")
                print(f"  - 当前共有 {result['current_tag_count']} 个标签")
            return
            
        except ValueError:
            print("请输入有效的数字，多个用逗号分隔")


def clear_tags_flow(editor: VideoTagEditor, video_id: int):
    """清空标签流程"""
    current_tags = editor.get_video_tags(video_id)
    
    if not current_tags:
        print("\n该视频暂无标签")
        return
    
    print(f"\n当前视频有 {len(current_tags)} 个标签:")
    for tag in current_tags:
        print(f"  - {tag['name']}")
    
    confirm = input("\n确认清空所有标签？(y/n): ").strip().lower()
    if confirm == 'y':
        count = editor.clear_video_tags(video_id)
        print(f"\n✓ 成功清空 {count} 个标签")


def edit_menu(editor: VideoTagEditor, video: dict):
    """编辑菜单"""
    while True:
        tags = editor.get_video_tags(video["id"])
        show_video_info(video, tags)
        
        print("\n操作菜单:")
        print_separator()
        print("  [1] 添加标签")
        print("  [2] 移除标签")
        print("  [3] 替换标签（批量设置）")
        print("  [4] 清空所有标签")
        print("  [5] 查看所有可用标签")
        print_separator()
        print("  [0] 返回搜索 / [q] 退出程序")
        print_separator()
        
        choice = input("\n请选择操作: ").strip().lower()
        
        if choice == "0":
            return
        elif choice == "q":
            print("\n再见！")
            sys.exit(0)
        elif choice == "1":
            add_tag_flow(editor, video["id"])
        elif choice == "2":
            remove_tag_flow(editor, video["id"])
        elif choice == "3":
            replace_tags_flow(editor, video["id"])
        elif choice == "4":
            clear_tags_flow(editor, video["id"])
        elif choice == "5":
            all_tags = editor.get_all_tags()
            print("\n所有可用标签:")
            print_separator()
            for tag in all_tags:
                parent_info = f" [{tag.get('parent_name', '')}]" if tag.get('parent_id') else ""
                print(f"  [{tag['id']}] {tag['name']}{parent_info}")
            print_separator()
            input("\n按回车键继续...")
        else:
            print("无效的选择")


def main():
    """主函数"""
    print("\n" + "=" * 60)
    print("  视频标签编辑器 v1.0")
    print("  用于交互式编辑视频标签")
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
        editor = VideoTagEditor(db_url=db_path)
        print(f"\n✓ 数据库连接成功: {db_file}")
    except Exception as e:
        print(f"\n✗ 数据库连接失败: {e}")
        sys.exit(1)
    
    while True:
        try:
            video = search_video_flow(editor)
            
            if video is None:
                print("\n再见！")
                break
            
            edit_menu(editor, video)
            
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

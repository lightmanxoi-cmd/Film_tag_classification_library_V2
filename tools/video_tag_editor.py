"""
视频标签编辑器

本模块提供交互式控制台工具，用于编辑视频标签。
支持以下功能：
- 搜索视频：按关键词搜索视频
- 查看标签：显示视频当前的所有标签
- 添加标签：为视频添加一个或多个标签
- 移除标签：从视频移除一个或多个标签
- 替换标签：批量设置视频的标签（替换现有标签）
- 清空标签：移除视频的所有标签

使用方式：
    python tools/video_tag_editor.py
    python tools/video_tag_editor.py /path/to/database.db

操作流程：
    1. 输入关键词搜索视频
    2. 从搜索结果中选择目标视频
    3. 在编辑菜单中选择操作（添加/移除/替换/清空标签）
    4. 完成后可继续搜索其他视频或退出

作者：Video Library System
创建时间：2024
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
    """
    视频标签编辑器类
    
    提供视频标签管理的核心功能，包括搜索视频、获取标签信息、
    添加/移除/设置标签等操作。
    
    属性：
        db_manager: 数据库管理器实例
    
    使用示例：
        editor = VideoTagEditor()
        videos = editor.search_videos("电影")
        editor.add_tag_to_video(video_id=1, tag_id=5)
    """
    
    def __init__(self, db_url: Optional[str] = None):
        """
        初始化视频标签编辑器
        
        Args:
            db_url: 数据库连接字符串，默认为当前目录下的video_library.db
        """
        self.db_manager = DatabaseManager(database_url=db_url or "sqlite:///./video_library.db", echo=False)
        self.db_manager.create_tables()
    
    def search_videos(self, keyword: str) -> List[dict]:
        """
        搜索视频
        
        根据关键词搜索视频标题或文件名，返回匹配的视频列表。
        
        Args:
            keyword: 搜索关键词
            
        Returns:
            视频字典列表，每个字典包含：
            - id: 视频ID
            - title: 视频标题
            - file_path: 文件路径
            - duration: 视频时长（秒）
        """
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
        """
        获取视频的标签列表
        
        Args:
            video_id: 视频ID
            
        Returns:
            标签字典列表，每个字典包含：
            - id: 标签ID
            - name: 标签名称
            - parent_id: 父标签ID（如果有）
            - parent_name: 父标签名称（如果有）
        """
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
        """
        获取所有标签（树形结构）
        
        返回系统中所有标签，按层级组织：
        - 一级标签在前
        - 二级标签紧跟其父标签
        
        Returns:
            标签字典列表，每个字典包含：
            - id: 标签ID
            - name: 标签名称
            - level: 标签层级（1或2）
            - parent_id: 父标签ID（二级标签才有）
            - parent_name: 父标签名称（二级标签才有）
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
        """
        为视频添加标签
        
        Args:
            video_id: 视频ID
            tag_id: 标签ID
            
        Returns:
            操作结果字典，包含：
            - added: 是否成功添加
            - message: 操作消息
        """
        with self.db_manager.get_session() as session:
            video_tag_service = VideoTagService(session)
            return video_tag_service.add_tag_to_video(video_id, tag_id)
    
    def remove_tag_from_video(self, video_id: int, tag_id: int) -> dict:
        """
        从视频移除标签
        
        Args:
            video_id: 视频ID
            tag_id: 标签ID
            
        Returns:
            操作结果字典，包含：
            - removed: 是否成功移除
            - message: 操作消息
        """
        with self.db_manager.get_session() as session:
            video_tag_service = VideoTagService(session)
            return video_tag_service.remove_tag_from_video(video_id, tag_id)
    
    def set_video_tags(self, video_id: int, tag_ids: List[int]) -> dict:
        """
        设置视频标签（替换现有标签）
        
        将视频的标签设置为指定的标签列表，移除不在列表中的标签。
        
        Args:
            video_id: 视频ID
            tag_ids: 标签ID列表
            
        Returns:
            操作结果字典，包含：
            - tags_added: 添加的标签数量
            - tags_removed: 移除的标签数量
            - current_tag_count: 当前标签总数
        """
        with self.db_manager.get_session() as session:
            video_tag_service = VideoTagService(session)
            return video_tag_service.set_video_tags(video_id, tag_ids)
    
    def clear_video_tags(self, video_id: int) -> int:
        """
        清空视频所有标签
        
        Args:
            video_id: 视频ID
            
        Returns:
            移除的标签数量
        """
        with self.db_manager.get_session() as session:
            video_tag_repo = VideoTagRepository(session)
            return video_tag_repo.delete_by_video_id(video_id)


def clear_screen():
    """
    清屏函数
    
    根据操作系统执行相应的清屏命令：
    - Windows: cls
    - Linux/Mac: clear
    """
    os.system('cls' if os.name == 'nt' else 'clear')


def print_separator(char='-', length=60):
    """
    打印分隔线
    
    Args:
        char: 分隔线字符，默认为'-'
        length: 分隔线长度，默认为60
    """
    print(char * length)


def format_duration(seconds: Optional[int]) -> str:
    """
    格式化时长显示
    
    将秒数转换为可读的时长格式：
    - 大于1小时：H:MM:SS
    - 小于1小时：M:SS
    
    Args:
        seconds: 时长秒数
        
    Returns:
        格式化的时长字符串，如 "1:30:45" 或 "45:30"
    """
    if not seconds:
        return "未知"
    minutes, secs = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    if hours > 0:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    return f"{minutes}:{secs:02d}"


def select_from_list(items: List[dict], prompt: str, key_name: str = "name") -> Optional[dict]:
    """
    从列表中选择一项
    
    显示列表项并提示用户选择，返回用户选择的项目。
    
    Args:
        items: 可选项列表
        prompt: 提示信息
        key_name: 用于显示的字段名
        
    Returns:
        用户选择的项目字典，如果取消则返回None
    """
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
    """
    搜索视频流程
    
    交互式搜索视频的流程：
    1. 提示用户输入搜索关键词
    2. 显示搜索结果
    3. 让用户选择目标视频
    
    Args:
        editor: 视频标签编辑器实例
        
    Returns:
        用户选择的视频字典，如果取消则返回None
    """
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
    """
    显示视频信息和标签
    
    在控制台中格式化显示视频的详细信息和当前标签。
    
    Args:
        video: 视频信息字典
        tags: 标签列表
    """
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
    """
    添加标签流程
    
    交互式添加标签的流程：
    1. 显示所有可添加的标签（排除已有标签）
    2. 让用户选择要添加的标签（支持多选）
    3. 确认后执行添加操作
    
    Args:
        editor: 视频标签编辑器实例
        video_id: 视频ID
    """
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
    """
    移除标签流程
    
    交互式移除标签的流程：
    1. 显示视频当前的标签
    2. 让用户选择要移除的标签（支持多选）
    3. 确认后执行移除操作
    
    Args:
        editor: 视频标签编辑器实例
        video_id: 视频ID
    """
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
    """
    替换标签流程
    
    交互式替换标签的流程：
    1. 显示所有标签，标记当前已选中的标签
    2. 让用户选择新的标签组合
    3. 确认后替换现有标签
    
    Args:
        editor: 视频标签编辑器实例
        video_id: 视频ID
    """
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
    """
    清空标签流程
    
    交互式清空标签的流程：
    1. 显示当前标签数量
    2. 确认后清空所有标签
    
    Args:
        editor: 视频标签编辑器实例
        video_id: 视频ID
    """
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
    """
    编辑菜单
    
    显示视频编辑菜单，提供标签管理操作选项。
    循环显示直到用户选择返回或退出。
    
    Args:
        editor: 视频标签编辑器实例
        video: 当前视频信息字典
    """
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


def quick_five_star_flow(editor: VideoTagEditor):
    """
    快捷五星标记流程
    
    快速为视频添加"评级/五星"标签的流程：
    1. 提示用户输入视频名称关键词
    2. 搜索匹配的视频
    3. 检查视频是否已有"评级"和"五星"标签
    4. 根据现有标签情况添加缺失的标签
    5. 完成后继续循环，直到用户主动退出
    
    Args:
        editor: 视频标签编辑器实例
    """
    all_tags = editor.get_all_tags()
    
    rating_tag_id = None
    five_star_tag_id = None
    
    for tag in all_tags:
        if tag["name"] == "评级" and tag.get("level") == 1:
            rating_tag_id = tag["id"]
        if tag["name"] == "五星" and tag.get("parent_name") == "评级":
            five_star_tag_id = tag["id"]
    
    if not rating_tag_id or not five_star_tag_id:
        print("\n错误：系统中未找到'评级'或'五星'标签，请先创建这些标签。")
        input("\n按回车键继续...")
        return
    
    while True:
        print("\n" + "=" * 60)
        print("  快捷五星标记")
        print("=" * 60)
        print("  为视频快速添加'评级/五星'标签")
        print("  （输入 q 返回主菜单）")
        print("=" * 60)
        
        keyword = input("\n请输入视频名称关键词: ").strip()
        
        if keyword.lower() == "q":
            return
        
        if not keyword:
            print("请输入有效的搜索关键词")
            continue
        
        videos = editor.search_videos(keyword)
        
        if not videos:
            print(f"未找到包含 '{keyword}' 的视频")
            continue
        
        if len(videos) == 1:
            selected = videos[0]
        else:
            selected = select_from_list(videos, f"搜索结果 (共 {len(videos)} 个视频)", "title")
            if not selected:
                continue
        
        video_id = selected["id"]
        video_title = selected["title"]
        
        current_tags = editor.get_video_tags(video_id)
        
        has_rating_tag = False
        has_five_star_tag = False
        
        for tag in current_tags:
            if tag.get("parent_name") == "评级" and tag["name"] == "五星":
                has_five_star_tag = True
            if tag["name"] == "评级" and not tag.get("parent_id"):
                has_rating_tag = True
        
        if has_five_star_tag:
            print(f"  '{video_title}' 已拥有'评级/五星'标签，跳过。")
            continue
        
        tags_to_add = []
        
        if not has_rating_tag:
            tags_to_add.append(("评级", rating_tag_id))
        
        tags_to_add.append(("五星", five_star_tag_id))
        
        added_count = 0
        failed_tags = []
        
        for name, tag_id in tags_to_add:
            result = editor.add_tag_to_video(video_id, tag_id)
            if result["added"]:
                added_count += 1
            else:
                failed_tags.append(name)
        
        if added_count > 0:
            print(f"✓ '{video_title}' 添加成功 (+{added_count} 标签)")
        
        if failed_tags:
            print(f"  以下标签添加失败: {', '.join(failed_tags)}")


def show_main_menu():
    """
    显示主菜单
    
    显示程序主菜单选项。
    """
    print("\n" + "=" * 60)
    print("  视频标签编辑器 v2.0")
    print("=" * 60)
    print("\n  请选择功能:")
    print_separator()
    print("  [1] 单独搜索更改")
    print("      - 搜索视频并编辑标签（添加/移除/替换/清空）")
    print()
    print("  [2] 快捷五星标记")
    print("      - 快速为视频添加'评级/五星'标签")
    print_separator()
    print("  [0] 退出程序")
    print_separator()


def main():
    """
    主函数 - 程序入口
    
    初始化编辑器并启动交互式界面。
    主循环处理功能选择和相应操作。
    """
    print("\n" + "=" * 60)
    print("  视频标签编辑器 v2.0")
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
            show_main_menu()
            
            choice = input("请选择功能 (0/1/2): ").strip().lower()
            
            if choice == "0" or choice == "q":
                print("\n再见！")
                break
            elif choice == "1":
                video = search_video_flow(editor)
                
                if video is None:
                    continue
                
                edit_menu(editor, video)
            elif choice == "2":
                quick_five_star_flow(editor)
            else:
                print("无效的选择，请输入 0、1 或 2")
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

"""
视频入库打标签工具

本模块提供交互式命令行工具，用于将视频文件及其标签信息导入数据库。
支持单个文件导入和文件夹批量导入两种模式。

主要功能：
- 单个文件导入：导入指定的视频文件并打标签
- 文件夹批量导入：扫描文件夹中的所有视频文件并批量导入
- 递归扫描：支持扫描子文件夹中的视频文件
- 自动匹配：根据文件名自动设置视频标题
- 重复检测：检测已存在的视频并更新而非重复创建

标签体系：
- 一级标签：主要分类标签（如：电影、电视剧、纪录片等）
- 二级标签：子分类标签（如：动作、喜剧、科幻等）

使用方式：
    交互式模式：
        python tools/video_importer.py --interactive
    
    单文件模式：
        python tools/video_importer.py --file "C:\\Videos\\movie.mp4" --level1 "电影" --level2 "动作"
    
    文件夹模式：
        python tools/video_importer.py --folder "C:\\Videos" --level1 "电影" --recursive

作者：Video Library System
创建时间：2024
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from typing import Optional, List

from sqlalchemy import select
from video_tag_system import DatabaseManager
from video_tag_system.models.video import Video, VideoCreate, VideoUpdate
from video_tag_system.services import VideoService, TagService, VideoTagService
from video_tag_system.exceptions import (
    VideoNotFoundError,
    TagNotFoundError,
    ValidationError,
)


class VideoImporterCLI:
    """
    视频入库打标签命令行工具类
    
    提供视频导入和标签管理的核心功能，支持交互式和命令行两种操作模式。
    
    属性：
        db_manager: 数据库管理器实例
        VIDEO_EXTENSIONS: 支持的视频文件扩展名集合
    
    使用示例：
        cli = VideoImporterCLI()
        cli.import_video("/path/to/video.mp4", "电影", "动作")
        cli.import_folder("/path/to/videos", "电影", recursive=True)
    """
    
    VIDEO_EXTENSIONS = {'.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv', '.webm', '.m4v', '.mpg', '.mpeg', '.3gp', '.ogv'}
    
    def __init__(self, db_url: Optional[str] = None):
        """
        初始化视频导入工具
        
        Args:
            db_url: 数据库连接字符串，默认为当前目录下的video_library.db
        """
        self.db_manager = DatabaseManager(database_url=db_url, echo=False)
        self.db_manager.create_tables()
    
    def _strip_quotes(self, text: str) -> str:
        """
        去除字符串两端的引号
        
        处理用户输入中可能包含的引号，便于复制粘贴路径。
        
        Args:
            text: 输入字符串
            
        Returns:
            去除两端引号后的字符串
        """
        if not text:
            return text
        text = text.strip()
        if len(text) >= 2:
            if (text[0] == '"' and text[-1] == '"') or (text[0] == "'" and text[-1] == "'"):
                text = text[1:-1]
        return text.strip()

    def _parse_file_paths(self, input_text: str) -> List[str]:
        """
        解析多个文件路径
        
        支持引号包裹的路径和空格分隔的多个路径。
        例如：'C:\\a.mp4' "D:\\b.mp4" E:\\c.mp4
        
        Args:
            input_text: 用户输入的路径字符串
            
        Returns:
            解析后的路径列表
        """
        if not input_text:
            return []

        paths = []
        current_path = []
        in_quotes = False
        quote_char = None

        i = 0
        while i < len(input_text):
            char = input_text[i]

            if char in ('"', "'") and not in_quotes:
                in_quotes = True
                quote_char = char
                i += 1
                continue
            elif char == quote_char and in_quotes:
                in_quotes = False
                quote_char = None
                i += 1
                continue

            if char.isspace() and not in_quotes:
                if current_path:
                    path = ''.join(current_path).strip()
                    if path:
                        paths.append(self._strip_quotes(path))
                    current_path = []
            else:
                current_path.append(char)

            i += 1

        if current_path:
            path = ''.join(current_path).strip()
            if path:
                paths.append(self._strip_quotes(path))

        return paths

    def _is_video_file(self, filename: str) -> bool:
        """
        判断文件是否为视频文件
        
        根据文件扩展名判断是否为支持的视频格式。
        
        Args:
            filename: 文件名
            
        Returns:
            bool: 是视频文件返回True，否则返回False
        """
        ext = os.path.splitext(filename)[1].lower()
        return ext in self.VIDEO_EXTENSIONS
    
    def _scan_video_files(self, folder_path: str, recursive: bool = False) -> List[str]:
        """
        扫描文件夹中的所有视频文件
        
        Args:
            folder_path: 文件夹路径
            recursive: 是否递归扫描子文件夹
            
        Returns:
            视频文件路径列表
        """
        video_files = []
        
        if not os.path.isdir(folder_path):
            return video_files
        
        if recursive:
            for root, dirs, files in os.walk(folder_path):
                for filename in files:
                    if self._is_video_file(filename):
                        video_files.append(os.path.join(root, filename))
        else:
            for filename in os.listdir(folder_path):
                filepath = os.path.join(folder_path, filename)
                if os.path.isfile(filepath) and self._is_video_file(filename):
                    video_files.append(filepath)
        
        return sorted(video_files)
    
    def import_video(
        self,
        file_path: str,
        level1_tag_name: str,
        level2_tag_name: Optional[str] = None
    ) -> bool:
        """
        导入视频到数据库
        
        根据标题判断视频是否已存在：
        - 如果存在：更新路径并添加新标签
        - 如果不存在：创建新视频记录并添加标签
        
        Args:
            file_path: 视频文件路径
            level1_tag_name: 一级标签名称
            level2_tag_name: 二级标签名称（可选）
            
        Returns:
            bool: 导入成功返回True，失败返回False
        """
        if not os.path.exists(file_path):
            print(f"✗ 错误: 文件不存在 '{file_path}'")
            return False
        
        filename = os.path.basename(file_path)
        title = os.path.splitext(filename)[0]
        
        with self.db_manager.get_session() as session:
            video_service = VideoService(session)
            tag_service = TagService(session)
            video_tag_service = VideoTagService(session)
            
            try:
                level1_tag = tag_service.get_tag_by_name(level1_tag_name, parent_id=None)
                level1_tag_id = level1_tag.id
            except TagNotFoundError:
                print(f"✗ 错误: 一级标签 '{level1_tag_name}' 不存在")
                return False
            
            level2_tag_id = None
            if level2_tag_name:
                try:
                    level2_tag = tag_service.get_tag_by_name(level2_tag_name, parent_id=level1_tag_id)
                    level2_tag_id = level2_tag.id
                except TagNotFoundError:
                    print(f"✗ 错误: 二级标签 '{level2_tag_name}' 不存在 (父标签: {level1_tag_name})")
                    return False
            
            tag_ids = [level1_tag_id]
            if level2_tag_id:
                tag_ids.append(level2_tag_id)
            
            stmt = select(Video).where(Video.title == title)
            existing_video = session.execute(stmt).scalar_one_or_none()
            
            if existing_video:
                print(f"检测到已存在的视频 (标题匹配): {existing_video.title} (ID: {existing_video.id})")

                update_data = VideoUpdate(title=title, file_path=file_path)
                updated_video = video_service.update_video(existing_video.id, update_data)

                existing_tags = video_tag_service.get_video_tags(existing_video.id)
                existing_tag_ids = {tag.id for tag in existing_tags}

                tags_added = 0
                for tag_id in tag_ids:
                    if tag_id not in existing_tag_ids:
                        video_tag_service.add_tag_to_video(existing_video.id, tag_id)
                        tags_added += 1

                updated_tags = video_tag_service.get_video_tags(existing_video.id)

                print(f"✓ 成功更新视频:")
                print(f"  - 标题: '{existing_video.title}'")
                print(f"  - 路径: '{file_path}'")
                print(f"  - 新增标签: {tags_added} 个")
                print(f"  - 当前标签数: {len(updated_tags)}")

            else:
                video_data = VideoCreate(
                    file_path=file_path,
                    title=title
                )

                video = video_service.create_video(video_data)

                for tag_id in tag_ids:
                    video_tag_service.add_tag_to_video(video.id, tag_id)

                print(f"✓ 成功导入视频:")
                print(f"  - ID: {video.id}")
                print(f"  - 标题: {video.title}")
                print(f"  - 路径: {video.file_path}")
                print(f"  - 一级标签: {level1_tag_name}")
                if level2_tag_name:
                    print(f"  - 二级标签: {level2_tag_name}")
                print(f"  - 标签总数: {len(tag_ids)}")

        return True

    def import_folder(
        self,
        folder_path: str,
        level1_tag_name: str,
        level2_tag_name: Optional[str] = None,
        recursive: bool = False
    ) -> None:
        """
        批量导入文件夹中的所有视频
        
        扫描指定文件夹中的所有视频文件并批量导入。
        
        Args:
            folder_path: 文件夹路径
            level1_tag_name: 一级标签名称
            level2_tag_name: 二级标签名称（可选）
            recursive: 是否递归扫描子文件夹
        """
        if not os.path.isdir(folder_path):
            print(f"✗ 错误: 文件夹不存在 '{folder_path}'")
            return
        
        video_files = self._scan_video_files(folder_path, recursive)
        
        if not video_files:
            print(f"✗ 在文件夹 '{folder_path}' 中未找到视频文件")
            return
        
        print(f"\n在文件夹 '{folder_path}' 中找到 {len(video_files)} 个视频文件")
        print(f"递归扫描: {'是' if recursive else '否'}")
        print(f"一级标签: {level1_tag_name}")
        if level2_tag_name:
            print(f"二级标签: {level2_tag_name}")
        print("\n开始批量导入...\n")
        
        success_count = 0
        failed_count = 0
        
        for i, video_file in enumerate(video_files, 1):
            print(f"[{i}/{len(video_files)}] 处理: {os.path.basename(video_file)}")
            try:
                if self.import_video(video_file, level1_tag_name, level2_tag_name):
                    success_count += 1
                else:
                    failed_count += 1
            except Exception as e:
                print(f"✗ 导入失败: {e}")
                failed_count += 1
            print()
        
        print("="*60)
        print(f"批量导入完成!")
        print(f"  - 成功: {success_count} 个")
        print(f"  - 失败: {failed_count} 个")
        print(f"  - 总计: {len(video_files)} 个")
        print("="*60)
    
    def interactive_import(self) -> None:
        """
        交互式导入视频
        
        提供菜单驱动的交互界面，用户可以通过选择菜单项来执行导入操作。
        支持单个文件导入和文件夹批量导入两种模式。
        """
        print("\n" + "="*60)
        print("视频入库打标签工具")
        print("="*60 + "\n")

        with self.db_manager.get_session() as session:
            tag_service = TagService(session)

            tag_tree = tag_service.get_tag_tree()

            if tag_tree.total == 0:
                print("⚠ 警告: 数据库中没有标签，请先创建标签")
                return

            print("可用标签:")
            for root_tag in tag_tree.items:
                print(f"  一级: {root_tag.name}")
                if root_tag.children:
                    for child in root_tag.children:
                        print(f"    二级: {child.name}")
            print()

        while True:
            try:
                print("请选择导入模式:")
                print("  1. 单个文件导入")
                print("  2. 文件夹批量导入")
                print("  q. 退出")

                mode = input("\n请输入选项 (1/2/q): ").strip().lower()

                if mode == 'q':
                    print("\n退出程序")
                    break

                if mode not in ['1', '2']:
                    print("✗ 错误: 无效的选项\n")
                    continue

                if mode == '1':
                    file_paths_input = input("请输入视频文件路径 (多个路径用空格分隔): ").strip()

                    file_paths = self._parse_file_paths(file_paths_input)

                    if not file_paths:
                        print("✗ 错误: 文件路径不能为空\n")
                        continue

                    valid_files = []
                    for fp in file_paths:
                        if not os.path.exists(fp):
                            print(f"✗ 错误: 文件不存在 '{fp}'")
                            continue
                        if os.path.isdir(fp):
                            print(f"✗ 错误: 请输入文件路径，不是文件夹路径 '{fp}'")
                            continue
                        valid_files.append(fp)

                    if not valid_files:
                        print("✗ 没有有效的文件路径\n")
                        continue

                    file_paths = valid_files
                else:
                    folder_path = input("请输入文件夹路径: ").strip()
                    folder_path = self._strip_quotes(folder_path)

                    if not folder_path:
                        print("✗ 错误: 文件夹路径不能为空\n")
                        continue

                    if not os.path.isdir(folder_path):
                        print(f"✗ 错误: 文件夹不存在 '{folder_path}'\n")
                        continue

                    recursive_input = input("是否递归扫描子文件夹? (y/n, 默认n): ").strip().lower()
                    recursive = recursive_input == 'y'

                    file_path = folder_path

                while True:
                    print("\n" + "-"*40)
                    if mode == '1':
                        if len(file_paths) == 1:
                            print(f"当前文件: {file_paths[0]}")
                        else:
                            print(f"当前文件数: {len(file_paths)} 个")
                            for i, fp in enumerate(file_paths, 1):
                                print(f"  {i}. {os.path.basename(fp)}")
                    else:
                        print(f"当前文件夹: {file_path}")
                    print("-"*40)

                    level1_tag_name = input("请输入一级标签名称 (输入 'b' 返回上级菜单, 'q' 退出): ").strip()
                    level1_tag_name = self._strip_quotes(level1_tag_name)

                    if level1_tag_name.lower() == 'q':
                        print("\n退出程序")
                        return
                    if level1_tag_name.lower() == 'b':
                        print("返回上级菜单...\n")
                        break
                    if not level1_tag_name:
                        print("✗ 错误: 一级标签不能为空\n")
                        continue

                    level2_tag_name = input("请输入二级标签名称 (可选，直接回车跳过): ").strip()
                    level2_tag_name = self._strip_quotes(level2_tag_name)
                    level2_tag_name = level2_tag_name if level2_tag_name else None

                    if mode == '1':
                        for i, fp in enumerate(file_paths, 1):
                            if len(file_paths) > 1:
                                print(f"\n[{i}/{len(file_paths)}] 处理: {os.path.basename(fp)}")
                            self.import_video(fp, level1_tag_name, level2_tag_name)
                    else:
                        self.import_folder(file_path, level1_tag_name, level2_tag_name, recursive)

                    print()

            except KeyboardInterrupt:
                print("\n\n操作已取消")
                break
            except Exception as e:
                print(f"✗ 错误: {e}\n")


def main():
    """
    主函数 - 命令行入口
    
    解析命令行参数并执行相应的导入操作。
    """
    import argparse
    
    parser = argparse.ArgumentParser(description="视频入库打标签工具")
    parser.add_argument(
        "--file",
        type=str,
        help="视频文件路径"
    )
    parser.add_argument(
        "--folder",
        type=str,
        help="视频文件夹路径 (批量导入)"
    )
    parser.add_argument(
        "--level1",
        type=str,
        help="一级标签名称"
    )
    parser.add_argument(
        "--level2",
        type=str,
        help="二级标签名称 (可选)"
    )
    parser.add_argument(
        "--recursive",
        action="store_true",
        help="递归扫描子文件夹 (仅用于文件夹模式)"
    )
    parser.add_argument(
        "--interactive",
        action="store_true",
        help="交互式模式"
    )
    
    args = parser.parse_args()
    
    cli = VideoImporterCLI()
    
    if args.interactive:
        cli.interactive_import()
    elif args.file and args.level1:
        cli.import_video(args.file, args.level1, args.level2)
    elif args.folder and args.level1:
        cli.import_folder(args.folder, args.level1, args.level2, args.recursive)
    else:
        print("使用方法:")
        print("  交互式模式: python tools/video_importer.py --interactive")
        print("  单文件模式: python tools/video_importer.py --file <路径> --level1 <标签> [--level2 <标签>]")
        print("  文件夹模式: python tools/video_importer.py --folder <路径> --level1 <标签> [--level2 <标签>] [--recursive]")
        print("\n示例:")
        print("  python tools/video_importer.py --interactive")
        print("  python tools/video_importer.py --file \"C:\\Videos\\movie.mp4\" --level1 \"电影\" --level2 \"动作\"")
        print("  python tools/video_importer.py --folder \"C:\\Videos\" --level1 \"电影\" --recursive")


if __name__ == "__main__":
    main()

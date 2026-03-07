"""
视频条目删除工具

本模块提供视频记录的删除功能，支持多种删除方式：
- 按ID删除：精确删除指定ID的视频
- 按标题删除：支持精确匹配和模糊匹配
- 按路径删除：支持精确匹配和模糊匹配
- 删除失效记录：删除本地文件不存在的视频记录
- 批量删除：支持一次性删除多个视频

使用方式：
    命令行模式：
        python tools/delete_videos.py --id 1,2,3
        python tools/delete_videos.py --title "测试" --exact
        python tools/delete_videos.py --missing --dry-run
    
    交互式模式：
        python tools/delete_videos.py --interactive

注意事项：
    - 删除操作不可逆，建议先使用 --dry-run 模拟运行
    - 删除视频记录会同时删除相关的标签关联关系（级联删除）
    - 本工具仅删除数据库记录，不会删除本地视频文件

作者：Video Library System
创建时间：2024
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import argparse
from pathlib import Path
from typing import List, Tuple, Optional
import time

from sqlalchemy import select, or_
from video_tag_system.core.database import DatabaseManager
from video_tag_system.models.video import Video


class VideoDeleter:
    """
    视频删除器类
    
    提供视频记录的增删改查操作，主要用于从数据库中删除视频记录。
    支持多种删除条件和批量操作。
    
    属性：
        db_manager: 数据库管理器实例，负责数据库连接和会话管理
        verbose: 是否输出详细日志信息
        results: 操作结果统计字典，包含删除数量、跳过数量、错误信息等
    
    使用示例：
        deleter = VideoDeleter(db_url="sqlite:///./video_library.db")
        result = deleter.delete_by_ids([1, 2, 3])
        deleter.print_summary()
    """
    
    def __init__(self, db_url: str = "sqlite:///./video_library.db", verbose: bool = True):
        """
        初始化视频删除器
        
        Args:
            db_url: 数据库连接字符串，默认为当前目录下的video_library.db
            verbose: 是否输出详细日志，默认为True
        """
        self.db_manager = DatabaseManager(database_url=db_url)
        self.verbose = verbose
        self.results = {
            'deleted': 0,
            'skipped': 0,
            'errors': [],
            'deleted_items': []
        }
    
    def get_video_by_id(self, video_id: int) -> Optional[Video]:
        """
        根据ID获取单个视频记录
        
        Args:
            video_id: 视频ID
            
        Returns:
            Video对象，如果不存在则返回None
        """
        with self.db_manager.get_session() as session:
            return session.get(Video, video_id)
    
    def get_videos_by_ids(self, video_ids: List[int]) -> List[Tuple[int, str, str]]:
        """
        根据ID列表批量获取视频记录
        
        Args:
            video_ids: 视频ID列表
            
        Returns:
            元组列表，每个元组格式为 (id, title, file_path)
        """
        with self.db_manager.get_session() as session:
            result = session.execute(
                select(Video.id, Video.title, Video.file_path).where(Video.id.in_(video_ids))
            ).all()
            return [(row[0], row[1], row[2]) for row in result]
    
    def get_videos_by_title(self, title: str, exact: bool = False) -> List[Tuple[int, str, str]]:
        """
        根据标题获取视频记录
        
        支持精确匹配和模糊匹配两种模式：
        - 精确匹配：标题必须完全相同
        - 模糊匹配：标题包含指定字符串即可
        
        Args:
            title: 要搜索的标题字符串
            exact: 是否精确匹配，默认为False（模糊匹配）
            
        Returns:
            元组列表，每个元组格式为 (id, title, file_path)
        """
        with self.db_manager.get_session() as session:
            if exact:
                result = session.execute(
                    select(Video.id, Video.title, Video.file_path).where(Video.title == title)
                ).all()
            else:
                result = session.execute(
                    select(Video.id, Video.title, Video.file_path).where(Video.title.contains(title))
                ).all()
            return [(row[0], row[1], row[2]) for row in result]
    
    def get_videos_by_path(self, path: str, exact: bool = False) -> List[Tuple[int, str, str]]:
        """
        根据文件路径获取视频记录
        
        支持精确匹配和模糊匹配两种模式：
        - 精确匹配：路径必须完全相同
        - 模糊匹配：路径包含指定字符串即可
        
        Args:
            path: 要搜索的路径字符串
            exact: 是否精确匹配，默认为False（模糊匹配）
            
        Returns:
            元组列表，每个元组格式为 (id, title, file_path)
        """
        with self.db_manager.get_session() as session:
            if exact:
                result = session.execute(
                    select(Video.id, Video.title, Video.file_path).where(Video.file_path == path)
                ).all()
            else:
                result = session.execute(
                    select(Video.id, Video.title, Video.file_path).where(Video.file_path.contains(path))
                ).all()
            return [(row[0], row[1], row[2]) for row in result]
    
    def get_videos_with_missing_files(self) -> List[Tuple[int, str, str]]:
        """
        获取本地文件不存在的视频记录
        
        遍历数据库中的所有视频，检查其文件路径对应的文件是否存在。
        用于清理数据库中的失效记录。
        
        Returns:
            元组列表，每个元组格式为 (id, title, file_path)
            只包含本地文件不存在的视频
        """
        with self.db_manager.get_session() as session:
            result = session.execute(
                select(Video.id, Video.title, Video.file_path)
            ).all()
            missing = []
            for vid, title, path in result:
                if not os.path.exists(path):
                    missing.append((vid, title, path))
            return missing
    
    def get_all_videos(self) -> List[Tuple[int, str, str]]:
        """
        获取数据库中所有视频记录
        
        Returns:
            元组列表，每个元组格式为 (id, title, file_path)
        """
        with self.db_manager.get_session() as session:
            result = session.execute(
                select(Video.id, Video.title, Video.file_path)
            ).all()
            return [(row[0], row[1], row[2]) for row in result]
    
    def delete_video_by_id(self, video_id: int) -> Tuple[bool, str]:
        """
        根据ID删除单个视频记录
        
        Args:
            video_id: 要删除的视频ID
            
        Returns:
            元组 (成功与否, 消息)
            成功时消息为视频标题，失败时为错误信息
        """
        try:
            with self.db_manager.get_session() as session:
                video = session.get(Video, video_id)
                if video:
                    title = video.title or video.file_path
                    session.delete(video)
                    return True, title
                return False, f"ID {video_id} 不存在"
        except Exception as e:
            return False, f"删除失败: {str(e)}"
    
    def delete_videos_batch(self, video_ids: List[int]) -> Tuple[int, List[Tuple[int, str]]]:
        """
        批量删除视频记录
        
        在单个事务中删除多个视频记录，提高删除效率。
        如果某个视频删除失败，不影响其他视频的删除。
        
        Args:
            video_ids: 要删除的视频ID列表
            
        Returns:
            元组 (成功数量, 失败列表)
            失败列表中的每个元素为 (video_id, 错误信息)
        """
        success_count = 0
        failed = []
        
        try:
            with self.db_manager.get_session() as session:
                for video_id in video_ids:
                    try:
                        video = session.get(Video, video_id)
                        if video:
                            session.delete(video)
                            success_count += 1
                        else:
                            failed.append((video_id, "视频不存在"))
                    except Exception as e:
                        failed.append((video_id, str(e)))
        except Exception as e:
            return 0, [(vid, str(e)) for vid in video_ids]
        
        return success_count, failed
    
    def delete_by_ids(
        self,
        video_ids: List[int],
        dry_run: bool = False
    ) -> dict:
        """
        按ID列表删除视频
        
        先查询匹配的视频，显示给用户确认，然后执行删除。
        支持模拟运行模式，只显示将要删除的视频而不实际删除。
        
        Args:
            video_ids: 视频ID列表
            dry_run: 是否模拟运行，默认为False
            
        Returns:
            操作结果字典，包含deleted、skipped、errors等字段
        """
        print(f"\n按ID删除: {video_ids}")
        
        videos = self.get_videos_by_ids(video_ids)
        
        if not videos:
            print("未找到匹配的视频")
            return self.results
        
        print(f"找到 {len(videos)} 个视频:")
        for vid, title, path in videos:
            print(f"  [ID:{vid}] {title or path}")
        
        if dry_run:
            print("\n[模拟运行] 将删除以上视频")
            self.results['skipped'] = len(videos)
            return self.results
        
        print("\n正在删除...")
        success_count, failed = self.delete_videos_batch(video_ids)
        
        self.results['deleted'] = success_count
        self.results['errors'] = failed
        
        return self.results
    
    def delete_by_title(
        self,
        title: str,
        exact: bool = False,
        dry_run: bool = False
    ) -> dict:
        """
        按标题删除视频
        
        Args:
            title: 标题（支持模糊匹配）
            exact: 是否精确匹配，默认为False
            dry_run: 是否模拟运行，默认为False
            
        Returns:
            操作结果字典
        """
        mode = "精确匹配" if exact else "模糊匹配"
        print(f"\n按标题删除 ({mode}): {title}")
        
        videos = self.get_videos_by_title(title, exact=exact)
        
        if not videos:
            print("未找到匹配的视频")
            return self.results
        
        print(f"找到 {len(videos)} 个视频:")
        for vid, title, path in videos:
            print(f"  [ID:{vid}] {title or path}")
        
        if dry_run:
            print("\n[模拟运行] 将删除以上视频")
            self.results['skipped'] = len(videos)
            return self.results
        
        print("\n正在删除...")
        video_ids = [vid for vid, _, _ in videos]
        success_count, failed = self.delete_videos_batch(video_ids)
        
        self.results['deleted'] = success_count
        self.results['errors'] = failed
        
        return self.results
    
    def delete_by_path(
        self,
        path: str,
        exact: bool = False,
        dry_run: bool = False
    ) -> dict:
        """
        按路径删除视频
        
        Args:
            path: 路径（支持模糊匹配）
            exact: 是否精确匹配，默认为False
            dry_run: 是否模拟运行，默认为False
            
        Returns:
            操作结果字典
        """
        mode = "精确匹配" if exact else "模糊匹配"
        print(f"\n按路径删除 ({mode}): {path}")
        
        videos = self.get_videos_by_path(path, exact=exact)
        
        if not videos:
            print("未找到匹配的视频")
            return self.results
        
        print(f"找到 {len(videos)} 个视频:")
        for vid, title, path in videos:
            print(f"  [ID:{vid}] {path}")
        
        if dry_run:
            print("\n[模拟运行] 将删除以上视频")
            self.results['skipped'] = len(videos)
            return self.results
        
        print("\n正在删除...")
        video_ids = [vid for vid, _, _ in videos]
        success_count, failed = self.delete_videos_batch(video_ids)
        
        self.results['deleted'] = success_count
        self.results['errors'] = failed
        
        return self.results
    
    def delete_missing_files(self, dry_run: bool = False) -> dict:
        """
        删除本地文件不存在的视频记录
        
        清理数据库中的失效记录，保持数据库与实际文件系统的一致性。
        
        Args:
            dry_run: 是否模拟运行，默认为False
            
        Returns:
            操作结果字典
        """
        print("\n查找本地文件不存在的视频...")
        
        videos = self.get_videos_with_missing_files()
        
        if not videos:
            print("所有视频文件都存在")
            return self.results
        
        print(f"找到 {len(videos)} 个文件缺失的视频:")
        for vid, title, path in videos:
            print(f"  [ID:{vid}] {title or path}")
            print(f"    路径: {path}")
        
        if dry_run:
            print("\n[模拟运行] 将删除以上视频")
            self.results['skipped'] = len(videos)
            return self.results
        
        print("\n正在删除...")
        video_ids = [vid for vid, _, _ in videos]
        success_count, failed = self.delete_videos_batch(video_ids)
        
        self.results['deleted'] = success_count
        self.results['errors'] = failed
        
        return self.results
    
    def delete_all(self, dry_run: bool = False, confirm: bool = False) -> dict:
        """
        删除所有视频（危险操作）
        
        此操作将清空数据库中的所有视频记录，需要特别谨慎。
        需要输入 'DELETE ALL' 进行二次确认。
        
        Args:
            dry_run: 是否模拟运行，默认为False
            confirm: 是否已确认删除，默认为False
            
        Returns:
            操作结果字典
        """
        videos = self.get_all_videos()
        
        print(f"\n数据库中共有 {len(videos)} 个视频")
        
        if dry_run:
            print("\n[模拟运行] 将删除所有视频")
            self.results['skipped'] = len(videos)
            return self.results
        
        if not confirm:
            print("\n警告: 即将删除所有视频记录!")
            response = input("请输入 'DELETE ALL' 确认删除: ")
            if response != 'DELETE ALL':
                print("已取消")
                return self.results
        
        print("\n正在删除所有视频...")
        video_ids = [v[0] for v in videos]
        success_count, failed = self.delete_videos_batch(video_ids)
        
        self.results['deleted'] = success_count
        self.results['errors'] = failed
        
        return self.results
    
    def interactive_delete(self):
        """
        交互式删除模式
        
        提供菜单驱动的交互界面，用户可以通过选择菜单项来执行各种删除操作。
        支持的操作包括：
        1. 按ID删除
        2. 按标题删除
        3. 按路径删除
        4. 删除文件缺失的视频
        5. 列出所有视频
        0. 退出
        """
        print("\n" + "="*60)
        print("交互式视频删除工具")
        print("="*60)
        
        while True:
            print("\n选择操作:")
            print("  1. 按ID删除")
            print("  2. 按标题删除")
            print("  3. 按路径删除")
            print("  4. 删除文件缺失的视频")
            print("  5. 列出所有视频")
            print("  0. 退出")
            
            choice = input("\n请选择 [0-5]: ").strip()
            
            if choice == '0':
                print("再见!")
                break
            elif choice == '1':
                id_input = input("请输入视频ID (多个ID用逗号分隔): ").strip()
                try:
                    ids = [int(x.strip()) for x in id_input.split(',')]
                    self.delete_by_ids(ids)
                except ValueError:
                    print("无效的ID格式")
            elif choice == '2':
                title = input("请输入标题: ").strip()
                if title:
                    exact = input("精确匹配? (y/N): ").strip().lower() == 'y'
                    self.delete_by_title(title, exact=exact)
            elif choice == '3':
                path = input("请输入路径: ").strip()
                if path:
                    exact = input("精确匹配? (y/N): ").strip().lower() == 'y'
                    self.delete_by_path(path, exact=exact)
            elif choice == '4':
                self.delete_missing_files()
            elif choice == '5':
                videos = self.get_all_videos()
                print(f"\n共 {len(videos)} 个视频:")
                for vid, title, path in videos[:50]:
                    print(f"  [ID:{vid}] {title or path}")
                if len(videos) > 50:
                    print(f"  ... 还有 {len(videos) - 50} 个")
            else:
                print("无效选择")
    
    def print_summary(self):
        """
        打印操作结果摘要
        
        显示删除操作的统计信息，包括：
        - 已删除的视频数量
        - 已跳过的视频数量
        - 删除失败的视频及错误信息
        """
        print(f"\n{'='*60}")
        print("删除完成!")
        print(f"{'='*60}")
        print(f"已删除: {self.results['deleted']} 个")
        print(f"已跳过: {self.results['skipped']} 个")
        
        if self.results['errors']:
            print(f"\n删除失败:")
            for video_id, error in self.results['errors']:
                print(f"  - [ID:{video_id}] {error}")


def main():
    """
    主函数 - 命令行入口
    
    解析命令行参数并执行相应的删除操作。
    支持多种删除模式和选项。
    """
    parser = argparse.ArgumentParser(
        description='视频条目删除工具 - 从数据库中删除视频记录',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
示例:
  # 按ID删除
  python tools/delete_videos.py --id 1
  python tools/delete_videos.py --id 1,2,3
  
  # 按标题删除（模糊匹配）
  python tools/delete_videos.py --title "测试"
  
  # 按标题删除（精确匹配）
  python tools/delete_videos.py --title "测试视频" --exact
  
  # 按路径删除
  python tools/delete_videos.py --path "D:\\Videos"
  
  # 删除本地文件不存在的视频
  python tools/delete_videos.py --missing
  
  # 模拟运行（不实际删除）
  python tools/delete_videos.py --title "测试" --dry-run
  
  # 交互式模式
  python tools/delete_videos.py --interactive
        '''
    )
    
    parser.add_argument(
        '--id',
        type=str,
        help='按ID删除，多个ID用逗号分隔'
    )
    parser.add_argument(
        '--title',
        type=str,
        help='按标题删除（默认模糊匹配）'
    )
    parser.add_argument(
        '--path',
        type=str,
        help='按路径删除（默认模糊匹配）'
    )
    parser.add_argument(
        '--missing',
        action='store_true',
        help='删除本地文件不存在的视频'
    )
    parser.add_argument(
        '--all',
        action='store_true',
        help='删除所有视频（危险操作）'
    )
    parser.add_argument(
        '--exact',
        action='store_true',
        help='精确匹配（用于标题或路径搜索）'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='模拟运行，不实际删除'
    )
    parser.add_argument(
        '--interactive', '-i',
        action='store_true',
        help='交互式模式'
    )
    parser.add_argument(
        '--db',
        default='sqlite:///./video_library.db',
        help='数据库连接字符串（默认: sqlite:///./video_library.db）'
    )
    parser.add_argument(
        '-q', '--quiet',
        action='store_true',
        help='安静模式，减少输出'
    )
    parser.add_argument(
        '--yes',
        action='store_true',
        help='跳过确认提示'
    )
    
    args = parser.parse_args()
    
    deleter = VideoDeleter(db_url=args.db, verbose=not args.quiet)
    
    try:
        if args.interactive:
            deleter.interactive_delete()
        elif args.id:
            ids = [int(x.strip()) for x in args.id.split(',')]
            deleter.delete_by_ids(ids, dry_run=args.dry_run)
            deleter.print_summary()
        elif args.title:
            deleter.delete_by_title(args.title, exact=args.exact, dry_run=args.dry_run)
            deleter.print_summary()
        elif args.path:
            deleter.delete_by_path(args.path, exact=args.exact, dry_run=args.dry_run)
            deleter.print_summary()
        elif args.missing:
            deleter.delete_missing_files(dry_run=args.dry_run)
            deleter.print_summary()
        elif args.all:
            deleter.delete_all(dry_run=args.dry_run, confirm=args.yes)
            deleter.print_summary()
        else:
            parser.print_help()
    except KeyboardInterrupt:
        print("\n操作已取消")
    except Exception as e:
        print(f"错误: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()

"""
批量视频地址更新工具
根据视频名称匹配本地文件，更新数据库中的文件路径
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import argparse
from pathlib import Path
from typing import Dict, List, Tuple
import time

from sqlalchemy import select
from video_tag_system.core.database import DatabaseManager
from video_tag_system.models.video import Video


class VideoPathUpdater:
    """视频路径更新器"""
    
    VIDEO_EXTENSIONS = {
        '.mp4', '.mkv', '.avi', '.wmv', '.mov', '.flv', 
        '.webm', '.m4v', '.mpg', '.mpeg', '.ts', '.m2ts', 
        '.rmvb', '.rm'
    }
    
    def __init__(self, db_url: str = "sqlite:///./video_library.db", verbose: bool = True):
        self.db_manager = DatabaseManager(database_url=db_url)
        self.verbose = verbose
        self.results = {
            'updated': 0,
            'skipped': 0,
            'not_found_count': 0,
            'errors': [],
            'matched': [],
            'not_found': []
        }
    
    def get_all_videos(self) -> List[Tuple[int, str, str]]:
        """
        从数据库获取所有视频
        
        Returns:
            [(video_id, title, current_path), ...]
        """
        with self.db_manager.get_session() as session:
            result = session.execute(
                select(Video.id, Video.title, Video.file_path)
            ).all()
            return [(row[0], row[1], row[2]) for row in result]
    
    def scan_local_videos(self, root_path: str) -> Dict[str, str]:
        """
        扫描本地路径中的所有视频文件
        
        Returns:
            {文件名(不含后缀): 完整路径}
        """
        root = Path(root_path)
        if not root.exists():
            raise FileNotFoundError(f"路径不存在: {root_path}")
        
        local_videos = {}
        count = 0
        
        for ext in self.VIDEO_EXTENSIONS:
            for file_path in root.rglob(f"*{ext}"):
                name_without_ext = file_path.stem
                if name_without_ext not in local_videos:
                    local_videos[name_without_ext] = str(file_path)
                    count += 1
                    if self.verbose and count % 500 == 0:
                        print(f"  已扫描 {count} 个视频文件...")
        
        print(f"  本地共找到 {count} 个视频文件")
        return local_videos
    
    def match_videos(
        self,
        db_videos: List[Tuple[int, str, str]],
        local_videos: Dict[str, str]
    ) -> Dict[str, List]:
        """
        匹配数据库视频与本地文件
        
        Args:
            db_videos: [(video_id, title, current_path), ...]
            local_videos: {文件名: 完整路径}
            
        Returns:
            {
                'matched': [(video_id, title, old_path, new_path), ...],
                'not_found': [(video_id, title), ...]
            }
        """
        matched = []
        not_found = []
        
        for video_id, title, current_path in db_videos:
            if not title:
                continue
            
            if title in local_videos:
                new_path = local_videos[title]
                matched.append((video_id, title, current_path, new_path))
            else:
                not_found.append((video_id, title))
        
        return {
            'matched': matched,
            'not_found': not_found
        }
    
    def update_video_paths_batch(self, updates: List[Tuple[int, str]]) -> Tuple[int, List[Tuple[int, str]]]:
        """
        批量更新视频路径（单事务）
        
        Args:
            updates: [(video_id, new_path), ...]
            
        Returns:
            (成功数量, 失败列表)
        """
        success_count = 0
        failed = []
        
        try:
            with self.db_manager.get_session() as session:
                for video_id, new_path in updates:
                    try:
                        video = session.get(Video, video_id)
                        if video:
                            video.file_path = new_path
                            success_count += 1
                        else:
                            failed.append((video_id, "视频不存在"))
                    except Exception as e:
                        failed.append((video_id, str(e)))
        except Exception as e:
            if self.verbose:
                print(f"批量更新事务失败: {e}")
            return 0, [(vid, str(e)) for vid, _ in updates]
        
        return success_count, failed
    
    def update_video_path(self, video_id: int, new_path: str) -> bool:
        """更新单个视频的路径"""
        try:
            with self.db_manager.get_session() as session:
                video = session.get(Video, video_id)
                if video:
                    video.file_path = new_path
                    return True
                return False
        except Exception as e:
            if self.verbose:
                print(f"更新视频 {video_id} 失败: {e}")
            return False
    
    def export_not_found(self, output_file: str = "not_found_videos.txt"):
        """导出未找到的视频列表"""
        with open(output_file, 'w', encoding='utf-8') as f:
            for video_id, title in self.results['not_found']:
                f.write(f"{video_id}\t{title}\n")
        print(f"未找到的视频列表已导出到: {output_file}")
    
    def run(
        
        self,
        search_path: str,
        dry_run: bool = False,
        filter_missing: bool = False
    ) -> Dict:
        """
        执行批量更新
        
        Args:
            search_path: 搜索路径
            dry_run: 仅模拟运行，不实际更新
            filter_missing: 仅处理当前路径不存在的视频
        """
        print(f"\n{'='*60}")
        print("批量视频地址更新工具")
        print(f"{'='*60}")
        print(f"搜索路径: {search_path}")
        print(f"模式: {'模拟运行(不更新数据库)' if dry_run else '实际更新'}")
        if filter_missing:
            print("筛选: 仅处理路径失效的视频")
        print(f"{'='*60}\n")
        
        start_time = time.time()
        
        print("步骤1: 从数据库获取视频列表...")
        db_videos = self.get_all_videos()
        print(f"数据库中共有 {len(db_videos)} 个视频")
        
        if filter_missing:
            print("\n筛选路径失效的视频...")
            db_videos = [
                (vid, title, path) for vid, title, path in db_videos
                if not os.path.exists(path)
            ]
            print(f"路径失效的视频: {len(db_videos)} 个")
        
        print("\n步骤2: 扫描本地视频文件...")
        local_videos = self.scan_local_videos(search_path)
        
        print("\n步骤3: 匹配视频...")
        match_result = self.match_videos(db_videos, local_videos)
        
        matched = match_result['matched']
        not_found = match_result['not_found']
        
        print(f"\n匹配结果:")
        print(f"  匹配成功: {len(matched)} 个")
        print(f"  未找到文件: {len(not_found)} 个")
        
        if not matched:
            print("\n没有需要更新的视频")
            return self.results
        
        print(f"\n步骤4: {'模拟更新' if dry_run else '更新数据库'}...")
        
        updates_to_apply = []
        
        for video_id, title, old_path, new_path in matched:
            if old_path == new_path:
                self.results['skipped'] += 1
                if self.verbose:
                    print(f"  跳过 [ID:{video_id}] {title} (路径未变化)")
                continue
            
            if dry_run:
                self.results['updated'] += 1
                if self.verbose:
                    print(f"  [模拟] [ID:{video_id}] {title}")
                    print(f"    旧路径: {old_path}")
                    print(f"    新路径: {new_path}")
            else:
                updates_to_apply.append((video_id, new_path, title, old_path))
        
        if updates_to_apply and not dry_run:
            print(f"  正在批量更新 {len(updates_to_apply)} 条记录...")
            
            updates = [(vid, path) for vid, path, _, _ in updates_to_apply]
            success_count, failed = self.update_video_paths_batch(updates)
            
            self.results['updated'] = success_count
            
            for vid, path, title, old_path in updates_to_apply:
                if self.verbose:
                    print(f"  ✓ [ID:{vid}] {title}")
                    print(f"    旧: {old_path}")
                    print(f"    新: {path}")
            
            for vid, error in failed:
                self.results['errors'].append((vid, f"错误: {error}"))
        
        self.results['matched'] = matched
        self.results['not_found'] = not_found
        self.results['not_found_count'] = len(not_found)
        
        elapsed = time.time() - start_time
        
        print(f"\n{'='*60}")
        print("更新完成!")
        print(f"{'='*60}")
        print(f"已更新: {self.results['updated']} 个")
        print(f"已跳过: {self.results['skipped']} 个")
        print(f"未匹配: {self.results['not_found_count']} 个")
        print(f"耗时: {elapsed:.1f} 秒")
        
        if self.results['errors']:
            print(f"\n更新失败的视频:")
            for video_id, title in self.results['errors']:
                print(f"  - [ID:{video_id}] {title}")
        
        return self.results


def main():
    parser = argparse.ArgumentParser(
        description='批量视频地址更新工具 - 根据视频名称匹配并更新数据库路径',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
示例:
  python tools/update_video_paths.py "D:\\Videos"
  python tools/update_video_paths.py "D:\\Videos" --dry-run
  python tools/update_video_paths.py "D:\\Videos" --filter-missing
  python tools/update_video_paths.py "D:\\Videos" --export-not-found
        '''
    )
    
    parser.add_argument(
        'path',
        help='要搜索的本地路径'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='模拟运行，不实际更新数据库'
    )
    parser.add_argument(
        '--filter-missing',
        action='store_true',
        help='仅处理当前路径不存在的视频'
    )
    parser.add_argument(
        '--export-not-found',
        action='store_true',
        help='导出未找到的视频列表到文件'
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
    
    args = parser.parse_args()
    
    updater = VideoPathUpdater(db_url=args.db, verbose=not args.quiet)
    
    try:
        result = updater.run(
            search_path=args.path,
            dry_run=args.dry_run,
            filter_missing=args.filter_missing
        )
        
        if args.export_not_found:
            updater.export_not_found()
            
    except FileNotFoundError as e:
        print(f"错误: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"错误: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()

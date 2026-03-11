"""
视频名称哈希字符重命名工具

本模块用于搜索并重命名数据库中以 # 结尾的视频。
将视频标题和文件名中的尾部 # 替换为 _666。

主要功能：
- 搜索数据库中标题以 # 结尾的视频
- 更新数据库中的视频标题和文件路径
- 重命名本地视频文件
- 支持预览模式（dry-run）

使用方式：
    python tools/rename_videos_with_hash.py
    python tools/rename_videos_with_hash.py --dry-run
    python tools/rename_videos_with_hash.py --db-path "E:\\path\\to\\video_library.db"

作者：Video Library System
创建时间：2024
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import argparse
import shutil
from pathlib import Path
from typing import List, Tuple, Optional
from dataclasses import dataclass

from sqlalchemy import select, update
from video_tag_system.core.database import DatabaseManager
from video_tag_system.models.video import Video


@dataclass
class RenameResult:
    """重命名结果数据类"""
    video_id: int
    old_title: str
    new_title: str
    old_path: str
    new_path: str
    file_renamed: bool
    success: bool
    error: Optional[str] = None


class VideoHashRenamer:
    """
    视频哈希字符重命名器类
    
    提供搜索并重命名以 # 结尾的视频的功能。
    同时更新数据库记录和本地文件。
    
    属性：
        db_manager: 数据库管理器实例
        dry_run: 是否为预览模式
        results: 操作结果列表
    
    使用示例：
        renamer = VideoHashRenamer()
        results = renamer.run()
    """
    
    def __init__(self, db_url: str = "sqlite:///./video_library.db", dry_run: bool = False):
        """
        初始化视频哈希字符重命名器
        
        Args:
            db_url: 数据库连接字符串，默认为当前目录下的video_library.db
            dry_run: 是否为预览模式，默认为False
        """
        self.db_manager = DatabaseManager(database_url=db_url)
        self.dry_run = dry_run
        self.results: List[RenameResult] = []
    
    def find_videos_with_hash(self) -> List[Tuple[int, str, str]]:
        """
        搜索数据库中标题以 # 结尾的视频
        
        Returns:
            元组列表，每个元组格式为 (video_id, title, file_path)
        """
        with self.db_manager.get_session() as session:
            result = session.execute(
                select(Video.id, Video.title, Video.file_path)
                .where(Video.title.like('%#'))
            ).all()
            return [(row[0], row[1], row[2]) for row in result]
    
    def generate_new_names(self, title: str, file_path: str) -> Tuple[str, str]:
        """
        生成新的视频标题和文件路径
        
        将标题和文件名中的尾部 # 替换为 _666
        
        Args:
            title: 原始视频标题
            file_path: 原始文件路径
            
        Returns:
            元组 (new_title, new_file_path)
        """
        # 替换标题中的尾部 #
        new_title = title.rstrip('#') + '_666' if title.endswith('#') else title
        
        # 替换文件名中的尾部 #
        old_path = Path(file_path)
        old_name = old_path.stem  # 不含扩展名的文件名
        old_suffix = old_path.suffix  # 扩展名
        
        if old_name.endswith('#'):
            new_name = old_name.rstrip('#') + '_666' + old_suffix
        else:
            new_name = old_path.name
        
        new_file_path = str(old_path.parent / new_name)
        
        return new_title, new_file_path
    
    def rename_file(self, old_path: str, new_path: str) -> Tuple[bool, Optional[str]]:
        """
        重命名本地视频文件
        
        Args:
            old_path: 原文件路径
            new_path: 新文件路径
            
        Returns:
            元组 (success, error_message)
        """
        old_file = Path(old_path)
        new_file = Path(new_path)
        
        # 检查原文件是否存在
        if not old_file.exists():
            return False, f"原文件不存在: {old_path}"
        
        # 检查新文件是否已存在
        if new_file.exists():
            return False, f"目标文件已存在: {new_path}"
        
        try:
            if not self.dry_run:
                shutil.move(str(old_file), str(new_file))
            return True, None
        except Exception as e:
            return False, f"文件重命名失败: {str(e)}"
    
    def update_database(self, video_id: int, new_title: str, new_path: str) -> Tuple[bool, Optional[str]]:
        """
        更新数据库中的视频记录
        
        Args:
            video_id: 视频ID
            new_title: 新标题
            new_path: 新文件路径
            
        Returns:
            元组 (success, error_message)
        """
        try:
            with self.db_manager.get_session() as session:
                if not self.dry_run:
                    session.execute(
                        update(Video)
                        .where(Video.id == video_id)
                        .values(
                            title=new_title,
                            file_path=new_path,
                            updated_at=session.query(Video).filter(Video.id == video_id).first().updated_at
                        )
                    )
                    session.commit()
                return True, None
        except Exception as e:
            return False, f"数据库更新失败: {str(e)}"
    
    def process_video(self, video_id: int, title: str, file_path: str) -> RenameResult:
        """
        处理单个视频的重命名
        
        Args:
            video_id: 视频ID
            title: 视频标题
            file_path: 文件路径
            
        Returns:
            RenameResult 对象
        """
        new_title, new_path = self.generate_new_names(title, file_path)
        
        # 如果标题没有变化，跳过
        if new_title == title:
            return RenameResult(
                video_id=video_id,
                old_title=title,
                new_title=title,
                old_path=file_path,
                new_path=file_path,
                file_renamed=False,
                success=True,
                error="标题不以 # 结尾，无需处理"
            )
        
        # 第一步：重命名文件
        file_renamed, file_error = self.rename_file(file_path, new_path)
        if not file_renamed:
            return RenameResult(
                video_id=video_id,
                old_title=title,
                new_title=new_title,
                old_path=file_path,
                new_path=new_path,
                file_renamed=False,
                success=False,
                error=file_error
            )
        
        # 第二步：更新数据库
        db_updated, db_error = self.update_database(video_id, new_title, new_path)
        if not db_updated:
            # 如果数据库更新失败，尝试回滚文件重命名
            if file_renamed and not self.dry_run:
                try:
                    shutil.move(new_path, file_path)
                except Exception as e:
                    return RenameResult(
                        video_id=video_id,
                        old_title=title,
                        new_title=new_title,
                        old_path=file_path,
                        new_path=new_path,
                        file_renamed=True,
                        success=False,
                        error=f"数据库更新失败且无法回滚文件: {db_error}, 回滚错误: {str(e)}"
                    )
            
            return RenameResult(
                video_id=video_id,
                old_title=title,
                new_title=new_title,
                old_path=file_path,
                new_path=new_path,
                file_renamed=file_renamed,
                success=False,
                error=db_error
            )
        
        return RenameResult(
            video_id=video_id,
            old_title=title,
            new_title=new_title,
            old_path=file_path,
            new_path=new_path,
            file_renamed=file_renamed,
            success=True
        )
    
    def run(self) -> List[RenameResult]:
        """
        执行重命名操作
        
        Returns:
            RenameResult 列表
        """
        print("=" * 60)
        print("视频名称哈希字符重命名工具")
        print("=" * 60)
        
        if self.dry_run:
            print("\n[预览模式] 不会实际修改任何数据\n")
        
        # 查找需要处理的视频
        print("正在搜索标题以 # 结尾的视频...")
        videos = self.find_videos_with_hash()
        print(f"找到 {len(videos)} 个需要处理的视频\n")
        
        if not videos:
            print("没有需要处理的视频")
            return []
        
        # 显示预览
        print("-" * 60)
        print("预览:")
        print("-" * 60)
        for video_id, title, file_path in videos:
            new_title, new_path = self.generate_new_names(title, file_path)
            print(f"\n视频 ID: {video_id}")
            print(f"  原标题: {title}")
            print(f"  新标题: {new_title}")
            print(f"  原路径: {file_path}")
            print(f"  新路径: {new_path}")
        
        print("\n" + "=" * 60)
        
        if self.dry_run:
            print("预览模式完成，未进行实际修改")
            return []
        
        # 确认是否继续
        confirm = input("\n确认执行重命名操作? (yes/no): ")
        if confirm.lower() not in ('yes', 'y'):
            print("操作已取消")
            return []
        
        # 执行重命名
        print("\n开始执行重命名...")
        print("-" * 60)
        
        for video_id, title, file_path in videos:
            result = self.process_video(video_id, title, file_path)
            self.results.append(result)
            
            if result.success:
                print(f"✓ 视频 {video_id}: {result.old_title} -> {result.new_title}")
            else:
                print(f"✗ 视频 {video_id}: 失败 - {result.error}")
        
        # 打印统计
        print("\n" + "=" * 60)
        print("处理结果统计:")
        print("=" * 60)
        success_count = sum(1 for r in self.results if r.success)
        error_count = len(self.results) - success_count
        print(f"成功: {success_count}")
        print(f"失败: {error_count}")
        print(f"总计: {len(self.results)}")
        
        if error_count > 0:
            print("\n失败的记录:")
            for result in self.results:
                if not result.success:
                    print(f"  视频 {result.video_id}: {result.error}")
        
        return self.results


def main():
    """主入口函数"""
    parser = argparse.ArgumentParser(
        description='重命名以 # 结尾的视频，将 # 替换为 _666'
    )
    parser.add_argument(
        '--db-path',
        type=str,
        default='./video_library.db',
        help='数据库文件路径 (默认: ./video_library.db)'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='预览模式，不实际修改数据'
    )
    
    args = parser.parse_args()
    
    # 构建数据库URL
    db_path = Path(args.db_path).resolve()
    db_url = f"sqlite:///{db_path}"
    
    print(f"数据库路径: {db_path}")
    
    # 检查数据库文件是否存在
    if not db_path.exists():
        print(f"错误: 数据库文件不存在: {db_path}")
        sys.exit(1)
    
    # 执行重命名
    renamer = VideoHashRenamer(db_url=db_url, dry_run=args.dry_run)
    results = renamer.run()
    
    # 根据结果设置退出码
    if results and not all(r.success for r in results):
        sys.exit(1)
    
    sys.exit(0)


if __name__ == '__main__':
    main()

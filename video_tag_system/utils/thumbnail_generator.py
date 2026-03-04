"""
视频缩略图生成模块
"""
import os
import subprocess
import json
import re
from pathlib import Path
from typing import Optional, List, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading


class ThumbnailGenerator:
    """视频缩略图生成器"""
    
    THUMBNAIL_WIDTH = 640
    THUMBNAIL_HEIGHT = 360
    
    def __init__(self, thumbnail_dir: str = "web/static/thumbnails"):
        self.thumbnail_dir = Path(thumbnail_dir)
        self.thumbnail_dir.mkdir(parents=True, exist_ok=True)
        self.cache_file = self.thumbnail_dir / "thumbnail_cache.json"
        self.cache = self._load_cache()
        self._lock = threading.Lock()
        
    def _load_cache(self) -> dict:
        """加载缩略图缓存"""
        if self.cache_file.exists():
            try:
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                return {}
        return {}
    
    def _save_cache(self):
        """保存缩略图缓存"""
        with open(self.cache_file, 'w', encoding='utf-8') as f:
            json.dump(self.cache, f, ensure_ascii=False, indent=2)
    
    def _sanitize_title(self, title: str) -> str:
        """
        清理标题，生成安全的文件名
        移除或替换不安全的字符
        """
        if not title:
            return ""
        safe_title = re.sub(r'[<>:"/\\|?*]', '_', title)
        safe_title = re.sub(r'\s+', '_', safe_title)
        safe_title = safe_title.strip('._')
        return safe_title
    
    def _get_thumbnail_path_by_title(self, title: str) -> Path:
        """根据标题获取缩略图路径"""
        safe_title = self._sanitize_title(title)
        if safe_title:
            return self.thumbnail_dir / f"{safe_title}.jpg"
        return None
    
    def _get_thumbnail_path_by_id(self, video_id: int) -> Path:
        """根据视频ID获取缩略图路径（后备方案）"""
        return self.thumbnail_dir / f"video_{video_id}.jpg"
    
    def has_thumbnail(self, title: str) -> bool:
        """
        检查是否已有缩略图（通过标题名称）
        
        Args:
            title: 视频标题
            
        Returns:
            是否存在缩略图
        """
        if not title:
            return False
        thumb_path = self._get_thumbnail_path_by_title(title)
        return thumb_path and thumb_path.exists()
    
    def generate_thumbnail(
        self, 
        video_path: str, 
        title: str,
        time_offset: float = 5
    ) -> Optional[str]:
        """
        为视频生成缩略图
        
        Args:
            video_path: 视频文件路径
            title: 视频标题（用于命名缩略图）
            time_offset: 截取时间点（秒）
            
        Returns:
            缩略图路径或None
        """
        if not os.path.exists(video_path):
            print(f"Video file not found: {video_path}")
            return None
        
        if not title:
            print(f"Video title is empty, cannot generate thumbnail")
            return None
        
        thumb_path = self._get_thumbnail_path_by_title(title)
        if not thumb_path:
            return None
        
        try:
            cmd = [
                'ffmpeg',
                '-y',
                '-i', video_path,
                '-ss', str(time_offset),
                '-vframes', '1',
                '-vf', f'scale={self.THUMBNAIL_WIDTH}:{self.THUMBNAIL_HEIGHT}:force_original_aspect_ratio=decrease,pad={self.THUMBNAIL_WIDTH}:{self.THUMBNAIL_HEIGHT}:(ow-iw)/2:(oh-ih)/2:black',
                '-q:v', '5',
                str(thumb_path)
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            )
            
            if result.returncode == 0 and thumb_path.exists():
                with self._lock:
                    self.cache[title] = {
                        'file_path': video_path,
                        'thumbnail': str(thumb_path)
                    }
                    self._save_cache()
                return str(thumb_path)
            else:
                print(f"FFmpeg error for '{title}': {result.stderr.decode() if result.stderr else 'Unknown error'}")
                return None
                
        except FileNotFoundError:
            print("FFmpeg not installed, cannot generate thumbnail")
            return None
        except Exception as e:
            print(f"Failed to generate thumbnail: {e}")
            return None
    
    def generate_thumbnail_safe(self, video_path: str, title: str) -> Optional[str]:
        """安全地生成缩略图，尝试多个时间点"""
        time_offsets = ['5', '10', '3', '1', '0.5']
        
        for offset in time_offsets:
            result = self.generate_thumbnail(video_path, title, time_offset=float(offset))
            if result:
                return result
        
        return None
    
    def batch_generate(
        self, 
        videos: List[Tuple[int, str, str]], 
        max_workers: int = 4,
        force: bool = False
    ) -> dict:
        """
        批量生成缩略图
        
        Args:
            videos: [(video_id, file_path, title), ...]
            max_workers: 最大并发数
            force: 是否强制重新生成
            
        Returns:
            {'success': count, 'failed': count, 'skipped': count}
        """
        results = {'success': 0, 'failed': 0, 'skipped': 0}
        to_process = []
        
        for video_id, file_path, title in videos:
            if not title:
                results['failed'] += 1
                print(f"Skipped video {video_id}: no title")
                continue
                
            if not force and self.has_thumbnail(title):
                results['skipped'] += 1
                continue
            to_process.append((video_id, file_path, title))
        
        if not to_process:
            return results
        
        print(f"Generating {len(to_process)} thumbnails...")
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(self.generate_thumbnail_safe, path, title): (vid, title)
                for vid, path, title in to_process
            }
            
            for future in as_completed(futures):
                video_id, title = futures[future]
                try:
                    result = future.result()
                    if result:
                        results['success'] += 1
                        print(f"  [OK] {title}")
                    else:
                        results['failed'] += 1
                        print(f"  [FAIL] {title}")
                except Exception as e:
                    results['failed'] += 1
                    print(f"  [ERROR] {title}: {e}")
        
        return results
    
    def get_thumbnail_url(self, title: str) -> str:
        """
        获取缩略图URL
        
        Args:
            title: 视频标题
            
        Returns:
            缩略图URL路径
        """
        if title:
            thumb_path = self._get_thumbnail_path_by_title(title)
            if thumb_path and thumb_path.exists():
                safe_title = self._sanitize_title(title)
                return f"/static/thumbnails/{safe_title}.jpg"
        
        return "/static/images/placeholder.svg"
    
    def get_missing_thumbnails(self, videos: List[Tuple[int, str, str]]) -> List[Tuple[int, str, str]]:
        """
        获取没有缩略图的视频列表
        
        Args:
            videos: [(video_id, file_path, title), ...]
            
        Returns:
            缺少缩略图的视频列表
        """
        missing = []
        for video_id, file_path, title in videos:
            if not self.has_thumbnail(title):
                missing.append((video_id, file_path, title))
        return missing


thumbnail_generator = ThumbnailGenerator()


def get_thumbnail_generator() -> ThumbnailGenerator:
    """获取缩略图生成器实例"""
    return thumbnail_generator

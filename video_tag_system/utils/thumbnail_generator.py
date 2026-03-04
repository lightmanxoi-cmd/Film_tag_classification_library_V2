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
    GIF_WIDTH = 320
    GIF_HEIGHT = 180
    GIF_DURATION = 10
    GIF_FPS = 10
    
    def __init__(self, thumbnail_dir: str = "web/static/thumbnails", gif_dir: str = "web/static/gifs"):
        self.thumbnail_dir = Path(thumbnail_dir)
        self.thumbnail_dir.mkdir(parents=True, exist_ok=True)
        self.gif_dir = Path(gif_dir)
        self.gif_dir.mkdir(parents=True, exist_ok=True)
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
    
    def _get_gif_path_by_title(self, title: str) -> Path:
        """根据标题获取GIF路径"""
        safe_title = self._sanitize_title(title)
        if safe_title:
            return self.gif_dir / f"{safe_title}.gif"
        return None
    
    def has_gif(self, title: str) -> bool:
        """
        检查是否已有GIF预览
        
        Args:
            title: 视频标题
            
        Returns:
            是否存在GIF
        """
        if not title:
            return False
        gif_path = self._get_gif_path_by_title(title)
        return gif_path and gif_path.exists()
    
    def get_video_duration(self, video_path: str) -> Optional[float]:
        """
        获取视频时长
        
        Args:
            video_path: 视频文件路径
            
        Returns:
            视频时长（秒）或None
        """
        try:
            cmd = [
                'ffprobe',
                '-v', 'error',
                '-show_entries', 'format=duration',
                '-of', 'default=noprint_wrappers=1:nokey=1',
                video_path
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            )
            
            if result.returncode == 0:
                return float(result.stdout.strip())
            return None
        except Exception as e:
            print(f"Failed to get video duration: {e}")
            return None
    
    def generate_gif(
        self, 
        video_path: str, 
        title: str,
        duration: int = None
    ) -> Optional[str]:
        """
        为视频生成GIF预览（从视频中间截取10秒）
        
        Args:
            video_path: 视频文件路径
            title: 视频标题（用于命名GIF）
            duration: 视频时长（秒），如果为None则自动获取
            
        Returns:
            GIF路径或None
        """
        if not os.path.exists(video_path):
            print(f"Video file not found: {video_path}")
            return None
        
        if not title:
            print(f"Video title is empty, cannot generate GIF")
            return None
        
        gif_path = self._get_gif_path_by_title(title)
        if not gif_path:
            return None
        
        try:
            if duration is None:
                duration = self.get_video_duration(video_path)
            
            if duration is None or duration <= 0:
                print(f"Cannot determine video duration for '{title}'")
                return None
            
            start_time = max(0, (duration / 2) - (self.GIF_DURATION / 2))
            
            actual_duration = min(self.GIF_DURATION, duration - start_time)
            
            cmd = [
                'ffmpeg',
                '-y',
                '-ss', str(start_time),
                '-i', video_path,
                '-t', str(actual_duration),
                '-vf', f'fps={self.GIF_FPS},scale={self.GIF_WIDTH}:{self.GIF_HEIGHT}:force_original_aspect_ratio=decrease,pad={self.GIF_WIDTH}:{self.GIF_HEIGHT}:(ow-iw)/2:(oh-ih)/2:black,split[s0][s1];[s0]palettegen=max_colors=256:stats_mode=diff[p];[s1][p]paletteuse=dither=bayer:bayer_scale=5:diff_mode=rectangle',
                str(gif_path)
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            )
            
            if result.returncode == 0 and gif_path.exists():
                with self._lock:
                    if title in self.cache:
                        self.cache[title]['gif'] = str(gif_path)
                    else:
                        self.cache[title] = {
                            'file_path': video_path,
                            'gif': str(gif_path)
                        }
                    self._save_cache()
                return str(gif_path)
            else:
                print(f"FFmpeg GIF error for '{title}': {result.stderr.decode() if result.stderr else 'Unknown error'}")
                return None
                
        except FileNotFoundError:
            print("FFmpeg not installed, cannot generate GIF")
            return None
        except Exception as e:
            print(f"Failed to generate GIF: {e}")
            return None
    
    def batch_generate_gifs(
        self, 
        videos: List[Tuple[int, str, str, Optional[int]]], 
        max_workers: int = 2,
        force: bool = False
    ) -> dict:
        """
        批量生成GIF预览
        
        Args:
            videos: [(video_id, file_path, title, duration), ...]
            max_workers: 最大并发数
            force: 是否强制重新生成
            
        Returns:
            {'success': count, 'failed': count, 'skipped': count}
        """
        results = {'success': 0, 'failed': 0, 'skipped': 0}
        to_process = []
        
        for video_id, file_path, title, duration in videos:
            if not title:
                results['failed'] += 1
                print(f"Skipped video {video_id}: no title")
                continue
                
            if not force and self.has_gif(title):
                results['skipped'] += 1
                continue
            to_process.append((video_id, file_path, title, duration))
        
        if not to_process:
            return results
        
        print(f"Generating {len(to_process)} GIF previews...")
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(self.generate_gif, path, title, dur): (vid, title)
                for vid, path, title, dur in to_process
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
    
    def get_gif_url(self, title: str) -> Optional[str]:
        """
        获取GIF预览URL
        
        Args:
            title: 视频标题
            
        Returns:
            GIF URL路径或None
        """
        if title:
            gif_path = self._get_gif_path_by_title(title)
            if gif_path and gif_path.exists():
                safe_title = self._sanitize_title(title)
                return f"/static/gifs/{safe_title}.gif"
        return None
    
    def get_missing_gifs(self, videos: List[Tuple[int, str, str]]) -> List[Tuple[int, str, str]]:
        """
        获取没有GIF预览的视频列表
        
        Args:
            videos: [(video_id, file_path, title), ...]
            
        Returns:
            缺少GIF预览的视频列表
        """
        missing = []
        for video_id, file_path, title in videos:
            if not self.has_gif(title):
                missing.append((video_id, file_path, title))
        return missing


thumbnail_generator = ThumbnailGenerator()


def get_thumbnail_generator() -> ThumbnailGenerator:
    """获取缩略图生成器实例"""
    return thumbnail_generator

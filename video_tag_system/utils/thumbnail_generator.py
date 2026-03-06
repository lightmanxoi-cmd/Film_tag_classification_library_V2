"""
视频缩略图生成模块
支持内存缓存 + JSON持久化双层缓存
"""
import os
import subprocess
import json
import re
from pathlib import Path
from typing import Optional, List, Tuple, Dict, Set
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
from video_tag_system.utils.cache import get_cache, CACHE_KEYS


class ThumbnailCache:
    """缩略图内存缓存管理器"""
    
    def __init__(self):
        self._thumbnail_urls: Dict[str, str] = {}
        self._gif_urls: Dict[str, str] = {}
        self._existing_thumbnails: Set[str] = set()
        self._existing_gifs: Set[str] = set()
        self._lock = threading.RLock()
        self._initialized = False
    
    def initialize(self, thumbnail_dir: Path, gif_dir: Path):
        if self._initialized:
            return
        
        with self._lock:
            if self._initialized:
                return
            
            self._scan_existing_files(thumbnail_dir, gif_dir)
            self._initialized = True
    
    def _scan_existing_files(self, thumbnail_dir: Path, gif_dir: Path):
        if thumbnail_dir.exists():
            for f in thumbnail_dir.iterdir():
                if f.suffix.lower() in ('.jpg', '.jpeg', '.png'):
                    self._existing_thumbnails.add(f.stem)
        
        if gif_dir.exists():
            for f in gif_dir.iterdir():
                if f.suffix.lower() == '.gif':
                    self._existing_gifs.add(f.stem)
    
    def has_thumbnail(self, safe_title: str) -> bool:
        with self._lock:
            return safe_title in self._existing_thumbnails
    
    def has_gif(self, safe_title: str) -> bool:
        with self._lock:
            return safe_title in self._existing_gifs
    
    def add_thumbnail(self, safe_title: str):
        with self._lock:
            self._existing_thumbnails.add(safe_title)
    
    def add_gif(self, safe_title: str):
        with self._lock:
            self._existing_gifs.add(safe_title)
    
    def get_thumbnail_url(self, safe_title: str) -> Optional[str]:
        with self._lock:
            if safe_title in self._existing_thumbnails:
                return f"/static/thumbnails/{safe_title}.jpg"
            return None
    
    def get_gif_url(self, safe_title: str) -> Optional[str]:
        with self._lock:
            if safe_title in self._existing_gifs:
                return f"/static/gifs/{safe_title}.gif"
            return None
    
    def invalidate(self, safe_title: str):
        with self._lock:
            self._existing_thumbnails.discard(safe_title)
            self._existing_gifs.discard(safe_title)
    
    def get_stats(self) -> Dict:
        with self._lock:
            return {
                "thumbnails_cached": len(self._existing_thumbnails),
                "gifs_cached": len(self._existing_gifs),
                "initialized": self._initialized
            }


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
        self._memory_cache = ThumbnailCache()
        self._memory_cache.initialize(self.thumbnail_dir, self.gif_dir)
        
    def _load_cache(self) -> dict:
        if self.cache_file.exists():
            try:
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                return {}
        return {}
    
    def _save_cache(self):
        with open(self.cache_file, 'w', encoding='utf-8') as f:
            json.dump(self.cache, f, ensure_ascii=False, indent=2)
    
    def _sanitize_title(self, title: str) -> str:
        if not title:
            return ""
        safe_title = re.sub(r'[<>:"/\\|?*]', '_', title)
        safe_title = re.sub(r'\s+', '_', safe_title)
        safe_title = safe_title.strip('._')
        return safe_title
    
    def _get_thumbnail_path_by_title(self, title: str) -> Path:
        safe_title = self._sanitize_title(title)
        if safe_title:
            return self.thumbnail_dir / f"{safe_title}.jpg"
        return None
    
    def _get_gif_path_by_title(self, title: str) -> Path:
        safe_title = self._sanitize_title(title)
        if safe_title:
            return self.gif_dir / f"{safe_title}.gif"
        return None
    
    def has_thumbnail(self, title: str) -> bool:
        if not title:
            return False
        safe_title = self._sanitize_title(title)
        return self._memory_cache.has_thumbnail(safe_title)
    
    def generate_thumbnail(
        self, 
        video_path: str, 
        title: str,
        time_offset: float = 5
    ) -> Optional[str]:
        if not os.path.exists(video_path):
            print(f"Video file not found: {video_path}")
            return None
        
        if not title:
            print(f"Video title is empty, cannot generate thumbnail")
            return None
        
        thumb_path = self._get_thumbnail_path_by_title(title)
        if not thumb_path:
            return None
        
        safe_title = self._sanitize_title(title)
        
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
                    self._memory_cache.add_thumbnail(safe_title)
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
        if not title:
            return "/static/images/placeholder.svg"
        
        safe_title = self._sanitize_title(title)
        if not safe_title:
            return "/static/images/placeholder.svg"
        
        url = self._memory_cache.get_thumbnail_url(safe_title)
        if url:
            return url
        
        thumb_path = self.thumbnail_dir / f"{safe_title}.jpg"
        if thumb_path.exists():
            self._memory_cache.add_thumbnail(safe_title)
            return f"/static/thumbnails/{safe_title}.jpg"
        
        return "/static/images/placeholder.svg"
    
    def get_missing_thumbnails(self, videos: List[Tuple[int, str, str]]) -> List[Tuple[int, str, str]]:
        missing = []
        for video_id, file_path, title in videos:
            if not self.has_thumbnail(title):
                missing.append((video_id, file_path, title))
        return missing
    
    def has_gif(self, title: str) -> bool:
        if not title:
            return False
        safe_title = self._sanitize_title(title)
        return self._memory_cache.has_gif(safe_title)
    
    def get_video_duration(self, video_path: str) -> Optional[float]:
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
        if not os.path.exists(video_path):
            print(f"Video file not found: {video_path}")
            return None
        
        if not title:
            print(f"Video title is empty, cannot generate GIF")
            return None
        
        gif_path = self._get_gif_path_by_title(title)
        if not gif_path:
            return None
        
        safe_title = self._sanitize_title(title)
        
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
                    self._memory_cache.add_gif(safe_title)
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
        if not title:
            return None
        
        safe_title = self._sanitize_title(title)
        if not safe_title:
            return None
        
        url = self._memory_cache.get_gif_url(safe_title)
        if url:
            return url
        
        gif_path = self.gif_dir / f"{safe_title}.gif"
        if gif_path.exists():
            self._memory_cache.add_gif(safe_title)
            return f"/static/gifs/{safe_title}.gif"
        
        return None
    
    def get_missing_gifs(self, videos: List[Tuple[int, str, str]]) -> List[Tuple[int, str, str]]:
        missing = []
        for video_id, file_path, title in videos:
            if not self.has_gif(title):
                missing.append((video_id, file_path, title))
        return missing
    
    def get_cache_stats(self) -> Dict:
        return self._memory_cache.get_stats()


thumbnail_generator = ThumbnailGenerator()


def get_thumbnail_generator() -> ThumbnailGenerator:
    return thumbnail_generator

"""
视频缩略图生成模块

使用FFmpeg为视频文件生成缩略图和GIF预览动画。
支持内存缓存 + JSON持久化双层缓存机制，提升性能。

主要组件：
    - ThumbnailCache: 缩略图内存缓存管理器
    - ThumbnailGenerator: 视频缩略图生成器

功能特点：
    - 支持生成静态缩略图（JPG格式）
    - 支持生成动态GIF预览
    - 多线程批量生成
    - 自动跳过已存在的缩略图
    - 智能选择视频中间帧

依赖：
    - FFmpeg: 用于视频截图和GIF生成
    - FFprobe: 用于获取视频时长

使用示例：
    from video_tag_system.utils.thumbnail_generator import get_thumbnail_generator
    
    generator = get_thumbnail_generator()
    
    # 生成单个缩略图
    generator.generate_thumbnail("/path/to/video.mp4", "视频标题")
    
    # 批量生成
    videos = [(1, "/path/1.mp4", "标题1"), (2, "/path/2.mp4", "标题2")]
    results = generator.batch_generate(videos)
    
    # 获取缩略图URL
    url = generator.get_thumbnail_url("视频标题")

Attributes:
    thumbnail_generator: 全局缩略图生成器实例
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
    """
    缩略图内存缓存管理器
    
    维护已生成缩略图和GIF的内存索引，避免重复的文件系统检查。
    使用线程安全的数据结构，支持并发访问。
    
    缓存策略：
    1. 启动时扫描目录，加载已存在的文件列表
    2. 生成新文件时更新内存索引
    3. 支持手动失效特定条目
    
    Attributes:
        _thumbnail_urls: 缩略图URL映射字典
        _gif_urls: GIF URL映射字典
        _existing_thumbnails: 已存在的缩略图文件名集合
        _existing_gifs: 已存在的GIF文件名集合
        _lock: 可重入锁保证线程安全
        _initialized: 是否已初始化标记
    
    Example:
        cache = ThumbnailCache()
        cache.initialize(thumbnail_dir, gif_dir)
        
        if cache.has_thumbnail("video_title"):
            url = cache.get_thumbnail_url("video_title")
    """
    
    def __init__(self):
        """
        初始化缩略图缓存管理器
        
        创建空的缓存数据结构，等待initialize()调用。
        """
        self._thumbnail_urls: Dict[str, str] = {}
        self._gif_urls: Dict[str, str] = {}
        self._existing_thumbnails: Set[str] = set()
        self._existing_gifs: Set[str] = set()
        self._lock = threading.RLock()
        self._initialized = False
    
    def initialize(self, thumbnail_dir: Path, gif_dir: Path):
        """
        初始化缓存
        
        扫描缩略图和GIF目录，加载已存在的文件列表。
        使用双重检查锁定避免重复初始化。
        
        Args:
            thumbnail_dir: 缩略图目录路径
            gif_dir: GIF目录路径
        """
        if self._initialized:
            return
        
        with self._lock:
            if self._initialized:
                return
            
            self._scan_existing_files(thumbnail_dir, gif_dir)
            self._initialized = True
    
    def _scan_existing_files(self, thumbnail_dir: Path, gif_dir: Path):
        """
        扫描已存在的文件
        
        遍历目录，将所有已存在的缩略图和GIF文件名加入缓存。
        
        Args:
            thumbnail_dir: 缩略图目录路径
            gif_dir: GIF目录路径
        """
        if thumbnail_dir.exists():
            for f in thumbnail_dir.iterdir():
                if f.suffix.lower() in ('.jpg', '.jpeg', '.png'):
                    self._existing_thumbnails.add(f.stem)
        
        if gif_dir.exists():
            for f in gif_dir.iterdir():
                if f.suffix.lower() == '.gif':
                    self._existing_gifs.add(f.stem)
    
    def has_thumbnail(self, safe_title: str) -> bool:
        """
        检查缩略图是否存在
        
        Args:
            safe_title: 安全的标题（已清理非法字符）
        
        Returns:
            bool: 缩略图存在返回True
        """
        with self._lock:
            return safe_title in self._existing_thumbnails
    
    def has_gif(self, safe_title: str) -> bool:
        """
        检查GIF是否存在
        
        Args:
            safe_title: 安全的标题（已清理非法字符）
        
        Returns:
            bool: GIF存在返回True
        """
        with self._lock:
            return safe_title in self._existing_gifs
    
    def add_thumbnail(self, safe_title: str):
        """
        添加缩略图到缓存
        
        Args:
            safe_title: 安全的标题
        """
        with self._lock:
            self._existing_thumbnails.add(safe_title)
    
    def add_gif(self, safe_title: str):
        """
        添加GIF到缓存
        
        Args:
            safe_title: 安全的标题
        """
        with self._lock:
            self._existing_gifs.add(safe_title)
    
    def get_thumbnail_url(self, safe_title: str) -> Optional[str]:
        """
        获取缩略图URL
        
        Args:
            safe_title: 安全的标题
        
        Returns:
            Optional[str]: 缩略图URL，不存在返回None
        """
        with self._lock:
            if safe_title in self._existing_thumbnails:
                return f"/static/thumbnails/{safe_title}.jpg"
            return None
    
    def get_gif_url(self, safe_title: str) -> Optional[str]:
        """
        获取GIF URL
        
        Args:
            safe_title: 安全的标题
        
        Returns:
            Optional[str]: GIF URL，不存在返回None
        """
        with self._lock:
            if safe_title in self._existing_gifs:
                return f"/static/gifs/{safe_title}.gif"
            return None
    
    def invalidate(self, safe_title: str):
        """
        使缓存失效
        
        从缓存中移除指定的缩略图和GIF记录。
        
        Args:
            safe_title: 安全的标题
        """
        with self._lock:
            self._existing_thumbnails.discard(safe_title)
            self._existing_gifs.discard(safe_title)
    
    def get_stats(self) -> Dict:
        """
        获取缓存统计信息
        
        Returns:
            Dict: 包含缓存条目数和初始化状态的字典
        """
        with self._lock:
            return {
                "thumbnails_cached": len(self._existing_thumbnails),
                "gifs_cached": len(self._existing_gifs),
                "initialized": self._initialized
            }


class ThumbnailGenerator:
    """
    视频缩略图生成器
    
    使用FFmpeg为视频生成缩略图和GIF预览动画。
    支持批量生成、自动跳过已存在的文件。
    
    生成策略：
    - 缩略图：从视频第5秒截取一帧（可配置）
    - GIF：从视频中间位置截取10秒动画
    
    性能优化：
    - 内存缓存避免重复文件检查
    - JSON持久化记录生成历史
    - 多线程并行生成
    
    Attributes:
        THUMBNAIL_WIDTH: 缩略图宽度（640像素）
        THUMBNAIL_HEIGHT: 缩略图高度（360像素）
        GIF_WIDTH: GIF宽度（320像素）
        GIF_HEIGHT: GIF高度（180像素）
        GIF_DURATION: GIF时长（10秒）
        GIF_FPS: GIF帧率（10帧/秒）
        thumbnail_dir: 缩略图保存目录
        gif_dir: GIF保存目录
        cache_file: 缓存JSON文件路径
        cache: JSON缓存数据
        _memory_cache: 内存缓存实例
    
    Example:
        generator = ThumbnailGenerator()
        
        # 生成缩略图
        path = generator.generate_thumbnail("/video.mp4", "标题")
        
        # 获取URL
        url = generator.get_thumbnail_url("标题")
    """
    
    THUMBNAIL_WIDTH = 640
    THUMBNAIL_HEIGHT = 360
    GIF_WIDTH = 320
    GIF_HEIGHT = 180
    GIF_DURATION = 10
    GIF_FPS = 10
    
    def __init__(self, thumbnail_dir: str = "web/static/thumbnails", gif_dir: str = "web/static/gifs"):
        """
        初始化缩略图生成器
        
        创建保存目录，加载缓存数据，初始化内存缓存。
        
        Args:
            thumbnail_dir: 缩略图保存目录，默认"web/static/thumbnails"
            gif_dir: GIF保存目录，默认"web/static/gifs"
        """
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
        """
        加载JSON缓存文件
        
        从磁盘加载之前生成的缩略图记录。
        
        Returns:
            dict: 缓存数据字典，加载失败返回空字典
        """
        if self.cache_file.exists():
            try:
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                return {}
        return {}
    
    def _save_cache(self):
        """
        保存缓存到JSON文件
        
        将当前的缓存数据持久化到磁盘。
        """
        with open(self.cache_file, 'w', encoding='utf-8') as f:
            json.dump(self.cache, f, ensure_ascii=False, indent=2)
    
    def _sanitize_title(self, title: str) -> str:
        """
        清理标题为安全的文件名
        
        移除文件名中的非法字符，转换为适合作为文件名的格式。
        同时处理URL特殊字符，避免URL解析问题。
        
        Args:
            title: 原始标题
        
        Returns:
            str: 安全的文件名
        
        Example:
            >>> _sanitize_title("视频:标题/测试")
            '视频_标题_测试'
        """
        if not title:
            return ""
        # 包括Windows非法字符和URL特殊字符 (# 用于URL锚点，% 用于URL编码)
        safe_title = re.sub(r'[<>:"/\\|?*#%]', '_', title)
        safe_title = re.sub(r'\s+', '_', safe_title)
        safe_title = safe_title.strip('._')
        return safe_title
    
    def _get_thumbnail_path_by_title(self, title: str) -> Path:
        """
        根据标题获取缩略图路径
        
        Args:
            title: 视频标题
        
        Returns:
            Path: 缩略图文件路径，标题为空返回None
        """
        safe_title = self._sanitize_title(title)
        if safe_title:
            return self.thumbnail_dir / f"{safe_title}.jpg"
        return None
    
    def _get_gif_path_by_title(self, title: str) -> Path:
        """
        根据标题获取GIF路径
        
        Args:
            title: 视频标题
        
        Returns:
            Path: GIF文件路径，标题为空返回None
        """
        safe_title = self._sanitize_title(title)
        if safe_title:
            return self.gif_dir / f"{safe_title}.gif"
        return None
    
    def has_thumbnail(self, title: str) -> bool:
        """
        检查缩略图是否存在
        
        Args:
            title: 视频标题
        
        Returns:
            bool: 缩略图存在返回True
        """
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
        """
        生成视频缩略图
        
        使用FFmpeg从视频指定时间点截取一帧作为缩略图。
        自动缩放和填充黑边以保持宽高比。
        
        Args:
            video_path: 视频文件路径
            title: 视频标题（用于生成文件名）
            time_offset: 截取时间点（秒），默认5秒
        
        Returns:
            Optional[str]: 生成的缩略图路径，失败返回None
        
        FFmpeg参数说明：
            - -y: 覆盖已存在的文件
            - -ss: 定位到指定时间点
            - -vframes 1: 只截取一帧
            - -vf scale: 缩放滤镜，保持宽高比
            - -q:v 5: JPEG质量（1-31，越小质量越高）
        
        Note:
            - 需要系统安装FFmpeg
            - Windows下使用CREATE_NO_WINDOW隐藏命令行窗口
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
        """
        安全生成缩略图
        
        尝试多个时间点生成缩略图，直到成功。
        时间点顺序：5秒、10秒、3秒、1秒、0.5秒。
        
        这种策略可以处理：
        - 视频开头是黑屏或片头
        - 视频时长较短
        - 某些时间点解码失败
        
        Args:
            video_path: 视频文件路径
            title: 视频标题
        
        Returns:
            Optional[str]: 生成的缩略图路径，全部失败返回None
        """
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
        
        使用线程池并行生成多个视频的缩略图。
        自动跳过已存在的缩略图（除非force=True）。
        
        Args:
            videos: 视频列表，每个元素为(video_id, file_path, title)元组
            max_workers: 最大并发线程数，默认4
            force: 是否强制重新生成，默认False
        
        Returns:
            dict: 生成结果统计
                - success: 成功数量
                - failed: 失败数量
                - skipped: 跳过数量
        
        Example:
            videos = [
                (1, "/path/video1.mp4", "标题1"),
                (2, "/path/video2.mp4", "标题2"),
            ]
            results = generator.batch_generate(videos, max_workers=4)
            print(f"成功: {results['success']}, 失败: {results['failed']}")
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
        
        返回缩略图的Web访问URL。如果缩略图不存在，返回占位图URL。
        
        Args:
            title: 视频标题
        
        Returns:
            str: 缩略图URL或占位图URL
        """
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
        """
        获取缺少缩略图的视频列表
        
        筛选出还没有生成缩略图的视频。
        
        Args:
            videos: 视频列表，每个元素为(video_id, file_path, title)元组
        
        Returns:
            List[Tuple[int, str, str]]: 缺少缩略图的视频列表
        """
        missing = []
        for video_id, file_path, title in videos:
            if not self.has_thumbnail(title):
                missing.append((video_id, file_path, title))
        return missing
    
    def has_gif(self, title: str) -> bool:
        """
        检查GIF是否存在
        
        Args:
            title: 视频标题
        
        Returns:
            bool: GIF存在返回True
        """
        if not title:
            return False
        safe_title = self._sanitize_title(title)
        return self._memory_cache.has_gif(safe_title)
    
    def get_video_duration(self, video_path: str) -> Optional[float]:
        """
        获取视频时长
        
        使用FFprobe获取视频的总时长。
        
        Args:
            video_path: 视频文件路径
        
        Returns:
            Optional[float]: 视频时长（秒），失败返回None
        
        Note:
            需要系统安装FFprobe（通常与FFmpeg一起安装）
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
        生成视频GIF预览
        
        使用FFmpeg从视频中间位置截取片段生成GIF动画。
        使用调色板优化GIF质量和大小。
        
        Args:
            video_path: 视频文件路径
            title: 视频标题（用于生成文件名）
            duration: 视频时长（秒），None则自动获取
        
        Returns:
            Optional[str]: 生成的GIF路径，失败返回None
        
        GIF生成策略：
            1. 从视频中间位置开始截取
            2. 截取时长为GIF_DURATION（默认10秒）
            3. 使用调色板优化颜色
            4. 帧率为GIF_FPS（默认10帧/秒）
        
        FFmpeg滤镜说明：
            - fps: 设置帧率
            - scale: 缩放到指定尺寸
            - palettegen: 生成调色板
            - paletteuse: 应用调色板
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
        """
        批量生成GIF预览
        
        使用线程池并行生成多个视频的GIF预览。
        GIF生成比缩略图更耗时，建议使用较少的并发线程。
        
        Args:
            videos: 视频列表，每个元素为(video_id, file_path, title, duration)元组
            max_workers: 最大并发线程数，默认2
            force: 是否强制重新生成，默认False
        
        Returns:
            dict: 生成结果统计
                - success: 成功数量
                - failed: 失败数量
                - skipped: 跳过数量
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
        获取GIF URL
        
        返回GIF的Web访问URL。如果GIF不存在，返回None。
        
        Args:
            title: 视频标题
        
        Returns:
            Optional[str]: GIF URL，不存在返回None
        """
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
        """
        获取缺少GIF的视频列表
        
        筛选出还没有生成GIF预览的视频。
        
        Args:
            videos: 视频列表，每个元素为(video_id, file_path, title)元组
        
        Returns:
            List[Tuple[int, str, str]]: 缺少GIF的视频列表
        """
        missing = []
        for video_id, file_path, title in videos:
            if not self.has_gif(title):
                missing.append((video_id, file_path, title))
        return missing
    
    def get_cache_stats(self) -> Dict:
        """
        获取缓存统计信息
        
        Returns:
            Dict: 缓存统计信息
        """
        return self._memory_cache.get_stats()
    
    def submit_thumbnail_task(
        self,
        videos: List[Tuple[int, str, str]],
        force: bool = False,
        task_name: str = "批量生成缩略图"
    ) -> str:
        """
        异步提交缩略图生成任务
        
        将批量缩略图生成任务提交到后台执行，立即返回任务ID。
        通过任务ID可以查询进度和结果。
        
        Args:
            videos: 视频列表，每个元素为(video_id, file_path, title)元组
            force: 是否强制重新生成，默认False
            task_name: 任务名称
        
        Returns:
            str: 任务ID，用于查询进度和结果
        
        Example:
            videos = [(1, "/path/video.mp4", "标题")]
            task_id = generator.submit_thumbnail_task(videos)
            
            # 查询进度
            from video_tag_system.utils.async_tasks import get_task_manager
            manager = get_task_manager()
            progress = manager.get_progress(task_id)
        """
        from video_tag_system.utils.async_tasks import get_task_manager
        
        def process_thumbnail(item, **kwargs):
            video_id, file_path, title = item
            force_flag = kwargs.get('force', False)
            
            if not title:
                return False
            
            if not force_flag and self.has_thumbnail(title):
                return True
            
            result = self.generate_thumbnail_safe(file_path, title)
            return result is not None
        
        valid_videos = [
            (vid, path, title) for vid, path, title in videos
            if title
        ]
        
        if not valid_videos:
            return None
        
        manager = get_task_manager()
        task_id = manager.submit_batch(
            func=process_thumbnail,
            items=valid_videos,
            task_name=task_name,
            force=force
        )
        
        return task_id
    
    def submit_gif_task(
        self,
        videos: List[Tuple[int, str, str, Optional[int]]],
        force: bool = False,
        task_name: str = "批量生成GIF预览"
    ) -> str:
        """
        异步提交GIF生成任务
        
        将批量GIF生成任务提交到后台执行，立即返回任务ID。
        GIF生成比缩略图更耗时，建议使用异步方式。
        
        Args:
            videos: 视频列表，每个元素为(video_id, file_path, title, duration)元组
            force: 是否强制重新生成，默认False
            task_name: 任务名称
        
        Returns:
            str: 任务ID，用于查询进度和结果
        
        Example:
            videos = [(1, "/path/video.mp4", "标题", 3600)]
            task_id = generator.submit_gif_task(videos)
        """
        from video_tag_system.utils.async_tasks import get_task_manager
        
        def process_gif(item, **kwargs):
            video_id, file_path, title, duration = item
            force_flag = kwargs.get('force', False)
            
            if not title:
                return False
            
            if not force_flag and self.has_gif(title):
                return True
            
            result = self.generate_gif(file_path, title, duration)
            return result is not None
        
        valid_videos = [
            (vid, path, title, dur) for vid, path, title, dur in videos
            if title
        ]
        
        if not valid_videos:
            return None
        
        manager = get_task_manager()
        task_id = manager.submit_batch(
            func=process_gif,
            items=valid_videos,
            task_name=task_name,
            force=force
        )
        
        return task_id


    def compute_thumbnail_url(self, title: str) -> str:
        """
        计算缩略图URL（用于数据库持久化）
        
        根据标题计算缩略图URL，如果缩略图文件存在则返回实际URL，
        否则返回占位图URL。此方法用于将URL存入数据库，避免每次请求时重新计算。
        
        Args:
            title: 视频标题
        
        Returns:
            str: 缩略图URL
        """
        return self.get_thumbnail_url(title)
    
    def compute_gif_url(self, title: str) -> Optional[str]:
        """
        计算GIF URL（用于数据库持久化）
        
        根据标题计算GIF URL，如果GIF文件存在则返回实际URL，
        否则返回None。此方法用于将URL存入数据库，避免每次请求时重新计算。
        
        Args:
            title: 视频标题
        
        Returns:
            Optional[str]: GIF URL，不存在返回None
        """
        return self.get_gif_url(title)


thumbnail_generator = ThumbnailGenerator()


def get_thumbnail_generator() -> ThumbnailGenerator:
    """
    获取全局缩略图生成器实例
    
    返回全局的ThumbnailGenerator实例，用于统一管理缩略图生成。
    
    Returns:
        ThumbnailGenerator: 全局缩略图生成器实例
    
    Example:
        generator = get_thumbnail_generator()
        generator.generate_thumbnail("/video.mp4", "标题")
    """
    return thumbnail_generator

"""
视频缩略图生成模块
"""
import os
import subprocess
import hashlib
import json
from pathlib import Path
from typing import Optional, List, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading


class ThumbnailGenerator:
    """视频缩略图生成器"""
    
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
    
    def _get_video_hash(self, file_path: str) -> str:
        """根据文件路径和修改时间生成唯一标识"""
        try:
            mtime = os.path.getmtime(file_path)
            size = os.path.getsize(file_path)
            hash_input = f"{file_path}_{mtime}_{size}"
            return hashlib.md5(hash_input.encode()).hexdigest()
        except:
            return hashlib.md5(file_path.encode()).hexdigest()
    
    def _get_thumbnail_path(self, video_id: int) -> Path:
        """获取缩略图路径"""
        return self.thumbnail_dir / f"{video_id}.jpg"
    
    def has_thumbnail(self, video_id: int) -> bool:
        """检查是否已有缩略图"""
        thumb_path = self._get_thumbnail_path(video_id)
        return thumb_path.exists()
    
    def needs_update(self, video_id: int, file_path: str) -> bool:
        """检查缩略图是否需要更新"""
        video_hash = self._get_video_hash(file_path)
        cached_hash = self.cache.get(str(video_id), {}).get('hash')
        return cached_hash != video_hash
    
    def generate_thumbnail(
        self, 
        video_path: str, 
        video_id: int,
        time_offset: float = 0.1,
        width: int = 320,
        height: int = 180
    ) -> Optional[str]:
        """
        为视频生成缩略图
        
        Args:
            video_path: 视频文件路径
            video_id: 视频ID
            time_offset: 截取时间点（秒或百分比，如0.1表示10%位置）
            width: 缩略图宽度
            height: 缩略图高度
            
        Returns:
            缩略图路径或None
        """
        if not os.path.exists(video_path):
            print(f"视频文件不存在: {video_path}")
            return None
        
        thumb_path = self._get_thumbnail_path(video_id)
        
        try:
            cmd = [
                'ffmpeg',
                '-y',
                '-i', video_path,
                '-ss', str(time_offset),
                '-vframes', '1',
                '-vf', f'scale={width}:{height}:force_original_aspect_ratio=decrease,pad={width}:{height}:(ow-iw)/2:(oh-ih)/2:black',
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
                    self.cache[str(video_id)] = {
                        'hash': self._get_video_hash(video_path),
                        'file_path': video_path,
                        'thumbnail': str(thumb_path)
                    }
                    self._save_cache()
                return str(thumb_path)
            else:
                print(f"FFmpeg error for video {video_id}: {result.stderr.decode() if result.stderr else 'Unknown error'}")
                return None
                
        except FileNotFoundError:
            print("FFmpeg未安装，无法生成缩略图")
            return None
        except Exception as e:
            print(f"生成缩略图失败: {e}")
            return None
    
    def generate_thumbnail_safe(self, video_path: str, video_id: int) -> Optional[str]:
        """安全地生成缩略图，尝试多个时间点"""
        time_offsets = ['5', '10', '3', '1', '0.5']
        
        for offset in time_offsets:
            result = self.generate_thumbnail(video_path, video_id, time_offset=offset)
            if result:
                return result
        
        return self._create_placeholder(video_id)
    
    def _create_placeholder(self, video_id: int) -> str:
        """创建占位符图片"""
        thumb_path = self._get_thumbnail_path(video_id)
        
        placeholder_svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="320" height="180">
            <rect width="100%" height="100%" fill="#1a1a1a"/>
            <text x="50%" y="50%" font-family="Arial" font-size="48" fill="#333" text-anchor="middle" dominant-baseline="middle">▶</text>
        </svg>'''
        
        svg_path = self.thumbnail_dir / f"{video_id}.svg"
        with open(svg_path, 'w') as f:
            f.write(placeholder_svg)
        
        return str(svg_path)
    
    def batch_generate(
        self, 
        videos: List[Tuple[int, str]], 
        max_workers: int = 4,
        force: bool = False
    ) -> dict:
        """
        批量生成缩略图
        
        Args:
            videos: [(video_id, file_path), ...]
            max_workers: 最大并发数
            force: 是否强制重新生成
            
        Returns:
            {'success': count, 'failed': count, 'skipped': count}
        """
        results = {'success': 0, 'failed': 0, 'skipped': 0}
        to_process = []
        
        for video_id, file_path in videos:
            if not force and self.has_thumbnail(video_id) and not self.needs_update(video_id, file_path):
                results['skipped'] += 1
                continue
            to_process.append((video_id, file_path))
        
        if not to_process:
            return results
        
        print(f"需要生成 {len(to_process)} 个缩略图...")
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(self.generate_thumbnail_safe, path, vid): (vid, path)
                for vid, path in to_process
            }
            
            for future in as_completed(futures):
                video_id, path = futures[future]
                try:
                    result = future.result()
                    if result:
                        results['success'] += 1
                        print(f"✓ 视频 {video_id} 缩略图生成成功")
                    else:
                        results['failed'] += 1
                        print(f"✗ 视频 {video_id} 缩略图生成失败")
                except Exception as e:
                    results['failed'] += 1
                    print(f"✗ 视频 {video_id} 缩略图生成异常: {e}")
        
        return results
    
    def get_thumbnail_url(self, video_id: int) -> str:
        """获取缩略图URL"""
        thumb_path = self._get_thumbnail_path(video_id)
        svg_path = self.thumbnail_dir / f"{video_id}.svg"
        
        if thumb_path.exists():
            return f"/static/thumbnails/{video_id}.jpg"
        elif svg_path.exists():
            return f"/static/thumbnails/{video_id}.svg"
        else:
            return "/static/images/placeholder.svg"


thumbnail_generator = ThumbnailGenerator()


def get_thumbnail_generator() -> ThumbnailGenerator:
    """获取缩略图生成器实例"""
    return thumbnail_generator

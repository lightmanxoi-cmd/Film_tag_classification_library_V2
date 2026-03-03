"""
辅助工具函数
"""
import hashlib
from pathlib import Path
from typing import Optional, Union


def format_file_size(size_bytes: Optional[int]) -> str:
    """
    格式化文件大小
    
    Args:
        size_bytes: 文件大小（字节）
        
    Returns:
        格式化后的文件大小字符串
    """
    if size_bytes is None or size_bytes < 0:
        return "未知"
    
    units = ["B", "KB", "MB", "GB", "TB"]
    size = float(size_bytes)
    
    for unit in units[:-1]:
        if size < 1024:
            if unit == "B":
                return f"{int(size)} {unit}"
            return f"{size:.2f} {unit}"
        size /= 1024
    
    return f"{size:.2f} PB"


def format_duration(seconds: Optional[int]) -> str:
    """
    格式化时长
    
    Args:
        seconds: 时长（秒）
        
    Returns:
        格式化后的时长字符串
    """
    if seconds is None or seconds < 0:
        return "未知"
    
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    
    if hours > 0:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    return f"{minutes}:{secs:02d}"


def generate_file_hash(file_path: Union[str, Path], algorithm: str = "md5") -> str:
    """
    计算文件哈希值
    
    Args:
        file_path: 文件路径
        algorithm: 哈希算法（md5, sha1, sha256）
        
    Returns:
        文件哈希值
        
    Raises:
        FileNotFoundError: 文件不存在
        ValueError: 不支持的算法
    """
    path = Path(file_path)
    
    if not path.exists():
        raise FileNotFoundError(f"文件不存在: {file_path}")
    
    if algorithm.lower() == "md5":
        hasher = hashlib.md5()
    elif algorithm.lower() == "sha1":
        hasher = hashlib.sha1()
    elif algorithm.lower() == "sha256":
        hasher = hashlib.sha256()
    else:
        raise ValueError(f"不支持的哈希算法: {algorithm}")
    
    chunk_size = 8192
    with open(path, "rb") as f:
        while chunk := f.read(chunk_size):
            hasher.update(chunk)
    
    return hasher.hexdigest()


def parse_duration(duration_str: str) -> Optional[int]:
    """
    解析时长字符串为秒数
    
    支持格式：
    - "HH:MM:SS"
    - "MM:SS"
    - "SS"
    - "1h30m" / "90m" / "3600s"
    
    Args:
        duration_str: 时长字符串
        
    Returns:
        秒数，解析失败返回None
    """
    if not duration_str:
        return None
    
    duration_str = duration_str.strip().lower()
    
    if ":" in duration_str:
        parts = duration_str.split(":")
        try:
            if len(parts) == 3:
                hours, minutes, seconds = map(int, parts)
                return hours * 3600 + minutes * 60 + seconds
            elif len(parts) == 2:
                minutes, seconds = map(int, parts)
                return minutes * 60 + seconds
        except ValueError:
            return None
    
    import re
    match = re.match(r'^(?:(\d+)h)?(?:(\d+)m)?(?:(\d+)s)?$', duration_str)
    if match:
        hours = int(match.group(1) or 0)
        minutes = int(match.group(2) or 0)
        seconds = int(match.group(3) or 0)
        return hours * 3600 + minutes * 60 + seconds
    
    try:
        return int(duration_str)
    except ValueError:
        return None


def sanitize_filename(filename: str) -> str:
    """
    清理文件名，移除非法字符
    
    Args:
        filename: 原始文件名
        
    Returns:
        清理后的文件名
    """
    import re
    
    filename = filename.strip()
    
    filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
    
    filename = re.sub(r'[\x00-\x1f]', '', filename)
    
    filename = re.sub(r'\.{2,}', '.', filename)
    
    if not filename:
        filename = "unnamed"
    
    return filename


def get_file_extension(file_path: Union[str, Path]) -> str:
    """
    获取文件扩展名
    
    Args:
        file_path: 文件路径
        
    Returns:
        小写的文件扩展名（不含点号）
    """
    path = Path(file_path)
    return path.suffix.lower().lstrip(".")


def is_video_file(file_path: Union[str, Path]) -> bool:
    """
    检查是否为视频文件
    
    Args:
        file_path: 文件路径
        
    Returns:
        是否为视频文件
    """
    video_extensions = {
        "mp4", "avi", "mkv", "mov", "wmv", "flv", "webm",
        "m4v", "mpeg", "mpg", "3gp", "ts", "mts", "m2ts"
    }
    
    ext = get_file_extension(file_path)
    return ext in video_extensions

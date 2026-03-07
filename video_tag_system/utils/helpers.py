"""
辅助工具函数模块

提供常用的辅助函数，包括文件大小格式化、时长格式化、
文件哈希计算、文件名清理等功能。

主要函数：
    - format_file_size: 格式化文件大小为人类可读格式
    - format_duration: 格式化时长为HH:MM:SS格式
    - generate_file_hash: 计算文件的MD5/SHA1/SHA256哈希值
    - parse_duration: 解析时长字符串为秒数
    - sanitize_filename: 清理文件名中的非法字符
    - get_file_extension: 获取文件扩展名
    - is_video_file: 检查是否为视频文件

使用示例：
    from video_tag_system.utils.helpers import format_file_size, format_duration
    
    size_str = format_file_size(1024 * 1024)  # "1.00 MB"
    duration_str = format_duration(3661)  # "1:01:01"
"""
import hashlib
from pathlib import Path
from typing import Optional, Union


def format_file_size(size_bytes: Optional[int]) -> str:
    """
    格式化文件大小
    
    将字节数转换为人类可读的格式，自动选择合适的单位。
    支持的单位：B、KB、MB、GB、TB、PB
    
    Args:
        size_bytes: 文件大小（字节），可以为None或负数
    
    Returns:
        str: 格式化后的文件大小字符串
            - None或负数返回"未知"
            - 小于1KB返回整数格式，如"512 B"
            - 大于等于1KB返回两位小数格式，如"1.50 MB"
    
    Example:
        >>> format_file_size(512)
        '512 B'
        >>> format_file_size(1024)
        '1.00 KB'
        >>> format_file_size(1536)
        '1.50 KB'
        >>> format_file_size(1048576)
        '1.00 MB'
        >>> format_file_size(None)
        '未知'
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
    
    将秒数转换为人类可读的时长格式。
    格式规则：
    - 小于1小时：MM:SS
    - 大于等于1小时：HH:MM:SS
    
    Args:
        seconds: 时长（秒），可以为None或负数
    
    Returns:
        str: 格式化后的时长字符串
            - None或负数返回"未知"
            - 小于1小时返回"分:秒"格式
            - 大于等于1小时返回"时:分:秒"格式
    
    Example:
        >>> format_duration(65)
        '1:05'
        >>> format_duration(3661)
        '1:01:01'
        >>> format_duration(None)
        '未知'
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
    
    使用指定的哈希算法计算文件的哈希值。
    采用分块读取方式，支持大文件处理。
    
    Args:
        file_path: 文件路径，支持字符串或Path对象
        algorithm: 哈希算法，支持：
            - "md5": 32位十六进制字符串（默认）
            - "sha1": 40位十六进制字符串
            - "sha256": 64位十六进制字符串
    
    Returns:
        str: 文件哈希值（十六进制字符串）
    
    Raises:
        FileNotFoundError: 文件不存在时抛出
        ValueError: 不支持的哈希算法时抛出
    
    Example:
        >>> hash_value = generate_file_hash("/path/to/file.mp4", "md5")
        >>> print(hash_value)
        'd41d8cd98f00b204e9800998ecf8427e'
        
        >>> generate_file_hash("/path/to/file.mp4", "sha256")
        'e3b0c44298fc1c149afbf4c8996fb924...'
    
    Note:
        - 使用8KB块大小读取文件，平衡内存使用和性能
        - 对于大文件，计算可能需要较长时间
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
    
    支持多种时长格式的解析，返回统一的秒数。
    
    支持的格式：
    - "HH:MM:SS" - 标准时间格式
    - "MM:SS" - 分钟秒格式
    - "SS" - 纯秒数
    - "1h30m" / "90m" / "3600s" - 带单位格式
    
    Args:
        duration_str: 时长字符串
    
    Returns:
        Optional[int]: 秒数，解析失败返回None
    
    Example:
        >>> parse_duration("1:30:45")
        5445
        >>> parse_duration("90:30")
        5430
        >>> parse_duration("1h30m")
        5400
        >>> parse_duration("invalid")
        None
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
    
    移除或替换文件名中在Windows/Linux/macOS上
    不允许或可能导致问题的字符。
    
    处理规则：
    1. 移除首尾空白
    2. 替换非法字符 < > : " / \\ | ? * 为下划线
    3. 移除控制字符（ASCII 0-31）
    4. 合并连续的点号为单个点号
    5. 空文件名返回"unnamed"
    
    Args:
        filename: 原始文件名
    
    Returns:
        str: 清理后的安全文件名
    
    Example:
        >>> sanitize_filename("my<file>name.mp4")
        'my_file_name.mp4'
        >>> sanitize_filename("  test  ")
        'test'
        >>> sanitize_filename("")
        'unnamed'
        >>> sanitize_filename("file..name")
        'file.name'
    
    Note:
        - 不处理路径分隔符，仅处理文件名
        - 保留文件扩展名
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
    
    从文件路径中提取扩展名，返回小写格式。
    
    Args:
        file_path: 文件路径，支持字符串或Path对象
    
    Returns:
        str: 小写的文件扩展名（不含点号）
            - 无扩展名返回空字符串
            - 多个点号取最后一个
    
    Example:
        >>> get_file_extension("video.MP4")
        'mp4'
        >>> get_file_extension("/path/to/file.tar.gz")
        'gz'
        >>> get_file_extension("noextension")
        ''
        >>> get_file_extension(".hidden")
        'hidden'
    """
    path = Path(file_path)
    return path.suffix.lower().lstrip(".")


def is_video_file(file_path: Union[str, Path]) -> bool:
    """
    检查是否为视频文件
    
    根据文件扩展名判断是否为支持的视频格式。
    
    支持的视频格式：
    - 常见格式：mp4, avi, mkv, mov, wmv, flv, webm
    - 其他格式：m4v, mpeg, mpg, 3gp, ts, mts, m2ts
    
    Args:
        file_path: 文件路径，支持字符串或Path对象
    
    Returns:
        bool: 是视频文件返回True，否则返回False
    
    Example:
        >>> is_video_file("movie.mp4")
        True
        >>> is_video_file("document.pdf")
        False
        >>> is_video_file("video.MKV")
        True
    
    Note:
        - 仅根据扩展名判断，不检查文件内容
        - 扩展名比较不区分大小写
    """
    video_extensions = {
        "mp4", "avi", "mkv", "mov", "wmv", "flv", "webm",
        "m4v", "mpeg", "mpg", "3gp", "ts", "mts", "m2ts"
    }
    
    ext = get_file_extension(file_path)
    return ext in video_extensions

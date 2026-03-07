"""
数据验证器模块

提供数据输入验证功能，确保数据的完整性和安全性。
包含文件路径、标签名称、视频数据、标签数据等验证函数。

主要函数：
    - validate_file_path: 验证文件路径
    - validate_tag_name: 验证标签名称
    - validate_video_data: 验证视频数据
    - validate_tag_data: 验证标签数据
    - validate_hash: 验证哈希值

验证规则：
    - 文件路径：非空、长度限制、非法字符检查
    - 标签名称：非空、长度限制、不能纯数字
    - 视频数据：标题长度、时长范围、文件大小
    - 标签数据：父标签ID、描述长度、排序顺序

使用示例：
    from video_tag_system.utils.validators import validate_file_path, validate_tag_name
    
    try:
        path = validate_file_path("/path/to/video.mp4")
        name = validate_tag_name("动作片")
    except ValidationError as e:
        print(f"验证失败: {e}")

异常：
    ValidationError: 数据验证失败时抛出
"""
import os
import re
from typing import Optional

from video_tag_system.exceptions import ValidationError


def validate_file_path(file_path: str) -> str:
    """
    验证文件路径
    
    检查文件路径的有效性，确保路径格式正确。
    
    验证规则：
    1. 不能为空或纯空白
    2. 长度不能超过500个字符
    3. 不能包含非法字符 < > " | ? *
    
    Args:
        file_path: 文件路径字符串
    
    Returns:
        str: 清理后的文件路径（去除首尾空白）
    
    Raises:
        ValidationError: 文件路径验证失败时抛出
            - 路径为空
            - 路径过长
            - 包含非法字符
    
    Example:
        >>> validate_file_path("  /path/to/video.mp4  ")
        '/path/to/video.mp4'
        
        >>> validate_file_path("")
        ValidationError: 文件路径不能为空
    """
    if not file_path or not file_path.strip():
        raise ValidationError("file_path", file_path, "文件路径不能为空")
    
    file_path = file_path.strip()
    
    if len(file_path) > 500:
        raise ValidationError("file_path", file_path, "文件路径长度不能超过500个字符")
    
    invalid_chars = r'[<>:"|?*]'
    if re.search(invalid_chars, file_path):
        raise ValidationError("file_path", file_path, "文件路径包含非法字符")
    
    return file_path


def validate_tag_name(name: str) -> str:
    """
    验证标签名称
    
    检查标签名称的有效性，确保名称格式正确。
    
    验证规则：
    1. 不能为空或纯空白
    2. 长度不能超过50个字符
    3. 不能只包含数字
    
    Args:
        name: 标签名称字符串
    
    Returns:
        str: 清理后的标签名称（去除首尾空白）
    
    Raises:
        ValidationError: 标签名称验证失败时抛出
            - 名称为空
            - 名称过长
            - 名称只包含数字
    
    Example:
        >>> validate_tag_name("  动作片  ")
        '动作片'
        
        >>> validate_tag_name("123")
        ValidationError: 标签名称不能只包含数字
    """
    if not name or not name.strip():
        raise ValidationError("name", name, "标签名称不能为空")
    
    name = name.strip()
    
    if len(name) > 50:
        raise ValidationError("name", name, "标签名称长度不能超过50个字符")
    
    if re.match(r'^\d+$', name):
        raise ValidationError("name", name, "标签名称不能只包含数字")
    
    return name


def validate_video_data(
    file_path: str,
    title: Optional[str] = None,
    duration: Optional[int] = None,
    file_size: Optional[int] = None,
) -> dict:
    """
    验证视频数据
    
    综合验证视频的所有属性，返回验证后的数据字典。
    
    验证规则：
    - file_path: 必填，使用validate_file_path验证
    - title: 可选，长度不超过200个字符
    - duration: 可选，非负数，不超过10天（864000秒）
    - file_size: 可选，非负数
    
    Args:
        file_path: 视频文件路径（必填）
        title: 视频标题（可选）
        duration: 视频时长秒数（可选）
        file_size: 文件大小字节数（可选）
    
    Returns:
        dict: 验证后的数据字典，只包含非None的字段
    
    Raises:
        ValidationError: 任何字段验证失败时抛出
    
    Example:
        >>> data = validate_video_data(
        ...     file_path="/video.mp4",
        ...     title="测试视频",
        ...     duration=3600,
        ...     file_size=1024000
        ... )
        >>> print(data)
        {'file_path': '/video.mp4', 'title': '测试视频', 'duration': 3600, 'file_size': 1024000}
    """
    result = {}
    
    result["file_path"] = validate_file_path(file_path)
    
    if title is not None:
        if len(title) > 200:
            raise ValidationError("title", title, "标题长度不能超过200个字符")
        result["title"] = title.strip() if title else None
    
    if duration is not None:
        if duration < 0:
            raise ValidationError("duration", duration, "时长不能为负数")
        if duration > 86400 * 10:
            raise ValidationError("duration", duration, "时长超过合理范围")
        result["duration"] = duration
    
    if file_size is not None:
        if file_size < 0:
            raise ValidationError("file_size", file_size, "文件大小不能为负数")
        result["file_size"] = file_size
    
    return result


def validate_tag_data(
    name: str,
    parent_id: Optional[int] = None,
    description: Optional[str] = None,
    sort_order: Optional[int] = None,
) -> dict:
    """
    验证标签数据
    
    综合验证标签的所有属性，返回验证后的数据字典。
    
    验证规则：
    - name: 必填，使用validate_tag_name验证
    - parent_id: 可选，必须大于0
    - description: 可选，长度不超过200个字符
    - sort_order: 可选，非负数
    
    Args:
        name: 标签名称（必填）
        parent_id: 父标签ID（可选）
        description: 标签描述（可选）
        sort_order: 排序顺序（可选）
    
    Returns:
        dict: 验证后的数据字典，只包含非None的字段
    
    Raises:
        ValidationError: 任何字段验证失败时抛出
    
    Example:
        >>> data = validate_tag_data(
        ...     name="动作片",
        ...     parent_id=1,
        ...     description="动作类型电影",
        ...     sort_order=10
        ... )
        >>> print(data)
        {'name': '动作片', 'parent_id': 1, 'description': '动作类型电影', 'sort_order': 10}
    """
    result = {}
    
    result["name"] = validate_tag_name(name)
    
    if parent_id is not None:
        if parent_id <= 0:
            raise ValidationError("parent_id", parent_id, "父标签ID必须大于0")
        result["parent_id"] = parent_id
    
    if description is not None:
        if len(description) > 200:
            raise ValidationError("description", description, "描述长度不能超过200个字符")
        result["description"] = description.strip() if description else None
    
    if sort_order is not None:
        if sort_order < 0:
            raise ValidationError("sort_order", sort_order, "排序顺序不能为负数")
        result["sort_order"] = sort_order
    
    return result


def validate_hash(hash_value: str) -> str:
    """
    验证哈希值
    
    检查哈希值格式的有效性。支持MD5（32位）、SHA1（40位）、SHA256（64位）。
    
    验证规则：
    1. 空值直接返回（允许为空）
    2. 必须是32-64位的十六进制字符串
    
    Args:
        hash_value: 哈希值字符串
    
    Returns:
        str: 清理后的哈希值（小写，去除首尾空白）
    
    Raises:
        ValidationError: 哈希值格式无效时抛出
    
    Example:
        >>> validate_hash("d41d8cd98f00b204e9800998ecf8427e")
        'd41d8cd98f00b204e9800998ecf8427e'
        
        >>> validate_hash("")
        ''
        
        >>> validate_hash("invalid")
        ValidationError: 无效的哈希值格式
    """
    if not hash_value:
        return hash_value
    
    hash_value = hash_value.strip().lower()
    
    if not re.match(r'^[a-f0-9]{32,64}$', hash_value):
        raise ValidationError("file_hash", hash_value, "无效的哈希值格式")
    
    return hash_value

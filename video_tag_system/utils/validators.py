"""
数据验证器
"""
import os
import re
from typing import Optional

from video_tag_system.exceptions import ValidationError


def validate_file_path(file_path: str) -> str:
    """
    验证文件路径
    
    Args:
        file_path: 文件路径
        
    Returns:
        清理后的文件路径
        
    Raises:
        ValidationError: 验证失败
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
    
    Args:
        name: 标签名称
        
    Returns:
        清理后的标签名称
        
    Raises:
        ValidationError: 验证失败
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
    
    Args:
        file_path: 文件路径
        title: 视频标题
        duration: 视频时长
        file_size: 文件大小
        
    Returns:
        验证后的数据字典
        
    Raises:
        ValidationError: 验证失败
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
    
    Args:
        name: 标签名称
        parent_id: 父标签ID
        description: 标签描述
        sort_order: 排序顺序
        
    Returns:
        验证后的数据字典
        
    Raises:
        ValidationError: 验证失败
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
    
    Args:
        hash_value: 哈希值
        
    Returns:
        清理后的哈希值
        
    Raises:
        ValidationError: 验证失败
    """
    if not hash_value:
        return hash_value
    
    hash_value = hash_value.strip().lower()
    
    if not re.match(r'^[a-f0-9]{32,64}$', hash_value):
        raise ValidationError("file_hash", hash_value, "无效的哈希值格式")
    
    return hash_value

"""
自定义异常类
"""
from typing import Optional, Any


class VideoTagSystemError(Exception):
    """系统基础异常类"""
    
    def __init__(self, message: str, details: Optional[dict] = None):
        self.message = message
        self.details = details or {}
        super().__init__(self.message)
    
    def __str__(self) -> str:
        if self.details:
            return f"{self.message} - 详情: {self.details}"
        return self.message


class VideoNotFoundError(VideoTagSystemError):
    """视频未找到异常"""
    
    def __init__(self, video_id: Optional[int] = None, file_path: Optional[str] = None):
        if video_id:
            message = f"视频不存在: ID={video_id}"
        elif file_path:
            message = f"视频不存在: 路径={file_path}"
        else:
            message = "视频不存在"
        super().__init__(message, {"video_id": video_id, "file_path": file_path})


class TagNotFoundError(VideoTagSystemError):
    """标签未找到异常"""
    
    def __init__(self, tag_id: Optional[int] = None, tag_name: Optional[str] = None):
        if tag_id:
            message = f"标签不存在: ID={tag_id}"
        elif tag_name:
            message = f"标签不存在: 名称={tag_name}"
        else:
            message = "标签不存在"
        super().__init__(message, {"tag_id": tag_id, "tag_name": tag_name})


class DuplicateVideoError(VideoTagSystemError):
    """重复视频异常"""
    
    def __init__(self, file_path: str, existing_id: Optional[int] = None):
        message = f"视频已存在: {file_path}"
        super().__init__(message, {"file_path": file_path, "existing_id": existing_id})


class DuplicateTagError(VideoTagSystemError):
    """重复标签异常"""
    
    def __init__(self, tag_name: str, parent_id: Optional[int] = None):
        message = f"标签已存在: {tag_name}"
        super().__init__(message, {"tag_name": tag_name, "parent_id": parent_id})


class DatabaseError(VideoTagSystemError):
    """数据库异常"""
    
    def __init__(self, message: str, original_error: Optional[Exception] = None):
        details = {"original_error": str(original_error)} if original_error else {}
        super().__init__(message, details)


class ValidationError(VideoTagSystemError):
    """数据验证异常"""
    
    def __init__(self, field: str, value: Any, reason: str):
        message = f"验证失败 - 字段 '{field}': {reason}"
        super().__init__(message, {"field": field, "value": value, "reason": reason})


class TagMergeError(VideoTagSystemError):
    """标签合并异常"""
    
    def __init__(self, source_id: int, target_id: int, reason: str):
        message = f"标签合并失败: {reason}"
        super().__init__(message, {"source_id": source_id, "target_id": target_id})


class BackupError(VideoTagSystemError):
    """备份异常"""
    
    def __init__(self, operation: str, reason: str):
        message = f"备份操作失败 ({operation}): {reason}"
        super().__init__(message, {"operation": operation})

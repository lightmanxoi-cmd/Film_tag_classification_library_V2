"""
自定义异常类模块

本模块定义了视频标签分类系统中使用的所有自定义异常类。
采用层级化的异常设计，便于错误处理和日志记录。

异常层次结构：
    VideoTagSystemError (基类)
    ├── VideoNotFoundError      - 视频未找到
    ├── TagNotFoundError        - 标签未找到
    ├── DuplicateVideoError     - 重复视频
    ├── DuplicateTagError       - 重复标签
    ├── DatabaseError           - 数据库操作错误
    ├── ValidationError         - 数据验证错误
    ├── TagMergeError           - 标签合并错误
    └── BackupError             - 备份操作错误

使用示例：
    from video_tag_system.exceptions import VideoNotFoundError
    
    try:
        video = get_video(video_id)
    except VideoNotFoundError as e:
        print(f"错误: {e.message}")
        print(f"详情: {e.details}")
"""
from typing import Optional, Any


class VideoTagSystemError(Exception):
    """
    系统基础异常类
    
    所有自定义异常类的基类，提供统一的错误信息格式和详情存储。
    
    Attributes:
        message: 错误信息，人类可读的描述
        details: 错误详情字典，存储额外的上下文信息
    
    Example:
        raise VideoTagSystemError("操作失败", {"reason": "未知错误"})
    """
    
    def __init__(self, message: str, details: Optional[dict] = None):
        """
        初始化异常
        
        Args:
            message: 错误信息
            details: 错误详情字典，可选
        """
        self.message = message
        self.details = details or {}
        super().__init__(self.message)
    
    def __str__(self) -> str:
        """
        返回异常的字符串表示
        
        如果有详情信息，会附加在消息后面。
        
        Returns:
            str: 格式化的错误信息
        """
        if self.details:
            return f"{self.message} - 详情: {self.details}"
        return self.message


class VideoNotFoundError(VideoTagSystemError):
    """
    视频未找到异常
    
    当尝试访问不存在的视频时抛出。
    支持通过视频ID或文件路径标识缺失的视频。
    
    Example:
        raise VideoNotFoundError(video_id=123)
        raise VideoNotFoundError(file_path="/path/to/video.mp4")
    """
    
    def __init__(self, video_id: Optional[int] = None, file_path: Optional[str] = None):
        """
        初始化视频未找到异常
        
        Args:
            video_id: 视频ID，可选
            file_path: 视频文件路径，可选
        """
        if video_id:
            message = f"视频不存在: ID={video_id}"
        elif file_path:
            message = f"视频不存在: 路径={file_path}"
        else:
            message = "视频不存在"
        super().__init__(message, {"video_id": video_id, "file_path": file_path})


class TagNotFoundError(VideoTagSystemError):
    """
    标签未找到异常
    
    当尝试访问不存在的标签时抛出。
    支持通过标签ID或标签名称标识缺失的标签。
    
    Example:
        raise TagNotFoundError(tag_id=456)
        raise TagNotFoundError(tag_name="动作")
    """
    
    def __init__(self, tag_id: Optional[int] = None, tag_name: Optional[str] = None):
        """
        初始化标签未找到异常
        
        Args:
            tag_id: 标签ID，可选
            tag_name: 标签名称，可选
        """
        if tag_id:
            message = f"标签不存在: ID={tag_id}"
        elif tag_name:
            message = f"标签不存在: 名称={tag_name}"
        else:
            message = "标签不存在"
        super().__init__(message, {"tag_id": tag_id, "tag_name": tag_name})


class DuplicateVideoError(VideoTagSystemError):
    """
    重复视频异常
    
    当尝试添加已存在的视频时抛出。
    视频的唯一性由文件路径判断。
    
    Example:
        raise DuplicateVideoError("/path/to/video.mp4", existing_id=123)
    """
    
    def __init__(self, file_path: str, existing_id: Optional[int] = None):
        """
        初始化重复视频异常
        
        Args:
            file_path: 重复视频的文件路径
            existing_id: 已存在视频的ID，可选
        """
        message = f"视频已存在: {file_path}"
        super().__init__(message, {"file_path": file_path, "existing_id": existing_id})


class DuplicateTagError(VideoTagSystemError):
    """
    重复标签异常
    
    当尝试添加已存在的标签时抛出。
    标签的唯一性由名称和父标签ID组合判断。
    
    Example:
        raise DuplicateTagError("动作", parent_id=1)
    """
    
    def __init__(self, tag_name: str, parent_id: Optional[int] = None):
        """
        初始化重复标签异常
        
        Args:
            tag_name: 重复标签的名称
            parent_id: 父标签ID，可选
        """
        message = f"标签已存在: {tag_name}"
        super().__init__(message, {"tag_name": tag_name, "parent_id": parent_id})


class DatabaseError(VideoTagSystemError):
    """
    数据库操作异常
    
    当数据库操作失败时抛出，封装原始异常信息。
    
    Example:
        try:
            session.commit()
        except Exception as e:
            raise DatabaseError("保存数据失败", e)
    """
    
    def __init__(self, message: str, original_error: Optional[Exception] = None):
        """
        初始化数据库异常
        
        Args:
            message: 错误描述信息
            original_error: 原始异常对象，可选
        """
        details = {"original_error": str(original_error)} if original_error else {}
        super().__init__(message, details)


class ValidationError(VideoTagSystemError):
    """
    数据验证异常
    
    当数据验证失败时抛出，包含字段名、值和失败原因。
    
    Example:
        raise ValidationError("title", "", "标题不能为空")
        raise ValidationError("duration", -1, "时长必须为正数")
    """
    
    def __init__(self, field: str, value: Any, reason: str):
        """
        初始化验证异常
        
        Args:
            field: 验证失败的字段名
            value: 字段的值
            reason: 验证失败的原因
        """
        message = f"验证失败 - 字段 '{field}': {reason}"
        super().__init__(message, {"field": field, "value": value, "reason": reason})


class TagMergeError(VideoTagSystemError):
    """
    标签合并异常
    
    当标签合并操作失败时抛出。
    标签合并通常用于将一个标签的所有关联转移到另一个标签。
    
    Example:
        raise TagMergeError(source_id=1, target_id=2, reason="不能合并到自身")
    """
    
    def __init__(self, source_id: int, target_id: int, reason: str):
        """
        初始化标签合并异常
        
        Args:
            source_id: 源标签ID（将被合并的标签）
            target_id: 目标标签ID（合并到的标签）
            reason: 合并失败的原因
        """
        message = f"标签合并失败: {reason}"
        super().__init__(message, {"source_id": source_id, "target_id": target_id})


class BackupError(VideoTagSystemError):
    """
    备份操作异常
    
    当数据库备份或恢复操作失败时抛出。
    
    Example:
        raise BackupError("backup", "磁盘空间不足")
        raise BackupError("restore", "备份文件已损坏")
    """
    
    def __init__(self, operation: str, reason: str):
        """
        初始化备份异常
        
        Args:
            operation: 操作类型，如 "backup" 或 "restore"
            reason: 失败原因
        """
        message = f"备份操作失败 ({operation}): {reason}"
        super().__init__(message, {"operation": operation})

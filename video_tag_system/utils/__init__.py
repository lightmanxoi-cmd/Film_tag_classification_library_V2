"""
工具模块

提供系统通用的工具函数和类，包括缓存、验证、辅助函数、缩略图生成、日志等。

子模块：
    - cache: 查询缓存模块，支持LRU淘汰策略
    - validators: 数据验证器，确保输入数据的完整性
    - helpers: 辅助工具函数，如格式化、哈希计算等
    - thumbnail_generator: 视频缩略图和GIF生成器
    - logger: 统一日志系统，支持结构化日志和性能监控

主要导出：
    验证函数：
        - validate_file_path: 验证文件路径
        - validate_tag_name: 验证标签名称
        - validate_video_data: 验证视频数据
        - validate_tag_data: 验证标签数据
    
    辅助函数：
        - format_file_size: 格式化文件大小
        - format_duration: 格式化时长
        - generate_file_hash: 计算文件哈希值
    
    日志相关：
        - get_logger: 获取日志器
        - setup_logging: 初始化日志系统
        - console: 控制台输出器
        - metrics: 性能指标收集器
        - timed: 性能计时装饰器

使用示例：
    from video_tag_system.utils import validate_file_path, format_file_size, get_logger
    
    # 验证文件路径
    path = validate_file_path("/path/to/video.mp4")
    
    # 格式化文件大小
    size_str = format_file_size(1024 * 1024)  # "1.00 MB"
    
    # 使用日志
    logger = get_logger(__name__)
    logger.info("操作完成")

模块设计原则：
    1. 单一职责：每个子模块专注于特定功能
    2. 可复用：工具函数不依赖业务逻辑
    3. 可测试：纯函数易于单元测试
    4. 线程安全：缓存等组件支持并发访问
"""
from video_tag_system.utils.validators import (
    validate_file_path,
    validate_tag_name,
    validate_video_data,
    validate_tag_data,
)
from video_tag_system.utils.helpers import (
    format_file_size,
    format_duration,
    generate_file_hash,
)
from video_tag_system.utils.logger import (
    get_logger,
    setup_logging,
    console,
    metrics,
    timed,
)

__all__ = [
    "validate_file_path",
    "validate_tag_name",
    "validate_video_data",
    "validate_tag_data",
    "format_file_size",
    "format_duration",
    "generate_file_hash",
    "get_logger",
    "setup_logging",
    "console",
    "metrics",
    "timed",
]

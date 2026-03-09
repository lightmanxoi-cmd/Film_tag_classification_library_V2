"""
系统配置模块

本模块负责管理整个视频标签分类系统的配置信息，包括：
- 数据库连接配置
- 备份设置
- 批量操作参数
- 日志级别设置

配置来源优先级：
1. 环境变量（带 VTS_ 前缀）
2. .env 文件
3. 默认值

使用示例：
    from video_tag_system.core.config import get_settings
    
    settings = get_settings()
    print(settings.database_url)  # 获取数据库连接URL
"""
import os
from pathlib import Path
from typing import Optional
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    系统配置类
    
    使用 Pydantic 的 BaseSettings 实现配置管理，支持：
    - 类型验证：自动验证配置值的类型
    - 环境变量：自动从环境变量读取配置
    - .env 文件：支持从 .env 文件加载配置
    - 默认值：为所有配置项提供合理的默认值
    
    Attributes:
        database_url: 数据库连接URL，支持 SQLite、PostgreSQL 等
        database_echo: 是否在控制台打印 SQL 语句（调试用）
        backup_dir: 数据库备份文件存储目录
        max_backup_count: 最大保留的备份文件数量，超出后自动删除旧备份
        batch_size: 批量操作时的批次大小，影响导入/导出性能
        log_level: 日志输出级别（DEBUG/INFO/WARNING/ERROR）
    """
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="VTS_",
        extra="ignore"
    )
    
    database_url: str = Field(
        default="sqlite:///./video_tag_system.db",
        description="数据库连接URL，支持格式：sqlite:///path/to/db.db 或 postgresql://user:pass@host/db"
    )
    
    database_echo: bool = Field(
        default=False,
        description="是否打印SQL语句到控制台，开发调试时可设为 True"
    )
    
    backup_dir: str = Field(
        default="./backups",
        description="数据库备份文件存储目录路径"
    )
    
    max_backup_count: int = Field(
        default=100,
        description="最大备份数量，超过此数量后自动删除最旧的备份文件"
    )
    
    daily_backup_enabled: bool = Field(
        default=True,
        description="是否启用每日自动备份"
    )
    
    daily_backup_time: str = Field(
        default="03:00",
        description="每日备份时间，格式为 HH:MM（24小时制）"
    )
    
    batch_size: int = Field(
        default=100,
        description="批量操作时的批次大小，影响内存占用和处理速度"
    )
    
    log_level: str = Field(
        default="INFO",
        description="日志级别，可选值：DEBUG、INFO、WARNING、ERROR、CRITICAL"
    )
    
    @property
    def backup_path(self) -> Path:
        """
        获取备份目录的 Path 对象
        
        Returns:
            Path: 备份目录路径对象，可用于路径操作
        """
        return Path(self.backup_dir)
    
    def ensure_backup_dir(self) -> None:
        """
        确保备份目录存在
        
        如果备份目录不存在，会自动创建（包括所有父目录）。
        在执行备份操作前应调用此方法。
        """
        self.backup_path.mkdir(parents=True, exist_ok=True)


_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """
    获取配置单例
    
    使用单例模式确保整个应用程序使用同一份配置。
    首次调用时会创建配置实例，后续调用直接返回已创建的实例。
    
    Returns:
        Settings: 系统配置实例
    
    Example:
        >>> settings = get_settings()
        >>> print(settings.database_url)
        sqlite:///./video_tag_system.db
    """
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings


def reload_settings() -> Settings:
    """
    重新加载配置
    
    强制重新读取配置（从环境变量和 .env 文件）。
    当配置文件被修改后，可调用此方法使新配置生效。
    
    Returns:
        Settings: 新创建的配置实例
    
    Example:
        >>> # 修改 .env 文件后重新加载
        >>> settings = reload_settings()
    """
    global _settings
    _settings = Settings()
    return _settings

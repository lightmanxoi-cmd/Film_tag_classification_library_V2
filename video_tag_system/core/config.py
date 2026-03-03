"""
系统配置模块
"""
import os
from pathlib import Path
from typing import Optional
from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """系统配置类"""
    
    database_url: str = Field(
        default="sqlite:///./video_tag_system.db",
        description="数据库连接URL"
    )
    database_echo: bool = Field(
        default=False,
        description="是否打印SQL语句"
    )
    
    backup_dir: str = Field(
        default="./backups",
        description="备份目录路径"
    )
    
    max_backup_count: int = Field(
        default=10,
        description="最大备份数量"
    )
    
    batch_size: int = Field(
        default=100,
        description="批量操作大小"
    )
    
    log_level: str = Field(
        default="INFO",
        description="日志级别"
    )
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        env_prefix = "VTS_"
    
    @property
    def backup_path(self) -> Path:
        """获取备份目录的Path对象"""
        return Path(self.backup_dir)
    
    def ensure_backup_dir(self) -> None:
        """确保备份目录存在"""
        self.backup_path.mkdir(parents=True, exist_ok=True)


_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """获取配置单例"""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings


def reload_settings() -> Settings:
    """重新加载配置"""
    global _settings
    _settings = Settings()
    return _settings

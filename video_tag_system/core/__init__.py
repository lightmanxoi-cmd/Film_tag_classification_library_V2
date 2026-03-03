"""
核心模块
"""
from video_tag_system.core.config import Settings, get_settings
from video_tag_system.core.database import DatabaseManager, get_db_manager

__all__ = [
    "Settings",
    "get_settings",
    "DatabaseManager",
    "get_db_manager",
]

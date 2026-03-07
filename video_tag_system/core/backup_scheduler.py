"""
数据库备份调度器模块

本模块提供每日自动备份功能，包括：
- 后台定时备份任务
- 备份状态跟踪
- 备份日志记录

使用示例：
    from video_tag_system.core.backup_scheduler import BackupScheduler
    
    # 创建并启动调度器
    scheduler = BackupScheduler(db_manager)
    scheduler.start()
    
    # 停止调度器
    scheduler.stop()
"""
import os
import json
import threading
import time
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Callable

from video_tag_system.core.config import get_settings


logger = logging.getLogger(__name__)


class BackupScheduler:
    """
    数据库备份调度器
    
    在后台线程中运行，每天在指定时间自动执行数据库备份。
    
    Attributes:
        db_manager: 数据库管理器实例
        backup_callback: 备份回调函数
        running: 调度器是否正在运行
        last_backup_date: 最后备份日期
    
    Example:
        scheduler = BackupScheduler(db_manager)
        scheduler.start()
        
        # 检查状态
        if scheduler.is_running:
            print("调度器正在运行")
    """
    
    STATE_FILE = ".backup_state.json"
    
    def __init__(self, db_manager, backup_callback: Optional[Callable] = None):
        """
        初始化备份调度器
        
        Args:
            db_manager: 数据库管理器实例
            backup_callback: 可选的备份回调函数，在备份完成后调用
        """
        self.db_manager = db_manager
        self.backup_callback = backup_callback
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._lock = threading.Lock()
        self._last_backup_date: Optional[str] = None
        self._load_state()
    
    def _load_state(self):
        """从状态文件加载最后备份日期"""
        try:
            state_path = self._get_state_path()
            if state_path.exists():
                with open(state_path, 'r', encoding='utf-8') as f:
                    state = json.load(f)
                    self._last_backup_date = state.get('last_backup_date')
        except Exception as e:
            logger.warning(f"加载备份状态失败: {e}")
            self._last_backup_date = None
    
    def _save_state(self):
        """保存备份状态到文件"""
        try:
            state_path = self._get_state_path()
            state = {
                'last_backup_date': self._last_backup_date,
                'updated_at': datetime.now().isoformat()
            }
            with open(state_path, 'w', encoding='utf-8') as f:
                json.dump(state, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.warning(f"保存备份状态失败: {e}")
    
    def _get_state_path(self) -> Path:
        """获取状态文件路径"""
        settings = get_settings()
        return settings.backup_path / self.STATE_FILE
    
    @property
    def last_backup_date(self) -> Optional[str]:
        """获取最后备份日期"""
        return self._last_backup_date
    
    @property
    def is_running(self) -> bool:
        """检查调度器是否正在运行"""
        return self._thread is not None and self._thread.is_alive()
    
    def start(self):
        """
        启动备份调度器
        
        创建并启动后台线程，定期检查是否需要执行备份。
        如果调度器已在运行，则不做任何操作。
        """
        with self._lock:
            if self.is_running:
                logger.warning("备份调度器已在运行中")
                return
            
            self._stop_event.clear()
            self._thread = threading.Thread(
                target=self._run_scheduler,
                name="BackupScheduler",
                daemon=True
            )
            self._thread.start()
            logger.info("备份调度器已启动")
    
    def stop(self):
        """
        停止备份调度器
        
        设置停止标志并等待后台线程结束。
        """
        with self._lock:
            if not self.is_running:
                return
            
            self._stop_event.set()
            self._thread.join(timeout=10)
            self._thread = None
            logger.info("备份调度器已停止")
    
    def _run_scheduler(self):
        """
        调度器主循环
        
        每分钟检查一次是否需要执行备份。
        备份条件：
        1. 每日备份功能已启用
        2. 当前时间达到配置的备份时间
        3. 今天尚未执行过备份
        """
        logger.info("备份调度器线程开始运行")
        
        while not self._stop_event.is_set():
            try:
                self._check_and_backup()
            except Exception as e:
                logger.error(f"备份检查出错: {e}", exc_info=True)
            
            self._stop_event.wait(timeout=60)
        
        logger.info("备份调度器线程结束")
    
    def _check_and_backup(self):
        """
        检查并执行备份
        
        判断当前是否需要执行备份，如果需要则执行。
        """
        settings = get_settings()
        
        if not settings.daily_backup_enabled:
            return
        
        now = datetime.now()
        today_str = now.strftime("%Y-%m-%d")
        
        if self._last_backup_date == today_str:
            return
        
        try:
            backup_time = datetime.strptime(settings.daily_backup_time, "%H:%M").time()
            current_time = now.time()
            
            check_window = timedelta(minutes=1)
            backup_datetime = datetime.combine(now.date(), backup_time)
            current_datetime = datetime.combine(now.date(), current_time)
            
            if abs((current_datetime - backup_datetime).total_seconds()) <= check_window.total_seconds():
                logger.info(f"开始执行每日备份: {today_str} {settings.daily_backup_time}")
                self._execute_backup(today_str)
        except ValueError as e:
            logger.error(f"备份时间格式错误: {settings.daily_backup_time}, {e}")
    
    def _execute_backup(self, backup_date: str):
        """
        执行备份操作
        
        Args:
            backup_date: 备份日期字符串 (YYYY-MM-DD)
        """
        try:
            settings = get_settings()
            settings.ensure_backup_dir()
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_filename = f"daily_backup_{backup_date.replace('-', '')}_{timestamp}.db"
            backup_path = str(settings.backup_path / backup_filename)
            
            backup_result = self.db_manager.backup(backup_path)
            
            self._last_backup_date = backup_date
            self._save_state()
            
            logger.info(f"每日备份完成: {backup_result}")
            
            if self.backup_callback:
                try:
                    self.backup_callback(backup_result)
                except Exception as e:
                    logger.error(f"备份回调执行失败: {e}")
                    
        except Exception as e:
            logger.error(f"执行备份失败: {e}", exc_info=True)
    
    def force_backup(self) -> str:
        """
        强制执行备份
        
        不考虑时间和日期限制，立即执行一次备份。
        
        Returns:
            str: 备份文件路径
        
        Raises:
            Exception: 备份失败时抛出
        """
        logger.info("执行强制备份")
        today_str = datetime.now().strftime("%Y-%m-%d")
        self._execute_backup(today_str)
        return self._last_backup_date or ""
    
    def get_status(self) -> dict:
        """
        获取调度器状态
        
        Returns:
            dict: 包含调度器状态信息的字典
        """
        settings = get_settings()
        return {
            'running': self.is_running,
            'daily_backup_enabled': settings.daily_backup_enabled,
            'daily_backup_time': settings.daily_backup_time,
            'last_backup_date': self._last_backup_date,
            'next_backup_date': self._calculate_next_backup_date()
        }
    
    def _calculate_next_backup_date(self) -> Optional[str]:
        """
        计算下次备份日期
        
        Returns:
            Optional[str]: 下次备份日期字符串，如果备份已禁用则返回None
        """
        settings = get_settings()
        
        if not settings.daily_backup_enabled:
            return None
        
        now = datetime.now()
        today_str = now.strftime("%Y-%m-%d")
        
        if self._last_backup_date != today_str:
            return today_str
        
        tomorrow = now + timedelta(days=1)
        return tomorrow.strftime("%Y-%m-%d")


_backup_scheduler: Optional[BackupScheduler] = None


def get_backup_scheduler() -> Optional[BackupScheduler]:
    """
    获取备份调度器单例
    
    Returns:
        Optional[BackupScheduler]: 备份调度器实例，未初始化时返回None
    """
    global _backup_scheduler
    return _backup_scheduler


def init_backup_scheduler(db_manager, backup_callback: Optional[Callable] = None) -> BackupScheduler:
    """
    初始化并启动备份调度器
    
    Args:
        db_manager: 数据库管理器实例
        backup_callback: 可选的备份回调函数
    
    Returns:
        BackupScheduler: 备份调度器实例
    
    Example:
        from video_tag_system.core.database import get_db_manager
        from video_tag_system.core.backup_scheduler import init_backup_scheduler
        
        db = get_db_manager()
        scheduler = init_backup_scheduler(db)
    """
    global _backup_scheduler
    
    if _backup_scheduler is not None and _backup_scheduler.is_running:
        logger.warning("备份调度器已存在且正在运行")
        return _backup_scheduler
    
    _backup_scheduler = BackupScheduler(db_manager, backup_callback)
    
    settings = get_settings()
    if settings.daily_backup_enabled:
        _backup_scheduler.start()
    
    return _backup_scheduler


def stop_backup_scheduler():
    """
    停止备份调度器
    
    通常在应用程序退出时调用。
    """
    global _backup_scheduler
    
    if _backup_scheduler is not None:
        _backup_scheduler.stop()
        _backup_scheduler = None

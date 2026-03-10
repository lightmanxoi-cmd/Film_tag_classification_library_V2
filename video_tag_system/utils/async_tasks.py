"""
异步任务管理模块

提供后台任务执行、进度追踪、任务状态管理等功能。
解决耗时操作阻塞主线程的问题，支持批量操作的实时进度反馈。

主要组件：
    - TaskStatus: 任务状态枚举
    - TaskProgress: 任务进度数据类
    - AsyncTask: 异步任务封装类
    - TaskManager: 任务管理器（单例模式）

功能特点：
    - 后台线程池执行耗时任务
    - 实时进度追踪和状态更新
    - 任务取消和超时控制
    - 任务结果缓存和过期清理
    - 线程安全的任务管理

使用示例：
    from video_tag_system.utils.async_tasks import get_task_manager
    
    # 提交任务
    task_manager = get_task_manager()
    task_id = task_manager.submit(
        func=generate_thumbnails,
        args=([video_list],),
        kwargs={'force': True},
        task_name="批量生成缩略图"
    )
    
    # 查询进度
    progress = task_manager.get_progress(task_id)
    print(f"进度: {progress.current}/{progress.total}")
    
    # 获取结果
    result = task_manager.get_result(task_id)

Attributes:
    task_manager: 全局任务管理器实例
"""
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, Future
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, Optional, Tuple
from datetime import datetime


class TaskStatus(Enum):
    """
    任务状态枚举
    
    定义任务的生命周期状态：
    - PENDING: 等待执行
    - RUNNING: 正在执行
    - COMPLETED: 执行完成
    - FAILED: 执行失败
    - CANCELLED: 已取消
    """
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class TaskProgress:
    """
    任务进度数据类
    
    存储任务的执行进度信息，支持实时更新。
    
    Attributes:
        current: 当前处理数量
        total: 总数量
        message: 进度消息
        percentage: 完成百分比（0-100）
        items_processed: 已处理的项目列表
        items_failed: 失败的项目列表
    """
    current: int = 0
    total: int = 0
    message: str = ""
    percentage: float = 0.0
    items_processed: list = field(default_factory=list)
    items_failed: list = field(default_factory=list)
    
    def update(self, current: int, total: int, message: str = ""):
        """
        更新进度
        
        Args:
            current: 当前处理数量
            total: 总数量
            message: 进度消息
        """
        self.current = current
        self.total = total
        self.message = message
        if total > 0:
            self.percentage = round((current / total) * 100, 1)
    
    def add_processed(self, item: Any, success: bool = True):
        """
        添加处理结果
        
        Args:
            item: 处理的项目
            success: 是否成功
        """
        if success:
            self.items_processed.append(item)
        else:
            self.items_failed.append(item)


@dataclass
class AsyncTask:
    """
    异步任务封装类
    
    封装任务的所有信息，包括状态、进度、结果等。
    
    Attributes:
        id: 任务唯一标识
        name: 任务名称
        status: 任务状态
        progress: 任务进度
        result: 任务结果
        error: 错误信息
        created_at: 创建时间
        started_at: 开始时间
        completed_at: 完成时间
        future: ThreadPoolExecutor的Future对象
    """
    id: str
    name: str
    status: TaskStatus = TaskStatus.PENDING
    progress: TaskProgress = field(default_factory=TaskProgress)
    result: Any = None
    error: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    future: Optional[Future] = field(default=None, repr=False)
    
    def to_dict(self) -> Dict[str, Any]:
        """
        转换为字典格式
        
        Returns:
            Dict[str, Any]: 任务信息的字典表示
        """
        return {
            "id": self.id,
            "name": self.name,
            "status": self.status.value,
            "progress": {
                "current": self.progress.current,
                "total": self.progress.total,
                "percentage": self.progress.percentage,
                "message": self.progress.message,
                "processed_count": len(self.progress.items_processed),
                "failed_count": len(self.progress.items_failed),
            },
            "result": self.result,
            "error": self.error,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "duration_seconds": self._get_duration(),
        }
    
    def _get_duration(self) -> Optional[float]:
        """
        计算任务执行时长
        
        Returns:
            Optional[float]: 执行时长（秒），未完成返回None
        """
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None


class TaskManager:
    """
    异步任务管理器
    
    管理后台任务的提交、执行、状态追踪和结果获取。
    使用线程池执行耗时任务，支持进度回调和任务取消。
    
    特性：
    - 线程池隔离：后台任务不影响主线程
    - 进度追踪：支持实时更新任务进度
    - 结果缓存：任务结果保留一段时间
    - 自动清理：定期清理过期任务
    
    Attributes:
        _executor: 线程池执行器
        _tasks: 任务字典
        _lock: 线程锁
        _max_workers: 最大工作线程数
        _task_timeout: 任务结果超时时间（秒）
    
    Example:
        manager = TaskManager(max_workers=4)
        
        # 提交任务
        task_id = manager.submit(
            func=long_running_task,
            args=(arg1, arg2),
            task_name="我的任务"
        )
        
        # 查询进度
        progress = manager.get_progress(task_id)
        
        # 获取结果
        result = manager.get_result(task_id)
    """
    
    def __init__(self, max_workers: int = 4, task_timeout: int = 3600):
        """
        初始化任务管理器
        
        Args:
            max_workers: 最大工作线程数，默认4
            task_timeout: 任务结果超时时间（秒），默认1小时
        """
        self._executor = ThreadPoolExecutor(max_workers=max_workers)
        self._tasks: Dict[str, AsyncTask] = {}
        self._lock = threading.RLock()
        self._max_workers = max_workers
        self._task_timeout = task_timeout
        self._last_cleanup = time.time()
        self._cleanup_interval = 300
    
    def submit(
        self,
        func: Callable,
        args: Tuple = (),
        kwargs: Dict = None,
        task_name: str = "",
        progress_callback: Optional[Callable] = None
    ) -> str:
        """
        提交任务到线程池
        
        Args:
            func: 要执行的函数
            args: 位置参数元组
            kwargs: 关键字参数字典
            task_name: 任务名称
            progress_callback: 进度回调函数
        
        Returns:
            str: 任务ID
        
        Example:
            def my_task(progress, items):
                for i, item in enumerate(items):
                    progress.update(i + 1, len(items), f"处理 {item}")
                    process(item)
                return "完成"
            
            task_id = manager.submit(
                func=my_task,
                args=(items,),
                task_name="批量处理"
            )
        """
        if kwargs is None:
            kwargs = {}
        
        task_id = str(uuid.uuid4())
        task = AsyncTask(
            id=task_id,
            name=task_name or func.__name__
        )
        
        with self._lock:
            self._tasks[task_id] = task
        
        def task_wrapper():
            task.status = TaskStatus.RUNNING
            task.started_at = datetime.now()
            
            try:
                if 'progress' in func.__code__.co_varnames:
                    result = func(progress=task.progress, *args, **kwargs)
                else:
                    result = func(*args, **kwargs)
                
                task.result = result
                task.status = TaskStatus.COMPLETED
                task.completed_at = datetime.now()
                
            except Exception as e:
                task.error = str(e)
                task.status = TaskStatus.FAILED
                task.completed_at = datetime.now()
            
            return task.result
        
        future = self._executor.submit(task_wrapper)
        task.future = future
        
        self._cleanup_if_needed()
        
        return task_id
    
    def submit_batch(
        self,
        func: Callable,
        items: list,
        task_name: str = "",
        **kwargs
    ) -> str:
        """
        提交批量处理任务
        
        自动处理进度更新，简化批量任务的提交。
        
        Args:
            func: 处理单个项目的函数，签名为 func(item, **kwargs) -> bool
            items: 要处理的项目列表
            task_name: 任务名称
            **kwargs: 传递给处理函数的额外参数
        
        Returns:
            str: 任务ID
        
        Example:
            def process_video(video_path, **kwargs):
                return generate_thumbnail(video_path)
            
            task_id = manager.submit_batch(
                func=process_video,
                items=video_paths,
                task_name="生成缩略图"
            )
        """
        def batch_wrapper(progress: TaskProgress, **inner_kwargs):
            total = len(items)
            success_count = 0
            failed_count = 0
            
            progress.update(0, total, "开始处理...")
            
            for i, item in enumerate(items):
                if progress.message == "__CANCELLED__":
                    break
                
                try:
                    result = func(item, **inner_kwargs)
                    if result:
                        success_count += 1
                        progress.add_processed(item, success=True)
                    else:
                        failed_count += 1
                        progress.add_processed(item, success=False)
                except Exception as e:
                    failed_count += 1
                    progress.add_processed({"item": item, "error": str(e)}, success=False)
                
                progress.update(
                    i + 1, 
                    total, 
                    f"处理中... ({i + 1}/{total})"
                )
            
            return {
                "total": total,
                "success": success_count,
                "failed": failed_count,
            }
        
        return self.submit(
            func=batch_wrapper,
            kwargs=kwargs,
            task_name=task_name
        )
    
    def get_task(self, task_id: str) -> Optional[AsyncTask]:
        """
        获取任务对象
        
        Args:
            task_id: 任务ID
        
        Returns:
            Optional[AsyncTask]: 任务对象，不存在返回None
        """
        with self._lock:
            return self._tasks.get(task_id)
    
    def get_status(self, task_id: str) -> Optional[TaskStatus]:
        """
        获取任务状态
        
        Args:
            task_id: 任务ID
        
        Returns:
            Optional[TaskStatus]: 任务状态，不存在返回None
        """
        task = self.get_task(task_id)
        return task.status if task else None
    
    def get_progress(self, task_id: str) -> Optional[TaskProgress]:
        """
        获取任务进度
        
        Args:
            task_id: 任务ID
        
        Returns:
            Optional[TaskProgress]: 任务进度，不存在返回None
        """
        task = self.get_task(task_id)
        return task.progress if task else None
    
    def get_result(self, task_id: str, timeout: float = None) -> Any:
        """
        获取任务结果
        
        如果任务还在执行中，会等待任务完成。
        
        Args:
            task_id: 任务ID
            timeout: 等待超时时间（秒），None表示不等待
        
        Returns:
            Any: 任务结果
        
        Raises:
            TimeoutError: 等待超时时抛出
            Exception: 任务执行失败时抛出原始异常
        """
        task = self.get_task(task_id)
        if not task:
            return None
        
        if task.future is None:
            return task.result
        
        if timeout is not None:
            try:
                task.future.result(timeout=timeout)
            except Exception:
                pass
        
        if task.status == TaskStatus.FAILED:
            raise Exception(task.error)
        
        return task.result
    
    def cancel(self, task_id: str) -> bool:
        """
        取消任务
        
        尝试取消正在执行的任务。已完成的任务无法取消。
        
        Args:
            task_id: 任务ID
        
        Returns:
            bool: 取消成功返回True
        """
        task = self.get_task(task_id)
        if not task:
            return False
        
        if task.status in (TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED):
            return False
        
        task.progress.message = "__CANCELLED__"
        
        if task.future and task.future.cancel():
            task.status = TaskStatus.CANCELLED
            task.completed_at = datetime.now()
            return True
        
        return False
    
    def list_tasks(self, status: TaskStatus = None) -> list:
        """
        列出任务
        
        Args:
            status: 过滤状态，None表示不过滤
        
        Returns:
            list: 任务信息列表
        """
        with self._lock:
            tasks = []
            for task in self._tasks.values():
                if status is None or task.status == status:
                    tasks.append(task.to_dict())
            return tasks
    
    def clear_completed(self) -> int:
        """
        清理已完成的任务
        
        Returns:
            int: 清理的任务数量
        """
        count = 0
        with self._lock:
            to_remove = [
                task_id for task_id, task in self._tasks.items()
                if task.status in (TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED)
            ]
            for task_id in to_remove:
                del self._tasks[task_id]
                count += 1
        return count
    
    def _cleanup_if_needed(self):
        """
        检查并执行过期任务清理
        """
        now = time.time()
        if now - self._last_cleanup > self._cleanup_interval:
            self._last_cleanup = now
            self._cleanup_expired()
    
    def _cleanup_expired(self) -> int:
        """
        清理过期任务
        
        Returns:
            int: 清理的任务数量
        """
        count = 0
        now = time.time()
        
        with self._lock:
            to_remove = []
            for task_id, task in self._tasks.items():
                if task.completed_at:
                    age = (datetime.now() - task.completed_at).total_seconds()
                    if age > self._task_timeout:
                        to_remove.append(task_id)
            
            for task_id in to_remove:
                del self._tasks[task_id]
                count += 1
        
        return count
    
    def shutdown(self, wait: bool = True):
        """
        关闭任务管理器
        
        Args:
            wait: 是否等待所有任务完成
        """
        self._executor.shutdown(wait=wait)
    
    def get_stats(self) -> Dict[str, Any]:
        """
        获取任务管理器统计信息
        
        Returns:
            Dict[str, Any]: 统计信息
        """
        with self._lock:
            status_counts = {}
            for status in TaskStatus:
                status_counts[status.value] = sum(
                    1 for t in self._tasks.values() if t.status == status
                )
            
            return {
                "total_tasks": len(self._tasks),
                "max_workers": self._max_workers,
                "status_counts": status_counts,
                "task_timeout": self._task_timeout,
            }


task_manager: Optional[TaskManager] = None


def get_task_manager() -> TaskManager:
    """
    获取全局任务管理器实例
    
    Returns:
        TaskManager: 全局任务管理器实例
    
    Example:
        manager = get_task_manager()
        task_id = manager.submit(func=my_task)
    """
    global task_manager
    if task_manager is None:
        task_manager = TaskManager(max_workers=4)
    return task_manager


def init_task_manager(max_workers: int = 4, task_timeout: int = 3600) -> TaskManager:
    """
    初始化全局任务管理器
    
    Args:
        max_workers: 最大工作线程数
        task_timeout: 任务结果超时时间（秒）
    
    Returns:
        TaskManager: 任务管理器实例
    """
    global task_manager
    task_manager = TaskManager(max_workers=max_workers, task_timeout=task_timeout)
    return task_manager

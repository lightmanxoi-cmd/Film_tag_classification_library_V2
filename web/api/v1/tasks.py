"""
API v1 任务管理路由模块

提供异步任务的状态查询、进度追踪、结果获取等API接口。

路由列表：
    GET    /tasks                 # 获取任务列表
    GET    /tasks/<task_id>       # 获取任务详情
    GET    /tasks/<task_id>/progress  # 获取任务进度
    GET    /tasks/<task_id>/result    # 获取任务结果
    POST   /tasks/<task_id>/cancel    # 取消任务
    DELETE /tasks/completed       # 清理已完成任务

使用示例：
    # 获取任务进度
    GET /api/v1/tasks/abc123/progress
    
    # 取消任务
    POST /api/v1/tasks/abc123/cancel
"""
from flask import Blueprint, request

from web.auth.decorators import login_required
from web.core.responses import APIResponse
from web.core.errors import handle_exceptions
from video_tag_system.utils.async_tasks import get_task_manager, TaskStatus

tasks_bp = Blueprint('tasks', __name__, url_prefix='/tasks')


@tasks_bp.route('', methods=['GET'])
@login_required
@handle_exceptions
def list_tasks():
    """
    获取任务列表
    
    Query Parameters:
        status: 过滤状态 (pending/running/completed/failed/cancelled)
    
    Returns:
        JSON响应，包含任务列表
    
    Example:
        GET /api/v1/tasks?status=running
    """
    status_filter = request.args.get('status', None)
    
    manager = get_task_manager()
    
    status = None
    if status_filter:
        try:
            status = TaskStatus(status_filter)
        except ValueError:
            pass
    
    tasks = manager.list_tasks(status=status)
    
    return APIResponse.success(data={
        'tasks': tasks,
        'total': len(tasks)
    })


@tasks_bp.route('/<task_id>', methods=['GET'])
@login_required
@handle_exceptions
def get_task(task_id):
    """
    获取任务详情
    
    Args:
        task_id: 任务ID
    
    Returns:
        JSON响应，包含任务详细信息
    
    Example:
        GET /api/v1/tasks/abc123
    """
    manager = get_task_manager()
    task = manager.get_task(task_id)
    
    if not task:
        return APIResponse.not_found(f"任务不存在: {task_id}")
    
    return APIResponse.success(data=task.to_dict())


@tasks_bp.route('/<task_id>/progress', methods=['GET'])
@login_required
@handle_exceptions
def get_task_progress(task_id):
    """
    获取任务进度
    
    Args:
        task_id: 任务ID
    
    Returns:
        JSON响应，包含任务进度信息
    
    Example:
        GET /api/v1/tasks/abc123/progress
        {
            "success": true,
            "data": {
                "current": 50,
                "total": 100,
                "percentage": 50.0,
                "message": "处理中...",
                "processed_count": 48,
                "failed_count": 2
            }
        }
    """
    manager = get_task_manager()
    progress = manager.get_progress(task_id)
    
    if progress is None:
        return APIResponse.not_found(f"任务不存在: {task_id}")
    
    return APIResponse.success(data={
        'current': progress.current,
        'total': progress.total,
        'percentage': progress.percentage,
        'message': progress.message,
        'processed_count': len(progress.items_processed),
        'failed_count': len(progress.items_failed),
    })


@tasks_bp.route('/<task_id>/result', methods=['GET'])
@login_required
@handle_exceptions
def get_task_result(task_id):
    """
    获取任务结果
    
    Args:
        task_id: 任务ID
    
    Query Parameters:
        timeout: 等待超时时间（秒），默认不等待
    
    Returns:
        JSON响应，包含任务结果
    
    Example:
        GET /api/v1/tasks/abc123/result?timeout=5
    """
    from flask import request
    
    timeout = request.args.get('timeout', None, type=float)
    
    manager = get_task_manager()
    task = manager.get_task(task_id)
    
    if not task:
        return APIResponse.not_found(f"任务不存在: {task_id}")
    
    if task.status == TaskStatus.RUNNING:
        if timeout is None:
            return APIResponse.success(data={
                'status': 'running',
                'message': '任务正在执行中',
                'progress': {
                    'current': task.progress.current,
                    'total': task.progress.total,
                    'percentage': task.progress.percentage,
                }
            })
    
    try:
        result = manager.get_result(task_id, timeout=timeout)
        return APIResponse.success(data={
            'status': task.status.value,
            'result': result,
            'error': task.error
        })
    except Exception as e:
        return APIResponse.error(str(e))


@tasks_bp.route('/<task_id>/cancel', methods=['POST'])
@login_required
@handle_exceptions
def cancel_task(task_id):
    """
    取消任务
    
    Args:
        task_id: 任务ID
    
    Returns:
        JSON响应
    
    Example:
        POST /api/v1/tasks/abc123/cancel
    """
    manager = get_task_manager()
    
    task = manager.get_task(task_id)
    if not task:
        return APIResponse.not_found(f"任务不存在: {task_id}")
    
    if task.status in (TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED):
        return APIResponse.error(f"任务已完成，无法取消")
    
    success = manager.cancel(task_id)
    
    if success:
        return APIResponse.success(message='任务已取消')
    else:
        return APIResponse.error('取消任务失败')


@tasks_bp.route('/completed', methods=['DELETE'])
@login_required
@handle_exceptions
def clear_completed_tasks():
    """
    清理已完成任务
    
    Returns:
        JSON响应，包含清理的任务数量
    
    Example:
        DELETE /api/v1/tasks/completed
    """
    manager = get_task_manager()
    count = manager.clear_completed()
    
    return APIResponse.success(
        message=f'已清理 {count} 个已完成任务',
        data={'cleared_count': count}
    )


@tasks_bp.route('/stats', methods=['GET'])
@login_required
@handle_exceptions
def get_task_stats():
    """
    获取任务统计信息
    
    Returns:
        JSON响应，包含任务管理器统计信息
    
    Example:
        GET /api/v1/tasks/stats
    """
    manager = get_task_manager()
    stats = manager.get_stats()
    
    return APIResponse.success(data=stats)

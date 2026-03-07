"""
服务上下文管理模块

管理请求级别的服务实例，使用Flask的g对象存储。
确保每个请求使用独立的数据库会话和服务实例。

主要功能：
    - get_services: 获取当前请求的服务实例

使用示例：
    from web.services import get_services
    
    video_svc, tag_svc, video_tag_svc, session = get_services()
    video = video_svc.get_video(1)

设计原则：
    - 懒加载：首次访问时创建实例
    - 请求隔离：每个请求使用独立的会话
    - 自动清理：请求结束时自动关闭会话
"""
from flask import g


def get_services():
    """
    获取服务实例
    
    获取当前请求的服务实例，如果不存在则创建。
    使用Flask的g对象存储，确保请求隔离。
    
    Returns:
        tuple: (video_service, tag_service, video_tag_service, db_session)
            - video_service: 视频业务逻辑实例
            - tag_service: 标签业务逻辑实例
            - video_tag_service: 视频-标签关联业务逻辑实例
            - db_session: 数据库会话实例
    
    Example:
        video_svc, tag_svc, video_tag_svc, session = get_services()
        
        # 使用服务
        video = video_svc.get_video(1)
        tags = tag_svc.get_tag_tree()
        
        # 会话会在请求结束时自动关闭
    """
    from video_tag_system.services.video_service import VideoService
    from video_tag_system.services.tag_service import TagService
    from video_tag_system.services.video_tag_service import VideoTagService
    from web.app import get_db_manager
    
    if g.db_session is None:
        g.db_session = get_db_manager().session_factory()
    
    if g.video_service is None:
        g.video_service = VideoService(g.db_session)
    
    if g.tag_service is None:
        g.tag_service = TagService(g.db_session)
    
    if g.video_tag_service is None:
        g.video_tag_service = VideoTagService(g.db_session)
    
    return (
        g.video_service,
        g.tag_service,
        g.video_tag_service,
        g.db_session
    )

"""
服务上下文管理
"""
from flask import g


def get_services():
    """获取服务实例（用于请求上下文）"""
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

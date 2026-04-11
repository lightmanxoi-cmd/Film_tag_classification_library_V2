"""
服务定位器模块

管理请求级别的服务实例，使用Flask的g对象存储。
确保每个请求使用独立的数据库会话和服务实例。

主要功能：
    - ServiceLocator: 服务定位器，按需创建服务实例
    - get_services: 兼容旧接口，获取全部服务实例

设计原则：
    - 懒加载：首次访问时创建实例
    - 按需创建：只创建实际需要的服务
    - 请求隔离：每个请求使用独立的会话
    - 自动清理：请求结束时自动关闭会话

使用示例：
    from web.services import ServiceLocator
    
    # 按需获取单个服务
    video_svc = ServiceLocator.get_video_service()
    tag_svc = ServiceLocator.get_tag_service()
    
    # 兼容旧接口
    video_svc, tag_svc, video_tag_svc, session = get_services()
"""
from flask import g


class ServiceLocator:
    """
    服务定位器
    
    基于Flask的g对象管理请求级别的服务实例。
    支持按需创建，避免一次性创建所有服务。
    
    每个服务在首次请求时创建，后续请求直接返回缓存实例。
    所有服务共享同一个数据库会话，确保事务一致性。
    
    Example:
        video_svc = ServiceLocator.get_video_service()
        tag_svc = ServiceLocator.get_tag_service()
        video_tag_svc = ServiceLocator.get_video_tag_service()
        session = ServiceLocator.get_db_session()
    """

    @staticmethod
    def get_db_session():
        """
        获取数据库会话
        
        懒加载创建数据库会话，存储在Flask的g对象中。
        同一请求内复用同一会话。
        
        Returns:
            Session: SQLAlchemy 数据库会话实例
        """
        if getattr(g, 'db_session', None) is None:
            from video_tag_system.core.database import get_db_manager
            g.db_session = get_db_manager().session_factory()
        return g.db_session

    @staticmethod
    def get_video_service():
        """
        获取视频服务实例
        
        懒加载创建VideoService，仅在首次调用时创建。
        
        Returns:
            VideoService: 视频业务逻辑实例
        """
        if getattr(g, 'video_service', None) is None:
            from video_tag_system.services.video_service import VideoService
            g.video_service = VideoService(ServiceLocator.get_db_session())
        return g.video_service

    @staticmethod
    def get_tag_service():
        """
        获取标签服务实例
        
        懒加载创建TagService，仅在首次调用时创建。
        
        Returns:
            TagService: 标签业务逻辑实例
        """
        if getattr(g, 'tag_service', None) is None:
            from video_tag_system.services.tag_service import TagService
            g.tag_service = TagService(ServiceLocator.get_db_session())
        return g.tag_service

    @staticmethod
    def get_video_tag_service():
        """
        获取视频-标签关联服务实例
        
        懒加载创建VideoTagService，仅在首次调用时创建。
        
        Returns:
            VideoTagService: 视频-标签关联业务逻辑实例
        """
        if getattr(g, 'video_tag_service', None) is None:
            from video_tag_system.services.video_tag_service import VideoTagService
            g.video_tag_service = VideoTagService(ServiceLocator.get_db_session())
        return g.video_tag_service


def get_services():
    """
    获取全部服务实例（兼容旧接口）
    
    返回所有服务实例的元组，保持向后兼容。
    推荐使用 ServiceLocator 按需获取单个服务。
    
    Returns:
        tuple: (video_service, tag_service, video_tag_service, db_session)
            - video_service: 视频业务逻辑实例
            - tag_service: 标签业务逻辑实例
            - video_tag_service: 视频-标签关联业务逻辑实例
            - db_session: 数据库会话实例
    
    Example:
        video_svc, tag_svc, video_tag_svc, session = get_services()
    """
    return (
        ServiceLocator.get_video_service(),
        ServiceLocator.get_tag_service(),
        ServiceLocator.get_video_tag_service(),
        ServiceLocator.get_db_session()
    )

"""
测试配置
"""
import os
import tempfile
import pytest
from pathlib import Path

from video_tag_system.core.database import DatabaseManager, Base
from video_tag_system.core.config import Settings


@pytest.fixture
def temp_db():
    """创建临时数据库"""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    
    db_url = f"sqlite:///{db_path}"
    
    yield db_url
    
    if os.path.exists(db_path):
        os.unlink(db_path)


@pytest.fixture
def db_manager(temp_db):
    """创建数据库管理器"""
    manager = DatabaseManager(database_url=temp_db, echo=False)
    manager.create_tables()
    
    yield manager
    
    manager.close()


@pytest.fixture
def session(db_manager):
    """创建数据库会话"""
    with db_manager.get_session() as s:
        yield s


@pytest.fixture
def video_service(session):
    """创建视频服务"""
    from video_tag_system.services.video_service import VideoService
    return VideoService(session)


@pytest.fixture
def tag_service(session):
    """创建标签服务"""
    from video_tag_system.services.tag_service import TagService
    return TagService(session)


@pytest.fixture
def video_tag_service(session):
    """创建视频标签关联服务"""
    from video_tag_system.services.video_tag_service import VideoTagService
    return VideoTagService(session)


@pytest.fixture
def sample_video_data():
    """示例视频数据"""
    from video_tag_system.models.video import VideoCreate
    return VideoCreate(
        file_path="/videos/sample.mp4",
        title="测试视频",
        description="这是一个测试视频",
        duration=3600,
        file_size=1024 * 1024 * 100
    )


@pytest.fixture
def sample_tag_data():
    """示例标签数据"""
    from video_tag_system.models.tag import TagCreate
    return TagCreate(
        name="动作",
        description="动作类型视频"
    )


@pytest.fixture
def sample_child_tag_data():
    """示例子标签数据"""
    from video_tag_system.models.tag import TagCreate
    return TagCreate(
        name="武侠",
        description="武侠动作视频",
        parent_id=1
    )

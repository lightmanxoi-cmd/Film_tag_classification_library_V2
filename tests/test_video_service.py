"""
测试视频服务
"""
import pytest
from video_tag_system.models.video import VideoCreate, VideoUpdate
from video_tag_system.exceptions import VideoNotFoundError, DuplicateVideoError


class TestVideoService:
    """视频服务测试类"""
    
    def test_create_video(self, video_service, sample_video_data):
        """测试创建视频"""
        result = video_service.create_video(sample_video_data)
        
        assert result.id is not None
        assert result.file_path == sample_video_data.file_path
        assert result.title == sample_video_data.title
        assert result.description == sample_video_data.description
        assert result.duration == sample_video_data.duration
        assert result.file_size == sample_video_data.file_size
    
    def test_create_duplicate_video(self, video_service, sample_video_data):
        """测试创建重复视频"""
        video_service.create_video(sample_video_data)
        
        with pytest.raises(DuplicateVideoError):
            video_service.create_video(sample_video_data)
    
    def test_get_video(self, video_service, sample_video_data):
        """测试获取视频"""
        created = video_service.create_video(sample_video_data)
        
        result = video_service.get_video(created.id)
        
        assert result.id == created.id
        assert result.file_path == sample_video_data.file_path
    
    def test_get_video_not_found(self, video_service):
        """测试获取不存在的视频"""
        with pytest.raises(VideoNotFoundError):
            video_service.get_video(9999)
    
    def test_update_video(self, video_service, sample_video_data):
        """测试更新视频"""
        created = video_service.create_video(sample_video_data)
        
        update_data = VideoUpdate(
            title="更新后的标题",
            description="更新后的描述"
        )
        result = video_service.update_video(created.id, update_data)
        
        assert result.title == "更新后的标题"
        assert result.description == "更新后的描述"
    
    def test_update_video_not_found(self, video_service):
        """测试更新不存在的视频"""
        update_data = VideoUpdate(title="新标题")
        
        with pytest.raises(VideoNotFoundError):
            video_service.update_video(9999, update_data)
    
    def test_delete_video(self, video_service, sample_video_data):
        """测试删除视频"""
        created = video_service.create_video(sample_video_data)
        
        result = video_service.delete_video(created.id)
        assert result is True
        
        with pytest.raises(VideoNotFoundError):
            video_service.get_video(created.id)
    
    def test_delete_video_not_found(self, video_service):
        """测试删除不存在的视频"""
        with pytest.raises(VideoNotFoundError):
            video_service.delete_video(9999)
    
    def test_list_videos(self, video_service):
        """测试获取视频列表"""
        for i in range(5):
            video_data = VideoCreate(
                file_path=f"/videos/video_{i}.mp4",
                title=f"视频 {i}"
            )
            video_service.create_video(video_data)
        
        result = video_service.list_videos(page=1, page_size=10)
        
        assert result.total == 5
        assert len(result.items) == 5
    
    def test_list_videos_with_search(self, video_service):
        """测试搜索视频"""
        video_service.create_video(VideoCreate(
            file_path="/videos/action.mp4",
            title="动作电影"
        ))
        video_service.create_video(VideoCreate(
            file_path="/videos/comedy.mp4",
            title="喜剧电影"
        ))
        
        result = video_service.list_videos(search="动作")
        
        assert result.total == 1
        assert result.items[0].title == "动作电影"
    
    def test_count_videos(self, video_service):
        """测试获取视频数量"""
        assert video_service.count_videos() == 0
        
        video_service.create_video(VideoCreate(
            file_path="/videos/test.mp4",
            title="测试"
        ))
        
        assert video_service.count_videos() == 1

"""
测试视频-标签关联服务
"""
import pytest
from video_tag_system.models.video import VideoCreate
from video_tag_system.models.tag import TagCreate
from video_tag_system.models.video_tag import BatchTagOperation
from video_tag_system.exceptions import VideoNotFoundError, TagNotFoundError


class TestVideoTagService:
    """视频-标签关联服务测试类"""
    
    def test_add_tag_to_video(self, video_service, tag_service, video_tag_service):
        """测试为视频添加标签"""
        video = video_service.create_video(VideoCreate(
            file_path="/videos/test.mp4",
            title="测试视频"
        ))
        tag = tag_service.create_tag(TagCreate(name="动作"))
        
        result = video_tag_service.add_tag_to_video(video.id, tag.id)
        
        assert result["added"] is True
        assert result["video_id"] == video.id
        assert result["tag_id"] == tag.id
    
    def test_add_duplicate_tag(self, video_service, tag_service, video_tag_service):
        """测试重复添加标签"""
        video = video_service.create_video(VideoCreate(
            file_path="/videos/test.mp4"
        ))
        tag = tag_service.create_tag(TagCreate(name="动作"))
        
        video_tag_service.add_tag_to_video(video.id, tag.id)
        result = video_tag_service.add_tag_to_video(video.id, tag.id)
        
        assert result["added"] is False
        assert "已存在" in result["message"]
    
    def test_remove_tag_from_video(self, video_service, tag_service, video_tag_service):
        """测试从视频移除标签"""
        video = video_service.create_video(VideoCreate(
            file_path="/videos/test.mp4"
        ))
        tag = tag_service.create_tag(TagCreate(name="动作"))
        
        video_tag_service.add_tag_to_video(video.id, tag.id)
        result = video_tag_service.remove_tag_from_video(video.id, tag.id)
        
        assert result["removed"] is True
    
    def test_get_video_tags(self, video_service, tag_service, video_tag_service):
        """测试获取视频标签"""
        video = video_service.create_video(VideoCreate(
            file_path="/videos/test.mp4"
        ))
        tag1 = tag_service.create_tag(TagCreate(name="动作"))
        tag2 = tag_service.create_tag(TagCreate(name="喜剧"))
        
        video_tag_service.add_tag_to_video(video.id, tag1.id)
        video_tag_service.add_tag_to_video(video.id, tag2.id)
        
        tags = video_tag_service.get_video_tags(video.id)
        
        assert len(tags) == 2
        tag_names = {t.name for t in tags}
        assert "动作" in tag_names
        assert "喜剧" in tag_names
    
    def test_set_video_tags(self, video_service, tag_service, video_tag_service):
        """测试设置视频标签"""
        video = video_service.create_video(VideoCreate(
            file_path="/videos/test.mp4"
        ))
        tag1 = tag_service.create_tag(TagCreate(name="动作"))
        tag2 = tag_service.create_tag(TagCreate(name="喜剧"))
        tag3 = tag_service.create_tag(TagCreate(name="爱情"))
        
        video_tag_service.add_tag_to_video(video.id, tag1.id)
        
        result = video_tag_service.set_video_tags(video.id, [tag2.id, tag3.id])
        
        assert result["tags_added"] == 2
        assert result["tags_removed"] == 1
        
        tags = video_tag_service.get_video_tags(video.id)
        assert len(tags) == 2
    
    def test_batch_add_tags(self, video_service, tag_service, video_tag_service):
        """测试批量添加标签"""
        video1 = video_service.create_video(VideoCreate(
            file_path="/videos/test1.mp4"
        ))
        video2 = video_service.create_video(VideoCreate(
            file_path="/videos/test2.mp4"
        ))
        tag1 = tag_service.create_tag(TagCreate(name="动作"))
        tag2 = tag_service.create_tag(TagCreate(name="喜剧"))
        
        operation = BatchTagOperation(
            video_ids=[video1.id, video2.id],
            tag_ids=[tag1.id, tag2.id]
        )
        result = video_tag_service.batch_add_tags(operation)
        
        assert result["videos_affected"] == 2
        assert result["tags_added"] == 4
    
    def test_batch_remove_tags(self, video_service, tag_service, video_tag_service):
        """测试批量移除标签"""
        video1 = video_service.create_video(VideoCreate(
            file_path="/videos/test1.mp4"
        ))
        video2 = video_service.create_video(VideoCreate(
            file_path="/videos/test2.mp4"
        ))
        tag = tag_service.create_tag(TagCreate(name="动作"))
        
        video_tag_service.add_tag_to_video(video1.id, tag.id)
        video_tag_service.add_tag_to_video(video2.id, tag.id)
        
        operation = BatchTagOperation(
            video_ids=[video1.id, video2.id],
            tag_ids=[tag.id]
        )
        result = video_tag_service.batch_remove_tags(operation)
        
        assert result["tags_removed"] == 2
    
    def test_add_tag_to_nonexistent_video(self, tag_service, video_tag_service):
        """测试为不存在的视频添加标签"""
        tag = tag_service.create_tag(TagCreate(name="动作"))
        
        with pytest.raises(VideoNotFoundError):
            video_tag_service.add_tag_to_video(9999, tag.id)
    
    def test_add_nonexistent_tag_to_video(self, video_service, video_tag_service):
        """测试为视频添加不存在的标签"""
        video = video_service.create_video(VideoCreate(
            file_path="/videos/test.mp4"
        ))
        
        with pytest.raises(TagNotFoundError):
            video_tag_service.add_tag_to_video(video.id, 9999)
    
    def test_check_video_has_tag(self, video_service, tag_service, video_tag_service):
        """测试检查视频是否有标签"""
        video = video_service.create_video(VideoCreate(
            file_path="/videos/test.mp4"
        ))
        tag = tag_service.create_tag(TagCreate(name="动作"))
        
        assert video_tag_service.check_video_has_tag(video.id, tag.id) is False
        
        video_tag_service.add_tag_to_video(video.id, tag.id)
        
        assert video_tag_service.check_video_has_tag(video.id, tag.id) is True

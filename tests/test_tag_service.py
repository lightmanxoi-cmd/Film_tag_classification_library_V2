"""
测试标签服务
"""
import pytest
from video_tag_system.models.tag import TagCreate, TagUpdate
from video_tag_system.exceptions import (
    TagNotFoundError,
    DuplicateTagError,
    ValidationError
)


class TestTagService:
    """标签服务测试类"""
    
    def test_create_tag(self, tag_service, sample_tag_data):
        """测试创建标签"""
        result = tag_service.create_tag(sample_tag_data)
        
        assert result.id is not None
        assert result.name == sample_tag_data.name
        assert result.description == sample_tag_data.description
        assert result.level == 1
        assert result.parent_id is None
    
    def test_create_duplicate_tag(self, tag_service, sample_tag_data):
        """测试创建重复标签"""
        tag_service.create_tag(sample_tag_data)
        
        with pytest.raises(DuplicateTagError):
            tag_service.create_tag(sample_tag_data)
    
    def test_create_child_tag(self, tag_service, sample_tag_data, sample_child_tag_data):
        """测试创建子标签"""
        parent = tag_service.create_tag(sample_tag_data)
        
        child_data = TagCreate(
            name="武侠",
            description="武侠动作视频",
            parent_id=parent.id
        )
        result = tag_service.create_tag(child_data)
        
        assert result.parent_id == parent.id
        assert result.level == 2
    
    def test_create_tag_with_invalid_parent(self, tag_service):
        """测试使用无效父标签创建标签"""
        tag_data = TagCreate(
            name="测试",
            parent_id=9999
        )
        
        with pytest.raises(TagNotFoundError):
            tag_service.create_tag(tag_data)
    
    def test_create_three_level_tag(self, tag_service, sample_tag_data):
        """测试创建三级标签（应该失败）"""
        parent = tag_service.create_tag(sample_tag_data)
        
        child_data = TagCreate(
            name="子标签",
            parent_id=parent.id
        )
        child = tag_service.create_tag(child_data)
        
        grandchild_data = TagCreate(
            name="孙标签",
            parent_id=child.id
        )
        
        with pytest.raises(ValidationError):
            tag_service.create_tag(grandchild_data)
    
    def test_get_tag(self, tag_service, sample_tag_data):
        """测试获取标签"""
        created = tag_service.create_tag(sample_tag_data)
        
        result = tag_service.get_tag(created.id)
        
        assert result.id == created.id
        assert result.name == sample_tag_data.name
    
    def test_get_tag_not_found(self, tag_service):
        """测试获取不存在的标签"""
        with pytest.raises(TagNotFoundError):
            tag_service.get_tag(9999)
    
    def test_update_tag(self, tag_service, sample_tag_data):
        """测试更新标签"""
        created = tag_service.create_tag(sample_tag_data)
        
        update_data = TagUpdate(
            name="更新后的名称",
            description="更新后的描述"
        )
        result = tag_service.update_tag(created.id, update_data)
        
        assert result.name == "更新后的名称"
        assert result.description == "更新后的描述"
    
    def test_delete_tag(self, tag_service, sample_tag_data):
        """测试删除标签"""
        created = tag_service.create_tag(sample_tag_data)
        
        result = tag_service.delete_tag(created.id)
        assert result is True
        
        with pytest.raises(TagNotFoundError):
            tag_service.get_tag(created.id)
    
    def test_delete_tag_with_children(self, tag_service, sample_tag_data):
        """测试删除有子标签的标签"""
        parent = tag_service.create_tag(sample_tag_data)
        
        child_data = TagCreate(name="子标签", parent_id=parent.id)
        tag_service.create_tag(child_data)
        
        with pytest.raises(ValidationError):
            tag_service.delete_tag(parent.id)
    
    def test_list_tags(self, tag_service):
        """测试获取标签列表"""
        for i in range(5):
            tag_data = TagCreate(name=f"标签{i}")
            tag_service.create_tag(tag_data)
        
        result = tag_service.list_tags(page=1, page_size=10)
        
        assert result["total"] == 5
        assert len(result["items"]) == 5
    
    def test_get_tag_tree(self, tag_service):
        """测试获取标签树"""
        parent1 = tag_service.create_tag(TagCreate(name="动作"))
        parent2 = tag_service.create_tag(TagCreate(name="喜剧"))
        
        tag_service.create_tag(TagCreate(name="武侠", parent_id=parent1.id))
        tag_service.create_tag(TagCreate(name="爱情", parent_id=parent2.id))
        
        result = tag_service.get_tag_tree()
        
        assert result.total == 4
        assert len(result.items) == 2
    
    def test_same_name_different_parent(self, tag_service):
        """测试同名标签在不同父标签下共存"""
        parent1 = tag_service.create_tag(TagCreate(name="电影"))
        parent2 = tag_service.create_tag(TagCreate(name="电视剧"))
        
        child1 = tag_service.create_tag(TagCreate(name="动作", parent_id=parent1.id))
        child2 = tag_service.create_tag(TagCreate(name="动作", parent_id=parent2.id))
        
        assert child1.id != child2.id
        assert child1.name == child2.name
    
    def test_merge_tags(self, tag_service):
        """测试合并标签"""
        from video_tag_system.models.tag import TagMergeRequest
        source = tag_service.create_tag(TagCreate(name="动作片"))
        target = tag_service.create_tag(TagCreate(name="动作"))
        
        result = tag_service.merge_tags(TagMergeRequest(
            source_tag_id=source.id,
            target_tag_id=target.id
        ))
        
        assert result["deleted_source_tag"] is True
        
        with pytest.raises(TagNotFoundError):
            tag_service.get_tag(source.id)

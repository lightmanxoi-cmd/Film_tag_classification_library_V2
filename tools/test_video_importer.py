"""
测试视频导入工具
"""
import os
import sys
from .video_importer import VideoImporterCLI
from video_tag_system import DatabaseManager
from video_tag_system.services import TagService

def test_video_importer():
    """测试视频导入功能"""
    print("测试视频导入工具...")
    
    cli = VideoImporterCLI()
    
    with DatabaseManager().get_session() as session:
        tag_service = TagService(session)
        
        try:
            tag_service.get_tag_by_name("测试一级标签", parent_id=None)
        except:
            from video_tag_system.models.tag import TagCreate
            tag_service.create_tag(TagCreate(name="测试一级标签", description="用于测试"))
        
        try:
            tag_service.get_tag_by_name("测试二级标签", parent_id=None)
        except:
            from video_tag_system.models.tag import TagCreate
            parent = tag_service.get_tag_by_name("测试一级标签", parent_id=None)
            tag_service.create_tag(TagCreate(name="测试二级标签", parent_id=parent.id, description="用于测试"))
    
    test_file = r"C:\temp\test_video.mp4"
    
    if os.path.exists(test_file):
        print(f"测试导入文件: {test_file}")
        cli.import_video(test_file, "测试一级标签", "测试二级标签")
    else:
        print(f"测试文件不存在: {test_file}")
        print("跳过实际导入测试")
    
    print("测试完成!")

if __name__ == "__main__":
    test_video_importer()

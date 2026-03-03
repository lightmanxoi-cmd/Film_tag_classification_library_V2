"""
视频标签分类库管理系统 - 示例代码
演示系统的基本使用方法
"""
from video_tag_system import (
    DatabaseManager,
    VideoService,
    TagService,
    VideoTagService,
)
from video_tag_system.models.video import VideoCreate, VideoUpdate
from video_tag_system.models.tag import TagCreate, TagUpdate
from video_tag_system.models.video_tag import BatchTagOperation


def main():
    """主函数 - 演示系统使用"""
    
    print("=" * 60)
    print("视频标签分类库管理系统 - 使用示例")
    print("=" * 60)
    
    db_manager = DatabaseManager(
        database_url="sqlite:///./example_video_library.db",
        echo=False
    )
    db_manager.create_tables()
    print("\n[1] 数据库初始化完成")
    
    with db_manager.get_session() as session:
        video_service = VideoService(session)
        tag_service = TagService(session)
        video_tag_service = VideoTagService(session)
        
        print("\n[2] 创建标签体系")
        
        action_tag = tag_service.create_tag(TagCreate(
            name="动作",
            description="动作类型视频",
            sort_order=1
        ))
        print(f"   创建一级标签: {action_tag.name} (ID: {action_tag.id})")
        
        comedy_tag = tag_service.create_tag(TagCreate(
            name="喜剧",
            description="喜剧类型视频",
            sort_order=2
        ))
        print(f"   创建一级标签: {comedy_tag.name} (ID: {comedy_tag.id})")
        
        martial_arts = tag_service.create_tag(TagCreate(
            name="武侠",
            description="武侠动作片",
            parent_id=action_tag.id
        ))
        print(f"   创建二级标签: {martial_arts.name} (父标签: {action_tag.name})")
        
        gunfight = tag_service.create_tag(TagCreate(
            name="枪战",
            description="枪战动作片",
            parent_id=action_tag.id
        ))
        print(f"   创建二级标签: {gunfight.name} (父标签: {action_tag.name})")
        
        print("\n[3] 添加视频")
        
        video1 = video_service.create_video(VideoCreate(
            file_path="/movies/hero.mp4",
            title="英雄",
            description="张艺谋导演的武侠大片",
            duration=5400,
            file_size=1024 * 1024 * 1500
        ))
        print(f"   添加视频: {video1.title} (ID: {video1.id})")
        
        video2 = video_service.create_video(VideoCreate(
            file_path="/movies/matrix.mp4",
            title="黑客帝国",
            description="科幻动作经典",
            duration=7200,
            file_size=1024 * 1024 * 2000
        ))
        print(f"   添加视频: {video2.title} (ID: {video2.id})")
        
        video3 = video_service.create_video(VideoCreate(
            file_path="/movies/kungfu_panda.mp4",
            title="功夫熊猫",
            description="动画喜剧电影",
            duration=5700,
            file_size=1024 * 1024 * 1200
        ))
        print(f"   添加视频: {video3.title} (ID: {video3.id})")
        
        print("\n[4] 为视频添加标签")
        
        video_tag_service.add_tag_to_video(video1.id, action_tag.id)
        video_tag_service.add_tag_to_video(video1.id, martial_arts.id)
        print(f"   为《{video1.title}》添加标签: {action_tag.name}, {martial_arts.name}")
        
        video_tag_service.add_tag_to_video(video2.id, action_tag.id)
        video_tag_service.add_tag_to_video(video2.id, gunfight.id)
        print(f"   为《{video2.title}》添加标签: {action_tag.name}, {gunfight.name}")
        
        video_tag_service.add_tag_to_video(video3.id, action_tag.id)
        video_tag_service.add_tag_to_video(video3.id, comedy_tag.id)
        print(f"   为《{video3.title}》添加标签: {action_tag.name}, {comedy_tag.name}")
        
        print("\n[5] 查询视频详情")
        
        video_detail = video_service.get_video(video1.id)
        print(f"   视频: {video_detail.title}")
        print(f"   路径: {video_detail.file_path}")
        print(f"   标签: {[t.name for t in video_detail.tags]}")
        
        print("\n[6] 获取标签树")
        
        tag_tree = tag_service.get_tag_tree()
        print("   标签树结构:")
        for root_tag in tag_tree.items:
            print(f"   - {root_tag.name} (ID: {root_tag.id})")
            for child in root_tag.children:
                print(f"     - {child.name} (ID: {child.id})")
        
        print("\n[7] 根据标签筛选视频")
        
        action_videos = video_service.list_videos_by_tags(
            tag_ids=[action_tag.id],
            page=1,
            page_size=10
        )
        print(f"   动作类视频 ({action_videos.total}部):")
        for v in action_videos.items:
            print(f"   - {v.title}")
        
        print("\n[8] 批量操作示例")
        
        batch_result = video_tag_service.batch_add_tags(BatchTagOperation(
            video_ids=[video1.id, video2.id, video3.id],
            tag_ids=[comedy_tag.id]
        ))
        print(f"   批量添加标签结果: {batch_result['message']}")
        
        print("\n[9] 标签统计")
        
        action_stats = tag_service.get_tag_statistics(action_tag.id)
        print(f"   标签 '{action_stats['tag_name']}' 统计:")
        print(f"   - 关联视频数: {action_stats['video_count']}")
        print(f"   - 子标签数: {action_stats['children_count']}")
        
        print("\n[10] 数据库备份")
        
        backup_path = db_manager.backup()
        print(f"   备份已创建: {backup_path}")
        
        print("\n[11] 数据库完整性验证")
        
        integrity = db_manager.verify_integrity()
        print(f"   完整性验证: {'通过' if integrity['valid'] else '失败'}")
        if integrity['errors']:
            for error in integrity['errors']:
                print(f"   - 错误: {error}")
    
    db_manager.close()
    print("\n" + "=" * 60)
    print("示例运行完成!")
    print("=" * 60)


if __name__ == "__main__":
    main()

"""
视频标签分类库管理系统 - 快速入门示例
"""
from video_tag_system import DatabaseManager, VideoService, TagService, VideoTagService
from video_tag_system.models.video import VideoCreate
from video_tag_system.models.tag import TagCreate


def quick_start():
    """快速入门示例"""
    
    db = DatabaseManager(database_url="sqlite:///./my_videos.db")
    db.create_tables()
    
    with db.get_session() as session:
        video_svc = VideoService(session)
        tag_svc = TagService(session)
        video_tag_svc = VideoTagService(session)
        
        video = video_svc.create_video(VideoCreate(
            file_path="/movies/my_movie.mp4",
            title="我的电影",
            duration=7200
        ))
        
        tag = tag_svc.create_tag(TagCreate(name="科幻"))
        
        video_tag_svc.add_tag_to_video(video.id, tag.id)
        
        result = video_svc.get_video(video.id)
        print(f"视频: {result.title}")
        print(f"标签: {[t.name for t in result.tags]}")
    
    db.close()


if __name__ == "__main__":
    quick_start()

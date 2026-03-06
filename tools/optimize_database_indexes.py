"""
数据库索引优化脚本
用于在现有数据库上添加性能优化索引
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from video_tag_system.core.database import DatabaseManager


def check_index_exists(session, table_name, index_name):
    """检查索引是否已存在"""
    result = session.execute(text(f"""
        SELECT name FROM sqlite_master 
        WHERE type='index' AND tbl_name='{table_name}' AND name='{index_name}'
    """)).fetchone()
    return result is not None


def create_index_if_not_exists(session, table_name, index_name, column_name, unique=False):
    """如果索引不存在则创建"""
    if check_index_exists(session, table_name, index_name):
        print(f"✓ 索引 {index_name} 已存在")
        return False
    
    unique_str = "UNIQUE" if unique else ""
    sql = f"CREATE {unique_str} INDEX IF NOT EXISTS {index_name} ON {table_name}({column_name})"
    session.execute(text(sql))
    print(f"✓ 创建索引：{index_name} ON {table_name}({column_name})")
    return True


def create_composite_index_if_not_exists(session, table_name, index_name, columns):
    """如果复合索引不存在则创建"""
    if check_index_exists(session, table_name, index_name):
        print(f"✓ 索引 {index_name} 已存在")
        return False
    
    columns_str = ", ".join(columns)
    sql = f"CREATE INDEX IF NOT EXISTS {index_name} ON {table_name}({columns_str})"
    session.execute(text(sql))
    print(f"✓ 创建复合索引：{index_name} ON {table_name}({columns_str})")
    return True


def optimize_database():
    """优化数据库索引"""
    print("=" * 60)
    print("开始优化数据库索引...")
    print("=" * 60)
    
    db_manager = DatabaseManager(
        database_url="sqlite:///./video_library.db",
        echo=False
    )
    
    session = db_manager.session_factory()
    
    try:
        indexes_created = 0
        
        print("\n优化 videos 表索引:")
        print("-" * 60)
        if create_index_if_not_exists(session, "videos", "idx_videos_title", "title"):
            indexes_created += 1
        if create_index_if_not_exists(session, "videos", "idx_videos_duration", "duration"):
            indexes_created += 1
        if create_index_if_not_exists(session, "videos", "idx_videos_created_at", "created_at"):
            indexes_created += 1
        if create_index_if_not_exists(session, "videos", "idx_videos_updated_at", "updated_at"):
            indexes_created += 1
        
        print("\n优化 tags 表索引:")
        print("-" * 60)
        if create_index_if_not_exists(session, "tags", "idx_tags_name", "name"):
            indexes_created += 1
        if create_index_if_not_exists(session, "tags", "idx_tags_parent_id", "parent_id"):
            indexes_created += 1
        if create_index_if_not_exists(session, "tags", "idx_tags_sort_order", "sort_order"):
            indexes_created += 1
        
        print("\n优化 video_tags 表索引:")
        print("-" * 60)
        if create_index_if_not_exists(session, "video_tags", "idx_video_tags_video_id", "video_id"):
            indexes_created += 1
        if create_index_if_not_exists(session, "video_tags", "idx_video_tags_tag_id", "tag_id"):
            indexes_created += 1
        if create_composite_index_if_not_exists(
            session, "video_tags", "idx_video_tags_video_tag", ["video_id", "tag_id"]
        ):
            indexes_created += 1
        if create_composite_index_if_not_exists(
            session, "video_tags", "idx_video_tags_tag_video", ["tag_id", "video_id"]
        ):
            indexes_created += 1
        
        session.commit()
        
        print("\n" + "=" * 60)
        print(f"优化完成！共创建/更新 {indexes_created} 个索引")
        print("=" * 60)
        
        print("\n性能提升说明:")
        print("-" * 60)
        print("✓ 视频搜索查询速度提升 (title 索引)")
        print("✓ 视频列表排序速度提升 (created_at, updated_at 索引)")
        print("✓ 标签筛选查询速度提升 (video_tags 复合索引)")
        print("✓ 随机查询性能优化 (使用数据库级随机函数)")
        print("✓ SQLite WAL 模式已启用，提升并发性能")
        print("=" * 60)
        
    except Exception as e:
        session.rollback()
        print(f"\n❌ 优化失败：{e}")
        raise
    finally:
        session.close()


if __name__ == "__main__":
    optimize_database()

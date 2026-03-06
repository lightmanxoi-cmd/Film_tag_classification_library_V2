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
        print(f"  ✓ 索引 {index_name} 已存在")
        return False
    
    unique_str = "UNIQUE" if unique else ""
    sql = f"CREATE {unique_str} INDEX IF NOT EXISTS {index_name} ON {table_name}({column_name})"
    session.execute(text(sql))
    print(f"  + 创建索引：{index_name} ON {table_name}({column_name})")
    return True


def create_composite_index_if_not_exists(session, table_name, index_name, columns):
    """如果复合索引不存在则创建"""
    if check_index_exists(session, table_name, index_name):
        print(f"  ✓ 索引 {index_name} 已存在")
        return False
    
    columns_str = ", ".join(columns)
    sql = f"CREATE INDEX IF NOT EXISTS {index_name} ON {table_name}({columns_str})"
    session.execute(text(sql))
    print(f"  + 创建复合索引：{index_name} ON {table_name}({columns_str})")
    return True


def analyze_table_stats(session, table_name):
    """分析表统计信息"""
    result = session.execute(text(f"SELECT COUNT(*) FROM {table_name}")).scalar()
    return result


def optimize_database(database_url: str = "sqlite:///./video_library.db"):
    """优化数据库索引"""
    print("=" * 70)
    print("数据库性能优化工具")
    print("=" * 70)
    
    db_manager = DatabaseManager(database_url=database_url, echo=False)
    
    session = db_manager.session_factory()
    
    try:
        indexes_created = 0
        
        print("\n📊 数据库统计信息:")
        print("-" * 70)
        videos_count = analyze_table_stats(session, "videos")
        tags_count = analyze_table_stats(session, "tags")
        video_tags_count = analyze_table_stats(session, "video_tags")
        print(f"  videos 表: {videos_count} 条记录")
        print(f"  tags 表: {tags_count} 条记录")
        print(f"  video_tags 表: {video_tags_count} 条记录")
        
        print("\n🔧 优化 videos 表索引:")
        print("-" * 70)
        if create_index_if_not_exists(session, "videos", "idx_videos_title", "title"):
            indexes_created += 1
        if create_index_if_not_exists(session, "videos", "idx_videos_created_at", "created_at"):
            indexes_created += 1
        if create_index_if_not_exists(session, "videos", "idx_videos_updated_at", "updated_at"):
            indexes_created += 1
        if create_index_if_not_exists(session, "videos", "idx_videos_duration", "duration"):
            indexes_created += 1
        if create_index_if_not_exists(session, "videos", "idx_videos_file_size", "file_size"):
            indexes_created += 1
        
        print("\n🔧 优化 tags 表索引:")
        print("-" * 70)
        if create_index_if_not_exists(session, "tags", "idx_tags_name", "name"):
            indexes_created += 1
        if create_index_if_not_exists(session, "tags", "idx_tags_parent_id", "parent_id"):
            indexes_created += 1
        if create_index_if_not_exists(session, "tags", "idx_tags_sort_order", "sort_order"):
            indexes_created += 1
        if create_composite_index_if_not_exists(
            session, "tags", "idx_tags_name_parent", ["name", "parent_id"]
        ):
            indexes_created += 1
        
        print("\n🔧 优化 video_tags 表索引:")
        print("-" * 70)
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
        if create_index_if_not_exists(session, "video_tags", "idx_video_tags_created_at", "created_at"):
            indexes_created += 1
        
        print("\n🔧 执行数据库优化命令:")
        print("-" * 70)
        session.execute(text("PRAGMA optimize"))
        session.execute(text("ANALYZE"))
        print("  ✓ 已执行 PRAGMA optimize")
        print("  ✓ 已执行 ANALYZE 更新统计信息")
        
        session.commit()
        
        print("\n" + "=" * 70)
        print(f"✅ 优化完成！共创建/更新 {indexes_created} 个索引")
        print("=" * 70)
        
        print("\n📈 性能提升说明:")
        print("-" * 70)
        print("  ✓ WAL模式已启用 - 支持并发读写")
        print("  ✓ 连接池已优化 - 支持高并发连接")
        print("  ✓ 视频搜索查询速度提升 (title 索引)")
        print("  ✓ 视频列表排序速度提升 (created_at, updated_at 索引)")
        print("  ✓ 标签筛选查询速度提升 (video_tags 复合索引)")
        print("  ✓ 标签树查询速度提升 (parent_id, sort_order 索引)")
        print("=" * 70)
        
    except Exception as e:
        session.rollback()
        print(f"\n❌ 优化失败：{e}")
        raise
    finally:
        session.close()
        db_manager.close()


def show_index_info(database_url: str = "sqlite:///./video_library.db"):
    """显示数据库索引信息"""
    print("=" * 70)
    print("数据库索引信息")
    print("=" * 70)
    
    db_manager = DatabaseManager(database_url=database_url, echo=False)
    session = db_manager.session_factory()
    
    try:
        for table in ["videos", "tags", "video_tags"]:
            print(f"\n📋 {table} 表索引:")
            print("-" * 70)
            result = session.execute(text(f"""
                SELECT name, sql FROM sqlite_master 
                WHERE type='index' AND tbl_name='{table}'
                ORDER BY name
            """)).fetchall()
            
            for row in result:
                print(f"  • {row[0]}")
                if row[1]:
                    print(f"    {row[1]}")
    finally:
        session.close()
        db_manager.close()


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="数据库性能优化工具")
    parser.add_argument("--info", action="store_true", help="显示索引信息")
    parser.add_argument("--db", default="sqlite:///./video_library.db", help="数据库URL")
    args = parser.parse_args()
    
    if args.info:
        show_index_info(args.db)
    else:
        optimize_database(args.db)

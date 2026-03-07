"""
数据库索引优化脚本

本模块用于优化数据库性能，主要通过创建索引来加速查询操作。
优化内容包括：
- 创建单列索引：为常用查询字段创建索引
- 创建复合索引：为多字段联合查询创建索引
- 执行数据库优化命令：PRAGMA optimize 和 ANALYZE

索引优化说明：
- videos表：title, created_at, updated_at, duration, file_size
- tags表：name, parent_id, sort_order, 复合索引(name, parent_id)
- video_tags表：video_id, tag_id, 复合索引(video_id, tag_id)

使用方式：
    python tools/optimize_database_indexes.py
    python tools/optimize_database_indexes.py --info
    python tools/optimize_database_indexes.py --db "sqlite:///./video_library.db"

性能提升效果：
- 视频搜索查询速度提升（title索引）
- 视频列表排序速度提升（created_at, updated_at索引）
- 标签筛选查询速度提升（video_tags复合索引）
- 标签树查询速度提升（parent_id, sort_order索引）

作者：Video Library System
创建时间：2024
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from video_tag_system.core.database import DatabaseManager


def check_index_exists(session, table_name, index_name):
    """
    检查索引是否已存在
    
    查询sqlite_master表判断指定索引是否已创建。
    
    Args:
        session: 数据库会话
        table_name: 表名
        index_name: 索引名
        
    Returns:
        bool: 索引存在返回True，否则返回False
    """
    result = session.execute(text(f"""
        SELECT name FROM sqlite_master 
        WHERE type='index' AND tbl_name='{table_name}' AND name='{index_name}'
    """)).fetchone()
    return result is not None


def create_index_if_not_exists(session, table_name, index_name, column_name, unique=False):
    """
    如果索引不存在则创建
    
    创建单列索引，如果索引已存在则跳过。
    
    Args:
        session: 数据库会话
        table_name: 表名
        index_name: 索引名
        column_name: 列名
        unique: 是否创建唯一索引，默认为False
        
    Returns:
        bool: 创建成功返回True，索引已存在返回False
    """
    if check_index_exists(session, table_name, index_name):
        print(f"  ✓ 索引 {index_name} 已存在")
        return False
    
    unique_str = "UNIQUE" if unique else ""
    sql = f"CREATE {unique_str} INDEX IF NOT EXISTS {index_name} ON {table_name}({column_name})"
    session.execute(text(sql))
    print(f"  + 创建索引：{index_name} ON {table_name}({column_name})")
    return True


def create_composite_index_if_not_exists(session, table_name, index_name, columns):
    """
    如果复合索引不存在则创建
    
    创建多列复合索引，用于优化多字段联合查询。
    
    Args:
        session: 数据库会话
        table_name: 表名
        index_name: 索引名
        columns: 列名列表
        
    Returns:
        bool: 创建成功返回True，索引已存在返回False
    """
    if check_index_exists(session, table_name, index_name):
        print(f"  ✓ 索引 {index_name} 已存在")
        return False
    
    columns_str = ", ".join(columns)
    sql = f"CREATE INDEX IF NOT EXISTS {index_name} ON {table_name}({columns_str})"
    session.execute(text(sql))
    print(f"  + 创建复合索引：{index_name} ON {table_name}({columns_str})")
    return True


def analyze_table_stats(session, table_name):
    """
    分析表统计信息
    
    获取表中的记录总数。
    
    Args:
        session: 数据库会话
        table_name: 表名
        
    Returns:
        int: 表中的记录数
    """
    result = session.execute(text(f"SELECT COUNT(*) FROM {table_name}")).scalar()
    return result


def optimize_database(database_url: str = "sqlite:///./video_library.db"):
    """
    优化数据库索引
    
    主优化函数，执行以下操作：
    1. 显示数据库统计信息
    2. 为videos表创建索引
    3. 为tags表创建索引
    4. 为video_tags表创建索引
    5. 执行数据库优化命令
    
    Args:
        database_url: 数据库连接字符串，默认为当前目录下的video_library.db
    """
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
    """
    显示数据库索引信息
    
    列出数据库中所有表的索引信息，包括索引名称和创建语句。
    
    Args:
        database_url: 数据库连接字符串，默认为当前目录下的video_library.db
    """
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

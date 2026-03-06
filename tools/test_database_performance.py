"""
数据库性能测试脚本
用于测试和对比优化前后的性能
"""
import sys
import os
import time
import random

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text, func
from video_tag_system.core.database import DatabaseManager
from video_tag_system.repositories.video_repository import VideoRepository
from video_tag_system.models.video import VideoCreate


def setup_test_data(session, count=1000):
    """准备测试数据"""
    print(f"准备 {count} 条测试数据...")
    
    repo = VideoRepository(session)
    
    existing_count = session.execute(text("SELECT COUNT(*) FROM videos")).scalar()
    
    if existing_count >= count:
        print(f"数据库中已有 {existing_count} 条数据，跳过数据准备")
        return
    
    need_to_create = count - existing_count
    
    for i in range(need_to_create):
        try:
            video_data = VideoCreate(
                file_path=f"F:\\TestVideos\\video_{existing_count + i + 1}.mp4",
                title=f"测试视频 {existing_count + i + 1}",
                description=f"这是测试视频的描述信息 {existing_count + i + 1}",
                duration=random.randint(60, 7200),
                file_size=random.randint(1000000, 1000000000)
            )
            repo.create(video_data)
        except Exception:
            session.rollback()
    
    session.commit()
    print(f"✓ 已创建 {need_to_create} 条测试数据")


def test_random_query_performance(session, iterations=10):
    """测试随机查询性能"""
    print("\n测试随机查询性能...")
    print("-" * 60)
    
    repo = VideoRepository(session)
    
    start_time = time.time()
    
    for i in range(iterations):
        seed = random.randint(1, 10000)
        videos, total = repo.list_all(
            page=1,
            page_size=50,
            random_order=True,
            random_seed=seed
        )
    
    end_time = time.time()
    avg_time = (end_time - start_time) / iterations * 1000
    
    print(f"✓ 随机查询 {iterations} 次，平均耗时：{avg_time:.2f}ms")
    print(f"  总记录数：{total}")
    return avg_time


def test_search_query_performance(session, iterations=10):
    """测试搜索查询性能"""
    print("\n测试搜索查询性能...")
    print("-" * 60)
    
    repo = VideoRepository(session)
    
    start_time = time.time()
    
    for i in range(iterations):
        videos, total = repo.list_all(
            page=1,
            page_size=50,
            search="测试"
        )
    
    end_time = time.time()
    avg_time = (end_time - start_time) / iterations * 1000
    
    print(f"✓ 搜索查询 {iterations} 次，平均耗时：{avg_time:.2f}ms")
    print(f"  匹配记录数：{total}")
    return avg_time


def test_pagination_performance(session, iterations=5):
    """测试分页查询性能"""
    print("\n测试分页查询性能...")
    print("-" * 60)
    
    repo = VideoRepository(session)
    
    start_time = time.time()
    
    for i in range(iterations):
        for page in range(1, 11):
            videos, total = repo.list_all(
                page=page,
                page_size=50
            )
    
    end_time = time.time()
    avg_time = (end_time - start_time) / (iterations * 10) * 1000
    
    print(f"✓ 分页查询 {iterations * 10} 次，平均耗时：{avg_time:.2f}ms")
    return avg_time


def test_database_integrity(session):
    """测试数据库完整性"""
    print("\n测试数据库完整性...")
    print("-" * 60)
    
    result = session.execute(text("PRAGMA integrity_check")).scalar()
    print(f"✓ 完整性检查：{result}")
    
    journal_mode = session.execute(text("PRAGMA journal_mode")).scalar()
    print(f"✓ 日志模式：{journal_mode}")
    
    cache_size = session.execute(text("PRAGMA cache_size")).scalar()
    print(f"✓ 缓存大小：{cache_size} KB")
    
    synchronous = session.execute(text("PRAGMA synchronous")).scalar()
    sync_map = {0: "OFF", 1: "NORMAL", 2: "FULL"}
    print(f"✓ 同步模式：{sync_map.get(synchronous, synchronous)}")
    
    foreign_keys = session.execute(text("PRAGMA foreign_keys")).scalar()
    print(f"✓ 外键约束：{'已启用' if foreign_keys else '未启用'}")


def run_performance_tests():
    """运行性能测试"""
    print("=" * 60)
    print("数据库性能测试")
    print("=" * 60)
    
    db_manager = DatabaseManager(
        database_url="sqlite:///./video_library.db",
        echo=False
    )
    
    session = db_manager.session_factory()
    
    try:
        test_database_integrity(session)
        
        setup_test_data(session, count=1000)
        
        print("\n" + "=" * 60)
        print("性能测试结果")
        print("=" * 60)
        
        random_time = test_random_query_performance(session)
        search_time = test_search_query_performance(session)
        pagination_time = test_pagination_performance(session)
        
        print("\n" + "=" * 60)
        print("性能总结")
        print("=" * 60)
        print(f"随机查询平均耗时：{random_time:.2f}ms")
        print(f"搜索查询平均耗时：{search_time:.2f}ms")
        print(f"分页查询平均耗时：{pagination_time:.2f}ms")
        print("=" * 60)
        
        if random_time < 50:
            print("✓ 随机查询性能优秀")
        elif random_time < 100:
            print("✓ 随机查询性能良好")
        else:
            print("⚠ 随机查询性能有待优化")
        
        if search_time < 30:
            print("✓ 搜索查询性能优秀")
        elif search_time < 80:
            print("✓ 搜索查询性能良好")
        else:
            print("⚠ 搜索查询性能有待优化")
        
    except Exception as e:
        session.rollback()
        print(f"\n❌ 测试失败：{e}")
        import traceback
        traceback.print_exc()
    finally:
        session.close()


if __name__ == "__main__":
    run_performance_tests()

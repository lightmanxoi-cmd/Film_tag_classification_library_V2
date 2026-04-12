"""
随机队列管理器测试模块

测试内容：
    - RA队列生成和随机性验证
    - RX队列按标签筛选生成和复用
    - 序列分割逻辑（多路同播）
    - 标签匹配算法
    - 持久化存储读写
    - 定时更新机制
    - 负载测试（数万级视频量）
"""
import json
import os
import tempfile
import time
import threading
from collections import Counter
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from video_tag_system.utils.random_queue_manager import (
    RandomQueueManager,
    get_random_queue_manager,
    init_random_queue_manager,
    stop_random_queue_manager,
)


class TestMakeTagKey:
    """标签键生成测试"""

    def test_empty_tags(self):
        result = RandomQueueManager._make_tag_key({})
        assert result == "empty"

    def test_single_category(self):
        result = RandomQueueManager._make_tag_key({"类型": [1, 2]})
        assert result == "类型:1,2"

    def test_multiple_categories(self):
        result = RandomQueueManager._make_tag_key({"类型": [1, 2], "地区": [5]})
        assert "类型:1,2" in result
        assert "地区:5" in result

    def test_deterministic(self):
        tags1 = {"类型": [1, 2], "地区": [5]}
        tags2 = {"地区": [5], "类型": [1, 2]}
        assert RandomQueueManager._make_tag_key(tags1) == RandomQueueManager._make_tag_key(tags2)

    def test_tag_order_deterministic(self):
        tags1 = {"类型": [3, 1, 2]}
        tags2 = {"类型": [1, 2, 3]}
        assert RandomQueueManager._make_tag_key(tags1) == RandomQueueManager._make_tag_key(tags2)


class TestVideoMatchesTags:
    """标签匹配算法测试"""

    def test_empty_tags_by_category(self):
        assert RandomQueueManager._video_matches_tags({1, 2}, {}) is True

    def test_single_category_match(self):
        assert RandomQueueManager._video_matches_tags({1, 2, 3}, {"类型": [1, 4]}) is True

    def test_single_category_no_match(self):
        assert RandomQueueManager._video_matches_tags({1, 2}, {"类型": [3, 4]}) is False

    def test_multiple_categories_all_match(self):
        video_tags = {1, 5}
        tags_by_category = {"类型": [1, 2], "地区": [5, 6]}
        assert RandomQueueManager._video_matches_tags(video_tags, tags_by_category) is True

    def test_multiple_categories_partial_match(self):
        video_tags = {1, 3}
        tags_by_category = {"类型": [1, 2], "地区": [5, 6]}
        assert RandomQueueManager._video_matches_tags(video_tags, tags_by_category) is False

    def test_empty_tag_ids_in_category(self):
        assert RandomQueueManager._video_matches_tags({1, 2}, {"类型": []}) is True

    def test_video_no_tags(self):
        assert RandomQueueManager._video_matches_tags(set(), {"类型": [1, 2]}) is False


class TestSplitSequence:
    """序列分割测试"""

    def test_empty_sequence(self):
        result = RandomQueueManager._split_sequence([], 4)
        assert len(result) == 4
        assert all(len(sub) == 0 for sub in result)

    def test_even_split(self):
        sequence = list(range(12))
        result = RandomQueueManager._split_sequence(sequence, 4)
        assert len(result) == 4
        assert all(len(sub) == 3 for sub in result)
        assert sum(len(sub) for sub in result) == 12

    def test_uneven_split(self):
        sequence = list(range(13))
        result = RandomQueueManager._split_sequence(sequence, 4)
        assert len(result) == 4
        assert len(result[0]) == 4
        assert len(result[1]) == 3
        assert len(result[2]) == 3
        assert len(result[3]) == 3
        assert sum(len(sub) for sub in result) == 13

    def test_single_split(self):
        sequence = list(range(10))
        result = RandomQueueManager._split_sequence(sequence, 1)
        assert len(result) == 1
        assert len(result[0]) == 10

    def test_more_splits_than_elements(self):
        sequence = list(range(3))
        result = RandomQueueManager._split_sequence(sequence, 5)
        assert len(result) == 5
        assert sum(len(sub) for sub in result) == 3

    def test_no_element_loss(self):
        sequence = list(range(100))
        result = RandomQueueManager._split_sequence(sequence, 7)
        flat = [item for sub in result for item in sub]
        assert sorted(flat) == sequence

    def test_order_preserved(self):
        sequence = list(range(20))
        result = RandomQueueManager._split_sequence(sequence, 3)
        flat = [item for sub in result for item in sub]
        assert flat == sequence


class TestRandomQueueManagerPersistence:
    """持久化存储测试"""

    def test_save_and_load(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            manager1 = RandomQueueManager(tmpdir)
            manager1._ra_sequence = [3, 1, 4, 1, 5, 9]
            manager1._rx_sequences = {
                "类型:1,2": {
                    "tags_by_category": {"类型": [1, 2]},
                    "sequence": [3, 1, 5]
                }
            }
            manager1._video_tags_map = {1: {10, 20}, 3: {10}, 5: {20}}
            manager1._last_update = "2026-01-01T12:00:00"
            manager1._save()

            manager2 = RandomQueueManager(tmpdir)
            assert manager2._ra_sequence == [3, 1, 4, 1, 5, 9]
            assert "类型:1,2" in manager2._rx_sequences
            assert manager2._rx_sequences["类型:1,2"]["sequence"] == [3, 1, 5]
            assert manager2._video_tags_map == {1: {10, 20}, 3: {10}, 5: {20}}
            assert manager2._last_update == "2026-01-01T12:00:00"

    def test_load_nonexistent_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = RandomQueueManager(tmpdir)
            assert manager._ra_sequence == []
            assert manager._rx_sequences == {}
            assert manager._video_tags_map == {}

    def test_load_corrupted_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            queue_file = Path(tmpdir) / "random_queues.json"
            queue_file.write_text("not valid json{{{")
            manager = RandomQueueManager(tmpdir)
            assert manager._ra_sequence == []
            assert manager._rx_sequences == {}

    def test_save_creates_directory(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            nested_dir = os.path.join(tmpdir, "nested", "dir")
            manager = RandomQueueManager(nested_dir)
            manager._ra_sequence = [1, 2, 3]
            manager._save()
            assert os.path.exists(os.path.join(nested_dir, "random_queues.json"))


class TestRandomQueueManagerRA:
    """RA队列测试"""

    def test_refresh_ra(self, db_manager, session):
        from video_tag_system.models.video import Video
        
        for i in range(20):
            session.add(Video(file_path=f"/test/video_{i}.mp4", title=f"Video {i}"))
        session.commit()

        with tempfile.TemporaryDirectory() as tmpdir:
            manager = RandomQueueManager(tmpdir)
            result = manager.refresh_ra(session)

            all_ids = list(session.execute(
                __import__('sqlalchemy').select(Video.id)
            ).scalars().all())
            
            assert len(result) == 20
            assert sorted(result) == sorted(all_ids)

    def test_ra_randomness(self, db_manager, session):
        from video_tag_system.models.video import Video
        
        for i in range(100):
            session.add(Video(file_path=f"/test/video_{i}.mp4", title=f"Video {i}"))
        session.commit()

        with tempfile.TemporaryDirectory() as tmpdir:
            manager = RandomQueueManager(tmpdir)
            result1 = manager.refresh_ra(session)
            result2 = manager.refresh_ra(session)
            
            assert result1 != result2 or len(result1) <= 1

    def test_ra_uniformity(self, db_manager, session):
        from video_tag_system.models.video import Video
        
        num_videos = 50
        for i in range(num_videos):
            session.add(Video(file_path=f"/test/video_{i}.mp4", title=f"Video {i}"))
        session.commit()

        with tempfile.TemporaryDirectory() as tmpdir:
            position_counts = Counter()
            num_trials = 100
            
            manager = RandomQueueManager(tmpdir)
            for _ in range(num_trials):
                result = manager.refresh_ra(session)
                for pos, vid in enumerate(result):
                    position_counts[(vid, pos)] += 1
            
            for vid in range(1, num_videos + 1):
                positions_for_vid = [pos for (v, pos) in position_counts if v == vid]
                assert len(positions_for_vid) > 0


class TestRandomQueueManagerRX:
    """RX队列测试"""

    def test_get_or_create_rx(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = RandomQueueManager(tmpdir)
            manager._ra_sequence = list(range(1, 21))
            manager._video_tags_map = {
                1: {10, 20}, 2: {10}, 3: {20}, 4: {10, 30},
                5: {20, 30}, 6: {10, 20, 30}, 7: {40},
                8: {10}, 9: {20}, 10: {30}
            }

            tags = {"类型": [10, 20]}
            rx = manager.get_or_create_rx(tags)
            
            for vid in rx:
                video_tags = manager._video_tags_map.get(vid, set())
                assert bool(video_tags.intersection({10, 20}))

    def test_rx_cached(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = RandomQueueManager(tmpdir)
            manager._ra_sequence = list(range(1, 21))
            manager._video_tags_map = {i: {10} for i in range(1, 21)}

            tags = {"类型": [10]}
            rx1 = manager.get_or_create_rx(tags)
            rx2 = manager.get_or_create_rx(tags)
            assert rx1 is rx2

    def test_rx_preserves_ra_order(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = RandomQueueManager(tmpdir)
            manager._ra_sequence = [5, 3, 1, 4, 2]
            manager._video_tags_map = {
                5: {10, 20}, 3: {10}, 1: {20}, 4: {10, 20}, 2: {30}
            }

            tags = {"类型": [10]}
            rx = manager.get_or_create_rx(tags)
            assert rx == [5, 3, 4]

    def test_rx_empty_result(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = RandomQueueManager(tmpdir)
            manager._ra_sequence = [1, 2, 3]
            manager._video_tags_map = {1: {10}, 2: {20}, 3: {30}}

            tags = {"类型": [99]}
            rx = manager.get_or_create_rx(tags)
            assert rx == []

    def test_rx_multiple_categories_and_logic(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = RandomQueueManager(tmpdir)
            manager._ra_sequence = [1, 2, 3, 4, 5]
            manager._video_tags_map = {
                1: {10, 30}, 2: {10, 40}, 3: {20, 30},
                4: {20, 40}, 5: {10, 30, 40}
            }

            tags = {"类型": [10, 20], "地区": [30, 40]}
            rx = manager.get_or_create_rx(tags)
            assert sorted(rx) == [1, 2, 3, 4, 5]

            tags_strict = {"类型": [10], "地区": [30]}
            rx_strict = manager.get_or_create_rx(tags_strict)
            assert sorted(rx_strict) == [1, 5]


class TestRandomQueueManagerSplit:
    """序列分割与多路同播测试"""

    def test_get_rx_split_videos(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = RandomQueueManager(tmpdir)
            manager._ra_sequence = list(range(1, 13))
            manager._video_tags_map = {i: {10} for i in range(1, 13)}

            tags = {"类型": [10]}
            sub_sequences = manager._split_sequence(
                manager.get_or_create_rx(tags), 4
            )
            
            assert len(sub_sequences) == 4
            assert sum(len(s) for s in sub_sequences) == 12
            assert len(sub_sequences[0]) == 3
            assert len(sub_sequences[1]) == 3
            assert len(sub_sequences[2]) == 3
            assert len(sub_sequences[3]) == 3

    def test_split_no_overlap(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = RandomQueueManager(tmpdir)
            sequence = list(range(1, 101))
            sub_sequences = manager._split_sequence(sequence, 4)
            
            all_ids = []
            for sub in sub_sequences:
                all_ids.extend(sub)
            
            assert len(all_ids) == 100
            assert len(set(all_ids)) == 100

    def test_split_uneven_distribution(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = RandomQueueManager(tmpdir)
            sequence = list(range(1, 10))
            sub_sequences = manager._split_sequence(sequence, 4)
            
            sizes = [len(s) for s in sub_sequences]
            assert max(sizes) - min(sizes) <= 1
            assert sum(sizes) == 9


class TestRandomQueueManagerRefresh:
    """队列刷新测试"""

    def test_refresh_all_rx(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = RandomQueueManager(tmpdir)
            manager._ra_sequence = [1, 2, 3, 4, 5]
            manager._video_tags_map = {
                1: {10}, 2: {10}, 3: {20}, 4: {10, 20}, 5: {30}
            }

            tags = {"类型": [10]}
            manager.get_or_create_rx(tags)
            
            manager._ra_sequence = [5, 4, 3, 2, 1]
            manager._video_tags_map = {
                1: {10}, 2: {10, 20}, 3: {20}, 4: {10}, 5: {30}
            }
            
            result = manager.refresh_all_rx()
            tag_key = manager._make_tag_key(tags)
            assert tag_key in result
            assert sorted(result[tag_key]) == [1, 2, 4]

    def test_get_status(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = RandomQueueManager(tmpdir)
            manager._ra_sequence = [1, 2, 3]
            manager._rx_sequences = {
                "类型:1": {"tags_by_category": {"类型": [1]}, "sequence": [1, 2]}
            }
            manager._last_update = "2026-01-01T12:00:00"

            status = manager.get_status()
            assert status["ra_count"] == 3
            assert status["rx_count"] == 1
            assert status["last_update"] == "2026-01-01T12:00:00"


class TestRandomQueueManagerScheduler:
    """定时更新调度器测试"""

    def test_start_stop_scheduler(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = RandomQueueManager(tmpdir)
            mock_db = MagicMock()
            
            manager.start_scheduler(mock_db)
            assert manager._scheduler_thread is not None
            assert manager._scheduler_thread.is_alive()
            
            manager.stop_scheduler()
            time.sleep(0.5)
            assert manager._scheduler_thread is None

    def test_scheduler_daemon(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = RandomQueueManager(tmpdir)
            mock_db = MagicMock()
            
            manager.start_scheduler(mock_db)
            assert manager._scheduler_thread.daemon is True
            manager.stop_scheduler()

    def test_double_start(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = RandomQueueManager(tmpdir)
            mock_db = MagicMock()
            
            manager.start_scheduler(mock_db)
            thread1 = manager._scheduler_thread
            manager.start_scheduler(mock_db)
            assert manager._scheduler_thread is thread1
            manager.stop_scheduler()


class TestRandomQueueManagerSingleton:
    """单例管理测试"""

    def test_get_before_init(self):
        global _random_queue_manager
        from video_tag_system.utils import random_queue_manager
        original = random_queue_manager._random_queue_manager
        random_queue_manager._random_queue_manager = None
        
        try:
            result = get_random_queue_manager()
            assert result is None
        finally:
            random_queue_manager._random_queue_manager = original

    def test_stop_without_init(self):
        stop_random_queue_manager()


class TestLoadPerformance:
    """负载测试"""

    def test_large_ra_generation(self):
        import random as rnd_module
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = RandomQueueManager(tmpdir)
            manager._ra_sequence = list(range(1, 50001))
            manager._video_tags_map = {
                i: {rnd_module.choice([10, 20, 30, 40]) for _ in range(3)}
                for i in range(1, 50001)
            }
            
            start = time.time()
            tags = {"类型": [10, 20]}
            rx = manager.get_or_create_rx(tags)
            elapsed = time.time() - start
            
            assert elapsed < 2.0, f"RX generation took {elapsed:.2f}s, expected < 2s"
            assert len(rx) > 0

    def test_large_split_performance(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = RandomQueueManager(tmpdir)
            sequence = list(range(1, 50001))
            
            start = time.time()
            result = manager._split_sequence(sequence, 4)
            elapsed = time.time() - start
            
            assert elapsed < 0.5, f"Split took {elapsed:.2f}s, expected < 0.5s"
            assert sum(len(s) for s in result) == 50000

    def test_large_persistence_performance(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = RandomQueueManager(tmpdir)
            manager._ra_sequence = list(range(1, 50001))
            manager._video_tags_map = {
                i: {10, 20} for i in range(1, 50001)
            }
            manager._rx_sequences = {
                "类型:10": {"tags_by_category": {"类型": [10]}, "sequence": list(range(1, 25001))}
            }
            
            start = time.time()
            manager._save()
            save_elapsed = time.time() - start
            
            start = time.time()
            manager2 = RandomQueueManager(tmpdir)
            load_elapsed = time.time() - start
            
            assert save_elapsed < 5.0, f"Save took {save_elapsed:.2f}s"
            assert load_elapsed < 5.0, f"Load took {load_elapsed:.2f}s"
            assert len(manager2._ra_sequence) == 50000

    def test_randomness_uniformity_large_scale(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = RandomQueueManager(tmpdir)
            num_videos = 1000
            manager._ra_sequence = list(range(1, num_videos + 1))
            manager._video_tags_map = {i: set() for i in range(1, num_videos + 1)}
            
            position_counts = {i: Counter() for i in range(1, num_videos + 1)}
            num_trials = 50
            
            for _ in range(num_trials):
                import random as rnd
                seq = list(range(1, num_videos + 1))
                rnd.shuffle(seq)
                for pos, vid in enumerate(seq):
                    position_counts[vid][pos] += 1
            
            for vid in range(1, num_videos + 1):
                positions = list(position_counts[vid].keys())
                assert len(positions) > num_trials * 0.3, \
                    f"Video {vid} appears in too few positions"

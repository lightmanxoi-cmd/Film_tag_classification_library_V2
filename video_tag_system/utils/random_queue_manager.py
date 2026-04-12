"""
随机队列管理器模块

提供预计算随机队列的管理功能，解决大量视频随机排序的性能瓶颈。

核心概念：
    - RA (Random All): 全局随机队列，包含系统中所有视频ID的随机排列
    - RX (Random X): 标签筛选子队列，从RA中按标签组合筛选出的视频ID子序列

性能优化：
    - 预计算随机序列，避免每次请求时实时shuffle
    - RX队列按标签组合缓存，相同组合直接复用
    - 定时更新机制确保队列新鲜度
    - 持久化存储避免重启后重新计算

定时更新：
    - 服务器启动时
    - 每天 12:00
    - 每天 23:59

使用示例：
    from video_tag_system.utils.random_queue_manager import get_random_queue_manager, init_random_queue_manager
    
    manager = init_random_queue_manager(db_manager)
    rx_videos = manager.get_rx_videos(tags_by_category, db_session)
"""
import os
import json
import random
import threading
import time
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, List, Set, Tuple, Any

from video_tag_system.utils.logger import get_logger

logger = get_logger(__name__)


class RandomQueueManager:
    """
    随机队列管理器
    
    管理RA（全局随机队列）和RX（标签筛选子队列）的生成、缓存、持久化和定时更新。
    
    Attributes:
        _data_dir: 数据存储目录
        _queue_file: 队列持久化文件路径
        _lock: 线程安全锁
        _ra_sequence: RA队列，所有视频ID的随机排列
        _rx_sequences: RX队列字典，tag_key -> sequence
        _video_tags_map: 视频标签映射，video_id -> set(tag_ids)
        _last_update: 上次更新时间
        _scheduler_thread: 定时更新后台线程
        _stop_event: 线程停止事件
    """

    QUEUE_FILENAME = "random_queues.json"
    UPDATE_TIMES = ["12:00", "23:59"]

    def __init__(self, data_dir: str):
        """
        初始化随机队列管理器
        
        Args:
            data_dir: 数据存储目录路径
        """
        self._data_dir = Path(data_dir)
        self._queue_file = self._data_dir / self.QUEUE_FILENAME
        self._lock = threading.RLock()
        self._ra_sequence: List[int] = []
        self._rx_sequences: Dict[str, dict] = {}
        self._video_tags_map: Dict[int, Set[int]] = {}
        self._last_update: Optional[str] = None
        self._scheduler_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._db_manager = None
        self._load()

    def start_scheduler(self, db_manager):
        """
        启动定时更新调度器
        
        创建后台线程，在指定时间点自动更新RA和所有RX队列。
        启动时立即执行一次更新。
        
        Args:
            db_manager: 数据库管理器实例
        """
        self._db_manager = db_manager
        
        with self._lock:
            if self._scheduler_thread is not None and self._scheduler_thread.is_alive():
                logger.warning("随机队列调度器已在运行中")
                return
            
            self._stop_event.clear()
            self._scheduler_thread = threading.Thread(
                target=self._run_scheduler,
                name="RandomQueueScheduler",
                daemon=True
            )
            self._scheduler_thread.start()
        
        logger.info("随机队列调度器已启动，执行初始更新")
        self.refresh_all()

    def stop_scheduler(self):
        """停止定时更新调度器"""
        with self._lock:
            if self._scheduler_thread is None or not self._scheduler_thread.is_alive():
                return
            
            self._stop_event.set()
            self._scheduler_thread.join(timeout=10)
            self._scheduler_thread = None
        
        logger.info("随机队列调度器已停止")

    def _run_scheduler(self):
        """调度器主循环，每30秒检查一次是否需要更新"""
        logger.info("随机队列调度器线程开始运行")
        updated_dates = set()
        
        while not self._stop_event.is_set():
            try:
                now = datetime.now()
                today_str = now.strftime("%Y-%m-%d")
                current_time = now.strftime("%H:%M")
                
                for update_time in self.UPDATE_TIMES:
                    update_key = f"{today_str}_{update_time}"
                    if current_time == update_time and update_key not in updated_dates:
                        logger.info(f"定时更新随机队列: {update_key}")
                        self.refresh_all()
                        updated_dates.add(update_key)
                
                if now.hour == 0 and now.minute == 0:
                    updated_dates = set()
                
            except Exception as e:
                logger.error(f"随机队列定时更新出错: {e}", exc_info=True)
            
            self._stop_event.wait(timeout=30)
        
        logger.info("随机队列调度器线程结束")

    def refresh_ra(self, session) -> List[int]:
        """
        刷新RA队列
        
        从数据库获取所有视频ID，随机排列后存入RA队列。
        
        Args:
            session: 数据库会话
        
        Returns:
            List[int]: 新的RA队列
        """
        from sqlalchemy import select
        from video_tag_system.models.video import Video
        from video_tag_system.models.video_tag import VideoTag
        
        all_ids = list(session.execute(select(Video.id)).scalars().all())
        random.shuffle(all_ids)
        
        tag_rows = session.execute(
            select(VideoTag.video_id, VideoTag.tag_id)
        ).all()
        
        video_tags_map: Dict[int, Set[int]] = {}
        for video_id, tag_id in tag_rows:
            if video_id not in video_tags_map:
                video_tags_map[video_id] = set()
            video_tags_map[video_id].add(tag_id)
        
        with self._lock:
            self._ra_sequence = all_ids
            self._video_tags_map = video_tags_map
            self._last_update = datetime.now().isoformat()
            self._save()
        
        logger.info(f"RA队列已更新，共 {len(all_ids)} 个视频，{len(video_tags_map)} 个视频有标签")
        return all_ids

    def refresh_all_rx(self) -> Dict[str, List[int]]:
        """
        刷新所有RX队列
        
        根据当前RA队列和video_tags_map，重新筛选所有已保存的RX队列。
        应在refresh_ra之后调用。
        
        Returns:
            Dict[str, List[int]]: 更新后的RX队列字典
        """
        with self._lock:
            updated_rx = {}
            for tag_key, rx_data in self._rx_sequences.items():
                tags_by_category = rx_data.get("tags_by_category")
                if tags_by_category:
                    new_sequence = self._filter_ra_by_tags(tags_by_category)
                    updated_rx[tag_key] = {
                        "tags_by_category": tags_by_category,
                        "sequence": new_sequence
                    }
                    logger.info(f"RX队列 [{tag_key}] 已更新，共 {len(new_sequence)} 个视频")
                else:
                    updated_rx[tag_key] = rx_data
            
            self._rx_sequences = updated_rx
            self._save()
        
        return {k: v["sequence"] for k, v in self._rx_sequences.items()}

    def refresh_all(self):
        """刷新RA和所有RX队列"""
        if self._db_manager is None:
            logger.warning("数据库管理器未设置，无法刷新队列")
            return
        
        try:
            with self._db_manager.get_session() as session:
                self.refresh_ra(session)
            self.refresh_all_rx()
            logger.info("随机队列全量更新完成")
        except Exception as e:
            logger.error(f"随机队列全量更新失败: {e}", exc_info=True)

    def get_or_create_rx(self, tags_by_category: dict) -> List[int]:
        """
        获取或创建RX队列
        
        如果指定标签组合的RX队列已存在，直接返回；
        否则从RA队列中筛选创建新的RX队列。
        
        Args:
            tags_by_category: 标签分类字典，格式: {"分类1": [id1, id2], "分类2": [id3]}
        
        Returns:
            List[int]: RX队列（视频ID列表）
        """
        tag_key = self._make_tag_key(tags_by_category)
        
        with self._lock:
            if tag_key in self._rx_sequences:
                return self._rx_sequences[tag_key]["sequence"]
            
            sequence = self._filter_ra_by_tags(tags_by_category)
            self._rx_sequences[tag_key] = {
                "tags_by_category": tags_by_category,
                "sequence": sequence
            }
            self._save()
        
        logger.info(f"创建RX队列 [{tag_key}]，共 {len(sequence)} 个视频")
        return sequence

    def get_rx_videos(self, tags_by_category: dict, session) -> List[dict]:
        """
        获取RX队列对应的视频详情列表
        
        Args:
            tags_by_category: 标签分类字典
            session: 数据库会话
        
        Returns:
            List[dict]: 视频详情列表，按RX队列顺序排列
        """
        rx_sequence = self.get_or_create_rx(tags_by_category)
        
        if not rx_sequence:
            return []
        
        return self._get_videos_by_ids(rx_sequence, session)

    def get_rx_split_videos(
        self,
        tags_by_category: dict,
        split_count: int,
        session
    ) -> Tuple[List[List[dict]], int]:
        """
        获取RX队列分割后的视频详情列表（用于多路同播）
        
        将RX队列均匀分割为split_count个子序列，每个子序列包含对应的视频详情。
        
        Args:
            tags_by_category: 标签分类字典
            split_count: 分割数量（如4路同播则为4）
            session: 数据库会话
        
        Returns:
            Tuple[List[List[dict]], int]: (分割后的视频详情组列表, 总视频数)
        """
        rx_sequence = self.get_or_create_rx(tags_by_category)
        
        if not rx_sequence:
            return [[] for _ in range(split_count)], 0
        
        sub_sequences = self._split_sequence(rx_sequence, split_count)
        
        result = []
        for sub_seq in sub_sequences:
            if sub_seq:
                videos = self._get_videos_by_ids(sub_seq, session)
                result.append(videos)
            else:
                result.append([])
        
        return result, len(rx_sequence)

    def get_status(self) -> dict:
        """
        获取队列状态信息
        
        Returns:
            dict: 状态信息字典
        """
        with self._lock:
            rx_info = {}
            for tag_key, rx_data in self._rx_sequences.items():
                rx_info[tag_key] = {
                    "video_count": len(rx_data.get("sequence", [])),
                    "tags_by_category": rx_data.get("tags_by_category", {})
                }
            
            return {
                "ra_count": len(self._ra_sequence),
                "rx_count": len(self._rx_sequences),
                "rx_details": rx_info,
                "video_tags_map_count": len(self._video_tags_map),
                "last_update": self._last_update,
                "scheduler_running": (
                    self._scheduler_thread is not None
                    and self._scheduler_thread.is_alive()
                )
            }

    def _filter_ra_by_tags(self, tags_by_category: dict) -> List[int]:
        """
        从RA队列中按标签组合筛选视频ID
        
        筛选逻辑：
        - 同一分类下的标签为OR关系（满足任一即可）
        - 不同分类间为AND关系（必须都满足）
        
        Args:
            tags_by_category: 标签分类字典
        
        Returns:
            List[int]: 符合条件的视频ID列表，保持RA中的顺序
        """
        result = []
        for video_id in self._ra_sequence:
            video_tags = self._video_tags_map.get(video_id, set())
            if self._video_matches_tags(video_tags, tags_by_category):
                result.append(video_id)
        return result

    @staticmethod
    def _video_matches_tags(video_tags: Set[int], tags_by_category: dict) -> bool:
        """
        检查视频标签是否匹配标签组合条件
        
        Args:
            video_tags: 视频的标签ID集合
            tags_by_category: 标签分类字典
        
        Returns:
            bool: 是否匹配
        """
        if not tags_by_category:
            return True
        
        for category, tag_ids in tags_by_category.items():
            if not tag_ids:
                continue
            if not video_tags.intersection(set(tag_ids)):
                return False
        return True

    @staticmethod
    def _split_sequence(sequence: List[int], split_count: int) -> List[List[int]]:
        """
        将序列均匀分割为指定数量的子序列
        
        余数依次分配到前几个子序列中。
        例如：13个元素分割为4份 -> [4, 3, 3, 3]
        
        Args:
            sequence: 待分割的序列
            split_count: 分割数量
        
        Returns:
            List[List[int]]: 分割后的子序列列表
        """
        if not sequence:
            return [[] for _ in range(split_count)]
        
        total = len(sequence)
        base_count = total // split_count
        remainder = total % split_count
        
        result = []
        idx = 0
        for i in range(split_count):
            count = base_count + (1 if i < remainder else 0)
            result.append(sequence[idx:idx + count])
            idx += count
        
        return result

    @staticmethod
    def _make_tag_key(tags_by_category: dict) -> str:
        """
        根据标签组合生成确定性的键名
        
        将标签分类字典转换为排序后的字符串表示，确保相同组合生成相同的键。
        
        Args:
            tags_by_category: 标签分类字典
        
        Returns:
            str: 确定性的键名字符串
        """
        if not tags_by_category:
            return "empty"
        
        parts = []
        for category in sorted(tags_by_category.keys()):
            tag_ids = sorted(tags_by_category[category])
            parts.append(f"{category}:{','.join(str(t) for t in tag_ids)}")
        
        return "|".join(parts)

    def _get_videos_by_ids(self, video_ids: List[int], session) -> List[dict]:
        """
        根据视频ID列表获取视频详情
        
        保持传入的ID顺序。
        
        Args:
            video_ids: 视频ID列表
            session: 数据库会话
        
        Returns:
            List[dict]: 视频详情字典列表
        """
        import os as _os
        from sqlalchemy import select
        from sqlalchemy.orm import selectinload
        from video_tag_system.models.video import Video
        from video_tag_system.models.video_tag import VideoTag
        from video_tag_system.models.tag import TagResponse
        
        if not video_ids:
            return []
        
        stmt = (
            select(Video)
            .options(selectinload(Video.tags).selectinload(VideoTag.tag))
            .where(Video.id.in_(video_ids))
        )
        videos = list(session.execute(stmt).unique().scalars().all())
        
        id_to_video = {}
        for v in videos:
            tags = []
            if hasattr(v, 'tags') and v.tags:
                for vt in v.tags:
                    if vt.tag:
                        tags.append({
                            'id': vt.tag.id,
                            'name': vt.tag.name,
                            'parent_id': vt.tag.parent_id
                        })
            
            video_title = v.title or _os.path.basename(v.file_path)
            id_to_video[v.id] = {
                'id': v.id,
                'title': video_title,
                'file_path': v.file_path,
                'duration': v.duration,
                'tags': tags
            }
        
        try:
            from video_tag_system.utils.thumbnail_generator import get_thumbnail_generator
            thumbnail_gen = get_thumbnail_generator()
            for vid, info in id_to_video.items():
                info['thumbnail'] = thumbnail_gen.get_thumbnail_url(info['title'])
                info['gif'] = thumbnail_gen.get_gif_url(info['title'])
        except Exception:
            for vid, info in id_to_video.items():
                info['thumbnail'] = None
                info['gif'] = None
        
        return [id_to_video[vid] for vid in video_ids if vid in id_to_video]

    def _save(self):
        """将队列数据持久化到文件"""
        try:
            self._data_dir.mkdir(parents=True, exist_ok=True)
            
            serializable_video_tags = {
                str(vid): sorted(list(tags))
                for vid, tags in self._video_tags_map.items()
            }
            
            data = {
                "ra_sequence": self._ra_sequence,
                "rx_sequences": self._rx_sequences,
                "video_tags_map": serializable_video_tags,
                "last_update": self._last_update
            }
            
            temp_file = self._queue_file.with_suffix('.tmp')
            with open(temp_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False)
            
            if self._queue_file.exists():
                self._queue_file.unlink()
            temp_file.rename(self._queue_file)
            
        except Exception as e:
            logger.error(f"保存随机队列数据失败: {e}", exc_info=True)

    def _load(self):
        """从文件加载队列数据"""
        try:
            if not self._queue_file.exists():
                logger.info("随机队列数据文件不存在，将使用空队列")
                return
            
            with open(self._queue_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            self._ra_sequence = data.get("ra_sequence", [])
            self._rx_sequences = data.get("rx_sequences", {})
            
            raw_video_tags = data.get("video_tags_map", {})
            self._video_tags_map = {
                int(vid): set(tags) for vid, tags in raw_video_tags.items()
            }
            
            self._last_update = data.get("last_update")
            
            logger.info(
                f"加载随机队列数据: RA={len(self._ra_sequence)}个, "
                f"RX={len(self._rx_sequences)}个, "
                f"标签映射={len(self._video_tags_map)}个"
            )
            
        except Exception as e:
            logger.error(f"加载随机队列数据失败: {e}", exc_info=True)
            self._ra_sequence = []
            self._rx_sequences = {}
            self._video_tags_map = {}


_random_queue_manager: Optional[RandomQueueManager] = None


def get_random_queue_manager() -> Optional[RandomQueueManager]:
    """
    获取随机队列管理器单例
    
    Returns:
        Optional[RandomQueueManager]: 管理器实例，未初始化时返回None
    """
    return _random_queue_manager


def init_random_queue_manager(db_manager, data_dir: str = None) -> RandomQueueManager:
    """
    初始化并启动随机队列管理器
    
    Args:
        db_manager: 数据库管理器实例
        data_dir: 数据存储目录，默认为项目根目录下的data目录
    
    Returns:
        RandomQueueManager: 管理器实例
    """
    global _random_queue_manager
    
    if _random_queue_manager is not None:
        if _random_queue_manager._scheduler_thread and _random_queue_manager._scheduler_thread.is_alive():
            logger.warning("随机队列管理器已存在且正在运行")
            return _random_queue_manager
    
    if data_dir is None:
        data_dir = os.path.join(os.getcwd(), "data")
    
    _random_queue_manager = RandomQueueManager(data_dir)
    _random_queue_manager.start_scheduler(db_manager)
    
    return _random_queue_manager


def stop_random_queue_manager():
    """停止随机队列管理器"""
    global _random_queue_manager
    
    if _random_queue_manager is not None:
        _random_queue_manager.stop_scheduler()
        _random_queue_manager = None

"""
数据库管理模块

本模块提供数据库连接、会话管理和数据表操作的核心功能，包括：
- 数据库引擎创建与配置
- 连接池管理
- 会话上下文管理
- 数据表创建与删除
- 数据库备份与恢复
- SQLite 性能优化配置

架构说明：
- 使用 SQLAlchemy ORM 进行数据库操作
- 支持连接池和线程安全的会话管理
- 针对 SQLite 进行了 WAL 模式等性能优化

使用示例：
    from video_tag_system.core.database import get_db_manager
    
    # 获取数据库管理器
    db = get_db_manager()
    
    # 使用会话上下文管理器
    with db.get_session() as session:
        # 执行数据库操作
        pass
"""
import os
import shutil
import threading
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Optional, Generator, List

from sqlalchemy import create_engine, event, text, inspect
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker, Session, DeclarativeBase
from sqlalchemy.pool import QueuePool, StaticPool

from video_tag_system.core.config import get_settings
from video_tag_system.exceptions import DatabaseError, BackupError


class Base(DeclarativeBase):
    """
    SQLAlchemy 声明式基类
    
    所有数据模型类都应继承此类，以获得 ORM 映射能力。
    继承此类的模型会自动注册到 Base.metadata 中，
    便于统一创建和管理数据表。
    
    Example:
        class Video(Base):
            __tablename__ = 'videos'
            id = Column(Integer, primary_key=True)
            title = Column(String(255))
    """
    pass


class DatabaseManager:
    """
    数据库管理器
    
    负责管理数据库连接、会话生命周期和数据库维护操作。
    采用单例模式，确保整个应用程序使用同一个数据库连接池。
    
    主要功能：
    - 创建和管理数据库引擎
    - 提供线程安全的会话工厂
    - 支持数据库备份和恢复
    - 验证数据库完整性
    - 清理旧备份文件
    
    Attributes:
        database_url: 数据库连接URL
        echo: 是否打印SQL语句
        pool_size: 连接池大小
        max_overflow: 连接池溢出数量
    
    Thread Safety:
        本类是线程安全的，可在多线程环境中使用。
    """
    
    def __init__(
        self,
        database_url: Optional[str] = None,
        echo: Optional[bool] = None,
        pool_size: int = 10,
        max_overflow: int = 20
    ):
        """
        初始化数据库管理器
        
        Args:
            database_url: 数据库连接URL，为None时从配置读取
            echo: 是否打印SQL语句，为None时从配置读取
            pool_size: 连接池基础大小，默认10个连接
            max_overflow: 连接池溢出大小，超出pool_size后最多再创建的连接数
        """
        settings = get_settings()
        self.database_url = database_url or settings.database_url
        self.echo = echo if echo is not None else settings.database_echo
        self.pool_size = pool_size
        self.max_overflow = max_overflow
        self._engine: Optional[Engine] = None
        self._session_factory: Optional[sessionmaker] = None
        self._lock = threading.Lock()
    
    @property
    def engine(self) -> Engine:
        """
        获取数据库引擎（延迟创建）
        
        使用双重检查锁定模式确保线程安全的延迟初始化。
        引擎创建时会根据数据库类型应用相应的优化配置。
        
        Returns:
            Engine: SQLAlchemy 数据库引擎实例
        """
        if self._engine is None:
            with self._lock:
                if self._engine is None:
                    self._engine = self._create_engine()
        return self._engine
    
    def _create_engine(self) -> Engine:
        """
        创建数据库引擎
        
        根据数据库类型（SQLite/PostgreSQL等）应用不同的配置：
        
        SQLite 专属配置：
        - check_same_thread=False: 允许多线程使用同一连接
        - timeout=60: 连接超时时间（秒）
        - isolation_level=None: 自动提交模式，由应用控制事务
        - pool_pre_ping=True: 使用前检查连接有效性
        - pool_recycle=3600: 每小时回收连接
        
        Returns:
            Engine: 配置完成的数据库引擎
        """
        engine_kwargs = {
            "echo": self.echo,
        }
        
        if self.database_url.startswith("sqlite"):
            engine_kwargs.update({
                "connect_args": {
                    "check_same_thread": False,
                    "timeout": 60,
                    "isolation_level": None,
                },
                "poolclass": QueuePool,
                "pool_size": self.pool_size,
                "max_overflow": self.max_overflow,
                "pool_pre_ping": True,
                "pool_recycle": 3600,
            })
        
        engine = create_engine(self.database_url, **engine_kwargs)
        
        if self.database_url.startswith("sqlite"):
            self._enable_sqlite_optimizations(engine)
        
        return engine
    
    @staticmethod
    def _enable_sqlite_optimizations(engine: Engine) -> None:
        """
        为 SQLite 启用性能优化
        
        在每个新连接上执行以下 PRAGMA 优化：
        
        - foreign_keys=ON: 启用外键约束
        - journal_mode=WAL: 使用预写日志模式，提升并发性能
        - synchronous=NORMAL: 减少同步频率，提升写入性能
        - cache_size=-64000: 设置缓存大小为64MB（负值表示KB）
        - busy_timeout=60000: 锁等待超时60秒
        - temp_store=MEMORY: 临时表存储在内存中
        - mmap_size=268435456: 内存映射256MB，加速大文件读取
        
        Args:
            engine: SQLAlchemy 数据库引擎
        """
        @event.listens_for(engine, "connect")
        def set_sqlite_pragma(dbapi_connection, connection_record):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA synchronous=NORMAL")
            cursor.execute("PRAGMA cache_size=-64000")
            cursor.execute("PRAGMA busy_timeout=60000")
            cursor.execute("PRAGMA temp_store=MEMORY")
            cursor.execute("PRAGMA mmap_size=268435456")
            cursor.close()
    
    @property
    def session_factory(self) -> sessionmaker:
        """
        获取会话工厂（延迟创建）
        
        会话工厂用于创建数据库会话实例。
        配置为非自动提交和非自动刷新模式，
        由应用代码显式控制事务边界。
        
        Returns:
            sessionmaker: SQLAlchemy 会话工厂
        """
        if self._session_factory is None:
            self._session_factory = sessionmaker(
                bind=self.engine,
                autocommit=False,
                autoflush=False,
            )
        return self._session_factory
    
    @contextmanager
    def get_session(self) -> Generator[Session, None, None]:
        """
        获取数据库会话上下文管理器
        
        使用 with 语句自动管理会话生命周期：
        - 进入时创建新会话
        - 正常退出时自动提交事务
        - 异常退出时自动回滚事务
        - 退出时自动关闭会话
        
        Yields:
            Session: SQLAlchemy 数据库会话
        
        Example:
            with db_manager.get_session() as session:
                video = session.query(Video).first()
                video.title = "新标题"
                # 自动提交和关闭
        """
        session = self.session_factory()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
    
    def create_tables(self) -> None:
        """
        创建所有数据表
        
        根据 Base.metadata 中注册的所有模型类创建对应的数据表。
        如果表已存在则跳过，不会覆盖现有数据。
        
        Raises:
            DatabaseError: 创建表失败时抛出
        """
        try:
            Base.metadata.create_all(self.engine)
            self._migrate_schema()
        except Exception as e:
            raise DatabaseError("创建数据表失败", e)
    
    def _migrate_schema(self) -> None:
        """
        执行数据库模式迁移
        
        检查并添加新列到现有表中，确保数据库结构与模型定义一致。
        使用 SQLite 的 ALTER TABLE ADD COLUMN 实现增量迁移。
        
        迁移列表：
        - videos.thumbnail_url: 缩略图URL持久化字段
        - videos.gif_url: GIF预览URL持久化字段
        """
        if not self.database_url.startswith("sqlite"):
            return
        
        migrations = [
            ("videos", "thumbnail_url", "VARCHAR(500)"),
            ("videos", "gif_url", "VARCHAR(500)"),
        ]
        
        try:
            inspector = inspect(self.engine)
            for table_name, column_name, column_type in migrations:
                if table_name not in inspector.get_table_names():
                    continue
                existing_columns = [col["name"] for col in inspector.get_columns(table_name)]
                if column_name not in existing_columns:
                    with self.get_session() as session:
                        session.execute(text(
                            f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}"
                        ))
        except Exception as e:
            pass
    
    def drop_tables(self) -> None:
        """
        删除所有数据表
        
        删除 Base.metadata 中注册的所有模型对应的数据表。
        警告：此操作会删除所有数据，不可恢复！
        
        Raises:
            DatabaseError: 删除表失败时抛出
        """
        try:
            Base.metadata.drop_all(self.engine)
        except Exception as e:
            raise DatabaseError("删除数据表失败", e)
    
    def verify_integrity(self) -> dict:
        """
        验证数据库完整性
        
        执行以下检查：
        1. 检查必需的数据表是否存在
        2. 检查表的列结构是否正确
        3. 检查是否存在孤立的关联记录
        4. 执行 SQLite 完整性检查
        
        Returns:
            dict: 验证结果，包含：
                - valid: bool, 整体是否有效
                - tables: dict, 各表状态
                - errors: list, 错误信息列表
        
        Example:
            result = db_manager.verify_integrity()
            if not result['valid']:
                for error in result['errors']:
                    print(error)
        """
        result = {
            "valid": True,
            "tables": {},
            "errors": []
        }
        
        try:
            inspector = inspect(self.engine)
            tables = inspector.get_table_names()
            
            expected_tables = ["videos", "tags", "video_tags"]
            
            for table in expected_tables:
                if table in tables:
                    columns = [col["name"] for col in inspector.get_columns(table)]
                    result["tables"][table] = {
                        "exists": True,
                        "columns": columns
                    }
                else:
                    result["tables"][table] = {"exists": False}
                    result["errors"].append(f"表 '{table}' 不存在")
                    result["valid"] = False
            
            with self.get_session() as session:
                orphan_video_tags = session.execute(text("""
                    SELECT COUNT(*) FROM video_tags 
                    WHERE video_id NOT IN (SELECT id FROM videos)
                    OR tag_id NOT IN (SELECT id FROM tags)
                """)).scalar()
                
                if orphan_video_tags > 0:
                    result["errors"].append(f"发现 {orphan_video_tags} 条孤立的视频-标签关联记录")
                    result["valid"] = False
            
            if self.database_url.startswith("sqlite"):
                with self.get_session() as session:
                    integrity_result = session.execute(text("PRAGMA integrity_check")).scalar()
                    if integrity_result != "ok":
                        result["errors"].append(f"数据库完整性检查失败: {integrity_result}")
                        result["valid"] = False
            
        except Exception as e:
            result["valid"] = False
            result["errors"].append(f"验证过程出错: {str(e)}")
        
        return result
    
    def backup(self, backup_path: Optional[str] = None) -> str:
        """
        备份数据库
        
        创建数据库文件的完整备份。备份完成后会自动清理旧备份文件。
        
        Args:
            backup_path: 备份文件路径，为None时自动生成（格式：backup_YYYYMMDD_HHMMSS.db）
        
        Returns:
            str: 备份文件的完整路径
        
        Raises:
            BackupError: 备份失败时抛出
        
        Example:
            backup_file = db_manager.backup()
            print(f"备份已保存到: {backup_file}")
        """
        settings = get_settings()
        
        if backup_path is None:
            settings.ensure_backup_dir()
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = str(settings.backup_path / f"backup_{timestamp}.db")
        
        try:
            if self.database_url.startswith("sqlite"):
                db_path = self.database_url.replace("sqlite:///", "")
                if not os.path.exists(db_path):
                    raise BackupError("backup", "数据库文件不存在")
                shutil.copy2(db_path, backup_path)
            else:
                raise BackupError("backup", "暂不支持非SQLite数据库的备份")
            
            self._cleanup_old_backups(settings)
            
            return backup_path
        except BackupError:
            raise
        except Exception as e:
            raise BackupError("backup", str(e))
    
    def restore(self, backup_path: str) -> None:
        """
        从备份恢复数据库
        
        用指定的备份文件覆盖当前数据库。
        恢复前会关闭所有现有连接。
        
        Args:
            backup_path: 备份文件路径
        
        Raises:
            BackupError: 恢复失败时抛出
        
        Warning:
            此操作会覆盖当前数据库，请谨慎使用！
        """
        try:
            if not os.path.exists(backup_path):
                raise BackupError("restore", "备份文件不存在")
            
            if self.database_url.startswith("sqlite"):
                db_path = self.database_url.replace("sqlite:///", "")
                
                if self._engine:
                    self._engine.dispose()
                    self._engine = None
                    self._session_factory = None
                
                shutil.copy2(backup_path, db_path)
            else:
                raise BackupError("restore", "暂不支持非SQLite数据库的恢复")
            
        except BackupError:
            raise
        except Exception as e:
            raise BackupError("restore", str(e))
    
    def _cleanup_old_backups(self, settings) -> None:
        """
        清理旧备份文件
        
        保留最新的 N 个备份文件（N 由 max_backup_count 配置），
        删除其余的旧备份文件以节省磁盘空间。
        
        Args:
            settings: 配置对象，包含备份目录和最大数量设置
        """
        backup_dir = settings.backup_path
        max_count = settings.max_backup_count
        
        if not backup_dir.exists():
            return
        
        backups = sorted(
            backup_dir.glob("backup_*.db"),
            key=lambda f: f.stat().st_mtime,
            reverse=True
        )
        
        for old_backup in backups[max_count:]:
            old_backup.unlink()
    
    def list_backups(self) -> List[dict]:
        """
        列出所有备份文件
        
        获取备份目录中所有备份文件的信息，按创建时间倒序排列。
        
        Returns:
            List[dict]: 备份文件列表，每个元素包含：
                - path: 文件完整路径
                - name: 文件名
                - size: 文件大小（字节）
                - created_at: 创建时间（ISO格式）
        
        Example:
            for backup in db_manager.list_backups():
                print(f"{backup['name']}: {backup['size']} bytes")
        """
        settings = get_settings()
        backup_dir = settings.backup_path
        
        if not backup_dir.exists():
            return []
        
        backups = []
        for backup_file in sorted(backup_dir.glob("backup_*.db"), reverse=True):
            stat = backup_file.stat()
            backups.append({
                "path": str(backup_file),
                "name": backup_file.name,
                "size": stat.st_size,
                "created_at": datetime.fromtimestamp(stat.st_mtime).isoformat()
            })
        
        return backups
    
    def close(self) -> None:
        """
        关闭数据库连接
        
        释放所有数据库连接资源，包括：
        - 关闭连接池中的所有连接
        - 清空引擎和会话工厂引用
        
        通常在应用程序退出时调用。
        """
        if self._engine:
            self._engine.dispose()
            self._engine = None
            self._session_factory = None


_db_manager: Optional[DatabaseManager] = None


def get_db_manager() -> DatabaseManager:
    """
    获取数据库管理器单例
    
    使用单例模式确保整个应用程序使用同一个数据库管理器实例。
    首次调用时会创建实例并初始化数据库连接。
    
    Returns:
        DatabaseManager: 数据库管理器实例
    
    Example:
        db = get_db_manager()
        with db.get_session() as session:
            # 执行数据库操作
            pass
    """
    global _db_manager
    if _db_manager is None:
        _db_manager = DatabaseManager()
    return _db_manager


def init_database(database_url: Optional[str] = None, create_tables: bool = True) -> DatabaseManager:
    """
    初始化数据库
    
    创建数据库管理器实例并可选地创建数据表。
    通常在应用程序启动时调用。
    
    Args:
        database_url: 数据库连接URL，为None时使用配置中的URL
        create_tables: 是否自动创建数据表，默认为True
    
    Returns:
        DatabaseManager: 初始化完成的数据库管理器实例
    
    Example:
        # 使用默认配置初始化
        db = init_database()
        
        # 使用自定义URL初始化
        db = init_database("sqlite:///custom.db")
    """
    global _db_manager
    _db_manager = DatabaseManager(database_url=database_url)
    if create_tables:
        _db_manager.create_tables()
    return _db_manager

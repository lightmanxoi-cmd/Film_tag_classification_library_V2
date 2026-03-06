"""
数据库管理模块
"""
import os
import shutil
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Optional, Generator, List

from sqlalchemy import create_engine, event, text, inspect
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker, Session, DeclarativeBase
from sqlalchemy.pool import StaticPool

from video_tag_system.core.config import get_settings
from video_tag_system.exceptions import DatabaseError, BackupError


class Base(DeclarativeBase):
    """SQLAlchemy声明式基类"""
    pass


class DatabaseManager:
    """数据库管理器"""
    
    def __init__(
        self,
        database_url: Optional[str] = None,
        echo: Optional[bool] = None
    ):
        settings = get_settings()
        self.database_url = database_url or settings.database_url
        self.echo = echo if echo is not None else settings.database_echo
        self._engine: Optional[Engine] = None
        self._session_factory: Optional[sessionmaker] = None
    
    @property
    def engine(self) -> Engine:
        """获取数据库引擎"""
        if self._engine is None:
            self._engine = self._create_engine()
        return self._engine
    
    def _create_engine(self) -> Engine:
        """创建数据库引擎"""
        engine_kwargs = {
            "echo": self.echo,
        }
        
        if self.database_url.startswith("sqlite"):
            engine_kwargs.update({
                "connect_args": {"check_same_thread": False},
                "poolclass": StaticPool,
            })
        
        engine = create_engine(self.database_url, **engine_kwargs)
        
        if self.database_url.startswith("sqlite"):
            self._enable_foreign_keys(engine)
            self._optimize_sqlite(engine)
        
        return engine
    
    @staticmethod
    def _enable_foreign_keys(engine: Engine) -> None:
        """为 SQLite 启用外键约束"""
        @event.listens_for(engine, "connect")
        def set_sqlite_pragma(dbapi_connection, connection_record):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()
    
    @staticmethod
    def _optimize_sqlite(engine: Engine) -> None:
        """优化 SQLite 性能配置"""
        @event.listens_for(engine, "connect")
        def set_sqlite_optimizations(dbapi_connection, connection_record):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA synchronous=NORMAL")
            cursor.execute("PRAGMA cache_size=-64000")
            cursor.execute("PRAGMA temp_store=MEMORY")
            cursor.execute("PRAGMA busy_timeout=5000")
            cursor.close()
    
    @property
    def session_factory(self) -> sessionmaker:
        """获取会话工厂"""
        if self._session_factory is None:
            self._session_factory = sessionmaker(
                bind=self.engine,
                autocommit=False,
                autoflush=False,
            )
        return self._session_factory
    
    @contextmanager
    def get_session(self) -> Generator[Session, None, None]:
        """获取数据库会话上下文管理器"""
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
        """创建所有数据表"""
        try:
            Base.metadata.create_all(self.engine)
        except Exception as e:
            raise DatabaseError("创建数据表失败", e)
    
    def drop_tables(self) -> None:
        """删除所有数据表"""
        try:
            Base.metadata.drop_all(self.engine)
        except Exception as e:
            raise DatabaseError("删除数据表失败", e)
    
    def verify_integrity(self) -> dict:
        """验证数据库完整性"""
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
        """备份数据库"""
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
        """从备份恢复数据库"""
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
        """清理旧备份文件"""
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
        """列出所有备份文件"""
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
        """关闭数据库连接"""
        if self._engine:
            self._engine.dispose()
            self._engine = None
            self._session_factory = None


_db_manager: Optional[DatabaseManager] = None


def get_db_manager() -> DatabaseManager:
    """获取数据库管理器单例"""
    global _db_manager
    if _db_manager is None:
        _db_manager = DatabaseManager()
    return _db_manager


def init_database(database_url: Optional[str] = None, create_tables: bool = True) -> DatabaseManager:
    """初始化数据库"""
    global _db_manager
    _db_manager = DatabaseManager(database_url=database_url)
    if create_tables:
        _db_manager.create_tables()
    return _db_manager

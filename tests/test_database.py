"""
测试数据库管理
"""
import os
import pytest
from video_tag_system.core.database import DatabaseManager
from video_tag_system.exceptions import BackupError


class TestDatabaseManager:
    """数据库管理器测试类"""
    
    def test_create_tables(self, db_manager):
        """测试创建数据表"""
        from sqlalchemy import inspect
        inspector = inspect(db_manager.engine)
        tables = inspector.get_table_names()
        
        assert "videos" in tables
        assert "tags" in tables
        assert "video_tags" in tables
    
    def test_get_session(self, db_manager):
        """测试获取会话"""
        with db_manager.get_session() as session:
            assert session is not None
    
    def test_verify_integrity(self, db_manager):
        """测试数据库完整性验证"""
        result = db_manager.verify_integrity()
        
        assert result["valid"] is True
        assert len(result["errors"]) == 0
    
    def test_backup_and_restore(self, db_manager):
        """测试备份和恢复"""
        backup_path = db_manager.backup()
        
        assert os.path.exists(backup_path)
        
        try:
            db_manager.restore(backup_path)
        finally:
            if os.path.exists(backup_path):
                os.unlink(backup_path)
    
    def test_list_backups(self, db_manager):
        """测试列出备份"""
        backup_path = db_manager.backup()
        
        try:
            backups = db_manager.list_backups()
            
            assert len(backups) >= 1
            assert any(b["path"] == backup_path for b in backups)
        finally:
            if os.path.exists(backup_path):
                os.unlink(backup_path)
    
    def test_backup_nonexistent_file(self):
        """测试备份不存在的数据库"""
        manager = DatabaseManager(
            database_url="sqlite:///./nonexistent.db",
            echo=False
        )
        
        with pytest.raises(BackupError):
            manager.backup()
    
    def test_restore_nonexistent_backup(self, db_manager):
        """测试恢复不存在的备份"""
        with pytest.raises(BackupError):
            db_manager.restore("./nonexistent_backup.db")

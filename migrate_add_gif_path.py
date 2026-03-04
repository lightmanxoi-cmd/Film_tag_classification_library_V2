"""
数据库迁移脚本：添加gif_path字段到videos表
"""
import sqlite3
import os

def migrate_database():
    db_path = "video_library.db"
    
    if not os.path.exists(db_path):
        print("数据库文件不存在，将在首次运行时自动创建")
        return
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        cursor.execute("PRAGMA table_info(videos)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'gif_path' not in columns:
            print("添加gif_path字段到videos表...")
            cursor.execute("ALTER TABLE videos ADD COLUMN gif_path VARCHAR(500)")
            conn.commit()
            print("迁移完成：gif_path字段已添加")
        else:
            print("gif_path字段已存在，无需迁移")
    
    except Exception as e:
        print(f"迁移失败: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    migrate_database()

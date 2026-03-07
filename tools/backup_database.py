"""
数据库备份脚本

独立的命令行工具，用于手动执行数据库备份。
可以配合系统计划任务（如 Windows 任务计划程序或 Linux cron）使用。

使用示例:
    python tools/backup_database.py                    # 执行备份
    python tools/backup_database.py --status           # 查看备份状态
    python tools/backup_database.py --list             # 列出所有备份
    python tools/backup_database.py --restore backup_xxx.db  # 恢复备份
"""
import os
import sys
import argparse
from datetime import datetime
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from video_tag_system.core.database import DatabaseManager
from video_tag_system.core.config import get_settings


def create_backup(db_manager: DatabaseManager, label: str = None) -> str:
    """
    创建数据库备份
    
    Args:
        db_manager: 数据库管理器实例
        label: 可选的备份标签
    
    Returns:
        str: 备份文件路径
    """
    settings = get_settings()
    settings.ensure_backup_dir()
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    if label:
        backup_filename = f"backup_{label}_{timestamp}.db"
    else:
        backup_filename = f"backup_{timestamp}.db"
    
    backup_path = str(settings.backup_path / backup_filename)
    
    result = db_manager.backup(backup_path)
    
    file_size = os.path.getsize(result) / (1024 * 1024)
    print(f"✅ 备份成功!")
    print(f"   文件: {result}")
    print(f"   大小: {file_size:.2f} MB")
    
    return result


def list_backups(db_manager: DatabaseManager):
    """
    列出所有备份文件
    
    Args:
        db_manager: 数据库管理器实例
    """
    backups = db_manager.list_backups()
    
    if not backups:
        print("📭 没有找到备份文件")
        return
    
    print(f"📋 共找到 {len(backups)} 个备份文件:\n")
    print(f"{'序号':<6} {'文件名':<40} {'大小':<12} {'创建时间'}")
    print("-" * 80)
    
    for i, backup in enumerate(backups, 1):
        size_mb = backup['size'] / (1024 * 1024)
        created = datetime.fromisoformat(backup['created_at']).strftime("%Y-%m-%d %H:%M:%S")
        print(f"{i:<6} {backup['name']:<40} {size_mb:>8.2f} MB  {created}")


def show_status(db_manager: DatabaseManager):
    """
    显示备份状态
    
    Args:
        db_manager: 数据库管理器实例
    """
    settings = get_settings()
    backups = db_manager.list_backups()
    
    print("=" * 60)
    print("📊 数据库备份状态")
    print("=" * 60)
    
    print(f"\n⚙️  配置信息:")
    print(f"   数据库路径: {settings.database_url}")
    print(f"   备份目录: {settings.backup_dir}")
    print(f"   最大备份数量: {settings.max_backup_count}")
    print(f"   每日自动备份: {'启用' if settings.daily_backup_enabled else '禁用'}")
    print(f"   备份时间: {settings.daily_backup_time}")
    
    print(f"\n📦 备份统计:")
    print(f"   现有备份数量: {len(backups)}")
    
    if backups:
        total_size = sum(b['size'] for b in backups) / (1024 * 1024)
        latest = backups[0]
        latest_time = datetime.fromisoformat(latest['created_at']).strftime("%Y-%m-%d %H:%M:%S")
        
        print(f"   总备份大小: {total_size:.2f} MB")
        print(f"   最新备份: {latest['name']}")
        print(f"   备份时间: {latest_time}")
    
    print("\n" + "=" * 60)


def restore_backup(db_manager: DatabaseManager, backup_name: str):
    """
    从备份恢复数据库
    
    Args:
        db_manager: 数据库管理器实例
        backup_name: 备份文件名或路径
    """
    settings = get_settings()
    
    if os.path.isabs(backup_name):
        backup_path = backup_name
    else:
        backup_path = str(settings.backup_path / backup_name)
    
    if not os.path.exists(backup_path):
        print(f"❌ 备份文件不存在: {backup_path}")
        return False
    
    print(f"⚠️  警告: 此操作将覆盖当前数据库!")
    print(f"   备份文件: {backup_path}")
    
    confirm = input("\n确认恢复? (输入 'yes' 继续): ")
    
    if confirm.lower() != 'yes':
        print("❌ 已取消恢复操作")
        return False
    
    try:
        print("\n正在恢复数据库...")
        db_manager.restore(backup_path)
        print("✅ 数据库恢复成功!")
        return True
    except Exception as e:
        print(f"❌ 恢复失败: {e}")
        return False


def cleanup_backups(db_manager: DatabaseManager, keep_count: int = None):
    """
    清理旧备份文件
    
    Args:
        db_manager: 数据库管理器实例
        keep_count: 保留的备份数量，默认使用配置值
    """
    settings = get_settings()
    backup_dir = settings.backup_path
    max_count = keep_count or settings.max_backup_count
    
    if not backup_dir.exists():
        print("📭 备份目录不存在，无需清理")
        return
    
    backups = sorted(
        backup_dir.glob("backup_*.db"),
        key=lambda f: f.stat().st_mtime,
        reverse=True
    )
    
    if len(backups) <= max_count:
        print(f"✅ 当前备份数量 ({len(backups)}) 未超过限制 ({max_count})，无需清理")
        return
    
    to_delete = backups[max_count:]
    print(f"🗑️  将删除 {len(to_delete)} 个旧备份文件:")
    
    for backup in to_delete:
        size_mb = backup.stat().st_size / (1024 * 1024)
        print(f"   - {backup.name} ({size_mb:.2f} MB)")
    
    confirm = input("\n确认删除? (输入 'yes' 继续): ")
    
    if confirm.lower() != 'yes':
        print("❌ 已取消清理操作")
        return
    
    for backup in to_delete:
        backup.unlink()
        print(f"   ✓ 已删除: {backup.name}")
    
    print(f"\n✅ 清理完成，保留 {max_count} 个最新备份")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description='数据库备份管理工具',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python tools/backup_database.py                    # 执行备份
  python tools/backup_database.py --status           # 查看状态
  python tools/backup_database.py --list             # 列出备份
  python tools/backup_database.py --restore backup_20240101_120000.db
  python tools/backup_database.py --cleanup          # 清理旧备份
  python tools/backup_database.py --label manual     # 带标签的备份
        """
    )
    
    parser.add_argument(
        '--status', '-s',
        action='store_true',
        help='显示备份状态'
    )
    
    parser.add_argument(
        '--list', '-l',
        action='store_true',
        help='列出所有备份文件'
    )
    
    parser.add_argument(
        '--restore', '-r',
        metavar='BACKUP_FILE',
        help='从指定备份恢复数据库'
    )
    
    parser.add_argument(
        '--cleanup', '-c',
        action='store_true',
        help='清理旧备份文件'
    )
    
    parser.add_argument(
        '--keep',
        type=int,
        metavar='COUNT',
        help='清理时保留的备份数量'
    )
    
    parser.add_argument(
        '--label',
        metavar='LABEL',
        help='备份标签（用于标识备份）'
    )
    
    args = parser.parse_args()
    
    db_manager = DatabaseManager()
    
    if args.status:
        show_status(db_manager)
    elif args.list:
        list_backups(db_manager)
    elif args.restore:
        restore_backup(db_manager, args.restore)
    elif args.cleanup:
        cleanup_backups(db_manager, args.keep)
    else:
        create_backup(db_manager, args.label)


if __name__ == '__main__':
    main()

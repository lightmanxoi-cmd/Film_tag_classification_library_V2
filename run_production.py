"""
生产环境启动脚本
使用 Waitress WSGI 服务器提供高性能服务
"""
import os
import sys
import argparse
from pathlib import Path


WAITRESS_CONFIG = {
    'threads': 16,
    'connection_limit': 1000,
    'backlog': 1024,
    'channel_timeout': 300,
    'cleanup_interval': 30,
    'max_request_body_size': 1073741824,
    'send_bytes': 65536,
    'outbuf_overflow': 1048576,
    'inbuf_overflow': 524288,
    'expose_tracebacks': False,
}


def check_environment():
    """检查生产环境配置"""
    print("=" * 60)
    print("生产环境启动检查")
    print("=" * 60)
    
    # 检查必要文件
    required_files = [
        'web_app.py',
        'video_library.db',
        'web/static',
        'web/templates'
    ]
    
    missing_files = []
    for file in required_files:
        if not os.path.exists(file):
            missing_files.append(file)
    
    if missing_files:
        print(f"❌ 缺少必要文件: {', '.join(missing_files)}")
        return False
    
    print("✓ 所有必要文件已找到")
    
    # 检查数据库
    db_path = 'video_library.db'
    if os.path.exists(db_path):
        db_size = os.path.getsize(db_path) / (1024 * 1024)
        print(f"✓ 数据库文件: {db_path} ({db_size:.2f} MB)")
    
    # 检查视频路径
    video_path = os.environ.get('VIDEO_BASE_PATH', 'F:\\666')
    if os.path.exists(video_path):
        print(f"✓ 视频目录: {video_path}")
    else:
        print(f"⚠ 视频目录不存在: {video_path}")
        print("  请设置正确的 VIDEO_BASE_PATH 环境变量")
    
    print("=" * 60)
    return True


def run_production_server(host='0.0.0.0', port=5000, threads=None):
    try:
        from waitress import serve
        from web_app import create_app
        
        app = create_app()
        
        actual_threads = threads if threads is not None else WAITRESS_CONFIG['threads']
        
        print(f"\n🚀 启动生产服务器...")
        print(f"   监听地址: {host}:{port}")
        print(f"   工作线程: {actual_threads}")
        print(f"   连接限制: {WAITRESS_CONFIG['connection_limit']}")
        print(f"   发送缓冲: {WAITRESS_CONFIG['send_bytes']} bytes")
        print(f"   访问地址: http://{host if host != '0.0.0.0' else 'localhost'}:{port}")
        print(f"   按 Ctrl+C 停止服务器\n")
        
        config = WAITRESS_CONFIG.copy()
        if threads is not None:
            config['threads'] = threads
        
        serve(
            app,
            host=host,
            port=port,
            threads=config['threads'],
            connection_limit=config['connection_limit'],
            backlog=config['backlog'],
            channel_timeout=config['channel_timeout'],
            cleanup_interval=config['cleanup_interval'],
            max_request_body_size=config['max_request_body_size'],
            send_bytes=config['send_bytes'],
            outbuf_overflow=config['outbuf_overflow'],
            inbuf_overflow=config['inbuf_overflow'],
            expose_tracebacks=config['expose_tracebacks'],
        )
        
    except ImportError as e:
        print(f"❌ 导入错误: {e}")
        print("请确保已安装 waitress: pip install waitress")
        sys.exit(1)
    except Exception as e:
        print(f"❌ 启动失败: {e}")
        sys.exit(1)


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description='视频标签管理系统 - 生产环境启动脚本',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python run_production.py                    # 使用默认配置启动
  python run_production.py -p 8080            # 使用8080端口
  python run_production.py -H 127.0.0.1 -p 5000 -t 8
        """
    )
    
    parser.add_argument(
        '-H', '--host',
        default='0.0.0.0',
        help='服务器监听地址 (默认: 0.0.0.0)'
    )
    
    parser.add_argument(
        '-p', '--port',
        type=int,
        default=5000,
        help='服务器监听端口 (默认: 5000)'
    )
    
    parser.add_argument(
        '-t', '--threads',
        type=int,
        default=None,
        help=f'工作线程数 (默认: {WAITRESS_CONFIG["threads"]})'
    )
    
    parser.add_argument(
        '--check-only',
        action='store_true',
        help='仅检查环境，不启动服务器'
    )
    
    args = parser.parse_args()
    
    # 检查环境
    if not check_environment():
        sys.exit(1)
    
    if args.check_only:
        print("环境检查完成，退出。")
        sys.exit(0)
    
    # 启动服务器
    run_production_server(args.host, args.port, args.threads)


if __name__ == '__main__':
    main()

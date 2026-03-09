"""
生产环境启动脚本
使用 Waitress WSGI 服务器提供高性能服务

配置说明:
    所有配置通过环境变量或 .env 文件设置
    复制 .env.example 为 .env 并修改配置值

必需配置:
    VIDEO_BASE_PATH: 视频文件存储路径
    SECRET_KEY: 应用密钥（生产环境必须设置）

可选配置:
    DEFAULT_PASSWORD: 初始默认密码
    DATABASE_URL: 数据库连接URL
    INACTIVITY_TIMEOUT: 会话超时时间
"""
import os
import sys
import argparse
from pathlib import Path


def load_env_file():
    """加载 .env 文件"""
    env_file = Path('.env')
    if env_file.exists():
        with open(env_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    key = key.strip()
                    value = value.strip()
                    if key and key not in os.environ:
                        os.environ[key] = value


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
    
    errors = []
    warnings = []
    
    required_files = [
        'web_app.py',
        'web/static',
        'web/templates'
    ]
    
    missing_files = []
    for file in required_files:
        if not os.path.exists(file):
            missing_files.append(file)
    
    if missing_files:
        errors.append(f"缺少必要文件: {', '.join(missing_files)}")
    else:
        print("✓ 所有必要文件已找到")
    
    db_path = 'video_library.db'
    if os.path.exists(db_path):
        db_size = os.path.getsize(db_path) / (1024 * 1024)
        print(f"✓ 数据库文件: {db_path} ({db_size:.2f} MB)")
    else:
        warnings.append(f"数据库文件不存在: {db_path}（首次运行将创建）")
    
    video_path = os.environ.get('VIDEO_BASE_PATH')
    if video_path:
        if os.path.exists(video_path):
            print(f"✓ 视频目录: {video_path}")
        else:
            errors.append(f"视频目录不存在: {video_path}")
    else:
        errors.append("VIDEO_BASE_PATH 环境变量未设置")
        print("  请通过以下方式设置:")
        print("    1. 创建 .env 文件并添加: VIDEO_BASE_PATH=/path/to/videos")
        print("    2. 或设置环境变量: set VIDEO_BASE_PATH=/path/to/videos")
    
    secret_key = os.environ.get('SECRET_KEY')
    if secret_key:
        if len(secret_key) < 16:
            warnings.append("SECRET_KEY 长度过短，建议至少16个字符")
        else:
            print("✓ SECRET_KEY 已设置")
    else:
        warnings.append("SECRET_KEY 未设置，将自动生成（生产环境建议手动设置）")
    
    default_password = os.environ.get('DEFAULT_PASSWORD')
    if default_password:
        warnings.append("DEFAULT_PASSWORD 已设置，请确保首次登录后修改密码")
    
    print("-" * 60)
    
    if warnings:
        print("警告:")
        for w in warnings:
            print(f"  ⚠ {w}")
    
    if errors:
        print("错误:")
        for e in errors:
            print(f"  ❌ {e}")
        print("-" * 60)
        print("请修复以上错误后重试")
        print("=" * 60)
        return False
    
    if not warnings:
        print("✓ 配置检查通过")
    
    print("=" * 60)
    return True


def validate_config():
    """使用配置验证模块验证配置"""
    try:
        from web.core.config_validator import print_config_status
        return print_config_status()
    except ImportError:
        return check_environment()


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

配置:
  复制 .env.example 为 .env 并修改配置值
  必须设置 VIDEO_BASE_PATH 环境变量
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
    
    parser.add_argument(
        '--no-env',
        action='store_true',
        help='不加载 .env 文件'
    )
    
    args = parser.parse_args()
    
    if not args.no_env:
        load_env_file()
    
    if not check_environment():
        sys.exit(1)
    
    if args.check_only:
        print("环境检查完成，退出。")
        sys.exit(0)
    
    run_production_server(args.host, args.port, args.threads)


if __name__ == '__main__':
    main()

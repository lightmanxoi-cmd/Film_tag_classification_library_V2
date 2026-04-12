"""
奈飞风格视频播放网站 - Flask后端入口
重构版本：模块化架构、API版本管理、统一错误处理

架构说明：
- web/core/: 核心模块（配置、错误处理、响应格式）
- web/auth/: 认证模块（登录、密码管理）
- web/api/v1/: API v1版本
- web/pages/: 页面路由
- web/app.py: 应用工厂

API版本：
- /api/v1/*: 当前版本API
- /api/*: 兼容旧版API（重定向到v1）
"""
import os
from pathlib import Path


def load_env_file():
    """加载 .env 文件到环境变量（必须在导入其他模块之前调用）"""
    env_file = Path(__file__).parent / '.env'
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
        print("已加载 .env 配置文件")


load_env_file()

from sqlalchemy import text

from web.app import create_app
from video_tag_system.core.database import get_db_manager
from video_tag_system.utils.thumbnail_generator import get_thumbnail_generator


def update_thumbnails():
    """更新视频缩略图和GIF预览"""
    print("=" * 50)
    print("Checking video thumbnails and GIF previews...")
    
    thumbnail_gen = get_thumbnail_generator()
    db_manager = get_db_manager()
    db_session = db_manager.session_factory()
    
    try:
        result = db_session.execute(text("SELECT id, file_path, title, duration FROM videos")).fetchall()
        videos = [(row[0], row[1], row[2]) for row in result]
        videos_with_duration = [(row[0], row[1], row[2], row[3]) for row in result]
        
        print(f"Total videos: {len(videos)}")
        
        missing = thumbnail_gen.get_missing_thumbnails(videos)
        
        if not missing:
            print("All videos have thumbnails.")
        else:
            print(f"Found {len(missing)} videos without thumbnails, generating...")
            results = thumbnail_gen.batch_generate(missing, max_workers=2, force=False)
            print(f"Thumbnail generation complete: Success {results['success']}, Failed {results['failed']}")
        
        missing_gifs = thumbnail_gen.get_missing_gifs(videos)
        
        if not missing_gifs:
            print("All videos have GIF previews.")
        else:
            print(f"Found {len(missing_gifs)} videos without GIF previews, generating...")
            gif_videos = [(v[0], v[1], v[2], None) for v in missing_gifs]
            results = thumbnail_gen.batch_generate_gifs(gif_videos, max_workers=1, force=False)
            print(f"GIF generation complete: Success {results['success']}, Failed {results['failed']}, Skipped {results['skipped']}")
    except Exception as e:
        print(f"Error updating thumbnails/GIFs: {e}")
    finally:
        db_session.close()
    
    print("=" * 50)


def run_server(app, debug=False):
    """运行服务器（默认使用Waitress）"""
    try:
        from waitress import serve
        print("使用 Waitress 生产服务器启动...")
        print("访问地址: http://0.0.0.0:5000")
        print("按 Ctrl+C 停止服务器")
        print("=" * 50)
        serve(
            app,
            host='0.0.0.0',
            port=5000,
            threads=16,
            connection_limit=200,
            channel_timeout=300,
            max_request_body_size=10737418240,
            cleanup_interval=60
        )
    except ImportError:
        print("警告: waitress 未安装，使用 Flask 开发服务器")
        print("建议运行: pip install waitress")
        print("=" * 50)
        app.run(host='0.0.0.0', port=5000, debug=debug)


def main():
    """主入口函数"""
    config_name = os.environ.get('FLASK_ENV', 'development')
    debug_mode = config_name == 'development'
    app = create_app(config_name)
    
    update_thumbnails()
    
    run_server(app, debug=debug_mode)


if __name__ == '__main__':
    main()

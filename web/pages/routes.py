"""
页面路由蓝图模块

提供Web页面的路由处理，所有页面都需要登录验证。

路由列表：
    GET /                  # 主页 - 视频库主页面
    GET /clock-wallpaper   # 时钟壁纸页面
    GET /multi-play        # 多屏播放页面
    GET /random-recommend  # 随机推荐页面

使用示例：
    from web.pages import pages_bp
    
    # 注册蓝图
    app.register_blueprint(pages_bp)

模板文件：
    - templates/index.html: 主页模板
    - templates/clock_wallpaper.html: 时钟壁纸模板
    - templates/multi_play.html: 多屏播放模板
    - templates/random_recommend.html: 随机推荐模板
"""
from flask import Blueprint, render_template

from web.auth.decorators import login_required

pages_bp = Blueprint('pages', __name__)


@pages_bp.route('/')
@login_required
def index():
    """
    主页
    
    视频库的主页面，展示视频列表和标签筛选功能。
    前端通过AJAX调用API获取数据。
    
    Returns:
        HTML: 主页模板
    
    Features:
        - 视频列表展示
        - 标签筛选
        - 搜索功能
        - 随机排序
    
    Template:
        templates/index.html
    """
    return render_template('index.html')


@pages_bp.route('/clock-wallpaper')
@login_required
def clock_wallpaper():
    """
    时钟壁纸页面
    
    展示时钟壁纸的页面。
    
    Returns:
        HTML: 时钟壁纸模板
    
    Template:
        templates/clock_wallpaper.html
    """
    return render_template('clock_wallpaper.html')


@pages_bp.route('/multi-play')
@login_required
def multi_play():
    """
    多屏播放页面
    
    支持同时播放多个视频的页面。
    
    Returns:
        HTML: 多屏播放模板
    
    Features:
        - 多视频同时播放
        - 自定义布局
        - 音量控制
    
    Template:
        templates/multi_play.html
    """
    return render_template('multi_play.html')


@pages_bp.route('/random-recommend')
@login_required
def random_recommend():
    """
    随机推荐页面
    
    随机推荐视频的页面。
    
    Returns:
        HTML: 随机推荐模板
    
    Features:
        - 随机视频推荐
        - 快速切换
        - 简洁界面
    
    Template:
        templates/random_recommend.html
    """
    return render_template('random_recommend.html')

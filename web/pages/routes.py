"""
页面路由蓝图
"""
from flask import Blueprint, render_template

from web.auth.decorators import login_required

pages_bp = Blueprint('pages', __name__)


@pages_bp.route('/')
@login_required
def index():
    """主页"""
    return render_template('index.html')


@pages_bp.route('/clock-wallpaper')
@login_required
def clock_wallpaper():
    """时钟壁纸页面"""
    return render_template('clock_wallpaper.html')


@pages_bp.route('/multi-play')
@login_required
def multi_play():
    """多屏播放页面"""
    return render_template('multi_play.html')


@pages_bp.route('/random-recommend')
@login_required
def random_recommend():
    """随机推荐页面"""
    return render_template('random_recommend.html')

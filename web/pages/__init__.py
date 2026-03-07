"""
页面模块

提供Web页面的路由处理。

主要组件：
    - pages_bp: 页面路由蓝图

路由列表：
    GET /                  # 主页
    GET /clock-wallpaper   # 时钟壁纸页面
    GET /multi-play        # 多屏播放页面
    GET /random-recommend  # 随机推荐页面

使用示例：
    from web.pages import pages_bp
    
    # 注册蓝图
    app.register_blueprint(pages_bp)

页面说明：
    - index: 视频库主页面，展示视频列表和标签筛选
    - clock_wallpaper: 时钟壁纸展示页面
    - multi_play: 多视频同时播放页面
    - random_recommend: 随机视频推荐页面
"""
from web.pages.routes import pages_bp

__all__ = ['pages_bp']

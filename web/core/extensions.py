"""
Flask扩展初始化模块

初始化和管理Flask扩展实例。

扩展列表：
    - cors: Flask-CORS跨域支持扩展

使用示例：
    from web.core.extensions import cors
    
    # 在应用中初始化
    cors.init_app(app)
    
    # 或者使用配置
    cors.init_app(app, resources={r"/api/*": {"origins": "*"}})

CORS配置：
    默认允许所有来源的跨域请求。
    可通过应用配置或init_app参数进行自定义。
"""
from flask_cors import CORS

cors = CORS()

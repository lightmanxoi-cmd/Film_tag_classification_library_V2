"""
Web模块
"""
from web.app import create_app, get_db_manager
from web.services import get_services

__all__ = ['create_app', 'get_services', 'get_db_manager']

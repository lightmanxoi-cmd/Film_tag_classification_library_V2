"""
统一API响应格式模块

提供标准化的API响应格式，确保所有接口返回一致的数据结构。

主要功能：
    - APIResponse: 统一API响应格式类

响应格式：
    成功响应:
    {
        "success": true,
        "message": "操作成功",
        "data": {...},
        "cached": false
    }
    
    错误响应:
    {
        "success": false,
        "error": "错误信息",
        "error_code": "ERROR_CODE",
        "details": {...}
    }

使用示例：
    from web.core.responses import APIResponse
    
    # 成功响应
    return APIResponse.success(data={'key': 'value'})
    
    # 错误响应
    return APIResponse.error(message='操作失败', error_code='INVALID_INPUT')
    
    # 分页响应
    return APIResponse.paginated(
        items=[...],
        total=100,
        page=1,
        page_size=20
    )

HTTP状态码：
    - 200: 成功
    - 201: 创建成功
    - 204: 无内容
    - 400: 请求错误
    - 401: 未授权
    - 403: 禁止访问
    - 404: 资源不存在
    - 422: 验证失败
    - 500: 服务器错误
"""
from typing import Any, Optional, Dict
from flask import jsonify, Response


class APIResponse:
    """
    统一API响应格式类
    
    提供静态方法生成标准化的API响应。
    所有方法返回Flask Response对象。
    
    Methods:
        success: 成功响应
        error: 错误响应
        paginated: 分页响应
        created: 创建成功响应
        no_content: 无内容响应
        unauthorized: 未授权响应
        forbidden: 禁止访问响应
        not_found: 资源不存在响应
        validation_error: 验证错误响应
        server_error: 服务器错误响应
    """
    
    @staticmethod
    def success(data: Any = None, message: str = "操作成功", cached: bool = False, status_code: int = 200) -> Response:
        """
        成功响应
        
        生成标准的成功响应格式。
        
        Args:
            data: 响应数据，可以是任意类型
            message: 成功消息，默认"操作成功"
            cached: 数据是否来自缓存
            status_code: HTTP状态码，默认200
        
        Returns:
            Response: Flask响应对象
        
        Example:
            return APIResponse.success(data={'id': 1, 'name': 'test'})
            # Response: {"success": true, "message": "操作成功", "data": {...}, "cached": false}
        """
        response = {
            'success': True,
            'message': message,
            'data': data,
            'cached': cached
        }
        return jsonify(response), status_code
    
    @staticmethod
    def error(message: str, error_code: str = None, details: Optional[Dict] = None, status_code: int = 400) -> Response:
        """
        错误响应
        
        生成标准的错误响应格式。
        
        Args:
            message: 错误消息
            error_code: 错误码，用于客户端识别错误类型
            details: 错误详情，包含额外信息
            status_code: HTTP状态码，默认400
        
        Returns:
            Response: Flask响应对象
        
        Example:
            return APIResponse.error(
                message='视频不存在',
                error_code='VIDEO_NOT_FOUND',
                status_code=404
            )
        """
        response = {
            'success': False,
            'error': message,
        }
        if error_code:
            response['error_code'] = error_code
        if details:
            response['details'] = details
        return jsonify(response), status_code
    
    @staticmethod
    def paginated(
        items: list,
        total: int,
        page: int,
        page_size: int,
        cached: bool = False
    ) -> Response:
        """
        分页响应
        
        生成分页数据的响应格式，自动计算总页数。
        
        Args:
            items: 当前页的数据项列表
            total: 总记录数
            page: 当前页码
            page_size: 每页记录数
            cached: 数据是否来自缓存
        
        Returns:
            Response: Flask响应对象
        
        Example:
            return APIResponse.paginated(
                items=[video1, video2],
                total=100,
                page=1,
                page_size=20
            )
            # Response: {
            #     "success": true,
            #     "data": {
            #         "items": [...],
            #         "total": 100,
            #         "page": 1,
            #         "page_size": 20,
            #         "total_pages": 5
            #     }
            # }
        """
        total_pages = (total + page_size - 1) // page_size if page_size > 0 else 0
        data = {
            'items': items,
            'total': total,
            'page': page,
            'page_size': page_size,
            'total_pages': total_pages
        }
        return APIResponse.success(data=data, cached=cached)
    
    @staticmethod
    def created(data: Any = None, message: str = "创建成功") -> Response:
        """
        创建成功响应
        
        用于资源创建成功的场景，返回201状态码。
        
        Args:
            data: 创建的资源数据
            message: 成功消息
        
        Returns:
            Response: Flask响应对象（201 Created）
        
        Example:
            return APIResponse.created(data={'id': 1, 'name': 'new_tag'})
        """
        return APIResponse.success(data=data, message=message, status_code=201)
    
    @staticmethod
    def no_content() -> Response:
        """
        无内容响应
        
        用于删除成功等不需要返回数据的场景。
        
        Returns:
            Response: Flask响应对象（204 No Content）
        
        Example:
            return APIResponse.no_content()
        """
        return jsonify({}), 204
    
    @staticmethod
    def unauthorized(message: str = "未授权访问，请先登录", timeout: bool = False) -> Response:
        """
        未授权响应
        
        用于用户未登录或会话过期的场景。
        
        Args:
            message: 错误消息
            timeout: 是否因会话超时
        
        Returns:
            Response: Flask响应对象（401 Unauthorized）
        
        Example:
            return APIResponse.unauthorized(timeout=True)
        """
        response = {
            'success': False,
            'error': message,
        }
        if timeout:
            response['timeout'] = True
        return jsonify(response), 401
    
    @staticmethod
    def forbidden(message: str = "禁止访问") -> Response:
        """
        禁止访问响应
        
        用于用户已登录但权限不足的场景。
        
        Args:
            message: 错误消息
        
        Returns:
            Response: Flask响应对象（403 Forbidden）
        
        Example:
            return APIResponse.forbidden(message='无权访问此资源')
        """
        return APIResponse.error(message=message, status_code=403)
    
    @staticmethod
    def not_found(message: str = "资源不存在") -> Response:
        """
        资源不存在响应
        
        用于请求的资源不存在的场景。
        
        Args:
            message: 错误消息
        
        Returns:
            Response: Flask响应对象（404 Not Found）
        
        Example:
            return APIResponse.not_found(message='视频不存在')
        """
        return APIResponse.error(message=message, status_code=404)
    
    @staticmethod
    def validation_error(field: str, reason: str) -> Response:
        """
        验证错误响应
        
        用于请求数据验证失败的场景。
        
        Args:
            field: 验证失败的字段名
            reason: 验证失败的原因
        
        Returns:
            Response: Flask响应对象（422 Unprocessable Entity）
        
        Example:
            return APIResponse.validation_error('name', '不能为空')
        """
        return APIResponse.error(
            message=f"验证失败 - 字段 '{field}': {reason}",
            error_code='VALIDATION_ERROR',
            details={'field': field, 'reason': reason},
            status_code=422
        )
    
    @staticmethod
    def server_error(message: str = "服务器内部错误") -> Response:
        """
        服务器错误响应
        
        用于服务器内部错误的场景。
        
        Args:
            message: 错误消息
        
        Returns:
            Response: Flask响应对象（500 Internal Server Error）
        
        Example:
            return APIResponse.server_error(message='数据库连接失败')
        """
        return APIResponse.error(message=message, status_code=500)

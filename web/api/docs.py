"""
API 文档路由模块

提供 Swagger UI 和 OpenAPI 文档访问接口。

路由列表：
    GET /api/docs          # Swagger UI 文档页面
    GET /api/openapi.yaml  # OpenAPI 规范文件

使用示例：
    # 访问 API 文档
    GET /api/docs
"""
import os
from flask import Blueprint, send_file, Response

docs_bp = Blueprint('docs', __name__, url_prefix='/api')


@docs_bp.route('/docs')
def swagger_ui():
    """
    Swagger UI 文档页面
    
    提供交互式的 API 文档界面，可以在线测试 API。
    
    Returns:
        HTML页面，包含 Swagger UI
    
    Example:
        GET /api/docs
    """
    html_content = '''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>视频标签分类系统 API 文档</title>
    <link rel="stylesheet" type="text/css" href="https://unpkg.com/swagger-ui-dist@5.9.0/swagger-ui.css">
    <style>
        html { box-sizing: border-box; overflow: -moz-scrollbars-vertical; overflow-y: scroll; }
        *, *:before, *:after { box-sizing: inherit; }
        body { margin:0; padding:0; }
        .swagger-ui .topbar { display: none; }
        .swagger-ui .info .title { font-size: 28px; }
        .swagger-ui .info .description { font-size: 14px; line-height: 1.6; }
        .swagger-ui .info .description code { 
            background: #f5f5f5; 
            padding: 2px 6px; 
            border-radius: 3px; 
        }
    </style>
</head>
<body>
    <div id="swagger-ui"></div>
    <script src="https://unpkg.com/swagger-ui-dist@5.9.0/swagger-ui-bundle.js"></script>
    <script src="https://unpkg.com/swagger-ui-dist@5.9.0/swagger-ui-standalone-preset.js"></script>
    <script>
    window.onload = function() {
        const ui = SwaggerUIBundle({
            url: "/api/openapi.yaml",
            dom_id: '#swagger-ui',
            deepLinking: true,
            presets: [
                SwaggerUIBundle.presets.apis,
                SwaggerUIStandalonePreset
            ],
            plugins: [
                SwaggerUIBundle.plugins.DownloadUrl
            ],
            layout: "StandaloneLayout",
            defaultModelsExpandDepth: 1,
            defaultModelExpandDepth: 1,
            docExpansion: "list",
            displayOperationId: false,
            displayRequestDuration: true,
            filter: true,
            showExtensions: true,
            showCommonExtensions: true,
            syntaxHighlight: {
                activate: true,
                theme: "monokai"
            },
            tryItOutEnabled: true,
            requestSnippetsEnabled: true,
            requestSnippets: {
                generators: {
                    "curl_bash": {
                        title: "cURL (bash)",
                        syntax: "bash"
                    },
                    "curl_powershell": {
                        title: "cURL (PowerShell)",
                        syntax: "powershell"
                    },
                    "curl_cmd": {
                        title: "cURL (CMD)",
                        syntax: "bash"
                    }
                },
                defaultExpanded: true,
                languages: ["curl_bash", "curl_powershell", "curl_cmd"]
            }
        });
        window.ui = ui;
    };
    </script>
</body>
</html>'''
    return Response(html_content, mimetype='text/html')


@docs_bp.route('/openapi.yaml')
def openapi_spec():
    """
    OpenAPI 规范文件
    
    返回 OpenAPI 3.0 规范的 YAML 文件。
    
    Returns:
        YAML文件，包含完整的 API 规范
    
    Example:
        GET /api/openapi.yaml
    """
    openapi_path = os.path.join(os.path.dirname(__file__), 'openapi.yaml')
    return send_file(openapi_path, mimetype='application/x-yaml')


@docs_bp.route('/docs/redirect')
def docs_redirect():
    """
    文档重定向
    
    兼容旧版文档路径。
    
    Returns:
        重定向到 /api/docs
    """
    from flask import redirect
    return redirect('/api/docs')

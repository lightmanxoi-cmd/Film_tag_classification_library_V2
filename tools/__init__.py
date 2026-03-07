"""
工具脚本模块

本模块包含一系列用于管理和维护视频标签系统的命令行工具。

工具列表：
==========

1. video_importer.py - 视频入库打标签工具
   用于将视频文件导入数据库并添加标签。
   支持单个文件导入和文件夹批量导入。
   
   使用示例：
       python tools/video_importer.py --interactive
       python tools/video_importer.py --file "video.mp4" --level1 "电影" --level2 "动作"

2. tag_manager.py - 标签管理工具
   提供标签的全面管理功能，包括创建、删除、重命名、合并等操作。
   支持一级和二级标签管理。
   
   使用示例：
       python tools/tag_manager.py list --tree
       python tools/tag_manager.py create "动作" --desc "动作类型视频"

3. video_tag_editor.py - 视频标签编辑工具
   提供交互式的视频标签编辑功能。
   支持搜索视频、添加/移除标签等操作。
   
   使用示例：
       python tools/video_tag_editor.py

4. delete_videos.py - 视频删除工具
   用于从数据库中删除视频记录。
   支持按ID、标题、路径等多种条件删除。
   
   使用示例：
       python tools/delete_videos.py --ids 1 2 3
       python tools/delete_videos.py --title "测试"

5. update_video_paths.py - 视频路径更新工具
   用于更新数据库中视频文件的路径。
   当视频文件移动位置后使用此工具更新路径。
   
   使用示例：
       python tools/update_video_paths.py --folder "D:\\Videos"

6. optimize_database_indexes.py - 数据库优化工具
   用于创建和优化数据库索引，提升查询性能。
   
   使用示例：
       python tools/optimize_database_indexes.py

7. test_database_performance.py - 数据库性能测试工具
   用于测试数据库查询性能，评估优化效果。
   
   使用示例：
       python tools/test_database_performance.py

标签体系说明：
==============

本系统采用两级标签体系：

一级标签（根标签）：
- 主要分类标签，如：电影、电视剧、纪录片、动漫等
- 没有父标签，parent_id 为 None
- level 属性为 1

二级标签（子标签）：
- 子分类标签，如：动作、喜剧、科幻、爱情等
- 必须属于一个一级标签
- parent_id 指向父标签的 ID
- level 属性为 2

使用建议：
==========

1. 首次使用时，建议先使用 tag_manager.py 创建标签体系
2. 使用 video_importer.py 导入视频并打标签
3. 定期使用 optimize_database_indexes.py 优化数据库
4. 使用 test_database_performance.py 评估系统性能
5. 当视频文件移动位置后，使用 update_video_paths.py 更新路径
6. 需要清理视频时，使用 delete_videos.py 删除记录

作者：Video Library System
创建时间：2024
"""

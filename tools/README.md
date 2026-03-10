# 视频标签分类库 - 工具使用指南

本目录包含一系列用于管理视频标签分类库的命令行工具。本文档将详细介绍每个工具的功能、使用方法和参数说明。

***

## 目录

1. [video\_importer.py - 视频导入工具](#1-video_importerpy---视频导入工具)
2. [tag\_manager.py - 标签管理工具](#2-tag_managerpy---标签管理工具)
3. [video\_tag\_editor.py - 视频标签编辑器](#3-video_tag_editorpy---视频标签编辑器)
4. [backup\_database.py - 数据库备份工具](#4-backup_databasepy---数据库备份工具)
5. [delete\_videos.py - 视频记录删除工具](#5-delete_videospy---视频记录删除工具)
6. [update\_video\_paths.py - 视频路径更新工具](#6-update_video_pathspy---视频路径更新工具)
7. [optimize\_database\_indexes.py - 数据库索引优化工具](#7-optimize_database_indexespy---数据库索引优化工具)
8. [test\_database\_performance.py - 数据库性能测试工具](#8-test_database_performancepy---数据库性能测试工具)

***

## 1. video\_importer.py - 视频导入工具

### 功能概述

视频导入工具是整个系统的核心工具之一，用于将视频文件导入数据库并自动关联标签。支持单文件导入、文件夹批量导入、递归扫描等多种导入模式。

### 主要功能

- 单个视频文件导入
- 文件夹批量导入
- 递归扫描子文件夹
- 自动检测重复视频
- 自动提取视频元数据（时长、分辨率、大小等）

### 使用方法

#### 命令行参数

```Python
python video_importer.py [选项]
```

| 参数            | 简写     | 说明         | 默认值   |
| ------------- | ------ | ---------- | ----- |
| `--path`      | `-p`   | 视频文件或文件夹路径 | 必填    |
| `--tag`       | `-t`   | 一级标签名称     | 必填    |
| `--subtag`    | `-s`   | 二级标签名称     | 可选    |
| `--recursive` | `-r`   | 递归扫描子文件夹   | False |
| `--dry-run`   | <br /> | 模拟运行，不实际导入 | False |

#### 使用示例

**导入单个视频：**

```bash
python video_importer.py --path "D:/Videos/movie.mp4" --tag "电影" --subtag "动作"
```

**批量导入文件夹：**

```bash
python video_importer.py --path "D:/Videos/Movies" --tag "电影" --recursive
```

**模拟运行（测试用）：**

```bash
python video_importer.py --path "D:/Videos" --tag "测试" --dry-run
```

### 核心类与方法

#### VideoImporter 类

```python
from tools.video_importer import VideoImporter

importer = VideoImporter()

# 导入单个视频
result = importer.import_video(
    file_path="D:/Videos/movie.mp4",
    level1_tag_name="电影",
    level2_tag_name="动作"
)

# 批量导入文件夹
result = importer.import_from_folder(
    folder_path="D:/Videos/Movies",
    level1_tag_name="电影",
    recursive=True
)
```

#### 主要方法说明

| 方法                     | 参数                                                            | 返回值        | 说明      |
| ---------------------- | ------------------------------------------------------------- | ---------- | ------- |
| `import_video()`       | file\_path, level1\_tag\_name, level2\_tag\_name              | bool       | 导入单个视频  |
| `import_from_folder()` | folder\_path, level1\_tag\_name, level2\_tag\_name, recursive | dict       | 批量导入文件夹 |
| `scan_video_files()`   | folder\_path, recursive                                       | List\[str] | 扫描视频文件  |
| `extract_metadata()`   | file\_path                                                    | dict       | 提取视频元数据 |

### 导入逻辑说明

1. **重复检测**：根据视频标题判断是否已存在
   - 如果存在：更新路径并添加新标签
   - 如果不存在：创建新视频记录并添加标签
2. **支持的文件格式**：.mp4, .avi, .mkv, .mov, .wmv, .flv, .webm
3. **元数据提取**：自动提取视频时长、分辨率、文件大小等信息

***

## 2. tag\_manager.py - 标签管理工具

### 功能概述

标签管理工具提供完整的标签生命周期管理功能，包括创建、删除、重命名、合并标签，以及查看标签统计信息等。

### 主要功能

- 创建一级/二级标签
- 删除标签（含关联检查）
- 重命名标签
- 合并标签
- 查看标签树结构
- 统计标签使用情况

### 使用方法

#### 命令行参数

```bash
python tag_manager.py [命令] [选项]
```

| 命令       | 说明     |
| -------- | ------ |
| `list`   | 列出所有标签 |
| `create` | 创建新标签  |
| `delete` | 删除标签   |
| `rename` | 重命名标签  |
| `merge`  | 合并标签   |
| `stats`  | 显示标签统计 |

#### 使用示例

**列出所有标签：**

```bash
python tag_manager.py list
```

**创建一级标签：**

```bash
python tag_manager.py create --name "电影" --level 1
```

**创建二级标签：**

```bash
python tag_manager.py create --name "动作" --level 2 --parent "电影"
```

**删除标签：**

```bash
python tag_manager.py delete --id 5
```

**重命名标签：**

```bash
python tag_manager.py rename --id 5 --new-name "动作片"
```

**合并标签：**

```bash
python tag_manager.py merge --source 3 --target 5
```

### 核心类与方法

#### TagManager 类

```python
from tools.tag_manager import TagManager

manager = TagManager()

# 创建标签
tag = manager.create_tag(name="电影", level=1)

# 创建二级标签
subtag = manager.create_tag(name="动作", level=2, parent_name="电影")

# 获取标签树
tree = manager.get_tag_tree()

# 合并标签
manager.merge_tags(source_id=3, target_id=5)
```

#### 主要方法说明

| 方法                | 参数                        | 返回值  | 说明     |
| ----------------- | ------------------------- | ---- | ------ |
| `create_tag()`    | name, level, parent\_name | Tag  | 创建标签   |
| `delete_tag()`    | tag\_id                   | bool | 删除标签   |
| `rename_tag()`    | tag\_id, new\_name        | bool | 重命名标签  |
| `merge_tags()`    | source\_id, target\_id    | None | 合并标签   |
| `get_tag_tree()`  | <br />                    | dict | 获取标签树  |
| `get_tag_stats()` | <br />                    | dict | 获取标签统计 |

### 标签层级结构

```
一级标签（Level 1）
├── 二级标签（Level 2）
│   ├── 二级标签（Level 2）
│   └── 二级标签（Level 2）
└── 二级标签（Level 2）
```

***

## 3. video\_tag\_editor.py - 视频标签编辑器

### 功能概述

视频标签编辑器是一个交互式工具，用于编辑单个或多个视频的标签关联。支持搜索视频、查看标签、添加/移除/替换标签等操作。

### 主要功能

- 按标题/ID搜索视频
- 查看视频当前标签
- 添加标签到视频
- 从视频移除标签
- 替换视频的所有标签
- 批量编辑多个视频

### 使用方法

#### 命令行参数

```bash
python video_tag_editor.py [命令] [选项]
```

| 命令            | 说明       |
| ------------- | -------- |
| `search`      | 搜索视频     |
| `show`        | 显示视频标签   |
| `add`         | 添加标签     |
| `remove`      | 移除标签     |
| `set`         | 设置标签（替换） |
| `interactive` | 交互模式     |

#### 使用示例

**搜索视频：**

```bash
python video_tag_editor.py search --title "复仇者"
```

**显示视频标签：**

```bash
python video_tag_editor.py show --id 123
```

**添加标签：**

```bash
python video_tag_editor.py add --id 123 --tags "科幻,动作"
```

**移除标签：**

```bash
python video_tag_editor.py remove --id 123 --tags "动作"
```

**替换标签：**

```bash
python video_tag_editor.py set --id 123 --tags "科幻,超级英雄"
```

**交互模式：**

```bash
python video_tag_editor.py interactive
```

### 核心类与方法

#### VideoTagEditor 类

```python
from tools.video_tag_editor import VideoTagEditor

editor = VideoTagEditor()

# 搜索视频
videos = editor.search_videos(title="复仇者")

# 获取视频标签
tags = editor.get_video_tags(video_id=123)

# 添加标签
result = editor.add_tags_to_video(video_id=123, tag_ids=[1, 2, 3])

# 移除标签
result = editor.remove_tags_from_video(video_id=123, tag_ids=[2])

# 设置标签（替换）
result = editor.set_video_tags(video_id=123, tag_ids=[1, 3, 5])
```

#### 主要方法说明

| 方法                         | 参数                  | 返回值          | 说明     |
| -------------------------- | ------------------- | ------------ | ------ |
| `search_videos()`          | title, limit        | List\[Video] | 搜索视频   |
| `get_video_tags()`         | video\_id           | List\[Tag]   | 获取视频标签 |
| `add_tags_to_video()`      | video\_id, tag\_ids | dict         | 添加标签   |
| `remove_tags_from_video()` | video\_id, tag\_ids | dict         | 移除标签   |
| `set_video_tags()`         | video\_id, tag\_ids | dict         | 设置标签   |

### 交互模式操作流程

1. 输入搜索关键词查找视频
2. 从搜索结果中选择要编辑的视频
3. 查看当前标签
4. 选择操作：添加/移除/替换标签
5. 输入标签名称或ID
6. 确认修改

***

## 4. backup\_database.py - 数据库备份工具

### 功能概述

数据库备份工具用于创建、管理和恢复数据库备份。支持自动命名、标签标记、备份列表查看、恢复和清理旧备份等功能。

### 主要功能

- 创建数据库备份
- 查看备份列表
- 从备份恢复数据库
- 清理旧备份
- 自动备份命名

### 使用方法

#### 命令行参数

```bash
python backup_database.py [命令] [选项]
```

| 命令        | 说明    |
| --------- | ----- |
| `create`  | 创建备份  |
| `list`    | 列出备份  |
| `restore` | 恢复备份  |
| `clean`   | 清理旧备份 |

| 参数        | 简写   | 说明             |
| --------- | ---- | -------------- |
| `--label` | `-l` | 备份标签名称         |
| `--file`  | `-f` | 备份文件路径（恢复时使用）  |
| `--keep`  | `-k` | 保留的备份数量（清理时使用） |

#### 使用示例

**创建备份：**

```bash
python backup_database.py create --label "升级前备份"
```

**列出所有备份：**

```bash
python backup_database.py list
```

**恢复备份：**

```bash
python backup_database.py restore --file "backups/backup_20240115_143022.db"
```

**清理旧备份（保留最近5个）：**

```bash
python backup_database.py clean --keep 5
```

### 核心函数说明

```python
from tools.backup_database import (
    create_backup,
    list_backups,
    restore_backup,
    clean_old_backups
)
from video_tag_system.database import DatabaseManager

db = DatabaseManager()

# 创建备份
backup_path = create_backup(db, label="重要操作前")

# 列出备份
backups = list_backups()

# 恢复备份
restore_backup("backups/backup_20240115_143022.db")

# 清理旧备份
clean_old_backups(keep_count=5)
```

### 备份文件命名规则

```
backup_YYYYMMDD_HHMMSS[_label].db

示例：
backup_20240115_143022.db
backup_20240115_143022_升级前备份.db
```

### 最佳实践

1. **重要操作前备份**：在进行批量删除、合并标签等操作前创建备份
2. **定期备份**：建议每周或每月创建一次备份
3. **标签标记**：为重要备份添加有意义的标签
4. **定期清理**：保留最近5-10个备份即可

***

## 5. delete\_videos.py - 视频记录删除工具

### 功能概述

视频记录删除工具用于从数据库中删除视频记录。支持多种删除方式，包括按ID、按标题、按路径删除，以及删除本地文件不存在的失效记录。

### 主要功能

- 按ID删除单个视频
- 按标题搜索并删除
- 按路径删除
- 批量删除本地文件不存在的记录
- 模拟运行模式

### 使用方法

#### 命令行参数

```bash
python delete_videos.py [命令] [选项]
```

| 命令         | 说明         |
| ---------- | ---------- |
| `by-id`    | 按ID删除      |
| `by-title` | 按标题删除      |
| `by-path`  | 按路径删除      |
| `missing`  | 删除文件不存在的记录 |

| 参数          | 简写     | 说明           |
| ----------- | ------ | ------------ |
| `--id`      | `-i`   | 视频ID         |
| `--title`   | `-t`   | 视频标题（支持模糊匹配） |
| `--path`    | `-p`   | 视频路径         |
| `--dry-run` | <br /> | 模拟运行，不实际删除   |
| `--force`   | `-f`   | 跳过确认提示       |

#### 使用示例

**按ID删除：**

```bash
python delete_videos.py by-id --id 123
```

**按标题删除（模糊匹配）：**

```bash
python delete_videos.py by-title --title "测试视频" --dry-run
```

**按路径删除：**

```bash
python delete_videos.py by-path --path "D:/Videos/old/"
```

**删除文件不存在的记录：**

```bash
python delete_videos.py missing --dry-run
```

**强制删除（跳过确认）：**

```bash
python delete_videos.py by-id --id 123 --force
```

### 核心类与方法

#### VideoDeleter 类

```python
from tools.delete_videos import VideoDeleter

deleter = VideoDeleter()

# 按ID删除
result = deleter.delete_by_id(video_id=123)

# 按标题删除
result = deleter.delete_by_title(title="测试", dry_run=True)

# 按路径删除
result = deleter.delete_by_path(path="D:/Videos/old/")

# 删除文件不存在的记录
result = deleter.delete_missing_files(dry_run=False)
```

#### 主要方法说明

| 方法                       | 参数              | 返回值  | 说明     |
| ------------------------ | --------------- | ---- | ------ |
| `delete_by_id()`         | video\_id       | dict | 按ID删除  |
| `delete_by_title()`      | title, dry\_run | dict | 按标题删除  |
| `delete_by_path()`       | path            | dict | 按路径删除  |
| `delete_missing_files()` | dry\_run        | dict | 删除失效记录 |

### 删除操作影响

删除视频记录会同时删除：

- 视频的基本信息记录
- 视频与标签的关联关系
- 视频的缩略图和GIF记录

**注意**：删除操作不会删除本地视频文件。

***

## 6. update\_video\_paths.py - 视频路径更新工具

### 功能概述

视频路径更新工具用于批量更新数据库中的视频文件路径。当视频文件被移动到新位置时，可以使用此工具快速更新数据库中的路径信息。

### 主要功能

- 扫描本地文件夹获取新路径
- 根据视频标题自动匹配
- 批量更新数据库路径
- 支持模拟运行
- 仅更新路径不存在的记录

### 使用方法

#### 命令行参数

```bash
python update_video_paths.py [选项]
```

| 参数                 | 简写     | 说明          | 默认值   |
| ------------------ | ------ | ----------- | ----- |
| `--search-path`    | `-s`   | 搜索路径        | 必填    |
| `--dry-run`        | <br /> | 模拟运行，不实际更新  | False |
| `--filter-missing` | `-f`   | 仅处理路径不存在的视频 | False |
| `--recursive`      | `-r`   | 递归扫描子文件夹    | True  |

#### 使用示例

**更新所有视频路径：**

```bash
python update_video_paths.py --search-path "D:/NewVideos"
```

**模拟运行（查看将要更新的内容）：**

```bash
python update_video_paths.py --search-path "D:/NewVideos" --dry-run
```

**仅更新路径不存在的视频：**

```bash
python update_video_paths.py --search-path "D:/NewVideos" --filter-missing
```

### 核心类与方法

#### VideoPathUpdater 类

```python
from tools.update_video_paths import VideoPathUpdater

updater = VideoPathUpdater()

# 执行更新
result = updater.run(
    search_path="D:/NewVideos",
    dry_run=False,
    filter_missing=True
)

print(f"更新成功: {result['updated']}")
print(f"跳过: {result['skipped']}")
print(f"错误: {result['errors']}")
```

#### 主要方法说明

| 方法                   | 参数                                      | 返回值  | 说明     |
| -------------------- | --------------------------------------- | ---- | ------ |
| `run()`              | search\_path, dry\_run, filter\_missing | dict | 执行批量更新 |
| `scan_local_files()` | search\_path, recursive                 | dict | 扫描本地文件 |
| `match_videos()`     | db\_videos, local\_files                | dict | 匹配视频记录 |
| `update_paths()`     | matches, dry\_run                       | dict | 更新路径   |

### 匹配逻辑

1. 从数据库获取所有视频记录
2. 扫描指定路径下的所有视频文件
3. 根据文件名（去除扩展名）与视频标题进行匹配
4. 匹配成功则更新路径

### 输出结果说明

```python
{
    'updated': 50,      # 成功更新的数量
    'skipped': 30,      # 跳过的数量（已存在或未匹配）
    'errors': 2,        # 错误数量
    'details': [...]    # 详细信息列表
}
```

***

## 7. optimize\_database\_indexes.py - 数据库索引优化工具

### 功能概述

数据库索引优化工具用于优化数据库性能，通过创建适当的索引来加速常见查询操作。建议在导入大量视频后运行此工具。

### 主要功能

- 分析数据库统计信息
- 创建查询优化索引
- 执行数据库优化命令
- 显示优化前后对比

### 使用方法

#### 命令行参数

```bash
python optimize_database_indexes.py [选项]
```

| 参数               | 简写     | 说明        | 默认值                           |
| ---------------- | ------ | --------- | ----------------------------- |
| `--database`     | `-d`   | 数据库连接字符串  | sqlite:///./video\_library.db |
| `--analyze-only` | <br /> | 仅分析，不创建索引 | False                         |

#### 使用示例

**执行完整优化：**

```bash
python optimize_database_indexes.py
```

**仅分析数据库：**

```bash
python optimize_database_indexes.py --analyze-only
```

**指定数据库路径：**

```bash
python optimize_database_indexes.py --database "sqlite:///D:/data/video_library.db"
```

### 核心函数说明

```python
from tools.optimize_database_indexes import (
    optimize_database,
    analyze_database,
    create_indexes
)

# 执行完整优化
optimize_database(database_url="sqlite:///./video_library.db")

# 仅分析
stats = analyze_database(database_url="sqlite:///./video_library.db")

# 创建索引
create_indexes(database_url="sqlite:///./video_library.db")
```

### 创建的索引

| 表名          | 索引字段              | 说明       |
| ----------- | ----------------- | -------- |
| videos      | title             | 加速标题搜索   |
| videos      | file\_path        | 加速路径查询   |
| videos      | created\_at       | 加速时间排序   |
| tags        | name              | 加速标签名搜索  |
| tags        | level, parent\_id | 加速层级查询   |
| video\_tags | video\_id         | 加速视频标签查询 |
| video\_tags | tag\_id           | 加速标签视频查询 |

### 优化建议

1. **导入后优化**：批量导入视频后运行优化
2. **定期优化**：建议每月运行一次
3. **性能测试**：优化后运行性能测试工具验证效果

***

## 8. test\_database\_performance.py - 数据库性能测试工具

### 功能概述

数据库性能测试工具用于测试和评估数据库查询性能。可以测试优化前后的性能差异，帮助判断优化效果。

### 主要功能

- 随机查询性能测试
- 搜索查询性能测试
- 分页查询性能测试
- 标签关联查询测试
- 性能对比分析

### 使用方法

#### 命令行参数

```bash
python test_database_performance.py [选项]
```

| 参数             | 简写   | 说明        | 默认值   |
| -------------- | ---- | --------- | ----- |
| `--iterations` | `-i` | 每项测试的迭代次数 | 100   |
| `--verbose`    | `-v` | 显示详细输出    | False |

#### 使用示例

**运行默认测试：**

```bash
python test_database_performance.py
```

**指定迭代次数：**

```bash
python test_database_performance.py --iterations 500
```

**详细输出：**

```bash
python test_database_performance.py --verbose
```

### 核心函数说明

```python
from tools.test_database_performance import (
    run_performance_tests,
    test_random_queries,
    test_search_queries,
    test_pagination
)

# 运行所有测试
results = run_performance_tests()

# 单独测试随机查询
result = test_random_queries(iterations=100)

# 单独测试搜索查询
result = test_search_queries(iterations=100)

# 单独测试分页
result = test_pagination(iterations=100)
```

### 测试项目说明

| 测试项目   | 说明         | 评估指标 |
| ------ | ---------- | ---- |
| 随机ID查询 | 随机选择ID进行查询 | 平均耗时 |
| 标题搜索   | 模糊搜索视频标题   | 平均耗时 |
| 标签查询   | 按标签获取视频列表  | 平均耗时 |
| 分页查询   | 大数据量分页性能   | 平均耗时 |
| 关联查询   | 多表关联查询     | 平均耗时 |

### 输出示例

```
=== 数据库性能测试报告 ===

测试配置:
- 迭代次数: 100
- 数据库: video_library.db

测试结果:
┌──────────────────┬────────────┬────────────┬────────────┐
│ 测试项目         │ 平均耗时   │ 最小耗时   │ 最大耗时   │
├──────────────────┼────────────┼────────────┼────────────┤
│ 随机ID查询       │ 0.52ms     │ 0.31ms     │ 1.85ms     │
│ 标题搜索         │ 2.34ms     │ 1.12ms     │ 8.56ms     │
│ 标签查询         │ 1.87ms     │ 0.98ms     │ 5.23ms     │
│ 分页查询         │ 0.89ms     │ 0.45ms     │ 3.21ms     │
│ 关联查询         │ 3.45ms     │ 1.89ms     │ 12.34ms    │
└──────────────────┴────────────┴────────────┴────────────┘

性能评估: 良好
建议: 当前性能表现良好，无需额外优化。
```

### 性能评估标准

| 等级 | 平均查询耗时 | 说明   |
| -- | ------ | ---- |
| 优秀 | < 1ms  | 性能极佳 |
| 良好 | 1-5ms  | 性能正常 |
| 一般 | 5-20ms | 建议优化 |
| 较差 | > 20ms | 需要优化 |

***

## 常见使用场景

### 场景1：初始化新数据库

```bash
# 1. 创建基础标签
python tag_manager.py create --name "电影" --level 1
python tag_manager.py create --name "电视剧" --level 1
python tag_manager.py create --name "纪录片" --level 1

# 2. 导入视频
python video_importer.py --path "D:/Videos/Movies" --tag "电影" --recursive

# 3. 优化数据库
python optimize_database_indexes.py

# 4. 创建初始备份
python backup_database.py create --label "初始化完成"
```

### 场景2：迁移视频文件

```bash
# 1. 创建备份
python backup_database.py create --label "迁移前备份"

# 2. 更新路径
python update_video_paths.py --search-path "D:/NewLocation" --filter-missing

# 3. 清理失效记录
python delete_videos.py missing

# 4. 创建新备份
python backup_database.py create --label "迁移完成"
```

### 场景3：批量编辑标签

```bash
# 1. 查看当前标签
python tag_manager.py list

# 2. 进入交互编辑模式
python video_tag_editor.py interactive

# 3. 合并重复标签
python tag_manager.py merge --source 5 --target 3

# 4. 查看统计
python tag_manager.py stats
```

### 场景4：性能优化流程

```bash
# 1. 测试当前性能
python test_database_performance.py

# 2. 执行优化
python optimize_database_indexes.py

# 3. 再次测试验证
python test_database_performance.py

# 4. 对比优化前后结果
```

***

## 注意事项

1. **备份重要**：在进行批量删除、合并等操作前，务必创建数据库备份
2. **模拟运行**：使用 `--dry-run` 参数可以先预览操作结果，避免误操作
3. **路径格式**：Windows系统建议使用正斜杠 `/` 或双反斜杠 `\\`
4. **编码问题**：确保终端支持UTF-8编码，避免中文显示乱码
5. **并发操作**：避免同时运行多个修改数据库的工具

***

## 技术支持

如遇到问题，请检查：

1. 数据库文件是否存在且可访问
2. Python环境和依赖包是否正确安装
3. 文件路径是否正确
4. 是否有足够的磁盘空间（备份时）

更多详细信息请参考项目主文档或提交Issue。

"""
视频文件管理工具集

本模块提供视频文件管理相关的命令行工具集，包含目录镜像创建和标签索引移动功能。

主要功能：
1. 目录镜像创建：根据源文件夹A的子文件夹结构，在目标文件夹B中创建相同的空文件夹结构
2. 标签索引移动：根据文件名中的标签索引，将视频文件移动到对应的分类文件夹
3. 批量目录镜像创建：在目标文件夹B的每个一级子文件夹内，按照源文件夹A的一级子文件夹结构创建对应的二级空文件夹

使用方式：
    python tools/video_file_manager.py

作者：Video Library System
创建时间：2024
"""
import os
import sys
import shutil


TAG_INDEX_MAP = {
    '_BAOCHAO': ('爆炒', '爆炒'),
    '_666': ('评级', '五星'),
    '_3P': ('类型', '3P'),
    '_FL': ('类型', '正入-躺'),
    '_BK': ('类型', '后入-跪'),
    '_BL': ('类型', '后入-躺'),
    '_BS': ('类型', '后入-站'),
    '_BP': ('类型', '后入-趴'),
    '_GU': ('类型', '女上'),
    '_FS': ('类型', '正入-站'),
    '_HU': ('类型', '抱草'),
    '_FG': ('类型', '前贴玻璃'),
    '_BSW': ('袜子类型', '白丝'),
    '_BTW': ('袜子类型', '白色小腿袜'),
    '_BYW': ('袜子类型', '白色渔网'),
    '_BGX': ('袜子类型', '白色过膝袜'),
    '_HYW': ('袜子类型', '黑色渔网'),
    '_HGX': ('袜子类型', '黑色过膝袜'),
    '_HTW': ('袜子类型', '黑色小腿袜'),
    '_HSW': ('袜子类型', '黑丝'),
    '_RSW': ('袜子类型', '肉丝'),
}

VIDEO_EXTENSIONS = {'.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv', '.webm', '.m4v', '.mpg', '.mpeg', '.3gp', '.ogv'}


def get_folder_path(prompt: str) -> str:
    """
    获取用户输入的文件夹路径，并验证路径是否存在。

    Args:
        prompt: 提示信息

    Returns:
        有效的文件夹路径
    """
    while True:
        path = input(prompt).strip()
        if not path:
            print("路径不能为空，请重新输入。")
            continue
        
        path = path.strip('"').strip("'")
        path = os.path.abspath(path)
        
        if not os.path.exists(path):
            print(f"路径不存在: {path}")
            retry = input("是否重新输入？(y/n): ").strip().lower()
            if retry != 'y':
                print("操作已取消。")
                return None
            continue
        
        if not os.path.isdir(path):
            print(f"路径不是文件夹: {path}")
            retry = input("是否重新输入？(y/n): ").strip().lower()
            if retry != 'y':
                print("操作已取消。")
                return None
            continue
        
        return path


def get_subfolders(root_path: str) -> list:
    """
    递归获取源文件夹中的所有子文件夹相对路径。

    Args:
        root_path: 源文件夹根路径

    Returns:
        子文件夹相对路径列表
    """
    subfolders = []
    
    for dirpath, dirnames, filenames in os.walk(root_path):
        rel_path = os.path.relpath(dirpath, root_path)
        if rel_path != '.':
            subfolders.append(rel_path)
    
    return subfolders


def create_folder_structure(source_path: str, target_path: str) -> tuple:
    """
    根据源文件夹结构在目标文件夹中创建相同的空文件夹结构。

    Args:
        source_path: 源文件夹路径
        target_path: 目标文件夹路径

    Returns:
        (成功创建数量, 跳过数量, 失败数量)
    """
    subfolders = get_subfolders(source_path)
    
    created_count = 0
    skipped_count = 0
    failed_count = 0
    
    for rel_path in subfolders:
        target_folder = os.path.join(target_path, rel_path)
        
        if os.path.exists(target_folder):
            print(f"  [跳过] 文件夹已存在: {rel_path}")
            skipped_count += 1
        else:
            try:
                os.makedirs(target_folder, exist_ok=True)
                print(f"  [创建] {rel_path}")
                created_count += 1
            except Exception as e:
                print(f"  [失败] {rel_path} - 错误: {e}")
                failed_count += 1
    
    return created_count, skipped_count, failed_count


def mirror_folder_structure():
    """
    目录镜像创建功能
    
    根据源文件夹A的子文件夹结构，在目标文件夹B中创建相同的空文件夹结构。
    """
    print("\n" + "=" * 60)
    print("目录镜像创建")
    print("=" * 60)
    print()
    print("本功能将根据源文件夹A的子文件夹结构，")
    print("在目标文件夹B中创建相同的空文件夹结构。")
    print()
    
    print("请输入源文件夹路径A（将复制此文件夹的子文件夹结构）:")
    source_path = get_folder_path("源文件夹路径: ")
    if source_path is None:
        return
    print(f"  已选择: {source_path}")
    print()
    
    print("请输入目标文件夹路径B（将在此创建相同的文件夹结构）:")
    target_path = get_folder_path("目标文件夹路径: ")
    if target_path is None:
        return
    print(f"  已选择: {target_path}")
    print()
    
    if source_path == target_path:
        print("错误：源文件夹和目标文件夹不能相同！")
        return
    
    source_subfolders = get_subfolders(source_path)
    
    if not source_subfolders:
        print("源文件夹中没有子文件夹，无需创建。")
        return
    
    print(f"源文件夹中共有 {len(source_subfolders)} 个子文件夹。")
    print()
    
    print("即将在目标文件夹中创建相同的文件夹结构。")
    confirm = input("确认继续？(y/n): ").strip().lower()
    
    if confirm != 'y':
        print("操作已取消。")
        return
    
    print()
    print("开始创建文件夹结构...")
    print("-" * 60)
    
    created, skipped, failed = create_folder_structure(source_path, target_path)
    
    print("-" * 60)
    print()
    print("操作完成！")
    print(f"  成功创建: {created} 个文件夹")
    print(f"  跳过（已存在）: {skipped} 个文件夹")
    print(f"  失败: {failed} 个文件夹")
    print()


def is_video_file(filename: str) -> bool:
    """
    判断文件是否为视频文件
    
    Args:
        filename: 文件名
        
    Returns:
        bool: 是视频文件返回True，否则返回False
    """
    ext = os.path.splitext(filename)[1].lower()
    return ext in VIDEO_EXTENSIONS


def extract_tags_from_filename(filename: str) -> list:
    """
    从文件名中提取标签索引对应的二级标签名
    
    Args:
        filename: 文件名（不含扩展名）
        
    Returns:
        匹配的二级标签名列表
    """
    matched_level2_tags = []
    
    for index_key, (level1, level2) in TAG_INDEX_MAP.items():
        if index_key in filename:
            matched_level2_tags.append(level2)
    
    return matched_level2_tags


def get_target_folders(target_base_path: str) -> dict:
    """
    获取目标文件夹中的子文件夹映射
    
    Args:
        target_base_path: 目标基础路径
        
    Returns:
        {二级标签名: 文件夹完整路径} 的映射字典
    """
    folder_map = {}
    
    if not os.path.isdir(target_base_path):
        return folder_map
    
    for item in os.listdir(target_base_path):
        item_path = os.path.join(target_base_path, item)
        if os.path.isdir(item_path):
            folder_map[item] = item_path
    
    return folder_map


def move_videos_by_tag_index():
    """
    标签索引移动功能
    
    根据文件名中的标签索引，将视频文件移动到对应的分类文件夹。
    """
    print("\n" + "=" * 60)
    print("标签索引移动")
    print("=" * 60)
    print()
    print("本功能将根据视频文件名中的标签索引，")
    print("将文件移动到对应名称的分类文件夹中。")
    print()
    
    print("支持的标签索引:")
    for index_key, (level1, level2) in TAG_INDEX_MAP.items():
        print(f"  {index_key}: {level1}/{level2}")
    print()
    
    print("请输入视频文件所在文件夹路径A:")
    source_path = get_folder_path("源文件夹路径: ")
    if source_path is None:
        return
    print(f"  已选择: {source_path}")
    print()
    
    print("请输入目标分类文件夹路径B（包含按二级标签命名的子文件夹）:")
    target_path = get_folder_path("目标文件夹路径: ")
    if target_path is None:
        return
    print(f"  已选择: {target_path}")
    print()
    
    target_folders = get_target_folders(target_path)
    if not target_folders:
        print(f"错误：目标文件夹中没有子文件夹！")
        return
    
    print(f"目标文件夹中包含 {len(target_folders)} 个子文件夹:")
    for folder_name in sorted(target_folders.keys()):
        print(f"  - {folder_name}")
    print()
    
    video_files = []
    for item in os.listdir(source_path):
        item_path = os.path.join(source_path, item)
        if os.path.isfile(item_path) and is_video_file(item):
            video_files.append(item_path)
    
    if not video_files:
        print("源文件夹中没有找到视频文件。")
        return
    
    print(f"源文件夹中找到 {len(video_files)} 个视频文件。")
    print()
    
    file_move_plan = []
    unmatched_files = []
    
    for video_file in video_files:
        filename = os.path.basename(video_file)
        name_without_ext = os.path.splitext(filename)[0]
        
        matched_tags = extract_tags_from_filename(name_without_ext)
        
        if matched_tags:
            for tag in matched_tags:
                if tag in target_folders:
                    target_folder = target_folders[tag]
                    target_file = os.path.join(target_folder, filename)
                    file_move_plan.append({
                        'source': video_file,
                        'target': target_file,
                        'tag': tag,
                        'filename': filename
                    })
        else:
            unmatched_files.append(video_file)
    
    if not file_move_plan:
        print("没有找到可以移动的文件（文件名中未检测到有效的标签索引）。")
        return
    
    print("-" * 60)
    print("文件移动计划:")
    print("-" * 60)
    
    move_summary = {}
    for plan in file_move_plan:
        tag = plan['tag']
        if tag not in move_summary:
            move_summary[tag] = []
        move_summary[tag].append(plan['filename'])
    
    for tag, files in sorted(move_summary.items()):
        print(f"\n移动到 [{tag}] 文件夹 ({len(files)} 个文件):")
        for f in files:
            print(f"  - {f}")
    
    if unmatched_files:
        print(f"\n未匹配到标签索引的文件 ({len(unmatched_files)} 个):")
        for f in unmatched_files:
            print(f"  - {os.path.basename(f)}")
    
    print()
    print(f"总计将移动 {len(file_move_plan)} 个文件。")
    confirm = input("确认执行移动操作？(y/n): ").strip().lower()
    
    if confirm != 'y':
        print("操作已取消。")
        return
    
    print()
    print("开始移动文件...")
    print("-" * 60)
    
    success_count = 0
    skip_count = 0
    fail_count = 0
    
    for plan in file_move_plan:
        source_file = plan['source']
        target_file = plan['target']
        filename = plan['filename']
        tag = plan['tag']
        
        if os.path.exists(target_file):
            print(f"  [跳过] 目标已存在: {filename} -> [{tag}]")
            skip_count += 1
        else:
            try:
                shutil.move(source_file, target_file)
                print(f"  [成功] {filename} -> [{tag}]")
                success_count += 1
            except Exception as e:
                print(f"  [失败] {filename} - 错误: {e}")
                fail_count += 1
    
    print("-" * 60)
    print()
    print("移动操作完成！")
    print(f"  成功移动: {success_count} 个文件")
    print(f"  跳过（目标已存在）: {skip_count} 个文件")
    print(f"  失败: {fail_count} 个文件")
    print(f"  未匹配标签: {len(unmatched_files)} 个文件")
    print()


def get_first_level_subfolders(root_path: str) -> list:
    """
    获取指定文件夹中的所有一级子文件夹名称。

    Args:
        root_path: 根文件夹路径

    Returns:
        一级子文件夹名称列表
    """
    subfolders = []
    
    if not os.path.isdir(root_path):
        return subfolders
    
    try:
        for item in os.listdir(root_path):
            item_path = os.path.join(root_path, item)
            if os.path.isdir(item_path):
                subfolders.append(item)
    except PermissionError:
        print(f"  [警告] 无权限访问文件夹: {root_path}")
    except Exception as e:
        print(f"  [错误] 读取文件夹时出错: {root_path} - {e}")
    
    return subfolders


def batch_mirror_folder_structure():
    """
    批量目录镜像创建功能
    
    读取源文件夹A的一级子文件夹结构，
    在目标文件夹B的每个一级子文件夹内创建对应的二级空文件夹。
    """
    print("\n" + "=" * 60)
    print("批量目录镜像创建")
    print("=" * 60)
    print()
    print("本功能将读取源文件夹A的一级子文件夹结构，")
    print("在目标文件夹B的每个一级子文件夹内创建对应的二级空文件夹。")
    print()
    print("示例说明：")
    print("  源文件夹A结构: A/文件夹1, A/文件夹2, A/文件夹3")
    print("  目标文件夹B结构: B/分类X, B/分类Y")
    print("  执行后B的结构: B/分类X/文件夹1, B/分类X/文件夹2, B/分类X/文件夹3")
    print("                B/分类Y/文件夹1, B/分类Y/文件夹2, B/分类Y/文件夹3")
    print()
    
    print("请输入源文件夹路径A（读取此文件夹的一级子文件夹结构）:")
    source_path = get_folder_path("源文件夹路径: ")
    if source_path is None:
        return
    print(f"  已选择: {source_path}")
    print()
    
    print("请输入目标文件夹路径B（在此文件夹的每个一级子文件夹内创建结构）:")
    target_path = get_folder_path("目标文件夹路径: ")
    if target_path is None:
        return
    print(f"  已选择: {target_path}")
    print()
    
    if source_path == target_path:
        print("错误：源文件夹和目标文件夹不能相同！")
        return
    
    source_subfolders = get_first_level_subfolders(source_path)
    
    if not source_subfolders:
        print("源文件夹中没有一级子文件夹，无需创建。")
        return
    
    print(f"源文件夹中共有 {len(source_subfolders)} 个一级子文件夹:")
    for folder in sorted(source_subfolders):
        print(f"  - {folder}")
    print()
    
    target_subfolders = get_first_level_subfolders(target_path)
    
    if not target_subfolders:
        print("目标文件夹中没有一级子文件夹，无法创建二级文件夹结构。")
        return
    
    print(f"目标文件夹中共有 {len(target_subfolders)} 个一级子文件夹:")
    for folder in sorted(target_subfolders):
        print(f"  - {folder}")
    print()
    
    total_to_create = len(source_subfolders) * len(target_subfolders)
    print(f"预计将创建最多 {total_to_create} 个二级文件夹。")
    print()
    
    print("即将开始批量创建文件夹结构。")
    confirm = input("确认继续？(y/n): ").strip().lower()
    
    if confirm != 'y':
        print("操作已取消。")
        return
    
    print()
    print("开始批量创建文件夹结构...")
    print("=" * 60)
    
    total_created = 0
    total_skipped = 0
    total_failed = 0
    
    for target_subfolder in sorted(target_subfolders):
        target_subfolder_path = os.path.join(target_path, target_subfolder)
        
        print()
        print(f"[处理目标文件夹] {target_subfolder}")
        print("-" * 50)
        
        for source_subfolder in sorted(source_subfolders):
            new_folder_path = os.path.join(target_subfolder_path, source_subfolder)
            
            if os.path.exists(new_folder_path):
                print(f"  [跳过] 已存在: {target_subfolder}/{source_subfolder}")
                total_skipped += 1
            else:
                try:
                    os.makedirs(new_folder_path, exist_ok=True)
                    print(f"  [创建] {target_subfolder}/{source_subfolder}")
                    total_created += 1
                except PermissionError:
                    print(f"  [失败] 无权限: {target_subfolder}/{source_subfolder}")
                    total_failed += 1
                except Exception as e:
                    print(f"  [失败] {target_subfolder}/{source_subfolder} - 错误: {e}")
                    total_failed += 1
    
    print()
    print("=" * 60)
    print("批量创建操作完成！")
    print(f"  成功创建: {total_created} 个文件夹")
    print(f"  跳过（已存在）: {total_skipped} 个文件夹")
    print(f"  失败: {total_failed} 个文件夹")
    print()


def show_main_menu():
    """
    显示主菜单界面
    """
    print("\n" + "=" * 60)
    print("视频文件管理工具集")
    print("=" * 60)
    print()
    print("请选择功能:")
    print()
    print("  1. 目录镜像创建")
    print("     - 根据源文件夹结构在目标位置创建相同的空文件夹结构")
    print()
    print("  2. 标签索引移动")
    print("     - 根据文件名中的标签索引将视频文件移动到对应分类文件夹")
    print()
    print("  3. 批量目录镜像创建")
    print("     - 在目标文件夹的每个一级子文件夹内创建源文件夹的一级子文件夹结构")
    print()
    print("  q. 退出程序")
    print()


def main():
    """
    主函数 - 程序入口
    """
    while True:
        try:
            show_main_menu()
            
            choice = input("请输入选项 (1/2/3/q): ").strip().lower()
            
            if choice == 'q':
                print("\n感谢使用，再见！")
                break
            elif choice == '1':
                mirror_folder_structure()
            elif choice == '2':
                move_videos_by_tag_index()
            elif choice == '3':
                batch_mirror_folder_structure()
            else:
                print("无效的选项，请重新选择。")
            
            input("\n按回车键继续...")
            
        except KeyboardInterrupt:
            print("\n\n操作已取消。")
            break
        except Exception as e:
            print(f"\n发生错误: {e}")
            input("\n按回车键继续...")


if __name__ == "__main__":
    main()

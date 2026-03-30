"""
工具API模块

提供视频移动和路径更新等工具功能的API接口。
"""
import os
import shutil
from pathlib import Path
from flask import Blueprint, request
from sqlalchemy import select

from video_tag_system.core.database import get_db_manager
from video_tag_system.models.video import Video
from video_tag_system.models.video_tag import VideoTag
from video_tag_system.models.tag import Tag
from web.auth.decorators import login_required
from web.core.responses import APIResponse
from web.core.errors import handle_exceptions

tools_bp = Blueprint('tools', __name__, url_prefix='/tools')

VIDEO_EXTENSIONS = {
    '.mp4', '.mkv', '.avi', '.wmv', '.mov', '.flv', 
    '.webm', '.m4v', '.mpg', '.mpeg', '.ts', '.m2ts', 
    '.rmvb', '.rm'
}


@tools_bp.route('/move-videos', methods=['POST'])
@login_required
@handle_exceptions
def move_videos():
    """
    根据视频标签移动视频文件
    
    根据视频在库中的标签，将视频文件移动到对应的分类文件夹中。
    系统会检索视频的所有标签，如果标签名与目标文件夹中的子文件夹同名，则移动到该文件夹。
    
    Request Body:
        sourcePath: 视频源文件夹路径
        targetPath: 目标分类文件夹路径
    
    Returns:
        {
            success: true,
            data: {
                moved: [{title, targetFolder, oldPath, newPath}],
                skipped: [{title, reason}],
                errors: [{title, error}]
            }
        }
    """
    try:
        data = request.get_json()
        print(f"[Tools] move_videos called with data: {data}")
        source_path = data.get('sourcePath', '')
        target_path = data.get('targetPath', '')
        print(f"[Tools] source_path: {source_path}, target_path: {target_path}")
        
        if not source_path or not target_path:
            return APIResponse.error('请提供源文件夹和目标文件夹路径', status_code=400)
        
        if not os.path.isdir(source_path):
            return APIResponse.error(f'源文件夹不存在: {source_path}', status_code=400)
        
        if not os.path.isdir(target_path):
            return APIResponse.error(f'目标文件夹不存在: {target_path}', status_code=400)
        
        target_folders = {}
        for item in os.listdir(target_path):
            item_path = os.path.join(target_path, item)
            if os.path.isdir(item_path):
                target_folders[item] = item_path
        
        print(f"[Tools] Found {len(target_folders)} target folders: {list(target_folders.keys())}")
        
        if not target_folders:
            return APIResponse.error('目标文件夹中没有子文件夹', status_code=400)
        
        db_manager = get_db_manager()
        
        moved = []
        skipped = []
        errors = []
        
        with db_manager.get_session() as session:
            videos = session.execute(
                select(Video.id, Video.title, Video.file_path)
            ).all()
            
            video_map = {}
            for vid, title, file_path in videos:
                if title:
                    video_map[title] = {'id': vid, 'title': title, 'file_path': file_path}
            
            print(f"[Tools] Found {len(video_map)} videos in database")
            
            video_tags = session.execute(
                select(VideoTag.video_id, VideoTag.tag_id)
            ).all()
            
            video_tag_map = {}
            for vid, tid in video_tags:
                if vid not in video_tag_map:
                    video_tag_map[vid] = []
                video_tag_map[vid].append(tid)
            
            tags = session.execute(
                select(Tag.id, Tag.name)
            ).all()
            
            tag_map = {tid: name for tid, name in tags}
        
        source_files = os.listdir(source_path)
        print(f"[Tools] Found {len(source_files)} files in source folder")
        
        for item in source_files:
            item_path = os.path.join(source_path, item)
            
            if not os.path.isfile(item_path):
                continue
            
            ext = os.path.splitext(item)[1].lower()
            if ext not in VIDEO_EXTENSIONS:
                continue
            
            title = os.path.splitext(item)[0]
            
            if title not in video_map:
                skipped.append({'title': title, 'reason': '不在视频库中'})
                continue
            
            video_info = video_map[title]
            video_id = video_info['id']
            
            if video_id not in video_tag_map or not video_tag_map[video_id]:
                skipped.append({'title': title, 'reason': '没有关联标签'})
                continue
            
            tag_ids = video_tag_map[video_id]
            tag_names = [tag_map.get(tid, '') for tid in tag_ids]
            
            target_folder = None
            target_folder_name = None
            for tag_name in tag_names:
                if tag_name in target_folders:
                    target_folder = target_folders[tag_name]
                    target_folder_name = tag_name
                    break
            
            if not target_folder:
                skipped.append({'title': title, 'reason': '标签与目标文件夹不匹配'})
                continue
            
            new_path = os.path.join(target_folder, item)
            
            if os.path.exists(new_path):
                skipped.append({'title': title, 'reason': '目标位置已存在同名文件'})
                continue
            
            try:
                shutil.move(item_path, new_path)
                
                with db_manager.get_session() as session:
                    video = session.get(Video, video_id)
                    if video:
                        video.file_path = new_path
                
                moved.append({
                    'title': title,
                    'targetFolder': target_folder_name,
                    'oldPath': item_path,
                    'newPath': new_path
                })
                print(f"[Tools] Moved: {title} -> {target_folder_name}")
            except Exception as e:
                errors.append({'title': title, 'error': str(e)})
                print(f"[Tools] Error moving {title}: {e}")
        
        print(f"[Tools] Move completed: moved={len(moved)}, skipped={len(skipped)}, errors={len(errors)}")
        
    except Exception as e:
        print(f"[Tools] Exception in move_videos: {e}")
        import traceback
        traceback.print_exc()
        return APIResponse.error(f'执行失败: {str(e)}', status_code=500)
    
    return APIResponse.success({
        'moved': moved,
        'skipped': skipped,
        'errors': errors
    })


@tools_bp.route('/update-paths', methods=['POST'])
@login_required
@handle_exceptions
def update_paths():
    """
    更新视频库中的文件路径
    
    扫描指定文件夹中的视频文件，根据文件名匹配数据库中的视频记录，并更新其文件路径。
    
    Request Body:
        searchPath: 搜索路径
    
    Returns:
        {
            success: true,
            data: {
                updated: [{title, oldPath, newPath}],
                notFound: [{title}]
            }
        }
    """
    try:
        data = request.get_json()
        print(f"[Tools] update_paths called with data: {data}")
        search_path = data.get('searchPath', '')
        print(f"[Tools] search_path: {search_path}")
        
        if not search_path:
            return APIResponse.error('请提供搜索路径', status_code=400)
        
        if not os.path.isdir(search_path):
            return APIResponse.error(f'搜索路径不存在: {search_path}', status_code=400)
        
        local_videos = {}
        for ext in VIDEO_EXTENSIONS:
            for file_path in Path(search_path).rglob(f"*{ext}"):
                name_without_ext = file_path.stem
                if name_without_ext not in local_videos:
                    local_videos[name_without_ext] = str(file_path)
        
        print(f"[Tools] Found {len(local_videos)} video files in search path")
        
        db_manager = get_db_manager()
        updated = []
        not_found = []
        
        with db_manager.get_session() as session:
            videos = session.execute(
                select(Video.id, Video.title, Video.file_path)
            ).all()
            
            print(f"[Tools] Found {len(videos)} videos in database")
            
            for vid, title, current_path in videos:
                if not title:
                    continue
                
                if title in local_videos:
                    new_path = local_videos[title]
                    
                    if current_path != new_path:
                        video = session.get(Video, vid)
                        if video:
                            video.file_path = new_path
                            updated.append({
                                'title': title,
                                'oldPath': current_path,
                                'newPath': new_path
                            })
                else:
                    not_found.append({'title': title})
        
        print(f"[Tools] Update completed: updated={len(updated)}, notFound={len(not_found)}")
        
    except Exception as e:
        print(f"[Tools] Exception in update_paths: {e}")
        import traceback
        traceback.print_exc()
        return APIResponse.error(f'执行失败: {str(e)}', status_code=500)
    
    return APIResponse.success({
        'updated': updated,
        'notFound': not_found
    })

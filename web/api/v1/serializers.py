import os
from typing import List, Dict, Any, Optional


def serialize_video(video, thumbnail_gen=None) -> Dict[str, Any]:
    from video_tag_system.utils.thumbnail_generator import get_thumbnail_generator
    if thumbnail_gen is None:
        thumbnail_gen = get_thumbnail_generator()

    video_title = video.title or os.path.basename(video.file_path)
    thumbnail = video.thumbnail_url or thumbnail_gen.get_thumbnail_url(video_title)
    gif = video.gif_url if video.gif_url is not None else thumbnail_gen.get_gif_url(video_title)

    return {
        'id': video.id,
        'title': video_title,
        'file_ext': os.path.splitext(video.file_path)[1].lower() if video.file_path else '',
        'duration': video.duration,
        'tags': [{'id': t.id, 'name': t.name, 'parent_id': t.parent_id} for t in video.tags],
        'thumbnail': thumbnail,
        'gif': gif
    }


def serialize_video_detail(video, thumbnail_gen=None) -> Dict[str, Any]:
    from video_tag_system.utils.thumbnail_generator import get_thumbnail_generator
    if thumbnail_gen is None:
        thumbnail_gen = get_thumbnail_generator()

    video_title = video.title or os.path.basename(video.file_path)
    thumbnail = video.thumbnail_url or thumbnail_gen.get_thumbnail_url(video_title)
    gif = video.gif_url if video.gif_url is not None else thumbnail_gen.get_gif_url(video_title)

    return {
        'id': video.id,
        'title': video_title,
        'file_ext': os.path.splitext(video.file_path)[1].lower() if video.file_path else '',
        'duration': video.duration,
        'description': video.description,
        'tags': [{'id': t.id, 'name': t.name, 'parent_id': t.parent_id} for t in video.tags],
        'thumbnail': thumbnail,
        'gif': gif
    }


def serialize_video_list(videos, thumbnail_gen=None) -> List[Dict[str, Any]]:
    return [serialize_video(v, thumbnail_gen) for v in videos]


def serialize_paginated_videos(result, thumbnail_gen=None) -> Dict[str, Any]:
    videos = serialize_video_list(result.items, thumbnail_gen)
    return {
        'videos': videos,
        'total': result.total,
        'page': result.page,
        'page_size': result.page_size,
        'total_pages': result.total_pages
    }

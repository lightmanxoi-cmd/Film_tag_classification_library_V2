import { videoService } from '../services/video.js';
import { showToast } from '../components/toast.js';
import { videoPlayerManager } from './video-player-manager.js';

export async function playVideo(videoIdOrVideo, title, tags) {
    try {
        let videoId, videoTags;

        if (typeof videoIdOrVideo === 'object' && videoIdOrVideo !== null) {
            videoId = videoIdOrVideo.id;
            videoTags = videoIdOrVideo.tags;
        } else {
            videoId = videoIdOrVideo;
            videoTags = tags;
        }

        const data = await videoService.getVideoStreamUrl(videoId);
        const fileExt = data.file_ext || '.mp4';

        videoPlayerManager.play(data.stream_url, fileExt, videoTags, data);
    } catch (error) {
        console.error('获取视频信息失败:', error);
        showToast('无法播放视频: ' + error.message, 'error');
    }
}

export function closeVideoModal() {
    videoPlayerManager.close();
}

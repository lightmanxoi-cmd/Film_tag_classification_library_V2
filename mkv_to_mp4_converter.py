"""
MKV转MP4批量转换工具
递归扫描文件夹中的MKV文件并转换为MP4格式
保持原视频品质，在原路径替换原文件
"""
import os
import sys
import subprocess
import json
import argparse
from pathlib import Path
from typing import List, Tuple, Optional, Dict
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
import time


class MKVtoMP4Converter:
    """MKV转MP4转换器"""
    
    def __init__(
        self,
        max_workers: int = 1,
        preserve_quality: bool = True,
        overwrite: bool = False,
        verbose: bool = True
    ):
        self.max_workers = max_workers
        self.preserve_quality = preserve_quality
        self.overwrite = overwrite
        self.verbose = verbose
        self._lock = threading.Lock()
        self._stop_flag = threading.Event()
        self.results = {
            'success': [],
            'failed': [],
            'skipped': [],
            'total_size_saved': 0
        }
    
    def find_mkv_files(self, root_path: str) -> List[Path]:
        """递归查找所有MKV文件"""
        root = Path(root_path)
        if not root.exists():
            raise FileNotFoundError(f"路径不存在: {root_path}")
        
        mkv_files = list(root.rglob("*.mkv"))
        return sorted(mkv_files)
    
    def get_video_info(self, file_path: Path) -> Optional[Dict]:
        """获取视频文件信息"""
        try:
            cmd = [
                'ffprobe',
                '-v', 'quiet',
                '-print_format', 'json',
                '-show_format',
                '-show_streams',
                str(file_path)
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            )
            
            if result.returncode == 0:
                stdout = result.stdout.decode('utf-8', errors='replace')
                return json.loads(stdout)
            return None
        except Exception as e:
            if self.verbose:
                print(f"获取视频信息失败: {e}")
            return None
    
    def analyze_streams(self, video_info: Dict) -> Dict:
        """分析视频流，判断是否可以直接复制"""
        analysis = {
            'video_codec': None,
            'audio_codec': None,
            'can_copy_video': False,
            'can_copy_audio': False,
            'needs_conversion': True
        }
        
        for stream in video_info.get('streams', []):
            codec_type = stream.get('codec_type')
            codec_name = stream.get('codec_name', '')
            
            if codec_type == 'video':
                analysis['video_codec'] = codec_name
                if codec_name in ['h264', 'hevc', 'h265', 'mpeg4', 'vp9', 'av1']:
                    analysis['can_copy_video'] = True
                    
            elif codec_type == 'audio':
                analysis['audio_codec'] = codec_name
                if codec_name in ['aac', 'mp3', 'ac3', 'eac3', 'opus']:
                    analysis['can_copy_audio'] = True
        
        if analysis['can_copy_video'] and analysis['can_copy_audio']:
            analysis['needs_conversion'] = False
        
        return analysis
    
    def build_ffmpeg_command(
        self,
        input_path: Path,
        output_path: Path,
        analysis: Dict
    ) -> List[str]:
        """构建FFmpeg命令"""
        cmd = ['ffmpeg', '-y', '-i', str(input_path)]
        
        if not analysis['needs_conversion'] and self.preserve_quality:
            cmd.extend(['-c', 'copy'])
        else:
            if analysis['can_copy_video']:
                cmd.extend(['-c:v', 'copy'])
            else:
                cmd.extend([
                    '-c:v', 'libx264',
                    '-preset', 'slow',
                    '-crf', '18',
                    '-pix_fmt', 'yuv420p'
                ])
            
            if analysis['can_copy_audio']:
                cmd.extend(['-c:a', 'copy'])
            else:
                cmd.extend([
                    '-c:a', 'aac',
                    '-b:a', '320k'
                ])
        
        cmd.extend(['-movflags', '+faststart'])
        cmd.append(str(output_path))
        
        return cmd
    
    def convert_file(self, mkv_path: Path) -> Tuple[bool, str, int]:
        """
        转换单个MKV文件为MP4
        
        Returns:
            (success, message, size_diff)
        """
        if self._stop_flag.is_set():
            return False, "转换已取消", 0
        
        mp4_path = mkv_path.with_suffix('.mp4')
        temp_path = mkv_path.with_name(mkv_path.stem + '.tmp.mp4')
        
        if mp4_path.exists() and not self.overwrite:
            return False, f"目标文件已存在: {mp4_path}", 0
        
        video_info = self.get_video_info(mkv_path)
        if not video_info:
            return False, "无法读取视频信息", 0
        
        analysis = self.analyze_streams(video_info)
        
        original_size = mkv_path.stat().st_size
        
        cmd = self.build_ffmpeg_command(mkv_path, temp_path, analysis)
        
        if self.verbose:
            codec_info = f"视频:{analysis['video_codec']}, 音频:{analysis['audio_codec']}"
            mode = "复制流" if not analysis['needs_conversion'] else "转码"
            print(f"  [{mode}] {codec_info}")
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            )
            
            if result.returncode != 0:
                if temp_path.exists():
                    temp_path.unlink()
                stderr = result.stderr.decode('utf-8', errors='replace')[-500:] if result.stderr else "未知错误"
                return False, f"FFmpeg错误: {stderr}", 0
            
            if not temp_path.exists():
                return False, "输出文件未生成", 0
            
            new_size = temp_path.stat().st_size
            
            mkv_path.unlink()
            
            temp_path.rename(mp4_path)
            
            size_diff = original_size - new_size
            
            return True, f"转换成功: {mkv_path.name} -> {mp4_path.name}", size_diff
            
        except Exception as e:
            if temp_path.exists():
                temp_path.unlink()
            return False, f"转换异常: {e}", 0
    
    def convert_folder(
        self,
        folder_path: str,
        pattern: str = None
    ) -> Dict:
        """
        批量转换文件夹中的MKV文件
        
        Args:
            folder_path: 目标文件夹路径
            pattern: 文件名匹配模式（可选）
            
        Returns:
            转换结果统计
        """
        print(f"\n{'='*60}")
        print(f"MKV转MP4批量转换工具")
        print(f"{'='*60}")
        print(f"目标文件夹: {folder_path}")
        
        mkv_files = self.find_mkv_files(folder_path)
        
        if pattern:
            import fnmatch
            mkv_files = [f for f in mkv_files if fnmatch.fnmatch(f.name, pattern)]
        
        if not mkv_files:
            print("未找到MKV文件")
            return self.results
        
        print(f"找到 {len(mkv_files)} 个MKV文件")
        print(f"并发数: {self.max_workers}")
        print(f"{'='*60}\n")
        
        start_time = time.time()
        
        if self.max_workers > 1:
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                futures = {
                    executor.submit(self.convert_file, mkv): mkv
                    for mkv in mkv_files
                }
                
                for i, future in enumerate(as_completed(futures), 1):
                    if self._stop_flag.is_set():
                        executor.shutdown(wait=False)
                        break
                    
                    mkv = futures[future]
                    try:
                        success, msg, size_diff = future.result()
                        with self._lock:
                            if success:
                                self.results['success'].append(str(mkv))
                                self.results['total_size_saved'] += size_diff
                                status = "✓"
                            else:
                                self.results['failed'].append((str(mkv), msg))
                                status = "✗"
                        
                        print(f"[{i}/{len(mkv_files)}] {status} {mkv.name}")
                        if not success and self.verbose:
                            print(f"    {msg}")
                            
                    except Exception as e:
                        with self._lock:
                            self.results['failed'].append((str(mkv), str(e)))
                        print(f"[{i}/{len(mkv_files)}] ✗ {mkv.name}")
                        print(f"    异常: {e}")
        else:
            for i, mkv in enumerate(mkv_files, 1):
                if self._stop_flag.is_set():
                    break
                
                print(f"\n[{i}/{len(mkv_files)}] 处理: {mkv}")
                success, msg, size_diff = self.convert_file(mkv)
                
                if success:
                    self.results['success'].append(str(mkv))
                    self.results['total_size_saved'] += size_diff
                    print(f"  ✓ {msg}")
                else:
                    self.results['failed'].append((str(mkv), msg))
                    print(f"  ✗ {msg}")
        
        elapsed = time.time() - start_time
        
        print(f"\n{'='*60}")
        print("转换完成!")
        print(f"{'='*60}")
        print(f"成功: {len(self.results['success'])} 个")
        print(f"失败: {len(self.results['failed'])} 个")
        print(f"节省空间: {self._format_size(self.results['total_size_saved'])}")
        print(f"耗时: {elapsed:.1f} 秒")
        
        if self.results['failed']:
            print(f"\n失败文件列表:")
            for path, msg in self.results['failed']:
                print(f"  - {Path(path).name}: {msg}")
        
        return self.results
    
    def _format_size(self, size_bytes: int) -> str:
        """格式化文件大小"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if abs(size_bytes) < 1024:
                return f"{size_bytes:.2f} {unit}"
            size_bytes /= 1024
        return f"{size_bytes:.2f} TB"
    
    def stop(self):
        """停止转换"""
        self._stop_flag.set()


def main():
    parser = argparse.ArgumentParser(
        description='MKV转MP4批量转换工具 - 保持原品质，原地替换',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
示例:
  python mkv_to_mp4_converter.py "D:\\Videos"
  python mkv_to_mp4_converter.py "D:\\Videos" --workers 2
  python mkv_to_mp4_converter.py "D:\\Videos" --overwrite
  python mkv_to_mp4_converter.py "D:\\Videos" --pattern "*电影*"
        '''
    )
    
    parser.add_argument(
        'folder',
        help='要转换的文件夹路径'
    )
    parser.add_argument(
        '-w', '--workers',
        type=int,
        default=1,
        help='并发转换数（默认1，建议不超过4）'
    )
    parser.add_argument(
        '-o', '--overwrite',
        action='store_true',
        help='覆盖已存在的MP4文件'
    )
    parser.add_argument(
        '-p', '--pattern',
        help='文件名匹配模式（如 "*电影*"）'
    )
    parser.add_argument(
        '-q', '--quiet',
        action='store_true',
        help='安静模式，减少输出'
    )
    parser.add_argument(
        '--no-preserve',
        action='store_true',
        help='不保持品质（允许重新编码）'
    )
    
    args = parser.parse_args()
    
    try:
        subprocess.run(
            ['ffmpeg', '-version'],
            capture_output=True,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        )
    except FileNotFoundError:
        print("错误: 未找到FFmpeg，请先安装FFmpeg并添加到系统PATH")
        sys.exit(1)
    
    converter = MKVtoMP4Converter(
        max_workers=args.workers,
        preserve_quality=not args.no_preserve,
        overwrite=args.overwrite,
        verbose=not args.quiet
    )
    
    try:
        converter.convert_folder(args.folder, args.pattern)
    except KeyboardInterrupt:
        print("\n\n用户取消转换...")
        converter.stop()
        sys.exit(0)
    except Exception as e:
        print(f"\n错误: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()

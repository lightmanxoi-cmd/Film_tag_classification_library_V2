"""
测试工具函数
"""
import pytest
import tempfile
import os
from video_tag_system.utils.validators import (
    validate_file_path,
    validate_tag_name,
    validate_video_data,
    validate_tag_data,
)
from video_tag_system.utils.helpers import (
    format_file_size,
    format_duration,
    parse_duration,
    sanitize_filename,
    get_file_extension,
    is_video_file,
)
from video_tag_system.exceptions import ValidationError


class TestValidators:
    """验证器测试类"""
    
    def test_validate_file_path(self):
        """测试文件路径验证"""
        assert validate_file_path("/videos/test.mp4") == "/videos/test.mp4"
        assert validate_file_path("  /videos/test.mp4  ") == "/videos/test.mp4"
    
    def test_validate_file_path_empty(self):
        """测试空文件路径"""
        with pytest.raises(ValidationError):
            validate_file_path("")
        
        with pytest.raises(ValidationError):
            validate_file_path("   ")
    
    def test_validate_file_path_too_long(self):
        """测试过长的文件路径"""
        long_path = "/videos/" + "a" * 600 + ".mp4"
        with pytest.raises(ValidationError):
            validate_file_path(long_path)
    
    def test_validate_tag_name(self):
        """测试标签名称验证"""
        assert validate_tag_name("动作") == "动作"
        assert validate_tag_name("  喜剧  ") == "喜剧"
    
    def test_validate_tag_name_empty(self):
        """测试空标签名称"""
        with pytest.raises(ValidationError):
            validate_tag_name("")
    
    def test_validate_tag_name_too_long(self):
        """测试过长的标签名称"""
        long_name = "a" * 60
        with pytest.raises(ValidationError):
            validate_tag_name(long_name)
    
    def test_validate_tag_name_only_numbers(self):
        """测试只有数字的标签名称"""
        with pytest.raises(ValidationError):
            validate_tag_name("123")


class TestHelpers:
    """辅助函数测试类"""
    
    def test_format_file_size(self):
        """测试文件大小格式化"""
        assert format_file_size(0) == "0 B"
        assert format_file_size(1023) == "1023 B"
        assert format_file_size(1024) == "1.00 KB"
        assert format_file_size(1024 * 1024) == "1.00 MB"
        assert format_file_size(1024 * 1024 * 1024) == "1.00 GB"
    
    def test_format_file_size_none(self):
        """测试空文件大小"""
        assert format_file_size(None) == "未知"
    
    def test_format_duration(self):
        """测试时长格式化"""
        assert format_duration(0) == "0:00"
        assert format_duration(59) == "0:59"
        assert format_duration(60) == "1:00"
        assert format_duration(3599) == "59:59"
        assert format_duration(3600) == "1:00:00"
        assert format_duration(3661) == "1:01:01"
    
    def test_format_duration_none(self):
        """测试空时长"""
        assert format_duration(None) == "未知"
    
    def test_parse_duration(self):
        """测试时长解析"""
        assert parse_duration("90") == 90
        assert parse_duration("1:30") == 90
        assert parse_duration("1:30:00") == 5400
        assert parse_duration("1h30m") == 5400
        assert parse_duration("90m") == 5400
        assert parse_duration("3600s") == 3600
    
    def test_sanitize_filename(self):
        """测试文件名清理"""
        assert sanitize_filename("normal.mp4") == "normal.mp4"
        assert sanitize_filename("test<>:\"/\\|?*.mp4") == "test_________.mp4"
        assert sanitize_filename("  test  ") == "test"
    
    def test_get_file_extension(self):
        """测试获取文件扩展名"""
        assert get_file_extension("/videos/test.mp4") == "mp4"
        assert get_file_extension("/videos/test.MKV") == "mkv"
        assert get_file_extension("no_extension") == ""
    
    def test_is_video_file(self):
        """测试视频文件判断"""
        assert is_video_file("/videos/test.mp4") is True
        assert is_video_file("/videos/test.avi") is True
        assert is_video_file("/videos/test.txt") is False
        assert is_video_file("/videos/test.jpg") is False


class TestGenerateFileHash:
    """文件哈希测试类"""
    
    def test_generate_file_hash(self):
        """测试生成文件哈希"""
        from video_tag_system.utils.helpers import generate_file_hash
        
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
            f.write("test content")
            temp_path = f.name
        
        try:
            md5_hash = generate_file_hash(temp_path, "md5")
            assert len(md5_hash) == 32
            
            sha256_hash = generate_file_hash(temp_path, "sha256")
            assert len(sha256_hash) == 64
        finally:
            os.unlink(temp_path)
    
    def test_generate_file_hash_nonexistent(self):
        """测试不存在的文件哈希"""
        from video_tag_system.utils.helpers import generate_file_hash
        
        with pytest.raises(FileNotFoundError):
            generate_file_hash("/nonexistent/file.txt")

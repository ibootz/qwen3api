"""
配置验证模块
提供配置项验证和环境检查功能
"""
import re
import logging
from typing import List, Dict, Any, Optional
from pathlib import Path

logger = logging.getLogger(__name__)


class ConfigValidator:
    """配置验证器"""
    
    @staticmethod
    def validate_token_group(token_group: Dict[str, str]) -> bool:
        """
        验证token组配置
        
        Args:
            token_group: token组配置字典
            
        Returns:
            bool: 验证是否通过
        """
        required_fields = ["token", "bx_ua", "bx_umidtoken"]
        
        for field in required_fields:
            if field not in token_group:
                logger.error(f"Token组缺少必需字段: {field}")
                return False
            
            if not isinstance(token_group[field], str) or not token_group[field].strip():
                logger.error(f"Token组字段 {field} 必须是非空字符串")
                return False
        
        # 验证token格式（JWT格式）
        token = token_group["token"]
        if not re.match(r'^[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+$', token):
            logger.warning(f"Token格式可能不正确，不符合JWT格式: {token[:20]}...")
        
        return True
    
    @staticmethod
    def validate_token_groups(token_groups: List[Dict[str, str]]) -> bool:
        """
        验证所有token组配置
        
        Args:
            token_groups: token组列表
            
        Returns:
            bool: 验证是否通过
        """
        if not token_groups:
            logger.error("未配置任何token组")
            return False
        
        valid_count = 0
        for i, token_group in enumerate(token_groups):
            if ConfigValidator.validate_token_group(token_group):
                valid_count += 1
            else:
                logger.error(f"Token组 {i} 验证失败")
        
        if valid_count == 0:
            logger.error("没有有效的token组")
            return False
        
        logger.info(f"验证完成，{valid_count}/{len(token_groups)} 个token组有效")
        return True
    
    @staticmethod
    def validate_port(port: int) -> bool:
        """
        验证端口配置
        
        Args:
            port: 端口号
            
        Returns:
            bool: 验证是否通过
        """
        if not isinstance(port, int):
            logger.error(f"端口必须是整数: {port}")
            return False
        
        if port < 1 or port > 65535:
            logger.error(f"端口号必须在1-65535范围内: {port}")
            return False
        
        if port < 1024:
            logger.warning(f"使用系统端口 {port}，可能需要管理员权限")
        
        return True
    
    @staticmethod
    def validate_url(url: str, field_name: str = "URL") -> bool:
        """
        验证URL格式
        
        Args:
            url: URL字符串
            field_name: 字段名称（用于错误信息）
            
        Returns:
            bool: 验证是否通过
        """
        if not isinstance(url, str) or not url.strip():
            logger.error(f"{field_name} 必须是非空字符串")
            return False
        
        url_pattern = re.compile(
            r'^https?://'  # http:// 或 https://
            r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # 域名
            r'localhost|'  # localhost
            r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # IP地址
            r'(?::\d+)?'  # 可选端口
            r'(?:/?|[/?]\S+)$', re.IGNORECASE)
        
        if not url_pattern.match(url):
            logger.error(f"{field_name} 格式不正确: {url}")
            return False
        
        return True
    
    @staticmethod
    def validate_log_level(log_level: str) -> bool:
        """
        验证日志级别
        
        Args:
            log_level: 日志级别字符串
            
        Returns:
            bool: 验证是否通过
        """
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        
        if log_level.upper() not in valid_levels:
            logger.error(f"无效的日志级别: {log_level}，有效值: {valid_levels}")
            return False
        
        return True


class EnvironmentChecker:
    """环境检查器"""
    
    @staticmethod
    def check_python_version() -> bool:
        """检查Python版本"""
        import sys
        
        required_version = (3, 12)
        current_version = sys.version_info[:2]
        
        if current_version < required_version:
            logger.error(f"Python版本过低，需要 {required_version[0]}.{required_version[1]}+，当前版本: {current_version[0]}.{current_version[1]}")
            return False
        
        logger.info(f"Python版本检查通过: {current_version[0]}.{current_version[1]}")
        return True
    
    @staticmethod
    def check_dependencies() -> bool:
        """检查依赖包"""
        required_packages = [
            "fastapi",
            "uvicorn", 
            "httpx",
            "python-dotenv",
            "yaml"
        ]
        
        missing_packages = []
        
        for package in required_packages:
            try:
                __import__(package)
                logger.debug(f"依赖包检查通过: {package}")
            except ImportError:
                missing_packages.append(package)
                logger.error(f"缺少依赖包: {package}")
        
        if missing_packages:
            logger.error(f"缺少以下依赖包: {missing_packages}")
            return False
        
        logger.info("所有依赖包检查通过")
        return True
    
    @staticmethod
    def check_config_file(config_file: str) -> bool:
        """检查配置文件"""
        config_path = Path(config_file)
        
        if not config_path.exists():
            logger.warning(f"配置文件不存在: {config_file}")
            return False
        
        if not config_path.is_file():
            logger.error(f"配置路径不是文件: {config_file}")
            return False
        
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                content = f.read()
                if not content.strip():
                    logger.warning(f"配置文件为空: {config_file}")
                    return False
        except Exception as e:
            logger.error(f"读取配置文件失败: {config_file} - {e}")
            return False
        
        logger.info(f"配置文件检查通过: {config_file}")
        return True
    
    @staticmethod
    def check_log_directory(log_file: str) -> bool:
        """检查日志目录"""
        log_path = Path(log_file)
        log_dir = log_path.parent
        
        if not log_dir.exists():
            try:
                log_dir.mkdir(parents=True, exist_ok=True)
                logger.info(f"创建日志目录: {log_dir}")
            except Exception as e:
                logger.error(f"创建日志目录失败: {log_dir} - {e}")
                return False
        
        # 检查写入权限
        try:
            test_file = log_dir / "test_write_permission.tmp"
            test_file.write_text("test")
            test_file.unlink()
            logger.debug(f"日志目录写入权限检查通过: {log_dir}")
        except Exception as e:
            logger.error(f"日志目录无写入权限: {log_dir} - {e}")
            return False
        
        return True
    
    @staticmethod
    def run_all_checks(config_file: str, log_file: str) -> bool:
        """运行所有环境检查"""
        checks = [
            ("Python版本", EnvironmentChecker.check_python_version),
            ("依赖包", EnvironmentChecker.check_dependencies),
            ("配置文件", lambda: EnvironmentChecker.check_config_file(config_file)),
            ("日志目录", lambda: EnvironmentChecker.check_log_directory(log_file)),
        ]
        
        failed_checks = []
        
        for check_name, check_func in checks:
            try:
                if not check_func():
                    failed_checks.append(check_name)
            except Exception as e:
                logger.error(f"{check_name}检查出错: {e}")
                failed_checks.append(check_name)
        
        if failed_checks:
            logger.error(f"以下检查失败: {failed_checks}")
            return False
        
        logger.info("所有环境检查通过")
        return True

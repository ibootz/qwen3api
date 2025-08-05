"""
配置管理模块
负责加载和管理应用配置，支持YAML文件和环境变量
"""
import os
import json
import yaml
import logging
from typing import Dict, List, Any
from pathlib import Path

logger = logging.getLogger(__name__)

class Config:
    """配置管理类"""
    
    def __init__(self):
        self.qwen_token_groups: List[Dict[str, str]] = []
        self.qwen_api_base_url: str = "https://chat.qwen.ai/api/v2"
        self.port: int = 8220
        self.qwen_bx_v: str = "2.5.31"
        self.qwen_source: str = "web"
        self.qwen_timezone: str = "Asia/Shanghai"
        self.log_level: str = "DEBUG"
        self.log_file: str = "logs/qwen_api.log"
        self.config_file: str = "config.yaml"
        
    def load_config(self) -> None:
        """加载配置文件"""
        # 加载环境变量
        self._load_env_config()
        
        # 优先加载YAML配置文件
        self._load_yaml_config()
        
        # 验证配置
        self._validate_config()
        
        logger.info(f"配置加载完成，共加载 {len(self.qwen_token_groups)} 个 token 组")
    
    def _load_env_config(self) -> None:
        """从环境变量加载配置"""
        self.port = int(os.getenv("PORT", self.port))
        self.qwen_api_base_url = os.getenv("QWEN_API_BASE_URL", self.qwen_api_base_url)
        self.qwen_bx_v = os.getenv("QWEN_BX_V", self.qwen_bx_v)
        self.qwen_source = os.getenv("QWEN_SOURCE", self.qwen_source)
        self.qwen_timezone = os.getenv("QWEN_TIMEZONE", self.qwen_timezone)
        self.log_level = os.getenv("LOG_LEVEL", self.log_level)
        self.log_file = os.getenv("LOG_FILE", self.log_file)
        self.config_file = os.getenv("CONFIG_FILE", self.config_file)
        
        # 从环境变量加载token组（兼容旧格式）
        self._load_token_groups_from_env()
    
    def _load_yaml_config(self) -> None:
        """从YAML配置文件加载配置"""
        config_file_path = Path(self.config_file)
        
        if not config_file_path.exists():
            logger.info(f"配置文件 {self.config_file} 不存在，跳过")
            return
            
        try:
            with open(config_file_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            
            logger.info(f"成功加载 YAML 配置文件: {self.config_file}")
            
            # 更新配置
            if 'qwen_token_groups' in config and config['qwen_token_groups']:
                self.qwen_token_groups = config['qwen_token_groups']
                logger.info(f"从 YAML 配置中加载了 {len(self.qwen_token_groups)} 个 token 组")
            
            # 更新其他配置
            config_mapping = {
                'qwen_api_base_url': 'qwen_api_base_url',
                'port': 'port',
                'qwen_bx_v': 'qwen_bx_v',
                'qwen_source': 'qwen_source',
                'qwen_timezone': 'qwen_timezone',
                'log_level': 'log_level',
                'log_file': 'log_file'
            }
            
            for yaml_key, attr_name in config_mapping.items():
                if yaml_key in config:
                    setattr(self, attr_name, config[yaml_key])
                    logger.debug(f"更新配置: {yaml_key} = {config[yaml_key]}")
                    
        except Exception as e:
            logger.error(f"加载 YAML 配置文件失败: {e}")
    
    def _load_token_groups_from_env(self) -> None:
        """从环境变量加载token组（兼容旧格式）"""
        if self.qwen_token_groups:  # 如果YAML已加载，跳过
            return
            
        # 检查新的环境变量格式
        tokens_env = os.getenv("QWEN_TOKENS")
        if tokens_env:
            try:
                # 支持JSON格式
                if tokens_env.strip().startswith('['):
                    self.qwen_token_groups = json.loads(tokens_env)
                else:
                    # 支持管道符分隔格式
                    token_groups = []
                    for group_str in tokens_env.split(','):
                        parts = group_str.strip().split('|')
                        if len(parts) >= 1:
                            token_groups.append({
                                'token': parts[0].strip()
                            })
                    self.qwen_token_groups = token_groups
                    
                logger.info(f"从环境变量加载了 {len(self.qwen_token_groups)} 个 token 组")
            except Exception as e:
                logger.error(f"解析环境变量 QWEN_TOKENS 失败: {e}")
    
    def _validate_config(self) -> None:
        """验证配置有效性"""
        if not self.qwen_token_groups:
            logger.warning("未配置任何 token 组，服务可能无法正常工作")
            return
            
        # 验证每个token组的完整性
        for i, group in enumerate(self.qwen_token_groups):
            required_fields = ['token']
            for field in required_fields:
                if field not in group or not group[field]:
                    logger.error(f"第 {i+1} 个 token 组缺少必需字段: {field}")
                    raise ValueError(f"配置错误: 第 {i+1} 个 token 组缺少 {field}")
    
    def get_token_groups(self) -> List[Dict[str, str]]:
        """获取所有token组"""
        return self.qwen_token_groups
    
    def to_dict(self) -> Dict[str, Any]:
        """将配置转换为字典"""
        return {
            'qwen_token_groups': self.qwen_token_groups,
            'qwen_api_base_url': self.qwen_api_base_url,
            'port': self.port,
            'qwen_bx_v': self.qwen_bx_v,
            'qwen_source': self.qwen_source,
            'qwen_timezone': self.qwen_timezone,
            'log_level': self.log_level,
            'log_file': self.log_file
        }

# 全局配置实例
config = Config()

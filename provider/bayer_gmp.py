"""
Bayer GMP Reporter Provider
"""
from typing import Any, Dict
import logging

from dify_plugin import ToolProvider
from dify_plugin.errors.tool import ToolProviderCredentialValidationError

# 创建日志记录器
logger = logging.getLogger("bayer_gmp")


class BayerGMPProvider(ToolProvider):
    """Bayer GMP Reporter Tool Provider实现"""
    
    def _validate_credentials(self, credentials: Dict[str, Any]) -> None:
        """验证提供的API凭证
        
        Args:
            credentials: 包含spring_app_api_key和spring_app_url的字典
        
        Raises:
            ToolProviderCredentialValidationError: 如果凭证无效
        """
        try:
            spring_app_api_key = credentials.get("spring_app_api_key")
            spring_app_url = credentials.get("spring_app_url")
            
            if not spring_app_api_key:
                raise ValueError("Missing required credential: spring_app_api_key")
            
            if not spring_app_url:
                raise ValueError("Missing required credential: spring_app_url")
                
            # 验证URL格式
            if not (spring_app_url.startswith("http://") or spring_app_url.startswith("https://")):
                raise ValueError("spring_app_url must start with http:// or https://")
                
            logger.info(f"Credentials validated successfully for Spring App URL: {spring_app_url}")
        except Exception as e:
            logger.error(f"Credential validation failed: {str(e)}")
            raise ToolProviderCredentialValidationError(str(e)) 
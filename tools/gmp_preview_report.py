"""
Bayer GMP Reporter - HTML预览工具
"""
from collections.abc import Generator
from typing import Any, Dict, List
import requests
import json
import logging
import sys
import os

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dify_plugin import Tool
from dify_plugin.entities.tool import ToolInvokeMessage

# 创建日志记录器
logger = logging.getLogger("bayer_gmp")

# 全局配置
DEFAULT_SPRING_APP_URL = "http://localhost:8080"
API_ENDPOINTS = {
    "generate_pdf": "/api/reports/generate-from-data",
    "preview_report": "/api/reports/preview-from-data"
}

class GMPPreviewReportTool(Tool):
    """预览GMP报告的HTML工具"""
    
    def __init__(self, runtime=None, session=None):
        """初始化工具
        
        Args:
            runtime: 运行时环境
            session: 会话信息
        """
        super().__init__(runtime, session)
        self.context = {}
    
    def _invoke(self, tool_parameters: Dict[str, Any]) -> Generator[ToolInvokeMessage, None, None]:
        """执行工具调用逻辑
        
        Args:
            tool_parameters: 工具参数，包含report_data或conversation_id
            
        Yields:
            ToolInvokeMessage: 工具调用消息
        """
        try:
            # 确保context有值
            if not hasattr(self, 'context') or not self.context:
                self.context = {}
                
            # 处理凭据获取 - 尝试多个来源
            credentials = {}
            
            # 1. 直接从参数获取顶层credentials（Dify通常这样传递）
            if 'credentials' in tool_parameters:
                credentials = tool_parameters.get('credentials', {})
                logger.info(f"Got credentials from tool_parameters: {list(credentials.keys())}")
            
            # 2. 查看传入的context中是否有credentials
            elif 'context' in tool_parameters and 'credentials' in tool_parameters.get('context', {}):
                credentials = tool_parameters.get('context', {}).get('credentials', {})
                logger.info(f"Got credentials from context in parameters: {list(credentials.keys())}")
            
            # 3. 查看对象属性
            elif hasattr(self, 'credentials') and self.credentials:
                credentials = self.credentials
                logger.info(f"Using existing credentials from tool instance: {list(credentials.keys())}")
                
            # 4. 从session获取
            elif self.session and hasattr(self.session, 'credentials') and self.session.credentials:
                credentials = self.session.credentials  
                logger.info(f"Got credentials from session: {list(credentials.keys())}")
                
            # 更新context
            self.context['credentials'] = credentials
                
            # 从请求中获取dify上下文
            if 'context' in tool_parameters:
                self.context.update(tool_parameters.get('context', {}))
            
            # 获取API密钥和URL
            api_key = credentials.get("spring_app_api_key", "")
            base_url = credentials.get("spring_app_url", DEFAULT_SPRING_APP_URL)
            
            logger.info(f"Using API key: {'[PRESENT]' if api_key else '[MISSING]'}")
            logger.info(f"Using base URL: {base_url}")
            
            if not api_key:
                logger.warning("Missing spring_app_api_key, using default test key")
                api_key = "test_key"  # 使用默认的测试密钥
            
            # 获取报告数据
            report_data_str = tool_parameters.get("report_data")
            conversation_id = tool_parameters.get("conversation_id")
            
            # 处理report_data作为JSON字符串的情况
            report_data = None
            if report_data_str:
                try:
                    if isinstance(report_data_str, str):
                        report_data = json.loads(report_data_str)
                    else:
                        # 如果已经是字典，直接使用
                        report_data = report_data_str
                except json.JSONDecodeError:
                    logger.error("Invalid JSON in report_data parameter")
                    yield self.create_json_message({
                        "success": False,
                        "message": "报告数据不是有效的JSON格式"
                    })
                    return
            
            # 如果没有直接提供报告数据，但提供了对话ID，则使用提取工具
            if not report_data and conversation_id:
                logger.info(f"Report data not provided, extracting from conversation: {conversation_id}")
                from .gmp_extract_data import GMPExtractDataTool
                extract_tool = GMPExtractDataTool(self.runtime, self.session)
                
                # 确保extract_tool有正确的上下文和凭据
                extract_tool.context = self.context
                extract_tool.credentials = credentials
                
                # 尝试使用提取工具获取数据
                try:
                    logger.info(f"Calling extract tool with conversation_id: {conversation_id}")
                    extract_responses = list(extract_tool._invoke({"conversation_id": conversation_id, "credentials": credentials}))
                    
                    for response in extract_responses:
                        if hasattr(response, 'json_data'):
                            result = json.loads(response.json_data)
                            logger.info(f"Extract tool response: {result.get('success')}")
                            if result.get("success"):
                                report_data = result.get("report_data", {})
                                logger.info(f"Successfully extracted report data with fields: {', '.join(report_data.keys())}")
                                break
                except Exception as e:
                    logger.error(f"Error calling extract tool: {str(e)}")
                    yield self.create_json_message({
                        "success": False,
                        "message": f"无法从对话中提取报告数据: {str(e)}"
                    })
                    return
            
            if not report_data:
                logger.error("Missing required parameter: report_data")
                yield self.create_json_message({
                    "success": False,
                    "message": "缺少必要参数：报告数据"
                })
                return
            
            # 调用Spring服务生成HTML预览
            try:
                logger.info(f"Generating HTML preview with Spring App URL: {base_url}")
                headers = {
                    "Content-Type": "application/json",
                    "X-API-KEY": api_key  # 使用X-API-KEY头而不是Authorization
                }
                
                # 设置请求超时(秒)
                timeout = 15
                
                response = requests.post(
                    f"{base_url}{API_ENDPOINTS['preview_report']}",
                    headers=headers,
                    json=report_data,
                    timeout=timeout
                )
                
                if response.status_code == 200:
                    logger.info("Successfully generated HTML preview")
                    html_content = response.text
                    
                    yield self.create_json_message({
                        "success": True,
                        "message": "成功生成HTML预览",
                        "html_content": html_content
                    })
                    return
                else:
                    logger.error(f"Failed to generate HTML preview: {response.status_code}, {response.text}")
                    yield self.create_json_message({
                        "success": False,
                        "message": f"生成HTML预览失败，服务返回错误: {response.status_code}，{response.text[:100]}"
                    })
                    return
            except Exception as e:
                logger.error(f"Error calling Spring service: {str(e)}")
                yield self.create_json_message({
                    "success": False,
                    "message": f"调用Spring服务失败: {str(e)}"
                })
                return
                
        except Exception as e:
            logger.error(f"Error in GMP HTML preview generation: {str(e)}")
            yield self.create_json_message({
                "success": False,
                "message": f"HTML预览生成失败: {str(e)}"
            }) 
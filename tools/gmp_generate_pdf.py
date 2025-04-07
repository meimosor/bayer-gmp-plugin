"""
Bayer GMP Reporter - PDF生成工具
"""
from collections.abc import Generator
from typing import Any, Dict, List
import requests
import base64
import json
import logging
import sys
import os
from datetime import datetime
from dotenv import load_dotenv

# 加载环境变量
env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env')
load_dotenv(env_path)

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dify_plugin import Tool
from dify_plugin.entities.tool import ToolInvokeMessage

# 创建日志记录器
logger = logging.getLogger("bayer_gmp")

# 导入公共工具函数
from utils import call_dify_model, extract_json_from_text

# 全局配置
DEFAULT_SPRING_APP_URL = os.getenv("SPRING_APP_URL", "http://localhost:8080")
DEFAULT_SPRING_APP_API_KEY = os.getenv("SPRING_APP_API_KEY", "test_key")
API_ENDPOINTS = {
    "generate_pdf": "/api/pdf/generate",
    "preview_report": "/api/reports/preview-from-data"
}

class GMPGeneratePDFTool(Tool):
    """生成GMP报告PDF的工具"""
    
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
            # 在最开始处详细打印所有tool_parameters信息
            logger.info("="*80)
            logger.info("调试信息: 完整的tool_parameters参数")
            logger.info("-"*80)
            
            # 打印tool_parameters内容
            param_keys = list(tool_parameters.keys())
            logger.info(f"参数键列表: {param_keys}")
            
            # 详细记录每个参数的信息
            for key in param_keys:
                value = tool_parameters.get(key)
                if key == 'report_data':
                    if isinstance(value, str):
                        logger.info(f"report_data (字符串): 长度={len(value)}, 预览={value[:200]}...")
                    elif isinstance(value, dict):
                        logger.info(f"report_data (字典): 键={list(value.keys())}, 预览={str(value)[:200]}...")
                    else:
                        logger.info(f"report_data: 类型={type(value)}, 值={str(value)[:200]}...")
                elif key == 'context':
                    if isinstance(value, dict):
                        logger.info(f"context: 键={list(value.keys())}")
                        # 打印credentials信息但隐藏敏感内容
                        if 'credentials' in value:
                            cred_keys = list(value.get('credentials', {}).keys())
                            logger.info(f"context.credentials: 键={cred_keys}")
                    else:
                        logger.info(f"context: 类型={type(value)}")
                elif key == 'credentials':
                    if isinstance(value, dict):
                        logger.info(f"credentials: 键={list(value.keys())}")
                    else:
                        logger.info(f"credentials: 类型={type(value)}")
                else:
                    # 其他参数
                    logger.info(f"{key}: 类型={type(value)}, 值={str(value)[:100]}")
            
            logger.info("="*80)
            
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
            
            # 获取API密钥和URL - 检查多个可能的来源
            # 首先从环境变量获取默认值
            api_key = DEFAULT_SPRING_APP_API_KEY
            base_url = DEFAULT_SPRING_APP_URL
            
            # 然后检查credentials中是否有值
            if "spring_app_api_key" in credentials and credentials["spring_app_api_key"]:
                api_key = credentials.get("spring_app_api_key")
                logger.info("Using spring_app_api_key from credentials")
                
            if "spring_app_url" in credentials and credentials["spring_app_url"]:
                base_url = credentials.get("spring_app_url")
                logger.info("Using spring_app_url from credentials")
            
            # 最后检查工具参数中是否直接提供
            if "spring_app_api_key" in tool_parameters and tool_parameters["spring_app_api_key"]:
                api_key = tool_parameters.get("spring_app_api_key")
                logger.info("Using spring_app_api_key from tool parameters")
            
            if "spring_app_url" in tool_parameters and tool_parameters["spring_app_url"]:
                base_url = tool_parameters.get("spring_app_url")
                logger.info("Using spring_app_url from tool parameters")
                
            # 记录Spring服务凭据信息
            logger.info(f"Spring服务API密钥(前5位): {api_key[:5]}..." if len(api_key) > 5 else "Spring服务API密钥: [MISSING]")
            logger.info(f"Spring服务基础URL: {base_url}")
            logger.info(f"从环境变量加载的API密钥(前5位): {DEFAULT_SPRING_APP_API_KEY[:5]}..." if len(DEFAULT_SPRING_APP_API_KEY) > 5 else "环境变量API密钥: [MISSING]")
            logger.info(f"从环境变量加载的基础URL: {DEFAULT_SPRING_APP_URL}")
            
            # 获取Dify相关参数 - 首先查看是否作为顶层参数传入
            api_base = tool_parameters.get("api_base", self.context.get("api_base", ""))
            dify_api_key = tool_parameters.get("api_key", self.context.get("api_key", ""))
            user_id = tool_parameters.get("user_id", self.context.get("user_id", "plugin-user"))
            
            # 更新到context中
            self.context.update({
                "api_base": api_base,
                "api_key": dify_api_key,
                "user_id": user_id
            })

            logger.info(f"Using API key: {'[PRESENT]' if api_key else '[MISSING]'}")
            logger.info(f"Using base URL: {base_url}")
            logger.info(f"Dify api_base: {api_base}")
            logger.info(f"Dify api_key: {'[PRESENT]' if dify_api_key else '[MISSING]'}")
            logger.info(f"Dify user_id: {user_id}")

            # 如果存在缺失的关键参数，记录警告
            if not all([api_base, dify_api_key]):
                logger.warning("部分Dify参数缺失，这可能影响报告优化功能")
                logger.warning(f"api_base: {'存在' if api_base else '缺失'}, api_key: {'存在' if dify_api_key else '缺失'}")
            
            # 获取报告数据和对话ID
            report_data_str = tool_parameters.get("report_data")
            conversation_id = tool_parameters.get("conversation_id")
            
            # 日志输出完整工具参数，帮助调试
            logger.info("="*50)
            logger.info("完整工具参数: %s", json.dumps(tool_parameters, ensure_ascii=False)[:500])
            logger.info("="*50)
            
            # 详细记录接收到的报告数据原始内容
            logger.info("收到的报告数据参数类型: %s", type(report_data_str))
            
            # 处理Dify必填参数的情况，当report_data为空字符串但有conversation_id时
            if (report_data_str == "" or report_data_str == '""' or report_data_str == "''") and conversation_id:
                logger.info("报告数据为空字符串但有conversation_id，将使用conversation_id")
                report_data_str = None  # 将空字符串设为None，触发自动提取逻辑
            
            if report_data_str:
                if isinstance(report_data_str, str):
                    logger.info("报告数据字符串长度: %d", len(report_data_str))
                    logger.info("报告数据字符串内容: %s", report_data_str[:1000] + "..." if len(report_data_str) > 1000 else report_data_str)
                else:
                    logger.info("报告数据对象键: %s", list(report_data_str.keys()) if isinstance(report_data_str, dict) else "不是字典对象")
                    logger.info("报告数据对象内容: %s", json.dumps(report_data_str, ensure_ascii=False, indent=2)[:1000] + "..." if len(json.dumps(report_data_str, ensure_ascii=False)) > 1000 else json.dumps(report_data_str, ensure_ascii=False, indent=2))
            else:
                logger.warning("报告数据为空值")
            logger.info("对话ID: %s", conversation_id)
            
            # 从报告数据字符串中提取实际的report_data
            report_data = None
            
            # 处理report_data_str参数
            if report_data_str:
                try:
                    # 1. 处理字符串情况
                    if isinstance(report_data_str, str):
                        # 处理可能的转义问题
                        report_data_str = report_data_str.replace("\\\\", "\\")
                        
                        # 记录尝试解析的原始字符串
                        logger.info(f"尝试解析的报告数据字符串: {report_data_str[:200]}..." if len(report_data_str) > 200 else report_data_str)
                        
                        # 首先尝试处理单引号JSON格式（新格式支持）
                        if report_data_str.startswith("{'") and "'" in report_data_str:
                            # 将单引号JSON转换为标准JSON
                            import ast
                            try:
                                # 尝试使用ast.literal_eval解析单引号JSON
                                parsed_data = ast.literal_eval(report_data_str)
                                logger.info("成功将单引号格式的报告数据字符串解析为Python对象")
                                report_data = parsed_data
                                logger.info(f"解析后的数据字段: {list(report_data.keys()) if isinstance(report_data, dict) else '非字典对象'}")
                            except Exception as e:
                                logger.warning(f"单引号JSON解析失败，尝试标准JSON解析: {str(e)}")
                                # 尝试转换为标准JSON格式再解析
                                try:
                                    # 使用正则表达式替换单引号为双引号，但保留字符串内的单引号
                                    import re
                                    json_str = re.sub(r"(?<!\\)'([^']*)'(?=:)", r'"\1"', report_data_str)
                                    json_str = re.sub(r":\s*'([^']*)'", r': "\1"', json_str)
                                    logger.info(f"转换后的JSON字符串: {json_str[:200]}..." if len(json_str) > 200 else json_str)
                                    
                                    parsed_data = json.loads(json_str)
                                    logger.info("成功将转换后的JSON字符串解析为对象")
                                    report_data = parsed_data
                                except Exception as e2:
                                    logger.warning(f"转换单引号JSON失败: {str(e2)}")
                        
                        # 如果还未成功解析，尝试标准JSON解析
                        if not report_data:
                            try:
                                # 尝试解析JSON字符串
                                parsed_data = json.loads(report_data_str)
                                logger.info("成功将报告数据字符串解析为JSON对象")
                                
                                # 特别处理: 检查是否是Dify提取工具的响应格式
                                if isinstance(parsed_data, dict):
                                    # 检查是否有reportData字段(工具链输出格式)
                                    if 'reportData' in parsed_data and parsed_data['reportData']:
                                        logger.info("检测到reportData字段，直接提取数据")
                                        report_data = parsed_data['reportData']
                                        logger.info(f"从reportData提取到的数据类型: {type(report_data)}")
                                        if isinstance(report_data, str):
                                            try:
                                                # 如果reportData是字符串，尝试解析成JSON
                                                report_data = json.loads(report_data)
                                                logger.info("成功将reportData字符串解析为JSON对象")
                                            except json.JSONDecodeError:
                                                logger.warning("reportData字符串不是有效的JSON格式")
                                        logger.info(f"成功从reportData中提取数据: {list(report_data.keys()) if isinstance(report_data, dict) else '非字典对象'}")
                                    
                                    # 检查是否包含json数组字段(Dify响应格式)
                                    elif 'json' in parsed_data and isinstance(parsed_data['json'], list) and len(parsed_data['json']) > 0:
                                        logger.info("检测到Dify响应格式[带json数组]，尝试提取嵌套数据")
                                        
                                        # 检查json[0]中是否包含report_data
                                        first_item = parsed_data['json'][0]
                                        if 'report_data' in first_item and first_item['report_data']:
                                            report_data = first_item['report_data']
                                            logger.info("成功从Dify响应的json[0].report_data中提取数据")
                                        # 检查是否整个item就是报告数据
                                        elif any(key in first_item for key in ['title', 'docId', 'investigationId']):
                                            report_data = first_item
                                            logger.info("使用Dify响应json[0]作为报告数据")
                                    # 直接包含report_data字段
                                    elif 'report_data' in parsed_data and parsed_data['report_data']:
                                        report_data = parsed_data['report_data']
                                        logger.info("直接从对象的report_data字段提取数据")
                                    # 本身就是报告数据
                                    elif any(key in parsed_data for key in ['title', 'docId', 'investigationId']):
                                        report_data = parsed_data
                                        logger.info("使用整个JSON对象作为报告数据")
                                    else:
                                        # 尝试寻找任何可能的嵌套
                                        for key, value in parsed_data.items():
                                            if isinstance(value, dict) and any(k in value for k in ['title', 'docId', 'investigationId']):
                                                report_data = value
                                                logger.info(f"从字段 {key} 中提取报告数据")
                                                break
                                        
                                        # 如果仍未找到，使用整个对象
                                        if not report_data:
                                            report_data = parsed_data
                                            logger.info("未找到标准格式，使用整个JSON对象")
                                else:
                                    report_data = parsed_data
                                    logger.info("使用整个JSON解析结果作为报告数据")
                            
                            except json.JSONDecodeError as e:
                                logger.warning(f"JSON解析失败，尝试其他方法: {str(e)}")
                                # 尝试使用正则表达式查找嵌入的JSON
                                try:
                                    import re
                                    json_pattern = r'(\{.*\})'
                                    matches = re.search(json_pattern, report_data_str)
                                    if matches:
                                        potential_json = matches.group(1)
                                        parsed_data = json.loads(potential_json)
                                        report_data = parsed_data
                                        logger.info("通过正则表达式提取并解析到嵌入JSON")
                                except Exception as e2:
                                    logger.error(f"正则提取的JSON解析失败: {str(e2)}")
                    
                    # 2. 处理对象情况
                    elif isinstance(report_data_str, dict):
                        # 检查是否包含json数组字段(Dify响应格式)
                        if 'json' in report_data_str and isinstance(report_data_str['json'], list) and len(report_data_str['json']) > 0:
                            logger.info("检测到对象中包含json数组字段，尝试提取嵌套数据")
                            first_item = report_data_str['json'][0]
                            
                            # 判断json[0]中是否有report_data字段
                            if 'report_data' in first_item and first_item['report_data']:
                                report_data = first_item['report_data']
                                logger.info("从json[0].report_data中提取数据")
                            else:
                                # 检查json[0]本身是否可能是报告数据(包含核心字段)
                                if any(key in first_item for key in ['title', 'docId', 'investigationId']):
                                    report_data = first_item
                                    logger.info("使用json[0]作为报告数据")
                                else:
                                    report_data = report_data_str
                                    logger.info("未在json字段中找到报告数据，使用完整对象")
                        # 直接包含report_data字段
                        elif 'report_data' in report_data_str and report_data_str['report_data']:
                            report_data = report_data_str['report_data']
                            logger.info("从对象的report_data字段直接提取数据")
                        # 自身可能是报告数据
                        elif any(key in report_data_str for key in ['title', 'docId', 'investigationId']):
                            report_data = report_data_str
                            logger.info("对象本身包含报告关键字段，直接使用")
                        else:
                            # 搜索任何可能包含报告数据的嵌套对象
                            for key, value in report_data_str.items():
                                if isinstance(value, dict) and any(k in value for k in ['title', 'docId', 'investigationId']):
                                    report_data = value
                                    logger.info(f"从字段 {key} 中提取嵌套报告数据")
                                    break
                                
                            # 如果没找到，使用整个对象
                            if not report_data:
                                report_data = report_data_str
                                logger.info("未找到标准格式的嵌套数据，使用整个对象")
                    else:
                        # 不是字符串也不是字典，直接使用
                        report_data = report_data_str
                        logger.info(f"报告数据类型为 {type(report_data_str)}，直接使用")
                        
                except Exception as e:
                    logger.error(f"处理报告数据字符串时发生错误: {str(e)}")
                    # 在出错时也尝试使用原始值
                    report_data = report_data_str
                    logger.info("处理报告数据时出错，尝试直接使用原始值")
            
            # 如果从report_data_str没有成功提取到数据且有conversation_id，尝试从对话ID提取
            if (not report_data or (isinstance(report_data, dict) and not report_data)) and conversation_id:
                logger.info("报告数据提取失败或为空，尝试从conversation_id获取数据")
                from .gmp_extract_data import GMPExtractDataTool
                extract_tool = GMPExtractDataTool(self.runtime, self.session)
                
                # 确保extract_tool有正确的上下文和凭据
                extract_tool.context = self.context
                if hasattr(self, 'credentials'):
                    extract_tool.credentials = self.credentials
                
                # 尝试使用提取工具获取数据
                try:
                    logger.info(f"调用数据提取工具，对话ID: {conversation_id}")
                    extract_params = {
                        "conversation_id": conversation_id, 
                        "context": self.context
                    }
                    if 'credentials' in tool_parameters:
                        extract_params["credentials"] = tool_parameters.get('credentials')
                        
                    extract_responses = list(extract_tool._invoke(extract_params))
                    
                    for response in extract_responses:
                        if hasattr(response, 'json_data'):
                            result = json.loads(response.json_data)
                            logger.info(f"数据提取工具响应结果: {result.get('success')}")
                            logger.info(f"数据提取工具响应键: {list(result.keys())}")
                            if result.get("success"):
                                report_data = result.get("report_data", {})
                                if report_data:
                                    logger.info(f"成功从对话中提取报告数据，字段: {', '.join(report_data.keys())}")
                                    # 记录提取到的数据
                                    logger.info(f"提取到的报告数据内容: {json.dumps(report_data, ensure_ascii=False)[:500]}")
                                    # 成功提取数据后，直接继续处理流程
                                    break
                                else:
                                    logger.error(f"提取的report_data为空或缺失")
                            else:
                                logger.error(f"数据提取工具返回失败: {result.get('message', '未知错误')}")
                    
                except Exception as e:
                    logger.error(f"调用数据提取工具时出错: {str(e)}")
                    yield self.create_json_message({
                        "success": False,
                        "message": f"无法从对话中提取报告数据: {str(e)}"
                    })
                    return
            
            # 打印处理后的报告数据详情
            if report_data:
                logger.info("处理后的报告数据类型: %s", type(report_data))
                if isinstance(report_data, dict):
                    logger.info("处理后的报告数据字段: %s", list(report_data.keys()))
                    
                    # 打印每个关键字段的内容
                    important_fields = ["investigationId", "title", "docId", "summary", "events", "rootCause", "impactAssessment"]
                    for field in important_fields:
                        if field in report_data:
                            if field == "events" and isinstance(report_data[field], list):
                                logger.info("events字段包含%d个事件", len(report_data[field]))
                                for i, event in enumerate(report_data[field][:3]):  # 只显示前3个事件
                                    logger.info("事件%d: %s", i+1, json.dumps(event, ensure_ascii=False))
                                if len(report_data[field]) > 3:
                                    logger.info("... 更多事件未显示 ...")
                            else:
                                value = report_data[field]
                                if isinstance(value, str) and len(value) > 200:
                                    logger.info("%s: %s...(已截断)", field, value[:200])
                                else:
                                    logger.info("%s: %s", field, value)
                        else:
                            logger.warning("缺少字段: %s", field)
                    
                    # 检查必要字段是否存在
                    missing_fields = []
                    for field in ["investigationId", "title", "docId"]:
                        if field not in report_data or not report_data[field]:
                            missing_fields.append(field)
                    
                    if missing_fields:
                        logger.warning("报告数据缺少关键字段: %s", ", ".join(missing_fields))
                else:
                    logger.warning("处理后的报告数据不是字典对象: %s", str(report_data)[:200])
            else:
                logger.error("处理后的报告数据为空")
            
            if not report_data:
                logger.error("Missing required parameter: report_data")
                yield self.create_json_message({
                    "success": False,
                    "message": "缺少必要参数：报告数据"
                })
                return
            
            # 确保report_data中包含必要字段
            if isinstance(report_data, dict):
                # 检查是否包含嵌套的report_data字段（Dify结果格式）
                if 'report_data' in report_data and isinstance(report_data['report_data'], dict):
                    logger.info("从嵌套结构中提取report_data字段")
                    report_data = report_data['report_data']
                    
                logger.info("报告数据的字段:")
                for field in ["investigationId", "title", "docId"]:
                    if field in report_data and report_data[field]:
                        value = report_data[field]
                        if isinstance(value, str) and len(value) > 100:
                            value = value[:100] + "..."
                        logger.info("%s: %s", field, value)
                    else:
                        logger.warning("缺少字段: %s", field)
                
                # 检查必要字段是否存在
                missing_fields = []
                for field in ["investigationId", "title", "docId"]:
                    if field not in report_data or not report_data[field]:
                        missing_fields.append(field)
                
                if missing_fields:
                    logger.warning("报告数据缺少关键字段: %s", ", ".join(missing_fields))
            else:
                logger.warning("处理后的报告数据不是字典对象: %s", str(report_data)[:200])
            
            # 优化报告数据（可选）
            if tool_parameters.get("optimize_data", False):
                report_data = self._optimize_report_data(report_data)
            
            # 调用Spring服务生成PDF
            try:
                logger.info(f"Generating PDF report with Spring App URL: {base_url}")
                
                # 确保使用有效的API密钥
                if not api_key:
                    logger.warning("Spring API密钥为空，将使用环境变量中的值")
                    api_key = DEFAULT_SPRING_APP_API_KEY
                
                # 确保API密钥不为空
                if not api_key:
                    logger.error("严重错误：Spring API密钥在所有可能的来源中均为空")
                    yield self.create_json_message({
                        "success": False,
                        "message": "无法生成PDF：未提供Spring服务API密钥。请检查.env文件或工具配置。"
                    })
                    return
                
                # 详细记录请求信息，便于调试
                logger.info(f"使用的API密钥(前5位): {api_key[:5]}..." if len(api_key) > 5 else "API密钥为空")
                logger.info(f"请求URL: {base_url}{API_ENDPOINTS['generate_pdf']}")
                logger.info(f"报告数据字段: {list(report_data.keys()) if isinstance(report_data, dict) else '非字典对象'}")
                
                headers = {
                    "Content-Type": "application/json",
                    "X-API-KEY": api_key  # 使用X-API-KEY头而不是Authorization
                }
                
                # 记录完整的headers信息
                logger.info(f"请求Headers: {headers}")
                
                # 设置请求超时(秒)
                timeout = 30  # 增加超时时间到30秒
                
                response = requests.post(
                    f"{base_url}{API_ENDPOINTS['generate_pdf']}",
                    headers=headers,
                    json=report_data,
                    timeout=timeout
                )
                
                if response.status_code == 200:
                    logger.info("Successfully generated PDF report")
                    # 检查内容类型
                    content_type = response.headers.get('Content-Type', '')
                    logger.info(f"Response Content-Type: {content_type}")
                    
                    # 处理JSON响应 - 先尝试获取Minio文件链接
                    if 'application/json' in content_type:
                        try:
                            response_data = response.json()
                            # 打印响应数据的所有键，便于调试
                            logger.info(f"JSON response keys: {list(response_data.keys())}")
                            logger.info(f"JSON response content: {str(response_data)[:200]}...")
                            
                            # 检查是否直接返回了Minio或下载链接
                            if 'minio_url' in response_data and response_data['minio_url']:
                                minio_url = response_data.get('minio_url')
                                logger.info(f"获取到Minio文件下载链接: {minio_url}")
                                
                                # 构建有效的文件名
                                filename = f"GMP_{report_data.get('investigationId', 'report')}.pdf"
                                if 'filename' in response_data:
                                    filename = response_data.get('filename')
                                
                                # 构建Markdown格式的链接
                                markdown_download_link = f"[下载PDF报告]({minio_url})"
                                
                                # 返回下载链接信息给用户
                                yield self.create_json_message({
                                    "success": True,
                                    "message": "成功生成PDF报告",
                                    "download_url": minio_url,
                                    "markdown_download_link": markdown_download_link,
                                    "filename": filename
                                })
                                return
                            elif 'download_url' in response_data and response_data['download_url']:
                                download_url = response_data.get('download_url')
                                logger.info(f"获取到文件下载链接: {download_url}")
                                
                                # 构建有效的文件名
                                filename = f"GMP_{report_data.get('investigationId', 'report')}.pdf"
                                if 'filename' in response_data:
                                    filename = response_data.get('filename')
                                
                                # 构建Markdown格式的链接
                                markdown_download_link = f"[下载PDF报告]({download_url})"
                                
                                # 返回下载链接信息给用户
                                yield self.create_json_message({
                                    "success": True,
                                    "message": "成功生成PDF报告",
                                    "download_url": download_url,
                                    "markdown_download_link": markdown_download_link,
                                    "filename": filename
                                })
                                return
                            else:
                                logger.error("JSON响应中不包含下载链接")
                                yield self.create_json_message({
                                    "success": False,
                                    "message": "无法生成PDF：服务器响应中不包含下载链接"
                                })
                                return
                        except Exception as e:
                            logger.error(f"Error parsing JSON response: {str(e)}")
                            yield self.create_json_message({
                                "success": False,
                                "message": f"解析JSON响应失败: {str(e)}"
                            })
                            return
                    # 处理PDF二进制响应
                    elif 'application/pdf' in content_type:
                        # 直接获取PDF二进制数据
                        pdf_content = response.content
                        logger.info("Received binary PDF content")
                        
                        # 验证PDF文件是否有效 (至少检查PDF文件头)
                        if pdf_content and pdf_content.startswith(b'%PDF-'):
                            logger.info("PDF content appears to be valid (has correct header)")
                            
                            # 额外检查PDF文件是否包含EOF标记
                            if b'%%EOF' in pdf_content[-1024:]:
                                logger.info("PDF content has EOF marker - likely complete")
                            else:
                                logger.warning("PDF content missing EOF marker - might be incomplete")
                            
                            # 上传二进制PDF到MinIO并获取链接
                            try:
                                # 生成文件名
                                filename = f"GMP_{report_data.get('investigationId', 'report')}.pdf"
                                
                                # 将二进制PDF上传到MinIO
                                upload_url = f"{base_url}/api/pdf/upload"
                                
                                logger.info(f"上传PDF到MinIO: {upload_url}")
                                files = {"file": (filename, pdf_content, "application/pdf")}
                                
                                upload_response = requests.post(
                                    upload_url,
                                    headers={"X-API-KEY": api_key},
                                    files=files,
                                    timeout=timeout
                                )
                                
                                if upload_response.status_code == 200:
                                    upload_data = upload_response.json()
                                    minio_url = upload_data.get("minio_url")
                                    
                                    if minio_url:
                                        # 构建Markdown格式的链接
                                        markdown_download_link = f"[下载PDF报告]({minio_url})"
                                        
                                        # 返回下载链接信息给用户
                                        yield self.create_json_message({
                                            "success": True,
                                            "message": "成功生成PDF报告",
                                            "download_url": minio_url,
                                            "markdown_download_link": markdown_download_link,
                                            "filename": filename
                                        })
                                        return
                                    else:
                                        logger.error("MinIO上传成功但未返回URL")
                                else:
                                    logger.error(f"上传PDF到MinIO失败: {upload_response.status_code}, {upload_response.text}")
                            except Exception as e:
                                logger.error(f"处理PDF二进制数据时出错: {str(e)}")
                            
                            # 如果上传失败，返回错误信息
                            yield self.create_json_message({
                                "success": False,
                                "message": "无法生成PDF下载链接，请稍后重试"
                            })
                            return
                        else:
                            logger.error(f"Invalid PDF content - missing PDF header")
                            yield self.create_json_message({
                                "success": False,
                                "message": "Spring服务返回的内容不是有效的PDF格式"
                            })
                            return
                    else:
                        logger.error(f"Invalid content type: {content_type}, expected application/pdf or application/json")
                        # 检查是否返回了JSON格式的错误信息
                        try:
                            error_data = response.json()
                            error_message = error_data.get("message", "未知错误")
                            logger.error(f"服务器返回错误: {error_message}")
                            
                            yield self.create_json_message({
                                "success": False,
                                "message": f"无法生成PDF: {error_message}"
                            })
                            return
                        except Exception:
                            # 返回通用错误
                            yield self.create_json_message({
                                "success": False,
                                "message": f"服务器返回了非PDF格式的内容，内容类型: {content_type}"
                            })
                            return
                else:
                    logger.error(f"Failed to generate PDF: {response.status_code}, {response.text}")
                    yield self.create_json_message({
                        "success": False,
                        "message": f"生成PDF失败，服务返回错误: {response.status_code}，{response.text[:100]}"
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
            logger.error(f"Error in GMP PDF generation: {str(e)}")
            yield self.create_json_message({
                "success": False,
                "message": f"PDF生成失败: {str(e)}"
            })
    
    def _optimize_report_data(self, report_data: Dict[str, Any]) -> Dict[str, Any]:
        """使用Dify模型优化报告数据
        
        Args:
            report_data: 原始报告数据
            
        Returns:
            优化后的报告数据
        """
        try:
            # 如果不能访问Dify模型，直接返回原始数据
            api_base = self.context.get("api_base", "")
            api_key = self.context.get("api_key", "")
            
            if not all([api_base, api_key]):
                logger.warning("Missing required parameters for report optimization, using original data")
                return report_data
            
            # 创建提示词，要求模型优化报告数据
            prompt = f"""
请帮助优化以下GMP报告数据，使其更加专业、清晰和准确。保持原始格式，但可以改进内容质量。
请返回完整的优化后JSON数据。

原始报告数据:
{json.dumps(report_data, ensure_ascii=False, indent=2)}

请返回优化后的JSON数据:
"""
            
            # 调用Dify模型
            model_response = call_dify_model(prompt, self.context)
            
            if not model_response:
                logger.warning("Failed to get optimization from Dify model, using original data")
                return report_data
            
            # 从回复中提取JSON
            optimized_data = extract_json_from_text(model_response)
            
            if not optimized_data:
                logger.warning("Could not extract valid JSON from model response, using original data")
                return report_data
            
            # 验证优化后的数据是否包含所有必需字段
            required_fields = [
                "refSop", "docId", "version", "title", "investigationId", 
                "preparedBy", "preparedDate", "summary", "rootCause",
                "impactAssessment", "events", "actions", "reviewers"
            ]
            
            missing_fields = [field for field in required_fields if field not in optimized_data]
            
            if missing_fields:
                logger.warning(f"Optimized data is missing required fields: {missing_fields}, using original data")
                return report_data
            
            logger.info("Successfully optimized report data using Dify model")
            return optimized_data
            
        except Exception as e:
            logger.warning(f"Error optimizing report data: {str(e)}, using original data")
            return report_data

    def generate_pdf_report(self, report_data, credentials=None):
        """从报告数据生成PDF报告
        
        Args:
            report_data (Dict): 报告数据，包含所有必要的字段
            credentials (Dict, optional): 用于API请求的凭据
            
        Returns:
            Dict: 包含PDF生成结果和下载链接的信息
        """
        try:
            # 记录要生成的报告类型和文档ID
            logger.info(f"开始生成PDF报告，文档ID: {report_data.get('docId', 'unknown')}")
            
            # 构建请求数据
            api_data = report_data.copy()
            
            # 发送请求到Spring Boot应用
            response = self._make_api_request(
                endpoint=API_ENDPOINTS["generate_pdf"],
                data=api_data,
                credentials=credentials
            )
            
            # 处理响应
            logger.debug(f"PDF生成API响应: {response}")
            
            if response and isinstance(response, dict):
                # API调用成功，检查返回的字段
                if "success" in response and response["success"]:
                    result = {
                        "success": True,
                        "message": response.get("message", "PDF报告生成成功")
                    }
                    
                    # 检查并添加下载链接 (可能是minio_url或download_url字段)
                    if "minio_url" in response:
                        result["download_url"] = response["minio_url"]
                    elif "download_url" in response:
                        result["download_url"] = response["download_url"]
                    else:
                        logger.warning("API响应中缺少下载链接字段")
                        result["download_url"] = None
                    
                    # 添加文件名，如果存在
                    if "filename" in response:
                        result["filename"] = response["filename"]
                    
                    return result
                else:
                    # API调用失败
                    error_message = response.get("message", "未知错误")
                    logger.error(f"PDF生成失败: {error_message}")
                    return {
                        "success": False,
                        "message": f"PDF生成失败: {error_message}"
                    }
            else:
                # 响应格式不正确
                logger.error("PDF生成API响应格式不正确")
                return {
                    "success": False,
                    "message": "PDF生成API响应格式不正确"
                }
                
        except Exception as e:
            logger.error(f"生成PDF报告时发生错误: {str(e)}")
            return {
                "success": False,
                "message": f"生成PDF报告时发生错误: {str(e)}"
            }

    def _make_api_request(self, endpoint: str, data: Dict[str, Any], credentials: Dict[str, Any] = None) -> Dict[str, Any]:
        """向Spring Boot应用发送API请求
        
        Args:
            endpoint: API端点
            data: 要发送的数据
            credentials: 凭据信息
            
        Returns:
            API响应
        """
        try:
            # 获取API密钥和URL
            api_key = credentials.get("spring_app_api_key", DEFAULT_SPRING_APP_API_KEY) if credentials else DEFAULT_SPRING_APP_API_KEY
            base_url = credentials.get("spring_app_url", DEFAULT_SPRING_APP_URL) if credentials else DEFAULT_SPRING_APP_URL
            
            # 确保URL和密钥有效
            if not base_url or not api_key:
                logger.error("缺少Spring应用URL或API密钥")
                return {"success": False, "message": "缺少Spring应用URL或API密钥"}
            
            # 预处理数据 - 确保包含正确的分组字段
            prepared_data = data.copy()
            
            # 记录处理前数据
            logger.info("预处理前数据:")
            logger.info(f"correctiveActions: {prepared_data.get('correctiveActions', '不存在')}")
            logger.info(f"preventiveActions: {prepared_data.get('preventiveActions', '不存在')}")
            logger.info(f"actions: {prepared_data.get('actions', '不存在')}")
            
            # 重新规范化corrective和preventive字段
            # 确保只存储纯措施文本，不带前缀
            if "correctiveActions" in prepared_data:
                if isinstance(prepared_data["correctiveActions"], list):
                    # 移除前缀标记
                    clean_list = []
                    for item in prepared_data["correctiveActions"]:
                        if isinstance(item, str):
                            if item.lower().startswith(("纠正措施:", "纠正措施：")):
                                # 提取冒号后的文本
                                if ":" in item:
                                    clean_list.append(item.split(":", 1)[1].strip())
                                elif "：" in item:
                                    clean_list.append(item.split("：", 1)[1].strip())
                            else:
                                clean_list.append(item.strip())
                    prepared_data["correctiveActions"] = clean_list
                elif isinstance(prepared_data["correctiveActions"], str):
                    prepared_data["correctiveActions"] = [prepared_data["correctiveActions"].strip()]
            else:
                prepared_data["correctiveActions"] = []
                
            if "preventiveActions" in prepared_data:
                if isinstance(prepared_data["preventiveActions"], list):
                    # 移除前缀标记
                    clean_list = []
                    for item in prepared_data["preventiveActions"]:
                        if isinstance(item, str):
                            if item.lower().startswith(("预防措施:", "预防措施：")):
                                # 提取冒号后的文本
                                if ":" in item:
                                    clean_list.append(item.split(":", 1)[1].strip())
                                elif "：" in item:
                                    clean_list.append(item.split("：", 1)[1].strip())
                            else:
                                clean_list.append(item.strip())
                    prepared_data["preventiveActions"] = clean_list
                elif isinstance(prepared_data["preventiveActions"], str):
                    prepared_data["preventiveActions"] = [prepared_data["preventiveActions"].strip()]
            else:
                prepared_data["preventiveActions"] = []
            
            # 如果只有actions字段，按前缀分割
            if ("actions" in prepared_data and prepared_data["actions"]) and \
               (not prepared_data["correctiveActions"] and not prepared_data["preventiveActions"]):
                actions = prepared_data["actions"]
                corrective = []
                preventive = []
                
                if isinstance(actions, list):
                    for action in actions:
                        if isinstance(action, str):
                            action = action.strip()
                            if action.lower().startswith(("纠正措施:", "纠正措施：")):
                                # 提取冒号后的文本
                                if ":" in action:
                                    corrective.append(action.split(":", 1)[1].strip())
                                elif "：" in action:
                                    corrective.append(action.split("：", 1)[1].strip())
                            elif action.lower().startswith(("预防措施:", "预防措施：")):
                                # 提取冒号后的文本
                                if ":" in action:
                                    preventive.append(action.split(":", 1)[1].strip())
                                elif "：" in action:
                                    preventive.append(action.split("：", 1)[1].strip())
                            # 通过内容判断类型
                            elif "更换" in action or "修复" in action or "检测" in action or "清理" in action:
                                corrective.append(action)
                            elif "增加" in action or "建立" in action or "开展" in action or "优化" in action or "培训" in action:
                                preventive.append(action)
                            
                # 更新分组字段
                if corrective:
                    prepared_data["correctiveActions"] = corrective
                if preventive:
                    prepared_data["preventiveActions"] = preventive
            
            # 移除重复措施
            if prepared_data["correctiveActions"] and prepared_data["preventiveActions"]:
                # 创建集合去重
                corrective_set = set(prepared_data["correctiveActions"])
                preventive_set = set(prepared_data["preventiveActions"])
                
                # 确保措施不重复出现在两个类别中
                # 优先保留在preventiveActions中
                corrective_unique = corrective_set - preventive_set
                
                prepared_data["correctiveActions"] = list(corrective_unique)
            
            # 修改格式：将纠正措施和预防措施以编号的形式显示
            # 以创建新的格式化字段
            if prepared_data["correctiveActions"]:
                formatted_corrective = []
                for i, action in enumerate(prepared_data["correctiveActions"], 1):
                    formatted_corrective.append(f"{i}. {action}")
                prepared_data["formattedCorrectiveActions"] = formatted_corrective
            else:
                prepared_data["formattedCorrectiveActions"] = []
                
            if prepared_data["preventiveActions"]:
                formatted_preventive = []
                for i, action in enumerate(prepared_data["preventiveActions"], 1):
                    formatted_preventive.append(f"{i}. {action}")
                prepared_data["formattedPreventiveActions"] = formatted_preventive
            else:
                prepared_data["formattedPreventiveActions"] = []
                
            # 重新构造actions字段
            formatted_actions = []
            if prepared_data.get("formattedCorrectiveActions"):
                formatted_actions.append("纠正措施:")
                formatted_actions.extend(prepared_data["formattedCorrectiveActions"])
                
            if prepared_data.get("formattedPreventiveActions"):
                if formatted_actions:  # 如果已经有纠正措施，添加空行分隔
                    formatted_actions.append("")
                formatted_actions.append("预防措施:")
                formatted_actions.extend(prepared_data["formattedPreventiveActions"])
                
            # 更新actions字段，以包含格式化的措施
            if formatted_actions:
                prepared_data["actions"] = formatted_actions
            
            # 记录发送到后端的实际数据
            logger.info("预处理后数据:")
            logger.info(f"correctiveActions ({len(prepared_data.get('correctiveActions', []))}项): {prepared_data.get('correctiveActions', '空')}")
            logger.info(f"preventiveActions ({len(prepared_data.get('preventiveActions', []))}项): {prepared_data.get('preventiveActions', '空')}")
            logger.info(f"formattedActions: {prepared_data.get('actions', '空')}")
            
            # 设置请求头
            headers = {
                "Content-Type": "application/json",
                "X-API-KEY": api_key  # 使用X-API-KEY头
            }
            
            # 记录请求详情
            logger.info(f"请求URL: {base_url}{endpoint}")
            logger.info(f"请求方法: POST")
            logger.info(f"Headers: {headers}")
            
            # 发送请求
            response = requests.post(
                f"{base_url}{endpoint}",
                headers=headers,
                json=prepared_data,
                timeout=30  # 30秒超时
            )
            
            # 处理响应
            if response.status_code == 200:
                try:
                    json_response = response.json()
                    logger.info(f"API请求成功: {endpoint}")
                    return json_response
                except Exception as e:
                    logger.error(f"解析JSON响应失败: {str(e)}")
                    # 如果是二进制响应，返回特殊结构
                    if 'application/pdf' in response.headers.get('Content-Type', ''):
                        return {
                            "success": True,
                            "content_type": "application/pdf",
                            "binary_data": response.content
                        }
                    return {"success": False, "message": "无法解析服务器响应"}
            else:
                logger.error(f"API请求失败: {response.status_code}, {response.text}")
                try:
                    error_response = response.json()
                    return {"success": False, "message": error_response.get("message", f"API请求失败: {response.status_code}")}
                except:
                    return {"success": False, "message": f"API请求失败: {response.status_code}, {response.text[:100]}"}
                
        except Exception as e:
            logger.error(f"发送API请求时出错: {str(e)}")
            return {"success": False, "message": f"发送API请求时出错: {str(e)}"} 
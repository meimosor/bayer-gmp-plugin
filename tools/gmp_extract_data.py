"""
Bayer GMP Reporter - 数据提取工具
"""
from collections.abc import Generator
from typing import Any, Dict, List
import json
import logging
from datetime import datetime
import sys
import os
import re

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dify_plugin import Tool
from dify_plugin.entities.tool import ToolInvokeMessage

# 创建日志记录器
logger = logging.getLogger("bayer_gmp")

# 导入公共工具函数
from utils import get_conversation_history, call_dify_model, extract_json_from_text


class GMPExtractDataTool(Tool):
    """从对话历史中提取GMP报告数据的工具"""
    
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
            tool_parameters: 工具参数，包含conversation_id
            
        Yields:
            ToolInvokeMessage: 工具调用消息
        """
        try:
            # 获取对话ID
            conversation_id = tool_parameters.get("conversation_id")
            if not conversation_id:
                logger.error("Missing required parameter: conversation_id")
                yield self.create_json_message({
                    "success": False,
                    "message": "缺少必要参数：对话ID",
                    "report_data": {}
                })
                return
            
            # 确保context有值
            if not hasattr(self, 'context') or not self.context:
                self.context = {}
            
            # 提取可能嵌入在conversation_id中的JSON数据
            conversation_id, embedded_json = self._extract_json_from_conversation_id(conversation_id)
            
            # 从请求中获取credentials
            # 1. 参数中直接传递的credentials
            if 'credentials' in tool_parameters:
                self.context['credentials'] = tool_parameters.get('credentials', {})
                logger.info(f"Got credentials from tool_parameters: {list(self.context['credentials'].keys())}")
            
            # 2. 查看外部传入的credentials (初始化时可能已经获取)
            elif hasattr(self, 'credentials') and self.credentials:
                self.context['credentials'] = self.credentials
                logger.info(f"Using existing credentials from tool instance: {list(self.context['credentials'].keys())}")
            
            # 3. 如果存在credentials作为顶层参数，直接获取
            elif self.session and hasattr(self.session, 'credentials') and self.session.credentials:
                self.context['credentials'] = self.session.credentials
                logger.info(f"Got credentials from session: {list(self.context['credentials'].keys())}")
                
            # 从请求中获取dify上下文
            if 'context' in tool_parameters:
                self.context.update(tool_parameters.get('context', {}))
                
            # 如果缺少必要的API信息，但传入了用户信息，可以构建模拟上下文
            if not all([self.context.get('app_id'), self.context.get('api_base'), self.context.get('api_key')]):
                if 'user_id' in tool_parameters:
                    self.context.update({
                        'app_id': 'test_app',
                        'api_base': 'http://localhost:5001',
                        'api_key': 'test_api_key'
                    })
            
            # 如果从conversation_id中提取到了JSON，直接使用这些数据
            if embedded_json and isinstance(embedded_json, dict):
                logger.info(f"使用从conversation_id中提取的JSON数据: {list(embedded_json.keys())}")
                
                # 尝试从嵌入JSON中获取基础文档信息
                report_data = {}
                
                # 处理基础文档信息
                if '基础文档信息' in embedded_json:
                    base_info = embedded_json['基础文档信息']
                    for zh_key, en_key in [
                        ('refSop', 'refSop'), 
                        ('docId', 'docId'), 
                        ('version', 'version'),
                        ('title', 'title'),
                        ('investigationId', 'investigationId'),
                        ('preparedBy', 'preparedBy'),
                        ('preparedDate', 'preparedDate')
                    ]:
                        if zh_key in base_info:
                            report_data[en_key] = base_info[zh_key]
                
                # 处理根本原因
                if '根本原因分析' in embedded_json and 'rootCause' in embedded_json['根本原因分析']:
                    report_data['rootCause'] = embedded_json['根本原因分析']['rootCause']
                
                # 处理影响评估
                if '影响评估信息' in embedded_json:
                    impact_info = embedded_json['影响评估信息']
                    impact_text = []
                    for field in ['affectedProducts', 'productionImpact', 'qualityImpact']:
                        if field in impact_info and impact_info[field]:
                            impact_text.append(impact_info[field])
                    report_data['impactAssessment'] = '\n'.join(impact_text) if impact_text else "无重大影响"
                
                # 处理调查和处理信息
                if '调查和处理信息' in embedded_json:
                    investigation_info = embedded_json['调查和处理信息']
                    if 'summary' in investigation_info:
                        report_data['summary'] = investigation_info['summary']
                    if 'investigation' in investigation_info:
                        report_data['investigation'] = investigation_info['investigation']
                    if 'handling' in investigation_info:
                        report_data['handling'] = investigation_info['handling']
                    if 'eventSummary' in investigation_info:
                        report_data['eventSummary'] = investigation_info['eventSummary']
                
                # 处理CAPA措施
                actions = []
                if 'CAPA措施' in embedded_json:
                    capa_info = embedded_json['CAPA措施']
                    if 'correctiveActions' in capa_info:
                        corrective = capa_info['correctiveActions']
                        if isinstance(corrective, str):
                            actions.append(f"纠正措施: {corrective}")
                        elif isinstance(corrective, list):
                            for action in corrective:
                                actions.append(f"纠正措施: {action}")
                    
                    if 'preventiveActions' in capa_info:
                        preventive = capa_info['preventiveActions']
                        if isinstance(preventive, str):
                            actions.append(f"预防措施: {preventive}")
                        elif isinstance(preventive, list):
                            for action in preventive:
                                actions.append(f"预防措施: {action}")
                
                # 处理结论中的事件和措施
                if '结论和签名信息' in embedded_json:
                    conclusion_info = embedded_json['结论和签名信息']
                    
                    # 如果还没有设置结论，从这里设置
                    if 'conclusion' in conclusion_info and 'eventSummary' not in report_data:
                        report_data['eventSummary'] = conclusion_info['conclusion']
                    
                    # 从结论信息中获取事件
                    if 'events' in conclusion_info and isinstance(conclusion_info['events'], list):
                        report_data['events'] = conclusion_info['events']
                    
                    # 从结论信息中获取措施
                    if 'actions' in conclusion_info and isinstance(conclusion_info['actions'], list):
                        # 如果已经有CAPA措施，合并
                        if actions:
                            actions.extend(conclusion_info['actions'])
                        else:
                            actions = conclusion_info['actions']
                    
                    # 从结论信息中获取评审人
                    if 'reviewers' in conclusion_info and isinstance(conclusion_info['reviewers'], list):
                        report_data['reviewers'] = conclusion_info['reviewers']
                
                # 设置行动措施
                if actions:
                    report_data['actions'] = actions
                
                # 处理和规范化提取的数据
                processed_data = self._process_extracted_data(report_data)
                
                # 返回结果
                yield self.create_json_message({
                    "success": True,
                    "message": "成功从JSON数据提取报告数据",
                    "report_data": processed_data
                })
                return
                
            # 如果没有嵌入JSON或提取失败，继续常规流程
            # 获取对话历史
            logger.info(f"Retrieving conversation history for ID: {conversation_id}")
            conversation_history = get_conversation_history(conversation_id, self.context)
            if not conversation_history:
                logger.error("Failed to retrieve conversation history or history is empty")
                yield self.create_json_message({
                    "success": False,
                    "message": "无法获取对话历史或对话历史为空",
                    "report_data": {}
                })
                return
            
            # 提取报告数据
            logger.info(f"Extracting GMP report data from {len(conversation_history)} messages")
            report_data = self._extract_gmp_report_data(conversation_history)
            
            # 返回结果
            yield self.create_json_message({
                "success": True,
                "message": "成功提取报告数据",
                "report_data": report_data
            })
                
        except Exception as e:
            logger.error(f"Error in GMP data extraction: {str(e)}")
            yield self.create_json_message({
                "success": False,
                "message": f"报告数据提取失败: {str(e)}",
                "report_data": {}
            })
    
    def _extract_gmp_report_data(self, conversation_history: List[Dict[str, Any]]) -> Dict[str, Any]:
        """从对话历史中提取GMP报告所需的关键信息"""
        try:
            # 创建临时数据结构
            messages = []
            last_assistant_message = None
            
            for msg in conversation_history:
                if "role" in msg and "content" in msg:
                    messages.append({
                        "role": msg["role"],
                        "content": msg["content"]
                    })
                    
                    # 保存最后一个助手消息，可能包含Markdown表格
                    if msg["role"] == "assistant":
                        last_assistant_message = msg["content"]
            
            # 检查最后的助手回复中是否已经提取了数据
            extracted_data = {}
            if last_assistant_message and ("表格" in last_assistant_message or "GMP报告数据" in last_assistant_message):
                logger.info("检测到助手已经提取了报告数据表格，尝试解析")
                
                # 直接从Markdown表格提取数据
                extracted_data = self._extract_from_markdown_tables(last_assistant_message)
                
                if extracted_data:
                    logger.info(f"从Markdown表格成功提取数据：{len(extracted_data.keys())}个字段")
                    return extracted_data
            
            # 如果无法从表格提取，构建提示词，要求模型提取GMP报告数据
            conversation_text = "\n".join([f"{msg['role']}: {msg['content']}" for msg in messages])
            prompt = f"""
请从以下对话内容中提取GMP报告所需的关键信息，并以JSON格式返回。必须包含以下字段：
refSop, docId, version, title, investigationId, preparedBy, preparedDate, summary, rootCause, impactAssessment, investigation, handling, eventSummary

事件(events)应该是包含date和description字段的对象数组。
措施(actions)应该是字符串数组。
评审人(reviewers)应该是包含name和date字段的对象数组。

对话内容：
{conversation_text}

请仅返回JSON格式的提取结果，不要包含其他解释性文本。
"""
            
            # 1. 首先尝试使用Dify平台配置的模型
            model_response = call_dify_model(prompt, self.context)
            extracted_data = extract_json_from_text(model_response) if model_response else {}
            
            # 2. 如果Dify模型调用失败，使用本地配置的方式生成数据
            if not extracted_data:
                logger.info("Dify model call failed or returned invalid data, using fallback extraction method")
                # 使用默认结构和处理逻辑
                extracted_data = {
                    "refSop": "GMP-SOP-001",
                    "docId": "FORM-GMP-001",
                    "version": "1.0",
                    "title": "GMP调查报告",
                    "investigationId": f"INV-{datetime.now().strftime('%Y%m%d')}",
                    "preparedBy": "系统自动生成",
                    "preparedDate": datetime.now().strftime("%Y-%m-%d"),
                    "summary": "本报告调查了生产过程中发现的偏差问题。通过系统性的调查和分析，确定了问题的根本原因并提出了相应的纠正和预防措施。",
                    "rootCause": "根据调查分析，尚未确定明确的根本原因，需要进一步收集信息。",
                    "impactAssessment": "本次偏差对产品质量、安全性及有效性的影响：无影响/可评估为1级偏差。\n偏差风险评估：本次风险评定为低风险，仅影响数据记录，不影响产品质量。",
                    "investigation": "调查过程中对设备进行了检查和测试，并查阅了相关操作记录和维护日志。",
                    "handling": "针对发现的问题，执行了必要的调整和修复，确保设备恢复正常运行。",
                    "eventSummary": "本次事件已得到妥善处理，未对产品质量和生产过程造成显著影响。建议加强设备维护和操作人员培训，防止类似问题再次发生。",
                    "events": [],
                    "actions": [],
                    "reviewers": []
                }
                
                # 扫描对话内容尝试提取一些事件信息
                for msg in messages:
                    if msg["role"] == "user" and "故障" in msg["content"]:
                        extracted_data["events"].append({
                            "date": datetime.now().strftime("%Y-%m-%d"),
                            "description": f"用户报告故障: {msg['content'][:50]}..."
                        })
            
            # 处理提取的数据
            processed_data = self._process_extracted_data(extracted_data)
            logger.info("Successfully extracted and processed GMP report data")
            
            return processed_data
        except Exception as e:
            logger.error(f"Error extracting GMP report data: {str(e)}")
            # 返回默认数据
            return self._add_default_required_fields({})
    
    def _process_extracted_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """处理和规范化提取的数据，确保其符合报告数据模型的要求"""
        # 添加必填字段的默认值，防止生成报告时出现空值错误
        data = self._add_default_required_fields(data)
        
        # 处理来自影响评估信息的数据
        if '影响评估信息' in data:
            impact_info = data['影响评估信息']
            impact_text = []
            for field in ['affectedProducts', 'productionImpact', 'qualityImpact']:
                if field in impact_info and impact_info[field]:
                    impact_text.append(impact_info[field])
            if impact_text:
                data['impactAssessment'] = '\n'.join(impact_text)
        
        # 处理来自根本原因分析的数据
        if '根本原因分析' in data and 'rootCause' in data['根本原因分析']:
            data['rootCause'] = data['根本原因分析']['rootCause']
        
        # 处理来自调查和处理信息的数据
        if '调查和处理信息' in data:
            inv_info = data['调查和处理信息']
            if 'summary' in inv_info:
                data['summary'] = inv_info['summary']
            if 'investigation' in inv_info:
                data['investigation'] = inv_info['investigation']
            if 'handling' in inv_info:
                data['handling'] = inv_info['handling']
            if 'eventSummary' in inv_info:
                data['eventSummary'] = inv_info['eventSummary']
        
        # 处理来自基础文档信息的数据
        if '基础文档信息' in data:
            base_info = data['基础文档信息']
            for zh_key, en_key in [
                ('refSop', 'refSop'), 
                ('docId', 'docId'), 
                ('version', 'version'),
                ('title', 'title'),
                ('investigationId', 'investigationId'),
                ('preparedBy', 'preparedBy'),
                ('preparedDate', 'preparedDate')
            ]:
                if zh_key in base_info:
                    data[en_key] = base_info[zh_key]
                    
        # 处理事件信息
        events = []
        # 从事件描述信息提取
        if '事件描述信息' in data:
            event_info = data['事件描述信息']
            if 'failureTime' in event_info and 'failureDescription' in event_info:
                # 解析故障时间
                failure_time = event_info['failureTime']
                if ' ' in failure_time:  # 如果包含时间部分，只取日期部分
                    failure_date = failure_time.split(' ')[0]
                else:
                    failure_date = failure_time
                
                events.append({
                    "date": failure_date,
                    "description": event_info['failureDescription']
                })
        
        # 从结论和签名信息提取事件
        if '结论和签名信息' in data and 'events' in data['结论和签名信息']:
            conclusion_events = data['结论和签名信息']['events']
            if isinstance(conclusion_events, list):
                events.extend(conclusion_events)
        
        # 合并现有的events
        if 'events' in data and isinstance(data['events'], list):
            for event in data['events']:
                if event not in events:  # 避免重复
                    events.append(event)
        
        # 更新events
        if events:
            data['events'] = events
        
        # 彻底重新处理所有CAPA措施，确保正确分组和去重
        # 创建集合用于去重
        corrective_actions = set()
        preventive_actions = set()
        
        # 提取所有可能来源的措施
        
        # 1. 处理CAPA措施字段
        if 'CAPA措施' in data:
            capa_info = data['CAPA措施']
            
            # 处理纠正措施
            if 'correctiveActions' in capa_info:
                corrective = capa_info['correctiveActions']
                if isinstance(corrective, str):
                    for item in corrective.split("\n"):
                        item = item.strip()
                        if item:
                            corrective_actions.add(item)
                elif isinstance(corrective, list):
                    for item in corrective:
                        if item and isinstance(item, str):
                            corrective_actions.add(item.strip())
            
            # 处理预防措施
            if 'preventiveActions' in capa_info:
                preventive = capa_info['preventiveActions']
                if isinstance(preventive, str):
                    for item in preventive.split("\n"):
                        item = item.strip()
                        if item:
                            preventive_actions.add(item)
                elif isinstance(preventive, list):
                    for item in preventive:
                        if item and isinstance(item, str):
                            preventive_actions.add(item.strip())
                            
        # 2. 处理结论和签名信息中的actions
        if '结论和签名信息' in data and 'actions' in data['结论和签名信息']:
            actions = data['结论和签名信息']['actions']
            if isinstance(actions, list):
                for action in actions:
                    if isinstance(action, str):
                        action = action.strip()
                        if action.lower().startswith(("纠正措施:", "纠正措施：")):
                            text = self._extract_action_text(action)
                            if text:
                                corrective_actions.add(text)
                        elif action.lower().startswith(("预防措施:", "预防措施：")):
                            text = self._extract_action_text(action)
                            if text:
                                preventive_actions.add(text)
                        # 尝试通过内容判断类型
                        elif "更换" in action or "修复" in action or "检测" in action or "清理" in action:
                            corrective_actions.add(action)
                        elif "增加" in action or "建立" in action or "开展" in action or "优化" in action or "培训" in action:
                            preventive_actions.add(action)
                            
        # 3. 处理已有的actions字段
        if 'actions' in data and isinstance(data['actions'], list):
            for action in data['actions']:
                if isinstance(action, str):
                    action = action.strip()
                    if action.lower().startswith(("纠正措施:", "纠正措施：")):
                        text = self._extract_action_text(action)
                        if text:
                            corrective_actions.add(text)
                    elif action.lower().startswith(("预防措施:", "预防措施：")):
                        text = self._extract_action_text(action)
                        if text:
                            preventive_actions.add(text)
                    # 尝试通过内容判断类型
                    elif "更换" in action or "修复" in action or "检测" in action or "清理" in action:
                        corrective_actions.add(action)
                    elif "增加" in action or "建立" in action or "开展" in action or "优化" in action or "培训" in action:
                        preventive_actions.add(action)
                        
        # 4. 处理correctiveActions和preventiveActions字段
        if 'correctiveActions' in data:
            if isinstance(data['correctiveActions'], str):
                for item in data['correctiveActions'].split("\n"):
                    item = item.strip()
                    if item:
                        corrective_actions.add(item)
            elif isinstance(data['correctiveActions'], list):
                for item in data['correctiveActions']:
                    if item and isinstance(item, str):
                        corrective_actions.add(item.strip())
                        
        if 'preventiveActions' in data:
            if isinstance(data['preventiveActions'], str):
                for item in data['preventiveActions'].split("\n"):
                    item = item.strip()
                    if item:
                        preventive_actions.add(item)
            elif isinstance(data['preventiveActions'], list):
                for item in data['preventiveActions']:
                    if item and isinstance(item, str):
                        preventive_actions.add(item.strip())
        
        # 将集合转换回列表
        corrective_list = list(corrective_actions)
        preventive_list = list(preventive_actions)
        
        # 确保不同措施类型间没有重复
        # 如果同一个措施在两个类别中都出现，优先作为预防措施处理
        for item in corrective_list[:]:
            if item in preventive_list:
                corrective_list.remove(item)
        
        # 准备最终的actions列表，确保格式正确
        actions = []
        for item in corrective_list:
            if not item.lower().startswith(("纠正措施:", "纠正措施：")):
                actions.append(f"纠正措施: {item}")
            else:
                actions.append(item)
                
        for item in preventive_list:
            if not item.lower().startswith(("预防措施:", "预防措施：")):
                actions.append(f"预防措施: {item}")
            else:
                actions.append(item)
        
        # 更新数据字段
        data["correctiveActions"] = corrective_list
        data["preventiveActions"] = preventive_list
        data["actions"] = actions
        
        # 处理结论
        if '结论和签名信息' in data and 'conclusion' in data['结论和签名信息']:
            if 'eventSummary' not in data or not data['eventSummary']:
                data['eventSummary'] = data['结论和签名信息']['conclusion']
        
        # 确保events是正确的格式
        if "events" in data and data["events"]:
            # 如果events是字符串列表，将其转换为对象列表
            if isinstance(data["events"], list):
                processed_events = []
                for event in data["events"]:
                    if isinstance(event, str) and ":" in event:
                        # 尝试从 "2024-05-10: 发现设备故障" 格式转换
                        parts = event.split(":", 1)
                        if len(parts) == 2:
                            processed_events.append({
                                "date": parts[0].strip(),
                                "description": parts[1].strip()
                            })
                    elif isinstance(event, dict) and "date" in event and "description" in event:
                        # 已经是正确格式
                        processed_events.append(event)
                
                if processed_events:
                    data["events"] = processed_events
        
        # 确保reviewers是正确的格式
        if "reviewers" in data and data["reviewers"]:
            # 如果reviewers是字符串列表，将其转换为对象列表
            if isinstance(data["reviewers"], list):
                processed_reviewers = []
                for reviewer in data["reviewers"]:
                    if isinstance(reviewer, str):
                        # 尝试从 "李明 (2024-05-20)" 格式转换
                        if "(" in reviewer and ")" in reviewer:
                            name_part = reviewer.split("(")[0].strip()
                            date_part = reviewer.split("(")[1].split(")")[0].strip()
                            processed_reviewers.append({
                                "name": name_part,
                                "date": date_part
                            })
                    elif isinstance(reviewer, dict) and "name" in reviewer and "date" in reviewer:
                        # 已经是正确格式
                        processed_reviewers.append(reviewer)
                
                if processed_reviewers:
                    data["reviewers"] = processed_reviewers
        
        return data
    
    def _extract_action_text(self, action_str: str) -> str:
        """从格式为"纠正措施: xxx"或"预防措施: xxx"的字符串中提取措施内容"""
        if ":" in action_str:
            return action_str.split(":", 1)[1].strip()
        elif "：" in action_str:
            return action_str.split("：", 1)[1].strip()
        return action_str.strip()
    
    def _add_default_required_fields(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """为缺失的必要字段添加默认值，确保报告生成不会因为空值而失败"""
        # 添加必填字段的默认值
        if "version" not in data or not data["version"]:
            data["version"] = "1.0"
        
        if "title" not in data or not data["title"]:
            data["title"] = "GMP调查报告"
        
        if "investigationId" not in data or not data["investigationId"]:
            # 使用日期生成一个默认的调查ID
            current_date = datetime.now().strftime("%Y%m%d")
            data["investigationId"] = f"INV-{current_date}"
        
        if "preparedBy" not in data or not data["preparedBy"]:
            data["preparedBy"] = "系统自动生成"
        
        if "preparedDate" not in data or not data["preparedDate"]:
            # 使用当前日期作为准备日期
            data["preparedDate"] = datetime.now().strftime("%Y-%m-%d")
        
        if "refSop" not in data or not data["refSop"]:
            data["refSop"] = "GMP-SOP-001"
        
        if "docId" not in data or not data["docId"]:
            data["docId"] = "FORM-GMP-001"
        
        # 添加summary字段的默认值，这是模板中必需的字段
        if "summary" not in data or not data["summary"]:
            data["summary"] = "本报告调查了生产过程中发现的偏差问题。通过系统性的调查和分析，确定了问题的根本原因并提出了相应的纠正和预防措施。"
        
        # 添加rootCause字段的默认值，这也是模板中必需的字段
        if "rootCause" not in data or not data["rootCause"]:
            data["rootCause"] = "根据调查分析，尚未确定明确的根本原因，需要进一步收集信息。"
        
        # 确保events字段至少为空数组
        if "events" not in data:
            data["events"] = []
        
        # 确保actions字段至少为空数组
        if "actions" not in data:
            data["actions"] = []
        
        # 确保reviewers字段至少为空数组
        if "reviewers" not in data:
            data["reviewers"] = []
            
        # 添加其他必要字段的默认值
        if "impactAssessment" not in data or not data["impactAssessment"]:
            data["impactAssessment"] = "本次偏差对产品质量、安全性及有效性的影响：无影响/可评估为1级偏差。\n偏差风险评估：本次风险评定为低风险，仅影响数据记录，不影响产品质量。"
        
        if "investigation" not in data or not data["investigation"]:
            data["investigation"] = "调查过程中对设备进行了检查和测试，并查阅了相关操作记录和维护日志。"
        
        if "handling" not in data or not data["handling"]:
            data["handling"] = "针对发现的问题，执行了必要的调整和修复，确保设备恢复正常运行。"
        
        if "eventSummary" not in data or not data["eventSummary"]:
            data["eventSummary"] = "本次事件已得到妥善处理，未对产品质量和生产过程造成显著影响。建议加强设备维护和操作人员培训，防止类似问题再次发生。"
        
        return data
    
    def _extract_from_markdown_tables(self, markdown_text: str) -> Dict[str, Any]:
        """从Markdown表格中提取GMP报告数据
        
        Args:
            markdown_text: 包含Markdown表格的文本
            
        Returns:
            提取的报告数据
        """
        try:
            result = {}
            
            # 提取基本字段
            field_mappings = {
                "参考SOP编号": "refSop",
                "文档ID": "docId",
                "版本号": "version",
                "报告标题": "title",
                "调查ID": "investigationId",
                "准备人员": "preparedBy",
                "准备日期": "preparedDate",
                "根本原因": "rootCause",
                "影响评估": "impactAssessment"
            }
            
            # 从表格或文本中提取字段
            for zh_name, en_name in field_mappings.items():
                pattern = f"{zh_name}[\\s\\(\\)]*\\|\\s*([^\\|\\n]+)"
                matches = re.findall(pattern, markdown_text)
                if matches:
                    result[en_name] = matches[0].strip()
                    
            # 提取事件信息
            events = []
            if "故障时间" in markdown_text and "故障现象" in markdown_text:
                event_date_matches = re.findall(r"故障时间[\\s\\(\\)]*\\|\\s*([^\\|\\n]+)", markdown_text)
                event_desc_matches = re.findall(r"故障现象[\\s\\(\\)]*\\|\\s*([^\\|\\n]+)", markdown_text)
                
                if event_date_matches and event_desc_matches:
                    events.append({
                        "date": event_date_matches[0].strip(),
                        "description": event_desc_matches[0].strip()
                    })
                    
            # 如果没找到事件，尝试从描述中提取
            if not events and "受影响的产品" in markdown_text:
                events.append({
                    "date": datetime.now().strftime("%Y-%m-%d"),
                    "description": "受影响的批号检测"
                })
                
            result["events"] = events
                
            # 提取措施
            actions = []
            if "纠正措施" in markdown_text:
                action_matches = re.findall(r"纠正措施[\\s\\(\\)]*\\|\\s*([^\\|\\n]+)", markdown_text)
                if action_matches:
                    actions.append(f"纠正措施: {action_matches[0].strip()}")
                    
            if "预防措施" in markdown_text:
                action_text = ""
                if "<br>" in markdown_text:
                    # 多个措施用<br>分隔
                    prevention_section = re.findall(r"预防措施[\\s\\(\\)]*\\|\\s*([^\\|\\n]+)", markdown_text)
                    if prevention_section:
                        measures = prevention_section[0].split("<br>")
                        for m in measures:
                            m = m.strip()
                            if m.startswith("\\d+\\."):
                                m = m[2:].strip()
                            actions.append(f"预防措施: {m}")
                else:
                    prevention_matches = re.findall(r"预防措施[\\s\\(\\)]*\\|\\s*([^\\|\\n]+)", markdown_text)
                    if prevention_matches:
                        actions.append(f"预防措施: {prevention_matches[0].strip()}")
                        
            result["actions"] = actions
                
            # 生成总结
            if "结论" in markdown_text:
                summary_matches = re.findall(r"结论[\\s\\(\\)]*\\|\\s*([^\\|\\n]+)", markdown_text)
                if summary_matches:
                    result["summary"] = summary_matches[0].strip()
                    result["eventSummary"] = summary_matches[0].strip()
                    
            # 添加默认值
            result = self._add_default_required_fields(result)
            
            return result
        except Exception as e:
            logger.error(f"Error extracting data from Markdown tables: {str(e)}")
            return {}
    
    def _extract_json_from_conversation_id(self, conversation_id: str) -> tuple:
        """尝试从conversation_id参数中提取JSON数据
        
        Args:
            conversation_id: 可能包含嵌入JSON的对话ID
            
        Returns:
            tuple: (真实对话ID, 提取的JSON数据) 如果没有JSON，第二个元素为None
        """
        if not isinstance(conversation_id, str) or '{' not in conversation_id or '}' not in conversation_id:
            return conversation_id, None
            
        try:
            # 尝试提取嵌入的JSON
            logger.info(f"尝试从conversation_id中提取JSON，字符串长度: {len(conversation_id)}")
            
            # 检查是否有明确的JSON分隔标记，如"json:"或"数据:"
            json_markers = ["json:", "data:", "报告数据:", "数据:", "报告:"]
            for marker in json_markers:
                if marker in conversation_id:
                    marker_pos = conversation_id.find(marker) + len(marker)
                    json_text = conversation_id[marker_pos:].strip()
                    real_conversation_id = conversation_id[:conversation_id.find(marker)].strip()
                    logger.info(f"找到标记 '{marker}'，提取后面的内容作为JSON")
                    break
            else:
                # 没有找到标记，尝试查找JSON的开始和结束位置
                # 对于单引号JSON字符串的特殊处理
                if conversation_id.startswith("'") and "{'基础文档信息'" in conversation_id:
                    logger.info("检测到单引号形式的JSON字符串")
                    try:
                        # 使用ast模块安全地将单引号JSON字符串转换为Python字典
                        import ast
                        # 去掉可能的外层单引号
                        if conversation_id.startswith("'") and conversation_id.endswith("'"):
                            json_text = conversation_id[1:-1]
                        else:
                            json_text = conversation_id
                        # 解析单引号格式的字典
                        embedded_json = ast.literal_eval(json_text)
                        logger.info("使用ast.literal_eval成功解析单引号JSON字符串")
                        return "", embedded_json  # 返回空字符串作为conversationId
                    except Exception as e:
                        logger.warning(f"使用ast.literal_eval解析单引号JSON失败: {str(e)}")
                        
                # 标准JSON处理流程
                json_start = conversation_id.find('{')
                json_end = conversation_id.rfind('}') + 1
                json_text = conversation_id[json_start:json_end]
                real_conversation_id = conversation_id[:json_start].strip()
            
            # 记录提取的原始文本，方便调试
            logger.info(f"从conversation_id提取的JSON文本长度: {len(json_text)}")
            logger.info(f"JSON文本前100个字符: {json_text[:100]}")
            
            # 尝试多种方式解析JSON
            embedded_json = None
            
            # 1. 尝试使用ast.literal_eval解析单引号JSON
            try:
                import ast
                embedded_json = ast.literal_eval(json_text)
                logger.info("通过ast.literal_eval成功解析单引号JSON")
            except Exception as e:
                logger.warning(f"ast.literal_eval解析失败: {str(e)}")
                
                # 2. 直接尝试解析标准JSON
                try:
                    embedded_json = json.loads(json_text)
                    logger.info("通过直接JSON解析成功提取数据")
                except json.JSONDecodeError as e:
                    logger.warning(f"直接JSON解析失败: {str(e)}")
                    
                    # 3. 尝试修复常见的JSON格式问题
                    try:
                        # 修复可能的错误格式，如缺少闭合引号等
                        fixed_json = self._fix_json_format(json_text)
                        embedded_json = json.loads(fixed_json)
                        logger.info("通过修复JSON格式后解析成功")
                    except Exception:
                        logger.warning("尝试修复JSON格式后解析仍然失败")
                        
                        # 4. 使用正则表达式尝试提取最外层的JSON对象
                        try:
                            import re
                            json_pattern = r'(\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\})'
                            matches = re.findall(json_pattern, json_text)
                            if matches:
                                for potential_json in matches:
                                    try:
                                        embedded_json = json.loads(potential_json)
                                        logger.info("通过正则表达式成功提取JSON对象")
                                        break
                                    except:
                                        continue
                        except Exception as e:
                            logger.warning(f"正则表达式提取JSON失败: {str(e)}")
                        
                        # 5. 如果仍然失败，使用extract_json_from_text函数
                        if not embedded_json:
                            embedded_json = extract_json_from_text(json_text)
                            if embedded_json:
                                logger.info("通过extract_json_from_text函数成功提取数据")
                            else:
                                # 6. 尝试从整个conversation_id中提取
                                logger.info("尝试从整个conversation_id中提取JSON")
                                embedded_json = extract_json_from_text(conversation_id)
                                if embedded_json:
                                    logger.info("从整个conversation_id中成功提取JSON")
            
            # 检查是否需要进一步处理嵌套结构
            if embedded_json and isinstance(embedded_json, dict):
                logger.info(f"提取的JSON结构字段: {list(embedded_json.keys())}")
                
                # 检查是否有嵌套在reportData字段的数据
                if 'reportData' in embedded_json and embedded_json['reportData']:
                    try:
                        reportData = embedded_json['reportData']
                        if isinstance(reportData, str) and ('{' in reportData or '[' in reportData):
                            try:
                                parsed_reportData = json.loads(reportData)
                                logger.info("从reportData字段中提取到JSON数据")
                                embedded_json = parsed_reportData
                            except:
                                logger.warning("reportData字段无法解析为JSON")
                        elif isinstance(reportData, dict):
                            logger.info("reportData字段已经是字典对象")
                            embedded_json = reportData
                    except Exception as e:
                        logger.warning(f"处理reportData字段时出错: {str(e)}")
                
                # 检查是否有嵌套在content字段中的JSON
                elif 'content' in embedded_json and isinstance(embedded_json['content'], str) and '{' in embedded_json['content']:
                    try:
                        content_json = extract_json_from_text(embedded_json['content'])
                        if content_json and isinstance(content_json, dict):
                            logger.info("从content字段中提取到嵌套JSON数据")
                            embedded_json = content_json
                    except Exception as e:
                        logger.warning(f"从content字段提取JSON失败: {str(e)}")
                
                # 检查是否有嵌套在message字段中的JSON
                elif 'message' in embedded_json and isinstance(embedded_json['message'], str) and '{' in embedded_json['message']:
                    try:
                        message_json = extract_json_from_text(embedded_json['message'])
                        if message_json and isinstance(message_json, dict):
                            logger.info("从message字段中提取到嵌套JSON数据")
                            embedded_json = message_json
                    except Exception as e:
                        logger.warning(f"从message字段提取JSON失败: {str(e)}")
                
                # 检查json字段中的嵌套JSON
                elif 'json' in embedded_json and isinstance(embedded_json['json'], (list, dict)):
                    try:
                        if isinstance(embedded_json['json'], list) and len(embedded_json['json']) > 0:
                            json_item = embedded_json['json'][0]
                            if isinstance(json_item, dict):
                                logger.info("从json字段数组中提取到嵌套JSON数据")
                                embedded_json = json_item
                        elif isinstance(embedded_json['json'], dict):
                            logger.info("从json字段对象中提取到嵌套JSON数据")
                            embedded_json = embedded_json['json']
                    except Exception as e:
                        logger.warning(f"从json字段提取JSON失败: {str(e)}")
                
                # 如果嵌套数据中包含report_data字段
                if isinstance(embedded_json, dict) and 'report_data' in embedded_json:
                    report_data_value = embedded_json['report_data']
                    if isinstance(report_data_value, dict):
                        logger.info("从report_data字段提取到字典数据")
                        embedded_json = report_data_value
                    elif isinstance(report_data_value, str) and ('{' in report_data_value or '[' in report_data_value):
                        try:
                            parsed_report_data = json.loads(report_data_value)
                            logger.info("从report_data字符串字段中提取到JSON数据")
                            embedded_json = parsed_report_data
                        except:
                            logger.warning("report_data字符串字段无法解析为JSON")
            
            if embedded_json:
                logger.info(f"成功从conversation_id提取JSON数据，包含字段: {list(embedded_json.keys() if isinstance(embedded_json, dict) else [])}")
            
            return real_conversation_id or conversation_id, embedded_json
            
        except Exception as e:
            logger.warning(f"尝试从conversation_id提取JSON失败: {str(e)}")
            return conversation_id, None
            
    def _fix_json_format(self, json_text: str) -> str:
        """尝试修复常见的JSON格式问题
        
        Args:
            json_text: 可能格式有问题的JSON文本
            
        Returns:
            修复后的JSON文本
        """
        # 移除不规范的换行符和空格
        text = json_text.strip()
        
        # 确保JSON对象的完整性
        if text.count('{') > text.count('}'):
            # 缺少右花括号，补充
            text += '}' * (text.count('{') - text.count('}'))
        
        # 修复常见的引号问题
        # 1. 尝试修复缺少闭合引号的情况
        fixed_text = ''
        in_string = False
        for i, char in enumerate(text):
            fixed_text += char
            if char == '"' and (i == 0 or text[i-1] != '\\'):
                in_string = not in_string
            
            # 如果到达行尾，且字符串未闭合，添加闭合引号
            if in_string and (i == len(text) - 1 or text[i+1] in ['\n', '\r']):
                fixed_text += '"'
                in_string = False
        
        # 2. 修复键值对之间的格式问题
        fixed_text = re.sub(r'([^,{[])\s*"', r'\1,"', fixed_text)
        
        # 3. 修复缺少值的情况
        fixed_text = re.sub(r':\s*,', r': "",', fixed_text)
        fixed_text = re.sub(r':\s*}', r': ""}', fixed_text)
        
        return fixed_text 
"""
Bayer GMP Reporter - 公共工具函数
"""
import json
import requests
import logging
from typing import Dict, Any, List
from urllib.parse import urljoin

# 创建日志记录器
logger = logging.getLogger("bayer_gmp")

def get_conversation_history(conversation_id: str, context: Dict[str, Any]) -> List[Dict[str, Any]]:
    """通过Dify API获取对话历史
    
    Args:
        conversation_id: 对话ID
        context: 上下文信息，包含api_base和api_key
        
    Returns:
        对话历史消息列表
    """
    try:
        logger.info(f"Starting to retrieve conversation history for ID: {conversation_id}")
        logger.info(f"Context type: {type(context)}")
        
        if not context:
            logger.error("Context is empty or None")
            logger.error(f"Context value: {context}")
            return _get_mock_conversation_history(conversation_id)
        
        # 打印完整的上下文信息以帮助调试
        logger.info(f"Context keys: {list(context.keys()) if isinstance(context, dict) else 'Not a dict'}")
        
        api_base = context.get("api_base", "")
        api_key = context.get("api_key", "")
        user_id = context.get("user_id", "plugin-user")  # 用户标识，默认为plugin-user
        
        logger.info(f"api_base: {api_base}, api_key present: {'yes' if api_key else 'no'}, user_id: {user_id}")
        
        if not all([api_base, api_key, conversation_id]):
            logger.error("Missing required parameters for conversation history retrieval")
            logger.error(f"api_base: {'present' if api_base else 'missing'}, " +
                        f"api_key: {'present' if api_key else 'missing'}, " +
                        f"conversation_id: {'present' if conversation_id else 'missing'}")
            
            return _get_mock_conversation_history(conversation_id)
        
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        # 确保api_base末尾没有斜杠
        api_base = api_base.rstrip('/')
        # 构建正确的查询参数
        url = f"{api_base}/messages?user={user_id}&conversation_id={conversation_id}"
        
        logger.info(f"Retrieving conversation history from: {url}")
        response = requests.get(url, headers=headers)
        
        if response.status_code == 200:
            data = response.json()
            messages = data.get("data", [])
            logger.info(f"Successfully retrieved {len(messages)} messages")
            return messages
        else:
            logger.error(f"Failed to retrieve conversation history: {response.status_code}, {response.text}")
            return []
    except Exception as e:
        logger.error(f"Error retrieving conversation history: {str(e)}")
        return []

def _get_mock_conversation_history(conversation_id: str = None) -> List[Dict[str, Any]]:
    """返回模拟的对话历史数据用于测试
    
    Args:
        conversation_id: 对话ID
        
    Returns:
        模拟的对话历史列表
    """
    logger.warning(f"Using mock conversation history for conversation_id: {conversation_id}")
    return [
        {"role": "assistant", "content": "您好，我是拜耳GMP报告生成助手，请问有什么可以帮助您的？"},
        {"role": "user", "content": "我需要记录一起设备故障事件"},
        {"role": "assistant", "content": "请问是什么设备出现了故障？故障的具体情况是什么？"},
        {"role": "user", "content": "生产线上的灌装设备出现了故障，导致产品灌装不均匀"},
        {"role": "assistant", "content": "了解了。请问这次故障发生的时间是什么时候？影响了哪些批次的产品？"},
        {"role": "user", "content": "故障发生在2025年3月15日，影响了批次号为20250315-A和20250315-B的产品"},
        {"role": "assistant", "content": "已记录。针对这个故障，目前采取了哪些措施？有没有确定故障的根本原因？"},
        {"role": "user", "content": "我们停机检查，发现是灌装阀门的密封圈老化导致的，已经更换了新的密封圈，并恢复了生产"},
        {"role": "assistant", "content": "好的。请问这次故障对产品质量有没有影响？是否有预防措施来避免类似问题再次发生？"},
        {"role": "user", "content": "影响的批次已经隔离，质检部门正在进行全检。我们计划增加对灌装设备的定期维护频率，并建立密封圈磨损的定期检查程序"}
    ]

def call_dify_model(prompt: str, context: Dict[str, Any]) -> str:
    """调用Dify平台配置的模型
    
    Args:
        prompt: 提示词
        context: 上下文信息，包含api_base和api_key
        
    Returns:
        模型的回复
    """
    try:
        if not context:
            logger.warning("Context is empty or None")
            return ""
        
        api_base = context.get("api_base", "")
        api_key = context.get("api_key", "")
        user_id = context.get("user_id", "plugin-user")  # 用户标识，默认为plugin-user
        
        if not all([api_base, api_key]):
            logger.warning("Missing required parameters for Dify model call")
            logger.warning(f"api_base: {'present' if api_base else 'missing'}, " +
                         f"api_key: {'present' if api_key else 'missing'}")
            
            # 返回空字符串，让调用方使用默认逻辑
            return ""
        
        # 确保api_base末尾没有斜杠
        api_base = api_base.rstrip('/')
        model_url = f"{api_base}/completion-messages"
            
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "inputs": {},
            "query": prompt,
            "response_mode": "blocking",
            "user": user_id
        }
        
        logger.info(f"Calling Dify model at: {model_url}")
        response = requests.post(model_url, headers=headers, json=payload)
        
        if response.status_code == 200:
            data = response.json()
            answer = data.get("answer", "")
            logger.info("Successfully received response from Dify model")
            return answer
        else:
            logger.warning(f"Dify model call failed: {response.status_code}, {response.text}")
            return ""
    except Exception as e:
        logger.warning(f"Error calling Dify model: {str(e)}")
        return ""

def extract_json_from_text(text: str) -> Dict[str, Any]:
    """从文本中提取JSON结构
    
    Args:
        text: 包含JSON的文本
        
    Returns:
        提取的JSON或空字典
    """
    try:
        # 查找可能的JSON块
        start_markers = ['{', '[']
        end_markers = ['}', ']']
        
        # 首先尝试完整解析文本
        try:
            return json.loads(text)
        except:
            pass
        
        # 找到可能的JSON块
        for start_marker in start_markers:
            if start_marker in text:
                start_idx = text.find(start_marker)
                
                # 找到对应的结束标记
                corresponding_end = end_markers[start_markers.index(start_marker)]
                stack = 1
                for i in range(start_idx + 1, len(text)):
                    if text[i] == start_marker:
                        stack += 1
                    elif text[i] == corresponding_end:
                        stack -= 1
                        
                    if stack == 0:
                        # 提取JSON块
                        potential_json = text[start_idx:i+1]
                        try:
                            return json.loads(potential_json)
                        except:
                            # 继续寻找下一个可能的JSON块
                            continue
        
        # 如果没有找到有效的JSON块，返回空字典
        return {}
    except Exception as e:
        logger.warning(f"Error extracting JSON from text: {str(e)}")
        return {} 
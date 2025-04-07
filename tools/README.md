# GMP意图检测工具

## 简介
GMP意图检测工具用于分析对话消息，检测用户是否有生成或下载GMP报告的意图。
该工具作为Dify插件集成，通过分析用户消息中的关键词和上下文判断用户意图。

## 主要特性
- 检测两种主要意图：生成GMP报告和下载GMP报告
- 基于关键词匹配和权重计算得出置信度
- 提供重置机制，在用户输入非GMP相关内容时重置之前的意图
- 支持多轮对话中的意图跟踪和更新

## 工作原理

### 意图检测
1. 从对话历史中提取用户消息
2. 分析消息内容中的关键词
3. 根据关键词匹配和权重计算意图置信度
4. 根据置信度确定最终意图类型
5. 返回包含意图信息的结果

### 重置机制
为了确保意图检测的准确性，当用户输入与GMP不相关的内容时，系统会重置之前检测到的意图。重置机制基于以下条件：

1. 最近一条用户消息不包含GMP相关内容
2. 意图检测置信度低于阈值(0.3)
3. 未检测到明确的意图

重置结果会包含`reset`标志，表明之前的意图已被清除。

### 调用示例
```python
parameters = {
    "conversation_id": "conversation_123",
    "message_limit": 5,
    "threshold": 0.4
}

# 创建检测器实例
detector = GMPIntentDetector()

# 调用检测方法
results = list(detector._invoke(parameters))

# 处理结果
for result in results:
    print(result)
```

## 开发和测试

### 安装依赖
```
pip install -r requirements.txt
```

### 运行测试
```
python test_reset_simplified.py  # 测试重置机制
python test_reset_integration.py  # 测试集成场景
```

## 常见问题

### Q: 如何调整意图检测的敏感度？
A: 调整`threshold`参数可以改变意图检测的敏感度，值越低越敏感，默认为0.4。

### Q: 如何添加新的关键词？
A: 在`GENERATE_INTENT_KEYWORDS`和`DOWNLOAD_INTENT_KEYWORDS`中添加新的关键词及其权重。 
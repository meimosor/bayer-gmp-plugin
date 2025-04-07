# Dify工作流配置指南

本文档提供了关于如何配置Dify工作流来生成GMP报告的详细说明。

## 配置工具

在Dify中，需要配置以下三个工具来生成GMP报告。

### 1. 提取数据工具 (gmp_extract_data)

**工具名称:** gmp_extract_data

**描述:** 从Spring API获取报告数据

**参数:**
- report_id: 报告ID (string)
- report_type: 报告类型 (string)
- spring_api_url: Spring API URL (string, 可选)
- api_key: Spring API密钥 (string, 可选)

**示例调用:**
```python
gmp_extract_data(report_id="1234", report_type="DIRECT", spring_api_url="http://localhost:8080", api_key="your-api-key")
```

### 2. 生成PDF工具 (gmp_generate_pdf)

**工具名称:** gmp_generate_pdf

**描述:** 根据提取的数据生成PDF报告

**参数:**
- report_data: 报告数据 (object)
- report_id: 报告ID (string, 可选)
- spring_api_url: Spring API URL (string, 可选)
- api_key: Spring API密钥 (string, 可选)
- conversation_id: 对话ID (string, 可选)，如果report_data为空，将自动使用此ID重新提取数据

**示例调用:**
```python
# 方式1：直接提供报告数据
gmp_generate_pdf(report_data=report_data, report_id="1234", spring_api_url="http://localhost:8080", api_key="your-api-key")

# 方式2：只提供conversation_id，由工具自动提取数据(推荐)
gmp_generate_pdf(conversation_id=sys.conversation_id, spring_api_url="http://localhost:8080", api_key="your-api-key")
```

### 3. 预览报告工具 (gmp_preview_report)

**工具名称:** gmp_preview_report

**描述:** 生成报告预览HTML

**参数:**
- report_data: 报告数据 (object)

**示例调用:**
```python
gmp_preview_report(report_data=report_data)
```

## Markdown格式输出模板

在Dify中，使用以下格式输出生成的PDF报告的下载链接：

```markdown
# GMP报告生成成功

报告ID: {{report_id}}
报告类型: {{report_type}}

## 下载链接

- {{markdown_download_link}}
- {{markdown_simple_pdf_link}}

## 预览报告

{{preview_html}}
```

**重要说明：**
- HTML格式使用`download_link`和`simple_pdf_link`字段
- Markdown格式使用`markdown_download_link`和`markdown_simple_pdf_link`字段
- **Markdown格式链接必须包含`title`属性以确保能正确下载PDF**，格式为：`[链接文本](数据URL "filename.pdf")`
- 请勿直接使用`pdf_data`字段

## 故障排除

如果PDF下载链接不正常工作，可能的原因包括：

1. **Markdown链接格式不正确**：
   - 确保Markdown格式的下载链接包含title属性（文件名）
   - 正确格式：`[下载PDF报告](data:application/pdf;base64,BASE64_DATA "filename.pdf")`
   - 错误格式：`[下载PDF报告](data:application/pdf;base64,BASE64_DATA)`

2. **浏览器安全设置**：有些浏览器会出于安全原因阻止基于data URI的下载
   - 尝试使用不同的浏览器
   - 检查浏览器的安全设置
   - 确认是否有浏览器扩展阻止了下载

3. **PDF数据不完整或格式错误**：确保Base64编码的数据是完整的PDF文件
   - 测试下载简单PDF链接（`markdown_simple_pdf_link`）是否可用
   - 如果简单PDF可以打开但Spring PDF不能，则问题可能在Spring应用程序生成的PDF中

4. **Dify环境限制**：某些Dify环境可能限制数据URI的大小
   - 尝试生成更小的PDF文件
   - 联系Dify管理员了解最大允许的数据URI大小

5. **参数传递错误**：工作流节点间的数据传递错误
   - 错误现象：收到"缺少必要参数：报告数据"的错误信息
   - 可能原因：
     - 生成PDF节点的`report_data`参数为空字符串而不是对象
     - `report_data`参数值设置不正确，没有正确引用提取数据节点的输出
   - 解决方案：
     - 检查生成PDF节点的参数设置，确保`report_data`设置为`{{提取GMP报告数据.json[0].report_data}}`
     - 检查提取数据节点的输出格式，确保包含`report_data`字段
     - 查看Dify表达式语法是否正确，以及节点名称是否与表达式中使用的一致

## 工作流触发示例

以下是在Dify中创建工作流的步骤：

1. 创建一个新的工作流
2. 添加用户意图识别节点:
   - **意图标签**: generate_gmp_report
   - **示例表达式**:
     - "我需要生成GMP报告"
     - "请帮我生成一份GMP调查报告"
     - "生成报告"
     - "基于我们的对话生成GMP报告"

3. 添加工具调用节点 - 提取数据:
   - 选择 `gmp_extract_data` 工具
   - 设置 `conversation_id` 为 `sys.conversation_id`

4. 添加条件分支:
   - **条件**: `{{提取GMP报告数据.json[0].success}} == true`
   - **成功分支**: 继续到预览或PDF生成
   - **失败分支**: 返回错误消息

5. 添加工具调用节点 - 预览报告:
   - 选择 `gmp_preview_report` 工具
   - 设置 `report_data` 为 `{{提取GMP报告数据.json[0].report_data}}`

6. 添加工具调用节点 - 生成PDF:
   - 选择 `gmp_generate_pdf` 工具
   - **方式1**(传统方式): 
     - 设置 `report_data` 为 `{{提取GMP报告数据.json[0].report_data}}`
     - **重要**: 确保这里使用的是对象而不是字符串，Dify会自动处理JSON对象
     - **注意**: 请勿使用 `{{提取GMP报告数据}}` 作为整体传递，这会导致嵌套结构错误
     - **错误示例**: 如果参数设置为 `"report_data": "{{提取GMP报告数据}}"` 或 `"report_data": ""` 会导致数据传递错误
   
   - **方式2**(推荐方式): 
     - 由于Dify界面显示`report_data`为必填参数，请按以下设置:
     - 设置 `report_data` 为 `""`（空字符串）或 `{}`（空对象）
     - 设置 `conversation_id` 为 `sys.conversation_id`
     - 插件将忽略空的report_data，自动通过conversation_id重新提取数据
     - 这种方式更稳定，可以避免复杂的数据传递问题

> **特别说明**: 
> 在JSON响应中，data.json[0].report_data是真正需要的报告数据对象。如果直接传递整个提取GMP报告数据节点的输出，生成PDF节点将收到嵌套的JSON对象而非所需的report_data内容，导致"缺少必要参数"错误。
> 
> **关于必填参数**：虽然Dify界面显示`report_data`为必填参数，但我们的插件已增强，支持传入空字符串，此时会自动使用`conversation_id`提取数据。这样，方式2实际上变成：设置`report_data`为空，同时提供`conversation_id`。
> 
> **推荐使用方式2**，即传递空的report_data和有效的conversation_id，让插件自行提取数据，可以最大限度地避免数据传递问题。这种方式只需要保证提取数据工具能正常工作即可。

7. **设置PDF下载链接模板**:
   - **关键**: 在生成PDF步骤后，使用以下方式输出下载链接:
   - **HTML格式输出模板** (适用于支持HTML渲染的场景): 
     ```
     如需进一步修改或补充报告内容，请告知。
     
     如果一切正确，我们已生成最终的GMP调查报告。
     
     1. {{生成GMP报告PDF.json[0].download_link}}
     
     2. {{生成GMP报告PDF.json[0].simple_pdf_link}}
     
     {{生成GMP报告PDF.json[0].comparison_message}}
     ```
   
   - **Markdown格式输出模板** (适用于仅支持Markdown的场景):
     ```
     如需进一步修改或补充报告内容，请告知。
     
     如果一切正确，我们已生成最终的GMP调查报告。
     
     1. {{生成GMP报告PDF.json[0].markdown_download_link}}
     
     2. {{生成GMP报告PDF.json[0].markdown_simple_pdf_link}}
     
     {{生成GMP报告PDF.json[0].comparison_message}}
     ```
   
   - **注意**: 
     - HTML格式使用`download_link`和`simple_pdf_link`字段
     - Markdown格式使用`markdown_download_link`和`markdown_simple_pdf_link`字段
     - Markdown格式的链接包含`title`属性，确保PDF能正确下载，格式为：`[链接文字](数据URL "文件名.pdf")`
     - 不要使用原始的`pdf_data`字段
   - **对比测试**: 如果简单PDF可以打开但Spring PDF不行，则问题出在Spring应用的PDF生成上

## 调试提示

如果工具调用失败，检查以下内容：

1. **上下文变量**: 确保 `sys.conversation_id` 正确传递
2. **凭证配置**: 检查Spring应用的API密钥和URL是否正确配置
3. **日志检查**: 查看插件的日志输出，寻找详细错误信息
4. **手动测试**: 使用 `test_dify_integration.py` 脚本测试插件调用

## 常见错误及解决方案

1. **"context"属性错误**: 
   - 原因: 插件工具类未正确初始化或参数传递有误
   - 解决: 确保工具类实现了正确的初始化方法，接受runtime和session参数

2. **对话历史获取失败**:
   - 原因: API密钥权限不足或conversation_id无效
   - 解决: 验证API密钥和conversation_id

3. **数据提取失败**:
   - 原因: 对话内容不足以提取完整报告数据
   - 解决: 引导用户提供更多信息，或使用默认数据回退

4. **PDF下载链接不显示或未正确渲染**:
   - 原因1: 使用了原始的`pdf_data`字段，而非链接字段
   - 解决1: 在流程配置中，确保使用`download_link`(HTML格式)或`markdown_download_link`(Markdown格式)
   - 原因2: Dify不支持渲染HTML内容
   - 解决2: 使用Markdown格式的链接字段(`markdown_download_link`和`markdown_simple_pdf_link`)
   - 原因3: Markdown链接未正确识别
   - 解决3: 确保使用带`title`属性的Markdown链接格式 `[链接文字](数据URL "文件名.pdf")`
   - 原因4: 浏览器安全设置阻止了数据URI链接
   - 解决4: 检查浏览器安全设置，或考虑将PDF保存到临时服务器并提供常规URL链接

5. **"缺少必要参数：报告数据"错误**:
   - 原因1: 生成PDF节点的`report_data`参数为空字符串而不是对象
   - 原因2: 工作流中节点之间的变量引用语法错误
   - 解决1: 在生成PDF节点中，将`report_data`参数设置为`{{提取GMP报告数据.json[0].report_data}}`
   - 解决2: 检查工作流节点名称是否与参数引用中的名称一致 
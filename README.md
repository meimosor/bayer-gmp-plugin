# 拜耳GMP报告生成器插件

这是一个为Dify平台设计的插件，用于从对话历史中提取GMP调查报告数据并生成标准化的PDF报告。

## 功能特点

- **数据提取**：从对话历史中分析并提取结构化的GMP报告数据
- **PDF报告生成**：根据提取的数据生成标准化的GMP调查报告PDF
- **HTML报告预览**：在生成PDF前预览报告的HTML版本
- **AI模型增强**：优先使用Dify平台模型，本地逻辑作为备选

## 安装要求

- Python 3.12或更高版本
- Dify平台访问权限
- Spring后端服务（用于PDF生成）

## 安装步骤

1. 下载并安装插件包
2. 在Dify平台中添加插件
3. 配置Spring应用API密钥和URL

## 开发与调试

1. 复制`.env.example`为`.env`并填写相应的值
2. 安装依赖：`pip install -r requirements.txt`
3. 运行：`python -m main`

## 测试指南

### 一键测试脚本

我们提供了一个一键式测试脚本，可帮助您快速验证插件的全部功能：

```bash
python run_tests.py
```

该脚本将自动执行以下步骤：
1. 测试Spring后端连接
2. 启动插件服务器
3. 测试三个工具功能
4. 生成测试报告

命令行选项：
- `--port`: 指定插件服务端口 (默认: 5003)
- `--api-key`: 指定Spring应用API密钥
- `--spring-url`: 指定Spring应用URL
- `--output-dir`: 指定测试输出目录 (默认: ./test_output)
- `--skip-spring-test`: 跳过Spring连接测试
- `--real-data`: 使用真实对话数据而非示例数据
- `--conversation-id`: 指定测试对话ID (与--real-data一起使用)

示例：
```bash
python run_tests.py --spring-url http://spring-backend.example.com --api-key my_api_key
```

### 单独测试脚本

您也可以单独运行各个测试脚本：

1. **测试Spring后端连接**：
   ```bash
   python test_spring_connection.py
   ```

2. **测试插件工具**：
   ```bash
   python test_tools.py --sample-data
   ```

### 本地调试测试

1. **环境准备**：
   - 确保Spring后端服务正在运行（默认地址：`http://localhost:8080`）
   - 在`.env`文件中配置正确的`SPRING_APP_URL`和调试凭证

2. **启动本地调试服务器**：
   ```bash
   cd bayer-gmp-plugin
   python -m main
   ```
   
3. **手动测试数据提取工具**：
   - 使用类似Postman的工具发送POST请求到`http://localhost:5003/tools/bayer_gmp/gmp_extract_data`
   - 请求体示例：
     ```json
     {
       "params": {
         "conversation_id": "your_test_conversation_id"
       },
       "credentials": {
         "spring_app_api_key": "your_api_key",
         "spring_app_url": "http://localhost:8080"
       }
     }
     ```

4. **测试PDF生成工具**：
   - 发送POST请求到`http://localhost:5003/tools/bayer_gmp/gmp_generate_pdf`
   - 请求体示例：
     ```json
     {
       "params": {
         "report_data": {
           "refSop": "GMP-SOP-001",
           "docId": "FORM-GMP-001",
           "version": "1.0",
           "title": "GMP调查报告",
           "investigationId": "INV-20250328",
           "preparedBy": "测试用户",
           "preparedDate": "2025-03-28",
           "summary": "这是一个测试报告",
           "rootCause": "测试根本原因",
           "impactAssessment": "无影响",
           "events": [
             {"date": "2025-03-28", "description": "测试事件"}
           ],
           "actions": ["测试措施1", "测试措施2"],
           "reviewers": [
             {"name": "审核人", "date": "2025-03-28"}
           ]
         }
       },
       "credentials": {
         "spring_app_api_key": "your_api_key",
         "spring_app_url": "http://localhost:8080"
       }
     }
     ```

5. **测试HTML预览工具**：
   - 使用与PDF生成工具相同的请求体格式，但发送到`http://localhost:5003/tools/bayer_gmp/gmp_preview_report`

### Dify平台集成测试

1. **安装插件到Dify平台**：
   - 在Dify平台的插件管理页面选择"添加插件"
   - 选择从本地安装或远程安装
   - 按照提示完成安装并配置Spring应用凭证

2. **创建测试应用**：
   - 在Dify平台创建一个聊天应用
   - 在应用设置中启用拜耳GMP报告生成器插件

3. **测试对话流程**：
   - 启动聊天并进行包含GMP调查信息的对话
   - 可以使用以下测试提示：
     ```
     我需要生成一份GMP调查报告，关于生产线2号在2025年3月15日发生的设备故障。
     设备型号为XJ-201，故障表现为温度控制系统异常。
     操作人员发现故障后立即停机并通知了维修团队。
     经调查，故障原因是温度传感器老化引起的误读。
     维修团队更换了传感器并重新校准了系统。
     为防止类似问题再次发生，我们决定：
     1. 缩短传感器的检查周期从季度改为月度
     2. 更新设备维护程序，增加传感器性能检测
     3. 培训操作人员识别早期温度异常信号
     ```

4. **测试工具调用**：
   - 在对话中明确请求生成GMP报告：
     ```
     请根据我们的对话生成GMP调查报告。
     ```
   - 观察Dify平台如何调用插件工具并返回结果

5. **验证输出结果**：
   - 检查生成的PDF报告内容是否完整
   - 验证HTML预览是否正确显示
   - 确认所有关键数据字段是否被正确提取

### 调试常见问题

- **连接错误**：确保Spring后端服务正在运行且URL配置正确
- **认证失败**：验证API密钥是否正确设置
- **数据提取失败**：检查对话ID是否有效，对话内容是否包含足够的GMP相关信息
- **插件工具不可用**：在Dify平台重新启用插件或检查工具配置

## 结构说明

该插件遵循Dify插件SDK标准结构，并已经过精简优化：

```
bayer-gmp-plugin/
├── _assets/             # 共享图标资源
│   └── icon.svg         # 插件图标
├── provider/            # 提供程序定义
│   ├── bayer_gmp.py     # 提供程序实现
│   ├── bayer_gmp.yaml   # 提供程序配置
│   └── icon.svg         # 提供程序图标
├── tools/               # 工具定义
│   ├── gmp_extract_data.py      # 数据提取工具实现
│   ├── gmp_extract_data.yaml    # 数据提取工具配置
│   ├── gmp_generate_pdf.py      # PDF生成工具实现
│   ├── gmp_generate_pdf.yaml    # PDF生成工具配置
│   ├── gmp_preview_report.py    # 报告预览工具实现
│   ├── gmp_preview_report.yaml  # 报告预览工具配置
│   └── icon.svg                 # 工具图标
├── utils.py             # 公共工具模块 (NEW)
├── .env.example         # 环境变量示例
├── main.py              # 插件入口
├── manifest.yaml        # 插件清单
├── PRIVACY.md           # 隐私政策
├── README.md            # 说明文档
├── requirements.txt     # 依赖文件
├── run_tests.py         # 一键测试脚本 (NEW)
├── test_spring_connection.py # Spring连接测试脚本 (NEW)
└── test_tools.py        # 插件工具测试脚本 (NEW)
```

## 优化更新说明

与旧版相比的主要优化：

1. **结构标准化**：完全符合Dify插件SDK标准结构
2. **日志系统**：使用Dify的`logger`替代`logging`库
3. **参数验证**：增强了凭证和参数验证
4. **错误处理**：标准化的错误响应格式
5. **工具实现**：将工具实现与配置文件分离，提高可维护性
6. **模型集成**：整合Dify平台模型，提升数据处理能力
7. **代码重构**：提取公共功能到`utils.py`模块，减少重复代码
8. **精简依赖**：只保留必要的依赖项，减小包体积
9. **移除冗余**：删除了未使用的代码和文件
10. **测试工具**：添加了全面的测试脚本和一键测试功能

## Dify模型使用说明

本插件支持以下两种模型使用方式：

1. **优先使用Dify平台模型**：插件会首先尝试使用Dify平台配置的模型来提取和优化GMP报告数据
2. **回退到本地逻辑**：如果无法访问Dify模型或模型返回结果无效，插件会自动使用内置的本地逻辑处理

### 模型功能

- **数据提取**：利用模型从对话历史中提取结构化的GMP报告数据
- **数据优化**：可选择使用模型优化报告数据，使其更加专业和准确
- **参数配置**：在生成PDF时可通过`optimize_data`参数启用模型优化功能

## 联系支持

如有任何问题，请联系拜耳技术支持团队。

## 许可证

© 2025 拜耳公司，保留所有权利。 
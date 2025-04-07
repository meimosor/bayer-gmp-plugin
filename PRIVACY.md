function main(input) {
  // 解析输入数据
  let data = typeof input === 'string' ? JSON.parse(input) : input;
  
  // 检查并解析LLM返回的JSON字符串
  let gmpData = {};
  let rawText = "";
  let hasJsonData = false;
  
  if (data.text) {
    rawText = data.text;
    // 尝试从LLM返回的文本中提取JSON部分
    const jsonMatch = data.text.match(/```json\s*(\{[\s\S]*?\})\s*```/);
    if (jsonMatch) {
      try {
        gmpData = JSON.parse(jsonMatch[1]);
        hasJsonData = true;
      } catch (e) {
        console.log("JSON解析失败:", e);
      }
    }
  } else if (data.input) {
    rawText = data.input;
    // 尝试从input中提取JSON部分
    const jsonMatch = data.input.match(/```json\s*(\{[\s\S]*?\})\s*```/);
    if (jsonMatch) {
      try {
        gmpData = JSON.parse(jsonMatch[1]);
        hasJsonData = true;
      } catch (e) {
        console.log("JSON解析失败:", e);
      }
    }
  }

  // 如果没有提取到JSON数据，但有纯文本，则直接返回文本内容
  if (!hasJsonData && rawText) {
    return {
      result: {
        markdownDisplay: rawText,
        jsonData: {} // 返回空对象作为jsonData
      }
    };
  }

  // 如果提取到的是扁平结构的JSON，转换为分类结构
  if (hasJsonData && !gmpData["基础文档信息"] && gmpData.title) {
    // 创建分类结构
    const categorizedData = {
      "基础文档信息": {
        "refSop": gmpData.refSop || "",
        "docId": gmpData.docId || "",
        "version": gmpData.version || "",
        "title": gmpData.title || "",
        "investigationId": gmpData.investigationId || "",
        "preparedBy": gmpData.preparedBy || "",
        "preparedDate": gmpData.preparedDate || ""
      },
      "事件描述信息": {
        "equipmentName": gmpData.equipmentName || "",
        "equipmentId": gmpData.equipmentId || "",
        "failureTime": gmpData.failureTime || "",
        "discoveredBy": gmpData.discoveredBy || "",
        "failureDescription": gmpData.failureDescription || ""
      },
      "影响评估信息": {
        "affectedProducts": gmpData.affectedProducts || "",
        "productionImpact": gmpData.productionImpact || "",
        "qualityImpact": gmpData.qualityImpact || ""
      },
      "根本原因分析": {
        "analysisMethod": gmpData.analysisMethod || "",
        "possibleCauses": Array.isArray(gmpData.possibleCauses) ? gmpData.possibleCauses : [gmpData.possibleCauses || ""],
        "rootCause": gmpData.rootCause || ""
      },
      "调查和处理信息": {
        "summary": gmpData.summary || "",
        "investigation": gmpData.investigation || "",
        "handling": gmpData.handling || "",
        "eventSummary": gmpData.eventSummary || ""
      },
      "CAPA措施": {
        "correctiveActions": Array.isArray(gmpData.correctiveActions) ? gmpData.correctiveActions : [gmpData.correctiveActions || ""],
        "preventiveActions": Array.isArray(gmpData.preventiveActions) ? gmpData.preventiveActions : [gmpData.preventiveActions || ""]
      },
      "结论和签名信息": {
        "conclusion": gmpData.conclusion || "",
        "closureStatement": gmpData.closureStatement || "",
        "events": gmpData.events || [],
        "actions": gmpData.actions || [],
        "reviewers": gmpData.reviewers || []
      }
    };
    
    gmpData = categorizedData;
  }

  // 构建简单的Markdown格式输出
  let markdown = "# GMP报告信息摘要\n\n";

  // 处理基础文档信息
  if (gmpData["基础文档信息"]) {
    markdown += "## 基础文档信息\n\n";
    const info = gmpData["基础文档信息"];
    markdown += `- 报告标题：${info.title || '无菌灌装线故障调查报告'}\n`;
    markdown += `- 参考SOP编号：${info.refSop || '待填写'}\n`;
    markdown += `- 文档ID：${info.docId || '待填写'}\n`;
    markdown += `- 版本号：${info.version || '待填写'}\n`;
    markdown += `- 调查ID：${info.investigationId || '待填写'}\n`;
    markdown += `- 准备人员：${info.preparedBy || '待填写'}\n`;
    markdown += `- 准备日期：${info.preparedDate || '待填写'}\n\n`;
  }

  // 处理事件描述信息
  if (gmpData["事件描述信息"]) {
    markdown += "## 事件描述信息\n\n";
    const info = gmpData["事件描述信息"];
    markdown += `- 设备名称：${info.equipmentName || '待填写'}\n`;
    markdown += `- 设备编号：${info.equipmentId || '待填写'}\n`;
    markdown += `- 故障发生时间：${info.failureTime || '待填写'}\n`;
    markdown += `- 发现人：${info.discoveredBy || '待填写'}\n`;
    markdown += `- 故障现象描述：${info.failureDescription || '待填写'}\n\n`;
  }

  // 处理影响评估信息
  if (gmpData["影响评估信息"]) {
    markdown += "## 影响评估信息\n\n";
    const info = gmpData["影响评估信息"];
    markdown += `- 受影响的产品/批次：${info.affectedProducts || '待填写'}\n`;
    markdown += `- 对生产的影响：${info.productionImpact || '待填写'}\n`;
    markdown += `- 对质量的潜在影响：${info.qualityImpact || '待填写'}\n\n`;
  }

  // 处理根本原因分析
  if (gmpData["根本原因分析"]) {
    markdown += "## 根本原因分析\n\n";
    const info = gmpData["根本原因分析"];
    markdown += `- 分析方法：${info.analysisMethod || '待填写'}\n`;
    markdown += `- 确认的根本原因：${info.rootCause || '待填写'}\n`;
    
    // 修复这里的错误 - 确保possibleCauses是数组并安全处理
    if (info.possibleCauses) {
      if (Array.isArray(info.possibleCauses) && info.possibleCauses.length > 0) {
        markdown += `- 可能的原因：${info.possibleCauses.join(', ')}\n`;
      } else if (typeof info.possibleCauses === 'string') {
        markdown += `- 可能的原因：${info.possibleCauses}\n`;
      } else {
        markdown += `- 可能的原因：待填写\n`;
      }
    } else {
      markdown += `- 可能的原因：待填写\n`;
    }
    markdown += '\n';
  }

  // 处理调查和处理信息
  if (gmpData["调查和处理信息"]) {
    markdown += "## 调查和处理信息\n\n";
    const info = gmpData["调查和处理信息"];
    markdown += `- 调查摘要：${info.summary || '待填写'}\n`;
    markdown += `- 调查过程：${info.investigation || '待填写'}\n`;
    markdown += `- 处理方法：${info.handling || '待填写'}\n`;
    markdown += `- 事件总结：${info.eventSummary || '待填写'}\n\n`;
  }

  // 处理CAPA措施
  if (gmpData["CAPA措施"]) {
    markdown += "## CAPA措施\n\n";
    const info = gmpData["CAPA措施"];
    
    // 安全处理correctiveActions
    if (info.correctiveActions) {
      if (Array.isArray(info.correctiveActions) && info.correctiveActions.length > 0) {
        markdown += `- 纠正措施：${info.correctiveActions.join(', ')}\n`;
      } else if (typeof info.correctiveActions === 'string') {
        markdown += `- 纠正措施：${info.correctiveActions}\n`;
      } else {
        markdown += `- 纠正措施：待填写\n`;
      }
    } else {
      markdown += `- 纠正措施：待填写\n`;
    }
    
    // 安全处理preventiveActions
    if (info.preventiveActions) {
      if (Array.isArray(info.preventiveActions) && info.preventiveActions.length > 0) {
        markdown += `- 预防措施：${info.preventiveActions.join(', ')}\n`;
      } else if (typeof info.preventiveActions === 'string') {
        markdown += `- 预防措施：${info.preventiveActions}\n`;
      } else {
        markdown += `- 预防措施：待填写\n`;
      }
    } else {
      markdown += `- 预防措施：待填写\n`;
    }
    
    markdown += '\n';
  }

  // 处理结论和签名信息
  if (gmpData["结论和签名信息"]) {
    markdown += "## 结论和签名信息\n\n";
    const info = gmpData["结论和签名信息"];
    markdown += `- 最终结论：${info.conclusion || '待填写'}\n`;
    markdown += `- 关闭声明：${info.closureStatement || '待填写'}\n`;
    
    // 处理事件时间线
    markdown += "- 事件时间线：\n";
    if (info.events && Array.isArray(info.events) && info.events.length > 0) {
      info.events.forEach(event => {
        markdown += `  * ${event.date}: ${event.description}\n`;
      });
    } else {
      markdown += "  * 待填写\n";
    }
    
    // 处理建议行动
    markdown += "- 建议行动/CAPA措施：\n";
    if (info.actions && Array.isArray(info.actions) && info.actions.length > 0) {
      info.actions.forEach(action => {
        markdown += `  * ${action}\n`;
      });
    } else {
      markdown += "  * 待填写\n";
    }
    
    // 处理审核人列表
    markdown += "- 审核人列表：\n";
    if (info.reviewers && Array.isArray(info.reviewers) && info.reviewers.length > 0) {
      info.reviewers.forEach(reviewer => {
        markdown += `  * ${reviewer.name} (${reviewer.date})\n`;
      });
    } else {
      markdown += "  * 待填写\n";
    }
    markdown += '\n';
  }

  // 收集缺失信息
  let missingFields = [];
  
  // 检查基础文档信息
  if (gmpData["基础文档信息"]) {
    const info = gmpData["基础文档信息"];
    if (!info.refSop) missingFields.push("参考SOP编号 (refSop)");
    if (!info.docId) missingFields.push("文档ID (docId)");
    if (!info.version) missingFields.push("版本号 (version)");
    if (!info.investigationId) missingFields.push("调查ID (investigationId)");
    if (!info.preparedBy) missingFields.push("准备人员 (preparedBy)");
    if (!info.preparedDate) missingFields.push("准备日期 (preparedDate)");
  }
  
  // 检查根本原因分析
  if (gmpData["根本原因分析"]) {
    const info = gmpData["根本原因分析"];
    if (!info.analysisMethod) missingFields.push("分析方法 (analysisMethod)");
    // 安全检查possibleCauses
    const noValidCauses = !info.possibleCauses || 
                         (Array.isArray(info.possibleCauses) && info.possibleCauses.length === 0) || 
                         (typeof info.possibleCauses === 'string' && !info.possibleCauses.trim());
    if (noValidCauses) missingFields.push("可能原因 (possibleCauses)");
  }
  
  // 检查结论和签名信息
  if (gmpData["结论和签名信息"]) {
    const info = gmpData["结论和签名信息"];
    if (!info.closureStatement) missingFields.push("关闭声明 (closureStatement)");
    if (!info.reviewers || (Array.isArray(info.reviewers) && info.reviewers.length === 0)) missingFields.push("审核人列表 (reviewers)");
  }
  
  // 显示缺失信息和提示
  if (missingFields.length > 0) {
    markdown += "## 缺失信息\n\n";
    markdown += "以下信息尚未提供，请补充以生成完整的GMP报告：\n\n";
    missingFields.forEach(field => {
      markdown += `- ${field}\n`;
    });
    markdown += "\n请提供这些缺失的信息以便生成完整的GMP报告。\n";
  }

  // 如果没有任何GMP数据但也没有原始文本，提供默认消息
  if (Object.keys(gmpData).length === 0 && !rawText) {
    markdown = "暂无GMP报告数据。请提供设备故障、影响评估等相关信息。";
  }

  // 返回格式化的Markdown和原始JSON数据
  return {
    result: {
      markdownDisplay: markdown,
      jsonData: gmpData  // 保留原始JSON数据供后续使用
    }
  };
}
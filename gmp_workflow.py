#!/usr/bin/env python
"""
Bayer GMP Reporter - 命令行入口

该脚本提供了一个命令行接口，用于直接调用GMP报告生成工作流。
"""
import argparse
import json
import logging
import os
import sys
import time

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'gmp_workflow.log'))
    ]
)

logger = logging.getLogger("bayer_gmp")

# 导入工作流集成模块
from code_execution.workflow_integration import integrate_workflow

def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description='Bayer GMP Reporter命令行工具')
    
    # 必需参数
    parser.add_argument('--conversation_id', required=True, help='Dify对话ID')
    parser.add_argument('--api_key', required=True, help='Dify API密钥')
    
    # 可选参数
    parser.add_argument('--api_base', default='http://dify.xscha.com', help='Dify API基础URL（默认: http://dify.xscha.com）')
    parser.add_argument('--user_id', default='plugin-user', help='用户ID（默认: plugin-user）')
    parser.add_argument('--optimize', action='store_true', help='是否优化报告数据')
    parser.add_argument('--output', default='gmp_report_result.json', help='输出结果的JSON文件路径（默认: gmp_report_result.json）')
    
    return parser.parse_args()

def main():
    """主函数"""
    try:
        # 解析命令行参数
        args = parse_args()
        
        logger.info("=" * 50)
        logger.info("开始Bayer GMP报告生成工作流")
        logger.info(f"对话ID: {args.conversation_id}")
        logger.info(f"API基础URL: {args.api_base}")
        logger.info(f"用户ID: {args.user_id}")
        logger.info(f"是否优化: {args.optimize}")
        logger.info("=" * 50)
        
        # 记录开始时间
        start_time = time.time()
        
        # 调用集成工作流
        result = integrate_workflow(
            conversation_id=args.conversation_id,
            api_base=args.api_base,
            api_key=args.api_key,
            user_id=args.user_id,
            optimize_data=args.optimize
        )
        
        # 计算执行时间
        elapsed_time = time.time() - start_time
        logger.info(f"工作流执行完成，耗时: {elapsed_time:.2f}秒")
        
        # 保存结果到文件
        with open(args.output, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        
        logger.info(f"结果已保存到: {args.output}")
        
        # 打印简要结果信息
        if result["success"]:
            print(f"\n✅ GMP报告生成成功！")
            print(f"📄 结果已保存到: {args.output}")
            if "download_link" in result:
                print(f"📎 PDF下载链接已包含在结果文件中")
        else:
            print(f"\n❌ GMP报告生成失败: {result['message']}")
            print(f"📄 详细错误信息已保存到: {args.output}")
        
        return 0 if result["success"] else 1
    
    except KeyboardInterrupt:
        logger.info("用户中断了操作")
        return 130
    except Exception as e:
        logger.error(f"执行中出现错误: {str(e)}", exc_info=True)
        print(f"\n❌ 执行出错: {str(e)}")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 
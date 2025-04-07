"""
Bayer GMP Reporter Plugin - 主入口文件
"""
import logging

from dify_plugin import Plugin, DifyPluginEnv

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("bayer_gmp_plugin.log")
    ]
)

# 创建插件实例
plugin = Plugin(DifyPluginEnv(MAX_REQUEST_TIMEOUT=120))

if __name__ == '__main__':
    plugin.run() 
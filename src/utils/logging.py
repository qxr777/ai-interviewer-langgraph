"""结构化日志工具。"""

import json
import logging
import os
from datetime import datetime


def get_structured_logger(log_dir: str = "logs") -> logging.Logger:
    """获取结构化日志器，输出到 JSONL 文件。"""
    os.makedirs(log_dir, exist_ok=True)

    logger = logging.getLogger("ai-interviewer")
    logger.setLevel(logging.DEBUG)

    # 清除已有 handler，确保每个调用都添加新 handler（测试友好）
    for h in logger.handlers[:]:
        logger.removeHandler(h)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = os.path.join(log_dir, f"interview_{timestamp}.jsonl")

    handler = logging.FileHandler(log_file, encoding="utf-8")
    handler.setFormatter(JsonlFormatter())
    logger.addHandler(handler)

    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    logger.addHandler(console)

    return logger


class JsonlFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "level": record.levelname,
            "message": record.getMessage(),
        }
        for key in ("node", "input_summary", "output_summary", "duration", "token_usage"):
            if hasattr(record, key):
                log_entry[key] = getattr(record, key)
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_entry, ensure_ascii=False)


def log_node_execution(logger: logging.Logger, node: str, input_summary: str,
                       output_summary: str, duration: float, token_usage: int = 0):
    """记录节点执行日志。"""
    logger.info(
        "node executed",
        extra={
            "node": node,
            "input_summary": input_summary,
            "output_summary": output_summary,
            "duration": duration,
            "token_usage": token_usage,
        },
    )

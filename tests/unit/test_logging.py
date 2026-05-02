"""T24: 结构化日志测试。

覆盖：日志文件生成、JSONL 格式、字段完整性、异常记录。
"""

import json
import logging
import os
import tempfile
import pytest


def _get_structured_logger():
    from src.utils.logging import get_structured_logger, log_node_execution
    return get_structured_logger, log_node_execution


class TestStructuredLogging:
    """结构化日志输出。"""

    def test_log_file_created(self):
        """运行后 logs/ 目录生成 interview_*.jsonl。"""
        get_structured_logger, log_node_execution = _get_structured_logger()
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = get_structured_logger(log_dir=tmpdir)
            log_node_execution(
                logger, node="planner",
                input_summary="test", output_summary="test",
                duration=0.1, token_usage=100,
            )

            files = [f for f in os.listdir(tmpdir) if f.endswith(".jsonl")]
            assert len(files) >= 1

    def test_log_entry_jsonl_format(self):
        """每条日志为单行 JSON。"""
        get_structured_logger, log_node_execution = _get_structured_logger()
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = get_structured_logger(log_dir=tmpdir)
            log_node_execution(
                logger, node="questioner",
                input_summary="input", output_summary="output",
                duration=1.5, token_usage=200,
            )

            files = [f for f in os.listdir(tmpdir) if f.endswith(".jsonl")]
            with open(os.path.join(tmpdir, files[0])) as f:
                line = f.readline()
            entry = json.loads(line)
            assert "node" in entry
            assert entry["node"] == "questioner"

    def test_log_fields_complete(self):
        """日志含 node/input_summary/output_summary/duration/token_usage。"""
        get_structured_logger, log_node_execution = _get_structured_logger()
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = get_structured_logger(log_dir=tmpdir)
            log_node_execution(
                logger, node="evaluator",
                input_summary="ans", output_summary="score:80",
                duration=2.0, token_usage=300,
            )

            files = [f for f in os.listdir(tmpdir) if f.endswith(".jsonl")]
            with open(os.path.join(tmpdir, files[0])) as f:
                entry = json.loads(f.readline())

            assert entry["node"] == "evaluator"
            assert entry["duration"] == 2.0
            assert entry["token_usage"] == 300

    def test_exception_logged(self):
        """异常通过 logging.exception 记录堆栈。"""
        get_structured_logger, log_node_execution = _get_structured_logger()
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = get_structured_logger(log_dir=tmpdir)
            try:
                raise ValueError("test error")
            except ValueError:
                logger.exception("node failed")

            files = [f for f in os.listdir(tmpdir) if f.endswith(".jsonl")]
            with open(os.path.join(tmpdir, files[0])) as f:
                content = f.read()
            assert "test error" in content

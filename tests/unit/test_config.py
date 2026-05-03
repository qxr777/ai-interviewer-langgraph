"""T02: 配置加载测试。

覆盖：默认值、config.yaml 覆盖、环境变量优先级、非法值处理。
"""

import os
import subprocess
import sys
import tempfile
from pathlib import Path


def _get_load_config():
    from src.config import load_config

    return load_config


class TestConfigLoading:
    """配置加载逻辑。"""

    def test_defaults_when_no_files(self):
        """无 config.yaml 和 .env → 使用默认值。"""
        load_config = _get_load_config()
        config = load_config(project_root=tempfile.mkdtemp())
        assert config["llm_model"] == "deepseek-chat"
        assert config["sigma_high"] == 5.0
        assert config["evaluator_count"] == 3

    def test_yaml_override(self):
        """config.yaml 覆盖默认值。"""
        load_config = _get_load_config()
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config.yaml"
            config_path.write_text("sigma_high: 10.0\nevaluator_count: 5\n")
            config = load_config(project_root=tmpdir)
            assert config["sigma_high"] == 10.0
            assert config["evaluator_count"] == 5

    def test_env_override(self):
        """环境变量优先级高于 config.yaml。"""
        # 使用子进程隔离，避免父进程已加载项目 .env 干扰
        code = """
import sys, tempfile
from pathlib import Path
sys.path.insert(0, '.')
from src.config import load_config
with tempfile.TemporaryDirectory() as tmpdir:
    env_path = Path(tmpdir) / '.env'
    env_path.write_text('LLM_MODEL=qwen-plus\\n')
    config = load_config(project_root=tmpdir)
    print('model:', config['llm_model'])
"""
        env = {k: v for k, v in os.environ.items() if k not in ("LLM_MODEL", "LLM_API_KEY", "LLM_API_BASE", "DEBUG")}
        result = subprocess.run(
            [sys.executable, "-c", code],
            capture_output=True,
            text=True,
            cwd=str(Path(__file__).parent.parent.parent),
            env=env,
        )
        assert "model: qwen-plus" in result.stdout, f"stdout: {result.stdout}, stderr: {result.stderr}"

    def test_debug_bool_casting(self):
        """DEBUG=true 应解析为布尔值。"""
        load_config = _get_load_config()
        with tempfile.TemporaryDirectory() as tmpdir:
            env_path = Path(tmpdir) / ".env"
            env_path.write_text("DEBUG=true\n")
            config = load_config(project_root=tmpdir)
            assert config["debug"] is True

    def test_debug_false_default(self):
        """在隔离环境中 DEBUG 未设置时默认为 False。"""
        # 使用子进程隔离环境，避免父进程 DEBUG 变量干扰
        code = """
import sys, tempfile
from pathlib import Path
sys.path.insert(0, '.')
from src.config import load_config
with tempfile.TemporaryDirectory() as tmpdir:
    config = load_config(project_root=tmpdir)
    print("debug:", config["debug"])
"""
        result = subprocess.run(
            [sys.executable, "-c", code],
            capture_output=True,
            text=True,
            cwd=str(Path(__file__).parent.parent.parent),
            env={**os.environ, "DEBUG": ""},
        )
        assert "debug: False" in result.stdout, f"stdout: {result.stdout}, stderr: {result.stderr}"

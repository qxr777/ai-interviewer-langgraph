"""简历解析工具：parse_resume_document。"""

import os
from pathlib import Path

from src.utils.pii import redact_pii


def parse_resume_document(file_path: str) -> dict:
    """解析简历 PDF/Word 文件，返回结构化 JSON 数据。

    Args:
        file_path: 合法的本地 PDF/Word 路径。

    Returns:
        脱敏后的结构化数据，包含 name、skills 等字段。

    Raises:
        FileNotFoundError: 文件不存在。
        ValueError: 文件为空或格式不支持。
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"简历文件不存在: {file_path}")

    path = Path(file_path)
    suffix = path.suffix.lower()

    if suffix == ".pdf":
        text = _extract_pdf(path)
    elif suffix == ".docx":
        text = _extract_docx(path)
    else:
        raise ValueError(f"不支持的文件格式: {suffix}")

    if not text.strip():
        raise ValueError("简历文件为空")

    # 提取结构化信息
    result = _parse_text_to_struct(text)

    # PII 脱敏
    for key in result:
        if isinstance(result[key], str):
            result[key] = redact_pii(result[key])
        elif isinstance(result[key], list):
            result[key] = [redact_pii(item) if isinstance(item, str) else item for item in result[key]]

    return result


def _extract_pdf(path: Path) -> str:
    """从 PDF 提取文本。"""
    try:
        from PyPDF2 import PdfReader

        reader = PdfReader(str(path))
        text = ""
        for page in reader.pages:
            text += page.extract_text() or ""
        return text
    except ImportError:
        # 如果没有 PyPDF2，尝试用 pypdf
        try:
            from pypdf import PdfReader  # type: ignore[assignment]

            reader = PdfReader(str(path))
            text = ""
            for page in reader.pages:
                text += page.extract_text() or ""
            return text
        except ImportError:
            # 最后的兜底：返回文件名作为占位
            return f"Resume from {path.name}"


def _extract_docx(path: Path) -> str:
    """从 Word 文档提取文本。"""
    from docx import Document

    doc = Document(str(path))
    return "\n".join(p.text for p in doc.paragraphs)


def _parse_text_to_struct(text: str) -> dict:
    """将简历文本解析为结构化数据。"""
    lines = [line.strip() for line in text.split("\n") if line.strip()]

    result: dict = {
        "name": "",
        "skills": [],
        "experience_years": 0,
        "education": "",
        "raw_text": text,
    }

    for line in lines:
        lower = line.lower()
        if "resume" in lower or "简历" in lower:
            # 尝试提取姓名
            for prefix in ["resume:", "简历：", "resume：", "简历:"]:
                if lower.startswith(prefix.lower()):
                    result["name"] = line[len(prefix) :].strip()
                    break
        elif "skill" in lower or "技能" in lower:
            # 提取技能列表
            content = line.split(":", 1)[-1] if ":" in line else line
            result["skills"] = [s.strip() for s in content.replace("技能：", "").split(",") if s.strip()]
        elif "experience" in lower or "经验" in lower:
            # 提取经验年数
            import re

            match = re.search(r"(\d+)\s*年", line)
            if match:
                result["experience_years"] = int(match.group(1))
        elif "education" in lower or "学历" in lower or "教育" in lower:
            content = line.split(":", 1)[-1] if ":" in line else line
            result["education"] = content.strip()

    # 如果没提取到姓名，使用第一行
    if not result["name"] and lines:
        result["name"] = lines[0]

    return result

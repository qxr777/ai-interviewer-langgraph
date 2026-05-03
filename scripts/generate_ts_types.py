#!/usr/bin/env python3
"""从后端 Pydantic 模型自动生成 TypeScript 类型定义。

基于 Pydantic model_json_schema() 输出，手动转换为 TypeScript 接口。
不依赖 datamodel-code-generator（v0.56+ 已移除 TypeScript 支持）。

用法:
    python scripts/generate_ts_types.py              # 默认输出到 web/src/types/generated.ts
    python scripts/generate_ts_types.py --output path # 指定输出路径
"""

import argparse
import sys
from pathlib import Path


def ts_type_from_schema(prop: dict, defs: dict, required_fields: set, field_name: str = "") -> str:
    """将 JSON Schema 属性节点转换为 TypeScript 类型。"""
    if "$ref" in prop:
        ref = prop["$ref"].split("/")[-1]
        return ref

    prop_type = prop.get("type")

    if prop_type == "string":
        if "enum" in prop:
            return " | ".join(f"'{v}'" for v in prop["enum"])
        return "string"

    if prop_type == "integer":
        return "number"

    if prop_type == "number":
        return "number"

    if prop_type == "boolean":
        return "boolean"

    if prop_type == "array":
        items = prop.get("items", {})
        inner = ts_type_from_schema(items, defs, set())
        return f"{inner}[]"

    if prop_type == "object":
        # 内联对象 — 递归生成接口
        properties = prop.get("properties", {})
        req = set(prop.get("required", []))
        lines = []
        for k, v in properties.items():
            ts_t = ts_type_from_schema(v, defs, req, k)
            lines.append(f"  {k}: {ts_t}")
        if lines:
            return "{\n" + "\n".join(lines) + "\n}"
        return "Record<string, unknown>"

    # anyOf / oneOf → 联合类型
    if "anyOf" in prop:
        parts = []
        for sub in prop["anyOf"]:
            if sub.get("type") == "null":
                parts.append("null")
            else:
                parts.append(ts_type_from_schema(sub, defs, set(), field_name))
        return " | ".join(parts)

    if "oneOf" in prop:
        parts = []
        for sub in prop["oneOf"]:
            if sub.get("type") == "null":
                parts.append("null")
            else:
                parts.append(ts_type_from_schema(sub, defs, set(), field_name))
        return " | ".join(parts)

    if prop_type == "null":
        return "null"

    # 兜底
    return "unknown"


def generate_ts_types(output_path: Path) -> None:
    """从 src/state.py 的 Pydantic 模型生成 TypeScript 类型定义。"""
    root = Path(__file__).resolve().parent.parent
    sys.path.insert(0, str(root))

    from src.state import (
        InterviewState,
    )

    # 1. 从 Pydantic 模型获取 JSON Schema
    schema = InterviewState.model_json_schema()
    defs = schema.get("$defs", {})

    # 2. 定义额外的 API 类型（不在 Pydantic 中）
    api_types = {
        "StartInterviewRequest": {
            "type": "object",
            "properties": {
                "resume_file": {"type": "string", "description": "base64 encoded PDF/DOCX"},
                "job_description": {"type": "string"},
            },
            "required": ["resume_file", "job_description"],
        },
        "StartInterviewResponse": {
            "type": "object",
            "properties": {
                "interview_id": {"type": "string"},
                "status": {"type": "string"},
                "ai_response": {"anyOf": [{"type": "string"}, {"type": "null"}]},
                "interview_plan": {"type": "array", "items": {"$ref": "#/$defs/TopicItem"}},
                "current_topic_id": {"anyOf": [{"type": "string"}, {"type": "null"}]},
            },
            "required": ["interview_id", "status", "interview_plan"],
        },
        "AnswerRequest": {
            "type": "object",
            "properties": {"answer": {"type": "string"}},
            "required": ["answer"],
        },
        "AnswerResponse": {
            "type": "object",
            "properties": {
                "ai_response": {"anyOf": [{"type": "string"}, {"type": "null"}]},
                "scores": {"type": "array", "items": {"$ref": "#/$defs/EvaluationRecord"}},
                "interview_plan": {"type": "array", "items": {"$ref": "#/$defs/TopicItem"}},
                "current_topic_id": {"anyOf": [{"type": "string"}, {"type": "null"}]},
                "routing_flag": {"anyOf": [{"$ref": "#/$defs/RoutingFlag"}, {"type": "null"}]},
                "status": {"type": "string"},
            },
            "required": ["status"],
        },
        "ArbitrateRequest": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ["CONTINUE", "SKIP", "END"]},
            },
            "required": ["action"],
        },
        "ArbitrateResponse": {
            "type": "object",
            "properties": {
                "status": {"type": "string"},
                "action": {"type": "string"},
            },
            "required": ["status", "action"],
        },
        "StatusResponse": {
            "type": "object",
            "properties": {
                "routing_flag": {"$ref": "#/$defs/RoutingFlag"},
                "current_topic_id": {"anyOf": [{"type": "string"}, {"type": "null"}]},
                "current_topic_index": {"type": "integer"},
                "chat_history": {"type": "array", "items": {"$ref": "#/$defs/ChatMessage"}},
                "interview_plan": {"type": "array", "items": {"$ref": "#/$defs/TopicItem"}},
                "chat_count": {"type": "integer"},
            },
            "required": ["routing_flag", "chat_count"],
        },
        "SSEEvent": {
            "type": "object",
            "properties": {
                "type": {"type": "string", "enum": ["status", "message", "heartbeat"]},
                "flag": {"$ref": "#/$defs/RoutingFlag"},
                "role": {"type": "string"},
                "content": {"type": "string"},
                "topic_id": {"anyOf": [{"type": "string"}, {"type": "null"}]},
            },
            "required": ["type"],
        },
        "InterviewReport": {
            "type": "object",
            "properties": {
                "status": {"type": "string"},
                "overall_average_score": {"anyOf": [{"type": "number"}, {"type": "null"}]},
                "topics": {"type": "array", "items": {"$ref": "#/$defs/ReportTopic"}},
                "total_evaluations": {"type": "integer"},
                "generated_at": {"type": "string"},
            },
            "required": ["status", "topics", "total_evaluations", "generated_at"],
        },
        "ReportTopic": {
            "type": "object",
            "properties": {
                "topic_id": {"type": "string"},
                "topic_name": {"type": "string"},
                "status": {"type": "string"},
                "average_score": {"anyOf": [{"type": "number"}, {"type": "null"}]},
                "scores": {"type": "array", "items": {"type": "number"}},
                "rationales": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["topic_id", "topic_name", "status", "scores", "rationales"],
        },
    }

    defs.update(api_types)

    # Add InterviewState itself as a named type
    defs["InterviewState"] = {
        "type": "object",
        "properties": schema.get("properties", {}),
        "required": schema.get("required", []),
    }

    # 3. 生成 TypeScript 代码
    lines = []
    lines.append("// Auto-generated TypeScript types aligned with backend Pydantic models")
    lines.append("// Source: src/state.py")
    lines.append("// Do not edit manually — run `python scripts/generate_ts_types.py` to regenerate.")
    lines.append("")

    # 生成枚举类型
    # RoutingFlag
    routing_flag_schema = defs.get("RoutingFlag", {})
    if "enum" in routing_flag_schema:
        enum_vals = " | ".join(f"'{v}'" for v in routing_flag_schema["enum"])
        lines.append(f"export type RoutingFlag = {enum_vals}")
        lines.append("")

    # 生成接口
    # 先排序：被引用的类型先输出
    output_order = [
        "TopicItem",
        "ChatMessage",
        "EvaluationRecord",
        "InterviewReport",
        "ReportTopic",
        "InterviewState",
        "StartInterviewRequest",
        "StartInterviewResponse",
        "AnswerRequest",
        "AnswerResponse",
        "ArbitrateRequest",
        "ArbitrateResponse",
        "StatusResponse",
        "SSEEvent",
    ]

    for name in output_order:
        if name not in defs:
            continue
        item_schema = defs[name]
        if item_schema.get("type") != "object":
            continue
        props = item_schema.get("properties", {})
        required = set(item_schema.get("required", []))

        lines.append(f"export interface {name} {{")
        for field_name, field_schema in props.items():
            is_required = field_name in required
            has_default = "default" in field_schema
            ts_t = ts_type_from_schema(field_schema, defs, required, field_name)
            # Optional: not required and no default → | null; has default → also optional but not null
            if not is_required and not has_default and "null" not in ts_t:
                ts_t = f"{ts_t} | null"
            lines.append(f"  {field_name}: {ts_t}")
        lines.append("}")
        lines.append("")

    output_path.write_text("\n".join(lines), "utf-8")
    print(f"Generated TypeScript types at {output_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate TypeScript types from Pydantic models")
    parser.add_argument(
        "--output",
        type=str,
        default="web/src/types/generated.ts",
        help="Output file path (default: web/src/types/generated.ts)",
    )
    args = parser.parse_args()
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    generate_ts_types(output_path)


if __name__ == "__main__":
    main()

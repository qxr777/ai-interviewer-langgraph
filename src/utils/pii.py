"""PII 脱敏工具：识别并替换电话号码、身份证号、家庭住址。"""

import re

# 中国大陆手机号：11 位，1 开头，可选 +86 前缀
_PHONE_PATTERN = re.compile(r"(?:\+86)?(1[3-9]\d{9})")
# 18 位身份证号
_ID_18_PATTERN = re.compile(r"\d{17}[\dXx]")
# 15 位旧身份证号
_ID_15_PATTERN = re.compile(r"\b\d{15}\b")
# 中文地址：必须以省/市/区/县开头，后跟路/街/号/栋 等
# 关键约束：必须有区域前缀（省/市/区/县）才能匹配，防止"编号"等误匹配
_ADDRESS_PATTERN = re.compile(
    r"[^\s,，:：]*"
    r"(?:省|市|区|县)"
    r"[^\s,，:：]*?"
    r"(?:路|街|巷|弄|道|街|巷|胡同)"
    r"\d+"
    r"(?:号|栋|座|幢|楼)?"
    r"[^\s,，:：]*"
    r"(?:室|栋|楼|号|座)?"
)

# 简化地址模式：有区域前缀 + 终端关键词（号/室/栋/楼），不要求路/街
_ADDRESS_SIMPLE_PATTERN = re.compile(
    r"[^\s,，:：]*?"
    r"(?:省|市|区|县)"
    r"[^\s,，:：]*?"
    r"\d+"
    r"(?:号|室|栋|楼)"
    r"[^\s,，:：]*"
)

_REDACTED = "[REDACTED]"


def redact_pii(text: str) -> str:
    """识别并替换 PII 信息，返回脱敏后的文本。"""
    if not text:
        return text

    result = _ID_18_PATTERN.sub(_REDACTED, text)
    result = _ID_15_PATTERN.sub(_REDACTED, result)
    result = _PHONE_PATTERN.sub(_REDACTED, result)
    result = _ADDRESS_PATTERN.sub(_REDACTED, result)
    result = _ADDRESS_SIMPLE_PATTERN.sub(_REDACTED, result)
    return result

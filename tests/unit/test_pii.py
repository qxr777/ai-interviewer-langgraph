"""T07: PII 脱敏工具测试。

覆盖：手机号、身份证号、地址脱敏；无 PII 不变；混合文本；边界值。
"""


def _redact_pii():
    from src.utils.pii import redact_pii

    return redact_pii


class TestPhoneNumberRedaction:
    """手机号脱敏测试。"""

    def test_chinese_mobile_11_digits(self):
        redact_pii = _redact_pii()
        result = redact_pii("联系电话：13800138000")
        assert "13800138000" not in result
        assert "[REDACTED]" in result

    def test_mobile_with_country_code(self):
        redact_pii = _redact_pii()
        result = redact_pii("电话：+8613800138000")
        assert "13800138000" not in result
        assert "[REDACTED]" in result

    def test_ten_digit_not_matched(self):
        """10 位数字不应被识别为手机号。"""
        redact_pii = _redact_pii()
        result = redact_pii("编号：1234567890")
        assert "[REDACTED]" not in result

    def test_multiple_phones(self):
        redact_pii = _redact_pii()
        result = redact_pii("手机1：13900001111，手机2：18600002222")
        assert result.count("[REDACTED]") == 2


class TestIDCardRedaction:
    """身份证号脱敏测试。"""

    def test_18_digit_id(self):
        redact_pii = _redact_pii()
        result = redact_pii("身份证号：110101199001011234")
        assert "110101199001011234" not in result
        assert "[REDACTED]" in result

    def test_15_digit_id(self):
        redact_pii = _redact_pii()
        result = redact_pii("旧身份证号：110101900101123")
        assert "[REDACTED]" in result


class TestAddressRedaction:
    """地址脱敏测试。"""

    def test_chinese_address(self):
        redact_pii = _redact_pii()
        text = "住址：北京市朝阳区建国路88号SOHO现代城A座1001"
        result = redact_pii(text)
        assert "[REDACTED]" in result

    def test_simple_address(self):
        redact_pii = _redact_pii()
        text = "地址：上海市浦东新区陆家嘴环路1000号"
        result = redact_pii(text)
        assert "[REDACTED]" in result


class TestNoPII:
    """无 PII 文本不变。"""

    def test_normal_text(self):
        redact_pii = _redact_pii()
        text = "候选人具备 5 年 Python 开发经验"
        result = redact_pii(text)
        assert result == text

    def test_empty_string(self):
        redact_pii = _redact_pii()
        assert redact_pii("") == ""


class TestMixedContent:
    """混合 PII + 正常文本。"""

    def test_mixed(self):
        redact_pii = _redact_pii()
        text = "张三，13800138000，擅长 Python。住址：北京市海淀区中关村大街1号。"
        result = redact_pii(text)
        assert "13800138000" not in result
        assert "[REDACTED]" in result
        assert "Python" in result

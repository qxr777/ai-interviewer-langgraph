"""T33: API 集成测试 — REST 路由 + SSE 端点。

覆盖：启动面试、提交回答、仲裁操作、SSE 事件流。
"""

import pytest

# Valid minimal PDF base64 for test fixtures (mock_resume.pdf)
MOCK_RESUME_B64 = "JVBERi0xLjQKMSAwIG9iajw8L1R5cGUvQ2F0YWxvZy9QYWdlcyAyIDAgUj4+ZW5kb2JqCjIgMCBvYmo8PC9UeXBlL1BhZ2VzL0tpZHNbMyAwIFJdL0NvdW50IDE+PmVuZG9iagozIDAgb2JqPDwvVHlwZS9QYWdlL01lZGlhQm94WzAgMCA2MTIgNzkyXS9QYXJlbnQgMiAwIFIvUmVzb3VyY2VzPDw+Pi9Db250ZW50cyA0IDAgUj4+ZW5kb2JqCjQgMCBvYmo8PC9MZW5ndGggNDQ+PnN0cmVhbQpCVCAvRjEgMTIgVGYgMTAwIDc1MCBUZCAoUmVzdW1lOiBaaGFuZyBTYW4pIFRqIEVUCmVuZHN0cmVhbQplbmRvYmoKeHJlZgowIDUKMDAwMDAwMDAwMCA2NTUzNSBmIAowMDAwMDAwMDA5IDAwMDAwIG4gCjAwMDAwMDAwNTggMDAwMDAgbiAKMDAwMDAwMDExNSAwMDAwMCBuIAowMDAwMDAwMjIwIDAwMDAwIG4gCnRyYWlsZXI8PC9TaXplIDUvUm9vdCAxIDAgUj4+CnN0YXJ0eHJlZgozMTQKJSVFT0Y="


def _get_api_app():
    from src.api.main import create_app
    return create_app


class TestRESTEndpoints:
    """REST API 端点测试。"""

    @pytest.mark.asyncio
    async def test_start_interview(self):
        """POST /interview/start → 返回 interview_id。"""
        create_app = _get_api_app()
        app = create_app()
        from httpx import AsyncClient, ASGITransport

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/interview/start",
                json={
                    "resume_file": MOCK_RESUME_B64,
                    "job_description": "Senior Developer",
                },
            )
            assert response.status_code == 200
            data = response.json()
            assert "interview_id" in data

    @pytest.mark.asyncio
    async def test_submit_answer(self):
        """POST /interview/{id}/answer → 返回 AI 响应。"""
        create_app = _get_api_app()
        app = create_app()
        from httpx import AsyncClient, ASGITransport

        # 先启动面试
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            start_resp = await client.post(
                "/interview/start",
                json={
                    "resume_file": MOCK_RESUME_B64,
                    "job_description": "Senior Developer",
                },
            )
            interview_id = start_resp.json()["interview_id"]

            # 提交回答
            response = await client.post(
                f"/interview/{interview_id}/answer",
                json={"answer": "装饰器是高阶函数..."},
            )
            assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_arbitrate(self):
        """POST /interview/{id}/arbitrate → 状态更新。"""
        create_app = _get_api_app()
        app = create_app()
        from httpx import AsyncClient, ASGITransport

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            start_resp = await client.post(
                "/interview/start",
                json={
                    "resume_file": MOCK_RESUME_B64,
                    "job_description": "Senior Developer",
                },
            )
            interview_id = start_resp.json()["interview_id"]

            response = await client.post(
                f"/interview/{interview_id}/arbitrate",
                json={"action": "CONTINUE"},
            )
            assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_get_report(self):
        """GET /interview/{id}/report → 返回 JSON 报告。"""
        create_app = _get_api_app()
        app = create_app()
        from httpx import AsyncClient, ASGITransport

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            start_resp = await client.post(
                "/interview/start",
                json={
                    "resume_file": MOCK_RESUME_B64,
                    "job_description": "Senior Developer",
                },
            )
            interview_id = start_resp.json()["interview_id"]

            response = await client.get(f"/interview/{interview_id}/report")
            assert response.status_code == 200


class TestSSEEndpoint:
    """SSE 流式端点测试。"""

    @pytest.mark.skip(reason="httpx ASGI transport does not support streaming responses well")
    @pytest.mark.asyncio
    async def test_stream_endpoint_exists(self):
        """GET /interview/{id}/stream → SSE 连接应建立。"""
        create_app = _get_api_app()
        app = create_app()
        from httpx import AsyncClient, ASGITransport

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test", timeout=5.0) as client:
            # 先创建面试
            start_resp = await client.post(
                "/interview/start",
                json={
                    "resume_file": MOCK_RESUME_B64,
                    "job_description": "Senior Developer",
                },
            )
            interview_id = start_resp.json()["interview_id"]

            # 用 send 获取响应头但不读取完整 body
            request = client.build_request("GET", f"/interview/{interview_id}/stream")
            response = await client.send(request, stream=True)
            try:
                assert response.status_code == 200
                content_type = response.headers.get("content-type", "")
                assert "text" in content_type or "event" in content_type
            finally:
                await response.aclose()

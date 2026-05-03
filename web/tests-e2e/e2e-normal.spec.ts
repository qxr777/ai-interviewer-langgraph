import { test, expect } from '@playwright/test';

const API_BASE = 'http://localhost:8765';

async function generateResumeBase64(): Promise<string> {
  const { execSync } = await import('child_process');
  return execSync(
    `python3 -c "import base64,io;from docx import Document;d=Document();d.add_paragraph('Resume: Test Candidate');d.add_paragraph('Skills: Python, Django, PostgreSQL');d.add_paragraph('Experience: 5 years');b=io.BytesIO();d.save(b);print(base64.b64encode(b.getvalue()).decode())"`
  ).toString().trim();
}

test.describe('正常面试流程 E2E', () => {
  test('面试页面 UI 渲染', async ({ page }) => {
    const resumeB64 = await generateResumeBase64();
    const startResp = await fetch(`${API_BASE}/interview/start`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        resume_file: resumeB64,
        job_description: 'Senior Python Developer',
      }),
    });
    expect(startResp.status).toBe(200);
    const startData = await startResp.json();
    const interviewId = startData.interview_id;
    expect(interviewId).toBeTruthy();
    expect(startData.interview_plan.length).toBeGreaterThanOrEqual(3);

    // 验证面试页面
    await page.goto(`/interview/${interviewId}`);
    await expect(page.locator('text=AI 面试中')).toBeVisible({ timeout: 10000 });
    await expect(page.locator('text=面试议题')).toBeVisible({ timeout: 5000 });
    await expect(page.locator('text=等待 AI 提问...')).toBeHidden({ timeout: 15000 });
    await expect(page.locator('input[placeholder="输入你的回答..."]')).toBeVisible({ timeout: 5000 });
    await expect(page.locator('button:has-text("提交")')).toBeVisible({ timeout: 5000 });
  });

  test('报告页面 UI 渲染', async ({ page }) => {
    // 通过 API 完成一轮问答获取有效面试数据
    const resumeB64 = await generateResumeBase64();
    const startResp = await fetch(`${API_BASE}/interview/start`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        resume_file: resumeB64,
        job_description: 'Senior Python Developer',
      }),
    });
    const startData = await startResp.json();
    const interviewId = startData.interview_id;

    // 触发一轮评估以产生报告数据
    const answerResp = await fetch(`${API_BASE}/interview/${interviewId}/answer`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ answer: 'Python is a versatile programming language.' }),
    });
    expect(answerResp.status).toBe(200);

    // 验证报告页面渲染
    await page.goto(`/report/${interviewId}`);
    await expect(page.getByRole('heading', { name: '面试报告' })).toBeVisible({ timeout: 10000 });
    await expect(page.locator('text=各议题详情')).toBeVisible({ timeout: 5000 });
  });
});

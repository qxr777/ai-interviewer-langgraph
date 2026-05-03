import { test, expect } from '@playwright/test';

const API_BASE = 'http://localhost:8765';

async function generateResumeBase64(): Promise<string> {
  const { execSync } = await import('child_process');
  return execSync(
    `python3 -c "import base64,io;from docx import Document;d=Document();d.add_paragraph('Resume: Test Candidate');d.add_paragraph('Skills: Python, Django, PostgreSQL');d.add_paragraph('Experience: 5 years');b=io.BytesIO();d.save(b);print(base64.b64encode(b.getvalue()).decode())"`
  ).toString().trim();
}

test.describe('仲裁流程 E2E', () => {
  test('仲裁页面：展示按钮 → 人工 CONTINUE → 验证后端状态更新', async ({ page }) => {
    // 1. 启动面试
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

    // 2. 完成一轮问答
    await page.goto(`/interview/${interviewId}`);
    await expect(page.locator('text=AI 面试中')).toBeVisible({ timeout: 10000 });
    await expect(page.locator('text=等待 AI 提问...')).toBeHidden({ timeout: 15000 });

    const input = page.locator('input[placeholder="输入你的回答..."]');
    await input.fill('My first answer to trigger evaluation');
    await page.locator('button:has-text("提交")').click();
    await expect(page.locator('text=AI 思考中...')).toBeHidden({ timeout: 30000 });

    // 3. 通过前端仲裁页面操作（模拟 ESCALATE 后的人工决定）
    await page.goto(`/arbitration/${interviewId}`);
    await expect(page.getByRole('heading', { name: '人工仲裁' })).toBeVisible({ timeout: 10000 });

    // 4. 验证三个操作按钮
    const continueBtn = page.getByRole('button', { name: '继续当前议题' });
    const skipBtn = page.getByRole('button', { name: '跳过此议题' });
    const endBtn = page.getByRole('button', { name: '结束面试' });

    await expect(continueBtn).toBeVisible({ timeout: 5000 });
    await expect(skipBtn).toBeVisible({ timeout: 5000 });
    await expect(endBtn).toBeVisible({ timeout: 5000 });

    // 5. 点击 CONTINUE 按钮
    await continueBtn.click();

    // 6. 验证后端 routing_flag 已更新为 CONTINUE
    const statusResp = await fetch(`${API_BASE}/interview/${interviewId}/status`);
    expect(statusResp.status).toBe(200);
    const statusData = await statusResp.json();
    expect(statusData.routing_flag).toBe('CONTINUE');
  });

  test('仲裁页面 END 按钮 → 跳转到报告', async ({ page }) => {
    // 1. 启动面试
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

    // 2. 直接访问仲裁页面
    await page.goto(`/arbitration/${interviewId}`);
    await expect(page.getByRole('heading', { name: '人工仲裁' })).toBeVisible({ timeout: 10000 });

    // 3. 点击"结束面试"按钮
    const endBtn = page.getByRole('button', { name: '结束面试' });
    await expect(endBtn).toBeVisible({ timeout: 5000 });
    await endBtn.click();

    // 4. 验证跳转到报告页面
    await expect(page).toHaveURL(/\/report\//, { timeout: 5000 });
    await expect(page.getByRole('heading', { name: '面试报告' })).toBeVisible({ timeout: 10000 });
  });
});

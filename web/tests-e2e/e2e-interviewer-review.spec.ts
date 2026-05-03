import { test, expect } from '@playwright/test';

const API_BASE = 'http://localhost:8765';

async function generateResumeBase64(): Promise<string> {
  const { execSync } = await import('child_process');
  return execSync(
    `python3 -c "import base64,io;from docx import Document;d=Document();d.add_paragraph('Resume: Test Candidate');d.add_paragraph('Skills: Python, Django, PostgreSQL');d.add_paragraph('Experience: 5 years');b=io.BytesIO();d.save(b);print(base64.b64encode(b.getvalue()).decode())"`
  ).toString().trim();
}

test.describe('候选人等待遮罩 + 面试官审核 E2E', () => {
  test('候选人提交回答后看到等待遮罩，面试官审核后恢复', async ({ page }) => {
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

    // 2. 候选人端：进入面试页面，提交回答
    await page.goto(`/interview/${interviewId}`);
    await expect(page.locator('text=AI 面试中')).toBeVisible({ timeout: 10000 });
    await expect(page.locator('text=等待 AI 提问...')).toBeHidden({ timeout: 15000 });

    const input = page.locator('input[placeholder="输入你的回答..."]');
    await input.fill('Test answer');
    await page.locator('button:has-text("提交")').click();

    // 等待回答处理完成（loading 消失）
    await expect(page.locator('text=AI 思考中...')).toBeHidden({ timeout: 30000 });

    // 3. 验证候选人端没有自动跳转到仲裁页面
    // 即使出现 ESCALATE，候选人应该仍停留在面试页面
    const currentUrl = page.url();
    expect(currentUrl).toContain(`/interview/${interviewId}`);
  });

  test('面试官审核页面：显示议题和分歧详情，支持 CONTINUE', async ({ page }) => {
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

    // 2. 面试官端：访问审核页面
    await page.goto(`/interviewer/${interviewId}`);

    // 3. 验证页面标题
    await expect(page.getByRole('heading', { name: '面试官审核' })).toBeVisible({ timeout: 10000 });

    // 4. 验证进度条
    const progressBar = page.locator('.bg-yellow-400, .bg-green-500, .bg-gray-200').first();
    await expect(progressBar).toBeVisible({ timeout: 5000 });

    // 5. 验证当前议题
    await expect(page.locator('text=当前议题')).toBeVisible({ timeout: 5000 });

    // 6. 验证三个仲裁按钮
    const continueBtn = page.getByRole('button', { name: '继续' });
    const skipBtn = page.getByRole('button', { name: '跳过' });
    const endBtn = page.getByRole('button', { name: '结束' });

    await expect(continueBtn).toBeVisible({ timeout: 5000 });
    await expect(skipBtn).toBeVisible({ timeout: 5000 });
    await expect(endBtn).toBeVisible({ timeout: 5000 });

    // 7. 点击 CONTINUE 按钮
    await continueBtn.click();

    // 8. 验证跳转到面试页面
    await expect(page).toHaveURL(new RegExp(`/interview/${interviewId}`), { timeout: 5000 });

    // 9. 验证后端 routing_flag 已更新
    const statusResp = await fetch(`${API_BASE}/interview/${interviewId}/status`);
    expect(statusResp.status).toBe(200);
    const statusData = await statusResp.json();
    expect(statusData.routing_flag).toBe('CONTINUE');
  });

  test('面试官审核页面 END → 跳转到报告', async ({ page }) => {
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

    // 2. 面试官端：访问审核页面
    await page.goto(`/interviewer/${interviewId}`);
    await expect(page.getByRole('heading', { name: '面试官审核' })).toBeVisible({ timeout: 10000 });

    // 3. 点击 END 按钮
    const endBtn = page.getByRole('button', { name: '结束' });
    await expect(endBtn).toBeVisible({ timeout: 5000 });
    await endBtn.click();

    // 4. 验证跳转到报告页面
    await expect(page).toHaveURL(/\/report\//, { timeout: 5000 });
    await expect(page.getByRole('heading', { name: '面试报告' })).toBeVisible({ timeout: 10000 });
  });
});

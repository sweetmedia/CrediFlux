import { expect, test, type Page } from '@playwright/test';

async function colores(page: Page, testId: string) {
  return page.getByTestId(testId).evaluate((el) => {
    const s = getComputedStyle(el);
    return { bg: s.backgroundColor, fg: s.color };
  });
}

async function tema(page: Page, oscuro: boolean) {
  await page.evaluate((d) => document.documentElement.classList.toggle('dark', d), oscuro);
  // Los cf-btn tienen transición de color: se lee al terminar.
  await page.waitForTimeout(400);
}

test('el DS cambia en oscuro y el papel sigue claro', async ({ page }) => {
  await page.goto('/__ds');
  await tema(page, false);
  const claroBtn = await colores(page, 'primary');
  const claroMuted = await colores(page, 'muted');
  const claroPapel = await colores(page, 'paper');

  await tema(page, true);
  expect((await colores(page, 'primary')).bg).not.toBe(claroBtn.bg);
  expect((await colores(page, 'muted')).fg).not.toBe(claroMuted.fg);
  expect(await colores(page, 'paper')).toEqual(claroPapel);
});

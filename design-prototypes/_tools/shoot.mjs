// Full-page screenshots of every V1 prototype for the canvas artifact.
import { chromium } from '../../frontend/node_modules/playwright/index.mjs';

const BASE = 'http://localhost:8765/design-prototypes/';
const OUT = process.env.OUT || decodeURIComponent(new URL('./shots/', import.meta.url).pathname);
const ONLY = process.env.ONLY ? process.env.ONLY.split(',') : null;
const SHOTS = [
  ['login', 'login.html'],
  ['login-2fa', 'login.html', "setState('2fa')"],
  ['register-1', 'register.html'],
  ['register-3', 'register.html', 'go(3)'],
  ['register-done', 'register.html', 'go(5)'],
  ['dashboard', 'dashboard.html'],
  ['customers-list', 'customers-list.html'],
  ['customer-detail', 'customer-detail.html'],
  ['customer-new', 'customer-new.html'],
  ['loans-list', 'loans-list.html'],
  ['loan-detail', 'loan-detail.html'],
  ['loan-new-1', 'loan-new.html', 'go(1)'],
  ['loan-new-2', 'loan-new.html', 'go(2)'],
  ['loan-new-3', 'loan-new.html', 'go(3)'],
  ['loan-new-4', 'loan-new.html', 'go(4)'],
  ['loan-new-5', 'loan-new.html', 'go(5)'],
  ['loan-new-6', 'loan-new.html', 'go(6)'],
  ['payments-new', 'payments-new.html'],
  ['loans-overdue', 'loans-overdue.html'],
  ['calculator', 'calculator.html'],
  ['collections', 'collections.html'],
  ['collection-contacts', 'collection-contacts.html'],
  ['collection-contact-new', 'collection-contact-new.html'],
  ['collection-reminders', 'collection-reminders.html'],
  ['collector-mobile', 'collector-mobile.html'],
  ['contracts-list', 'contracts-list.html'],
  ['contract-detail', 'contract-detail.html'],
  ['cashbox', 'cashbox.html'],
  ['billing-list', 'billing-list.html'],
  ['billing-new', 'billing-new.html'],
  ['reports', 'reports.html'],
  ['communications', 'communications.html'],
  ['tasks-kanban', 'tasks-kanban.html'],
  ['ai-assistant', 'ai-assistant.html'],
  ['team', 'team.html'],
  ['audit', 'audit.html'],
  ['settings-general', 'settings-general.html'],
  ['settings-roles', 'settings-roles.html'],
  ['appshell-v1', 'appshell.html'],
  ['appshell-v4', 'appshell-v4-calido.html'],
  ['appshell-v5', 'appshell-v5-banca-lat.html'],
  ['appshell-mobile', 'appshell-mobile.html'],
  ['print-receipt', 'print-receipt.html'],
  ['print-thermal', 'print-thermal.html'],
  ['print-statement', 'print-statement.html'],
  ['print-amortization', 'print-amortization.html'],
  ['print-contract', 'print-contract.html'],
  ['print-intimacion', 'print-intimacion.html'],
  ['print-cashbox-close', 'print-cashbox-close.html'],
  ['contract-generate', 'contract-generate.html'],
  ['contract-template-edit', 'contract-template-edit.html'],
  ['contract-sign', 'contract-sign.html'],
  ['impresos', 'impresos.html'],
];

const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
for (const [name, file, js] of SHOTS.filter(s => !ONLY || ONLY.includes(s[0]))) {
  await page.goto(BASE + file, { waitUntil: 'networkidle' });
  if (js) { await page.evaluate(js); await page.waitForTimeout(400); }
  await page.addStyleTag({ content: '.dev-banner,#cf-notes-root{display:none!important}' });
  await page.evaluate(() => document.fonts.ready);
  await page.waitForTimeout(300);
  // Sticky/fixed sidebars become absolute so a full-page capture keeps them at the top.
  const h = await page.evaluate(() => document.documentElement.scrollHeight);
  // Grow the viewport to the page height so h-screen sidebars span the whole capture.
  await page.setViewportSize({ width: 1440, height: h });
  await page.waitForTimeout(250);
  const h2 = await page.evaluate(() => document.documentElement.scrollHeight);
  await page.screenshot({ path: `${OUT}${name}.png`, fullPage: true });
  await page.setViewportSize({ width: 1440, height: 900 });
  console.log(name, h, h2);
}
await browser.close();

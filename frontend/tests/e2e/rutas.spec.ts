import { readdirSync, statSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { expect, test, type Page } from '@playwright/test';

/**
 * Humo de rutas: cada página estática de `app/` (su `page.tsx`) carga sin la pantalla de
 * error de React Router ni errores de JavaScript.
 *
 * Con E2E_EMAIL / E2E_PASSWORD (p. ej. el superusuario de
 * backend/setup_initial_tenant.py) entra primero y recorre las páginas
 * autenticadas; sin ellas recorre lo que se ve sin sesión.
 */

const APP_DIR = fileURLToPath(new URL('../../app', import.meta.url));

function rutasEstaticas(dir = APP_DIR, base = ''): string[] {
  const rutas: string[] = [];
  for (const nombre of readdirSync(dir)) {
    const full = path.join(dir, nombre);
    if (!statSync(full).isDirectory()) {
      if (nombre === 'page.tsx') rutas.push(base || '/');
      continue;
    }
    if (nombre.startsWith('[')) continue; // dinámicas: necesitan datos
    const segmento = /^\(.*\)$/.test(nombre) ? '' : `/${nombre}`;
    rutas.push(...rutasEstaticas(full, base + segmento));
  }
  return rutas;
}

const ERROR_ROUTER = /Unexpected Application Error|Failed to fetch dynamically imported module/;

const CON_SESION = Boolean(process.env.E2E_EMAIL && process.env.E2E_PASSWORD);

// Un login por worker (no por test): el backend limita los intentos de login.
let sesion: Awaited<ReturnType<import('@playwright/test').BrowserContext['storageState']>> | undefined;

test.beforeAll(async ({ browser }, testInfo) => {
  if (!CON_SESION) return;
  const context = await browser.newContext({ baseURL: testInfo.project.use.baseURL });
  const page = await context.newPage();
  await page.goto('/login');
  await page.getByLabel('Correo').fill(process.env.E2E_EMAIL!);
  await page.getByLabel('Contraseña', { exact: true }).fill(process.env.E2E_PASSWORD!);
  await page.getByRole('button', { name: 'Entrar' }).click();
  await page.waitForURL((url) => !url.pathname.startsWith('/login'));
  sesion = await context.storageState();
  await context.close();
});

async function abrir(browser: import('@playwright/test').Browser, baseURL: string | undefined): Promise<Page> {
  const context = await browser.newContext({ baseURL, storageState: sesion });
  return context.newPage();
}

for (const ruta of rutasEstaticas()) {
  test(`carga ${ruta}`, async ({ browser }, testInfo) => {
    const page = await abrir(browser, testInfo.project.use.baseURL);
    const errores: string[] = [];
    page.on('pageerror', (e) => errores.push(e.message));

    await page.goto(ruta);
    await page.waitForLoadState('networkidle');

    await expect(page.locator('body')).not.toHaveText(ERROR_ROUTER);
    expect((await page.locator('body').innerText()).trim().length).toBeGreaterThan(20);
    expect(errores).toEqual([]);
    await page.context().close();
  });
}

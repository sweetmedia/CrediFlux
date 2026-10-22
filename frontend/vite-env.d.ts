/// <reference types="vite/client" />

interface ImportMetaEnv {
  /** URL del backend cuando no se deduce del host (ver lib/api/client.ts). */
  readonly VITE_API_URL?: string;
  /** URL pública del frontend (og:image en index.html). */
  readonly VITE_APP_URL?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}

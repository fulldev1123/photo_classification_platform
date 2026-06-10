/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_AUTH_API: string;
  readonly VITE_SUBMISSION_API: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}

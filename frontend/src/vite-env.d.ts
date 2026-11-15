/// <reference types="vite/client" />

interface ImportMetaEnv {
  /** Base URL of the backend API, e.g. http://localhost:8000. Public: never a secret. */
  readonly VITE_API_BASE?: string;
  /** "1" builds the serverless online demo that serves the saved test-field results. */
  readonly VITE_STATIC?: string;
}
interface ImportMeta {
  readonly env: ImportMetaEnv;
}

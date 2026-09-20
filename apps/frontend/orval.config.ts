import { defineConfig } from 'orval';

/**
 * Orval генерирует TS-типы и react-query хуки из OpenAPI backend.
 *
 * Контракт:
 *   input  → docs/api/openapi.json (генерится backend через `make api-gen`)
 *   output → apps/frontend/src/generated/
 *
 * НИКОГДА не редактируйте файлы в src/generated/ вручную — они будут
 * перезаписаны. Если что-то не так — правьте backend (FastAPI routes/schemas).
 *
 * Запуск: `make fe-gen` или `cd apps/frontend && yarn orval`
 */
export default defineConfig({
  'transit-ai': {
    input: '../../docs/api/openapi.json',
    output: {
      target: './src/generated/api.ts',
      client: 'react-query',
      mode: 'split',        // split = tags-split для тегов + single для общих типов
      clean: true,
      override: {
        mutator: {
          path: './src/api/customInstance.ts',
          name: 'customInstance',
        },
      },
    },
  },
});

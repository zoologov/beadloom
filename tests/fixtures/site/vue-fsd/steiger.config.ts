import fsd from '@feature-sliced/steiger-plugin'
import { defineConfig } from 'steiger'

export default defineConfig([
  ...fsd.configs.recommended,
  {
    // The folders from before the move to Feature-Sliced Design.
    ignores: ['./src/components/**', './src/stores/**'],
  },
])

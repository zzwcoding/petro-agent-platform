/**
 * web/ ESLint 平面配置（P0-06——frontend-foundation §2.5：前端 eslint 进 CI，
 * 与后端四门禁并列；不迁 TS，jsx 存量不迁移，eslint 兜底；新写横切层用 JSDoc）。
 */

import js from '@eslint/js'
import react from 'eslint-plugin-react'
import reactHooks from 'eslint-plugin-react-hooks'
import globals from 'globals'

export default [
  // vite.config.js.timestamp-*.mjs：vite/vitest 装载配置的临时文件（用后即删）——
  // 若被 lint 扫描收列而读取前已被 vite 删掉即 ENOENT 闸红（web-eslint exit 2 实录，
  // UI-01 补闸修复；gitignore 语义无斜杠模式全深度匹配，排除后瞬存瞬删均免疫）。
  { ignores: ['dist/', 'node_modules/', 'vite.config.js.timestamp-*.mjs'] },
  js.configs.recommended,
  {
    files: ['**/*.{js,jsx,mjs}'],
    languageOptions: {
      ecmaVersion: 2023,
      sourceType: 'module',
      globals: { ...globals.browser, ...globals.es2023 },
      parserOptions: { ecmaFeatures: { jsx: true } }
    },
    settings: { react: { version: 'detect' } },
    plugins: { react, 'react-hooks': reactHooks },
    rules: {
      // JSX 内变量引用计数（核心 eslint 不认 JSXIdentifier，缺它全误报 unused）
      'react/jsx-uses-vars': 'error',
      'react/jsx-uses-react': 'error',
      'react-hooks/rules-of-hooks': 'error',
      'react-hooks/exhaustive-deps': 'warn',
      // args none：原型快照统一渲染签名占位参（chosen/onChoose/sc）不拦——
      // 未用实参＝接口占位，改名反搅快照；未用声明/import 仍报 error
      'no-unused-vars': ['error', { args: 'none', varsIgnorePattern: '^_', caughtErrors: 'none' }],
      // 全角空格是原型页中文排版刻意用字（契约溯源条等），不拦
      'no-irregular-whitespace': 'off'
    }
  },
  // 单测：vitest 全局（describe/it/expect 走 import，node 环境即可）
  {
    files: ['**/*.test.{js,jsx,mjs}'],
    languageOptions: { globals: { ...globals.node } }
  }
]

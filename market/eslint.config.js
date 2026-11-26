import babelParser from '@babel/eslint-parser';
import js from '@eslint/js';
import { defineConfig, globalIgnores } from 'eslint/config';
import prettier from 'eslint-config-prettier/flat';
import reactHooks from 'eslint-plugin-react-hooks';

export default defineConfig(
  globalIgnores(['dist/']),
  js.configs.recommended,
  {
    files: ['**/*.{ts,tsx}'],
    languageOptions: {
      parser: babelParser,
      parserOptions: {
        requireConfigFile: false,
        babelOptions: {
          babelrc: false,
          configFile: false,
          parserOpts: { plugins: ['typescript'] },
        },
      },
    },
    rules: {
      // TypeScript checks names and unused declarations in type and JSX positions.
      'no-undef': 'off',
      'no-unused-vars': 'off',
      'no-restricted-syntax': [
        'error',
        { selector: 'TSAnyKeyword', message: 'Unexpected any. Specify a different type.' },
      ],
    },
  },
  {
    files: ['**/*.tsx'],
    languageOptions: { parserOptions: { babelOptions: { parserOpts: { plugins: ['typescript', 'jsx'] } } } },
  },
  {
    files: ['src/**/*.{ts,tsx}'],
    plugins: { 'react-hooks': reactHooks },
    rules: {
      'react-hooks/rules-of-hooks': 'error',
      'react-hooks/exhaustive-deps': 'error',
    },
  },
  prettier,
);

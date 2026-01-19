module.exports = {
  extends: ['next/core-web-vitals', '../../.eslintrc.cjs'],
  parserOptions: {
    project: ['./tsconfig.eslint.json'],
    tsconfigRootDir: __dirname,
  },
  settings: {
    'import/resolver': {
      typescript: {
        project: ['./tsconfig.json'],
      },
    },
    next: {
      rootDir: ['.'],
    },
  },
  rules: {
    'next/no-html-link-for-pages': 'off',
    'import/no-unresolved': ['error', { ignore: ['^@agent-market/'] }],
  },
};

module.exports = {
  root: true,
  parser: "@typescript-eslint/parser",
  plugins: ["react-hooks"],
  extends: ["eslint:recommended", "plugin:react-hooks/recommended"],
  env: { es2022: true, node: true, browser: true },
  parserOptions: {
    ecmaVersion: 2022,
    sourceType: "module",
    ecmaFeatures: { jsx: true },
  },
  ignorePatterns: ["src/generated/**"],
  rules: {
    "no-unused-vars": "off",
    "no-undef": "off",
    "react-hooks/exhaustive-deps": "warn",
  },
};

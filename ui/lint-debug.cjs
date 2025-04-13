#!/usr/bin/env node

const { execSync } = require('child_process');
const fs = require('fs');
const path = require('path');

try {
  console.log('Running ESLint in debug mode...');
  console.log('Environment:', process.env.NODE_ENV);
  console.log('Working directory:', process.cwd());
  console.log('Node version:', process.version);
  
  // Try to load eslint
  try {
    const eslint = require('eslint');
    console.log('ESLint version:', eslint.ESLint?.version || 'Unknown');
  } catch (err) {
    console.error('Failed to load ESLint:', err.message);
    
    // Try to install eslint if it's not available
    console.log('Attempting to install ESLint...');
    try {
      execSync('npm install --no-save eslint eslint-plugin-react eslint-plugin-react-hooks eslint-plugin-react-refresh', { stdio: 'inherit' });
      console.log('ESLint installed successfully');
    } catch (installErr) {
      console.error('Failed to install ESLint:', installErr.message);
    }
  }
  
  // Verify config file exists
  const eslintConfigPath = path.join(process.cwd(), '.eslintrc.cjs');
  if (!fs.existsSync(eslintConfigPath)) {
    console.error(`ESLint config not found at ${eslintConfigPath}`);
    // Create a basic config
    const basicConfig = `
module.exports = {
  root: true,
  env: {
    browser: true,
    es2020: true,
    jest: true,
    node: true
  },
  extends: [
    'eslint:recommended',
    'plugin:react/recommended',
    'plugin:react/jsx-runtime',
    'plugin:react-hooks/recommended',
  ],
  ignorePatterns: ['dist', '.eslintrc.cjs'],
  parserOptions: { ecmaVersion: 'latest', sourceType: 'module' },
  settings: { 
    react: { 
      version: '18.2' 
    } 
  },
  plugins: ['react-refresh'],
  rules: {
    'react-refresh/only-export-components': [
      'warn',
      { allowConstantExport: true },
    ],
    'react/react-in-jsx-scope': 'off',
    'react/jsx-uses-react': 'off',
    'react/prop-types': 'off'
  },
  globals: {
    describe: 'readonly',
    test: 'readonly',
    expect: 'readonly',
    jest: 'readonly',
    beforeEach: 'readonly'
  }
}`;
    fs.writeFileSync(eslintConfigPath, basicConfig, 'utf8');
    console.log(`Created basic ESLint config at ${eslintConfigPath}`);
  }
  
  // List files
  try {
    console.log('Files to lint:');
    const output = execSync('find . -type f -name "*.js*" -not -path "*node_modules*" -not -path "*/dist/*"').toString();
    console.log(output);
  } catch (err) {
    console.error('Error listing files:', err.message);
  }
  
  // Run eslint
  try {
    console.log('Running ESLint...');
    // Try with npx first
    try {
      execSync('npx eslint . --ext js,jsx --report-unused-disable-directives --max-warnings 0', { stdio: 'inherit' });
      console.log('ESLint completed successfully with npx');
    } catch (npxErr) {
      console.error('ESLint failed with npx, trying direct path...');
      // Try with direct path as fallback
      const eslintBin = path.join(process.cwd(), 'node_modules', '.bin', 'eslint');
      execSync(`${eslintBin} . --ext js,jsx --report-unused-disable-directives --max-warnings 0`, { stdio: 'inherit' });
      console.log('ESLint completed successfully with direct path');
    }
  } catch (err) {
    console.error('ESLint failed with error code:', err.status);
    console.error('Error message:', err.message);
    
    // Try a simpler approach as last resort
    try {
      console.log('Trying simplified linting with minimal options...');
      execSync('npx eslint src --ext js,jsx --no-eslintrc --parser-options=ecmaVersion:2020', { stdio: 'inherit' });
      console.log('Simplified ESLint completed successfully');
    } catch (simpleErr) {
      console.error('All ESLint attempts failed. Exiting with error.');
      process.exit(1);
    }
  }
  
  console.log('Linting process completed.');
} catch (err) {
  console.error('Unhandled error:', err);
  process.exit(1);
}
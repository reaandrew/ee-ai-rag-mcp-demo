#!/usr/bin/env node

const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');

const MIN_COVERAGE = 80;

try {
  // Run coverage report to capture output
  console.log('Running coverage report...');
  const coverageOutput = execSync('pytest --cov=src', { encoding: 'utf8' });
  
  // Parse the coverage summary from the console output
  const lines = coverageOutput.split('\n');
  
  // Find the "TOTAL" line
  const totalLine = lines.find(line => line.includes('TOTAL'));
  
  if (!totalLine) {
    console.error('Error: Could not find coverage total in output.');
    process.exit(1);
  }
  
  // Parse the coverage percentage from the line
  // Format is something like: "TOTAL                   167      9    95%"
  const parts = totalLine.split(/\s+/).filter(Boolean);
  if (parts.length < 4) {
    console.error('Error: Unexpected coverage output format.');
    process.exit(1);
  }
  
  const coverageStr = parts[parts.length - 1].replace('%', '');
  const coverage = parseFloat(coverageStr);
  
  console.log(`Total coverage: ${coverage.toFixed(2)}%`);
  
  if (coverage < MIN_COVERAGE) {
    console.error(`Error: Coverage ${coverage.toFixed(2)}% is below the minimum required ${MIN_COVERAGE}%`);
    process.exit(1);
  } else {
    console.log(`Coverage check passed: ${coverage.toFixed(2)}% >= ${MIN_COVERAGE}%`);
  }
} catch (error) {
  console.error('Error running coverage check:', error.message);
  process.exit(1);
}
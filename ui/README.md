# Policy Search UI

A React-based user interface for the Policy Search application, using the GOV.UK Design System.

[![Quality Gate Status](https://sonarcloud.io/api/project_badges/measure?project=reaandrew_ee-ai-rag-mcp-demo&metric=alert_status)](https://sonarcloud.io/dashboard?id=reaandrew_ee-ai-rag-mcp-demo)
[![Coverage](https://sonarcloud.io/api/project_badges/measure?project=reaandrew_ee-ai-rag-mcp-demo&metric=coverage)](https://sonarcloud.io/dashboard?id=reaandrew_ee-ai-rag-mcp-demo)
[![Maintainability Rating](https://sonarcloud.io/api/project_badges/measure?project=reaandrew_ee-ai-rag-mcp-demo&metric=sqale_rating)](https://sonarcloud.io/dashboard?id=reaandrew_ee-ai-rag-mcp-demo)
[![Security Rating](https://sonarcloud.io/api/project_badges/measure?project=reaandrew_ee-ai-rag-mcp-demo&metric=security_rating)](https://sonarcloud.io/dashboard?id=reaandrew_ee-ai-rag-mcp-demo)

## Features

- Single Page Application (SPA) built with React and Vite
- JWT authentication for secure API access
- Chat interface for querying policies
- Storybook for component development and documentation
- GOV.UK Design System styles and components

## Getting Started

### Prerequisites

- Node.js (v14+)
- npm (v6+)

### Installation

1. Navigate to the UI directory:
```bash
cd ui
```

2. Install dependencies:
```bash
npm install
```

3. Start the development server:
```bash
npm run dev
```

The application will be available at http://localhost:5173

## Authentication

The application uses JWT tokens for authentication. Users authenticate with their email and API key, and the application securely stores the JWT token in local storage.

## Storybook

To view and develop components in isolation:

```bash
npm run storybook
```

This will launch Storybook at http://localhost:6006

## Building for Production

To create a production build:

```bash
npm run build
```

The build artifacts will be stored in the `dist/` directory.

## Testing and Code Quality

### Running Tests

```bash
# Run tests
npm test

# Run tests with coverage
npm run test:coverage
```

### SonarQube Integration

The project is integrated with SonarCloud for code quality analysis. Test coverage reports are automatically generated and sent to SonarCloud when running the full test suite.

To ensure your code meets quality standards:

1. Write tests for all new components and functionality
2. Maintain high test coverage (aim for >80%)
3. Follow React best practices and coding standards
4. Run tests locally before submitting PRs

## Project Structure

- `src/` - Source code
  - `components/` - Reusable React components
    - `auth/` - Authentication components
    - `chat/` - Chat interface components
    - `layout/` - Layout components (header, footer)
  - `contexts/` - React contexts (auth)
  - `pages/` - Top-level page components
  - `styles/` - SCSS stylesheets
    - `components/` - Component-specific styles
  - `utils/` - Utility functions and API helpers
- `public/` - Static assets
- `.storybook/` - Storybook configuration
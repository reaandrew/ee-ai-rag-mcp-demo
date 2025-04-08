# ee-ai-rag-mcp-demo

A repository with conventional commit enforcement, automatic versioning, and SonarQube code quality checks.

## Quality Gates with SonarQube

This repository uses SonarQube for quality checks:

1. **PR Quality Gate**: Runs SonarQube analysis on all PRs to the main branch
2. **Main Branch Quality Gate**: Runs analysis after merges to main
3. **Release Protection**: Version tags are only created if SonarQube checks pass

### Setup Requirements

1. Create a SonarCloud account at https://sonarcloud.io/
2. Create a SonarCloud organization (if you don't have one)
3. Add the following secrets to your GitHub repository:
   - `SONAR_TOKEN`: Your SonarCloud API token
4. **Important**: Disable automatic analysis in SonarCloud for this repository

### Configuration

The workflow is configured to automatically set up the SonarCloud project with:
- Organization: Your GitHub username or organization
- Project key: Automatically generated based on your repository name

No manual configuration is needed in `sonar-project.properties` as GitHub Actions will set these values dynamically.

## Conventional Commits

This repository uses [Conventional Commits](https://www.conventionalcommits.org/) to standardize commit messages and automate versioning.

### Commit Format

Each commit message should follow this format:

```
<type>[optional scope]: <description>

[optional body]

[optional footer(s)]
```

Examples:
- `feat: add new feature`
- `fix: resolve login bug`
- `docs: update README`
- `chore(deps): update dependencies`

### Common Types

- `feat`: A new feature
- `fix`: A bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting, etc.)
- `refactor`: Code changes that neither fix bugs nor add features
- `perf`: Performance improvements
- `test`: Adding or correcting tests
- `chore`: Changes to the build process or auxiliary tools

## Automatic Versioning

This repository uses [semantic-release](https://github.com/semantic-release/semantic-release) to automatically version and tag releases based on commit messages:

- `feat:` commits trigger a minor version bump (1.0.0 → 1.1.0)
- `fix:` commits trigger a patch version bump (1.0.0 → 1.0.1)
- `feat!:` or commits with `BREAKING CHANGE:` in the footer trigger a major version bump (1.0.0 → 2.0.0)

## Setup

Run the following to set up the commit hooks locally:

```bash
npm install
```
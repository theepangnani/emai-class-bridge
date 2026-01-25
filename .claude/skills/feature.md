# /feature - Create Feature Branch

Create a new feature branch and set up for development.

## Usage

`/feature <feature-name>`

Example: `/feature ai-study-guide`

## Instructions

1. Ensure working directory is clean (no uncommitted changes)
2. Fetch latest from origin
3. Create new branch from main: `feature/<feature-name>`
4. Push the branch to origin with tracking

## Commands

```bash
# Check for uncommitted changes
git status

# Fetch latest
git fetch origin

# Create and checkout new branch
git checkout -b feature/<feature-name> origin/main

# Push branch with tracking
git push -u origin feature/<feature-name>
```

## Branch Naming Convention

- `feature/` - New features
- `fix/` - Bug fixes
- `refactor/` - Code refactoring
- `docs/` - Documentation updates

## After Creation

The user should:
1. Make changes
2. Commit with descriptive messages
3. Push changes
4. Create a Pull Request on GitHub

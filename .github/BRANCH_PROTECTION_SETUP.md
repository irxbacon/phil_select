# Branch Protection Setup Guide

This document provides step-by-step instructions for setting up branch protection rules on the `main` branch to ensure only the repository owner can merge changes.

## Overview

Branch protection rules help maintain code quality and control who can merge changes to important branches. The main branch protection will:

- Require pull request reviews before merging
- Require status checks to pass (CI/CD workflows)
- Restrict who can push to the branch
- Prevent force pushing and deletion of the branch

## Manual Setup via GitHub Web Interface

### Step 1: Navigate to Branch Protection Settings

1. Go to your repository on GitHub: `https://github.com/bcox-ctv/phil_select`
2. Click on **Settings** tab
3. In the left sidebar, click **Branches**
4. Click **Add rule** or **Add branch protection rule**

### Step 2: Configure Branch Protection Rule

**Branch name pattern:** `main`

**Protect matching branches settings:**

✅ **Require a pull request before merging**
- ✅ Require approvals: `1`
- ✅ Dismiss stale pull request approvals when new commits are pushed
- ✅ Require review from code owners (if CODEOWNERS file exists)
- ✅ Restrict pushes that create files larger than 100MB

✅ **Require status checks to pass before merging**
- ✅ Require branches to be up to date before merging
- Status checks that are required:
  - `test` (from CI workflow)
  - `security` (from CI workflow)

✅ **Require conversation resolution before merging**

✅ **Require signed commits**

✅ **Require linear history**

✅ **Restrict pushes to matching branches**
- Add the repository owner's username to the list of people, teams, or apps with push access

✅ **Allow force pushes**
- ❌ Leave unchecked (prevents force pushing)

✅ **Allow deletions**
- ❌ Leave unchecked (prevents branch deletion)

### Step 3: Apply and Test

1. Click **Create** to save the branch protection rule
2. Test by creating a pull request to verify the rules are working
3. Confirm that direct pushes to main are blocked

## Automated Setup via GitHub CLI (Alternative)

If you have GitHub CLI installed and configured:

```bash
# Install GitHub CLI if not already installed
# https://cli.github.com/

# Create branch protection rule
gh api repos/bcox-ctv/phil_select/branches/main/protection \
  --method PUT \
  --field required_status_checks='{"strict":true,"contexts":["test","security"]}' \
  --field enforce_admins=true \
  --field required_pull_request_reviews='{"required_approving_review_count":1,"dismiss_stale_reviews":true}' \
  --field restrictions='{"users":["bcox-ctv"],"teams":[],"apps":[]}' \
  --field allow_force_pushes=false \
  --field allow_deletions=false
```

## Verification

After setting up branch protection, verify it's working by:

1. **Testing direct push blocking:**
   ```bash
   # This should fail if protection is set up correctly
   git push origin main
   ```

2. **Testing pull request requirement:**
   - Create a new branch
   - Make changes and push to the new branch
   - Open a pull request to main
   - Verify that merge is blocked until reviews and status checks pass

3. **Checking protection status:**
   ```bash
   gh api repos/bcox-ctv/phil_select/branches/main/protection
   ```

## Status Checks Configuration

The CI workflow in `.github/workflows/ci.yml` provides the following status checks:

- **test**: Runs linting, application startup tests, and database schema validation
- **security**: Runs security scans using Bandit and Safety

These checks must pass before any pull request can be merged to main.

## Additional Security Measures

### CODEOWNERS File

Create a `.github/CODEOWNERS` file to require specific people to review changes:

```
# Global code owners
* @bcox-ctv

# Specific file patterns
*.py @bcox-ctv
*.sql @bcox-ctv
*.md @bcox-ctv
```

### Required Status Checks

The CI workflow will automatically run on all pull requests. Ensure these checks pass:

- Code linting (flake8)
- Application startup tests
- Database schema validation
- Security scanning (Bandit)
- Dependency vulnerability checks (Safety)

## Troubleshooting

### Common Issues

1. **Status checks not appearing:**
   - Ensure the CI workflow has run at least once on a pull request
   - Check that workflow names match the required status check names

2. **Unable to merge even as owner:**
   - Check if "Include administrators" is enabled
   - Verify that all required status checks are passing

3. **Workflow failures:**
   - Check the Actions tab for detailed error logs
   - Ensure all dependencies are properly specified in requirements.txt

### Support

If you encounter issues setting up branch protection:

1. Check GitHub's documentation: https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/defining-the-mergeability-of-pull-requests/about-protected-branches
2. Review the repository's Actions tab for workflow execution details
3. Verify that the repository settings allow the desired protection level

## Summary

Once configured, the main branch will be protected by:

- ✅ Pull request requirement with review approval
- ✅ Status check requirements (CI tests must pass)
- ✅ Restriction to repository owner for direct pushes
- ✅ Prevention of force pushes and branch deletion

This ensures that all changes go through proper review and testing before being merged to the main branch.
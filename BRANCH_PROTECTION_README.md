# Main Branch Protection Implementation

This repository now includes branch protection configuration to ensure only the repository owner can merge changes to the main branch.

## What's Been Added

### 1. GitHub Actions CI Workflow (`.github/workflows/ci.yml`)
- **Linting**: Runs flake8 to check code quality
- **Application Testing**: Verifies the Flask app starts correctly
- **Database Validation**: Tests that schema.sql is valid
- **Security Scanning**: Runs Bandit and Safety to check for vulnerabilities

### 2. Repository Configuration Files
- **`.github/CODEOWNERS`**: Requires owner review for all changes
- **`.github/pull_request_template.md`**: Standardized PR template
- **`.github/BRANCH_PROTECTION_SETUP.md`**: Detailed setup instructions

## Quick Setup (Repository Owner Only)

### Option 1: Via GitHub Web Interface

1. Go to your repository Settings → Branches
2. Click "Add rule" for the `main` branch
3. Enable these settings:
   - ✅ Require a pull request before merging (1 approval)
   - ✅ Require status checks to pass (`test` and `security`)
   - ✅ Require conversation resolution before merging
   - ✅ Restrict pushes to matching branches (add your username)
   - ❌ Allow force pushes (disabled)
   - ❌ Allow deletions (disabled)

### Option 2: Via GitHub CLI

```bash
gh api repos/bcox-ctv/phil_select/branches/main/protection \
  --method PUT \
  --field required_status_checks='{"strict":true,"contexts":["test","security"]}' \
  --field enforce_admins=true \
  --field required_pull_request_reviews='{"required_approving_review_count":1,"dismiss_stale_reviews":true}' \
  --field restrictions='{"users":["bcox-ctv"],"teams":[],"apps":[]}' \
  --field allow_force_pushes=false \
  --field allow_deletions=false
```

## How It Works

### Protection Features
1. **Pull Request Requirement**: All changes must go through PRs
2. **Code Review**: Owner must approve all PRs
3. **Automated Testing**: CI checks must pass before merge
4. **Push Restrictions**: Only owner can push directly (emergency only)
5. **No Force Push**: Prevents history rewriting
6. **No Branch Deletion**: Prevents accidental main branch removal

### Workflow for Contributors
1. Fork the repository or create a feature branch
2. Make changes and push to the branch
3. Open a Pull Request to main
4. Wait for CI checks to pass
5. Request review from repository owner
6. Owner reviews and merges if approved

### Workflow for Repository Owner
1. Review Pull Requests when they're opened
2. Check that CI tests pass
3. Review the code changes
4. Approve and merge if acceptable
5. For emergency fixes, can push directly to main (not recommended)

## Benefits

- **Quality Control**: All code is reviewed before merging
- **Automated Testing**: Catches issues before they reach main
- **Security**: Prevents unauthorized changes
- **History Protection**: Maintains clean git history
- **Documentation**: Standardized PR process

## Verification

After setup, test the protection by:

1. Trying to push directly to main (should fail)
2. Creating a test PR (should require review)
3. Checking that CI runs on PRs
4. Verifying merge is blocked until approval

## Emergency Procedures

If urgent fixes are needed:

1. **Preferred**: Create hotfix branch and fast-track PR
2. **Emergency Only**: Owner can temporarily disable protection rules
3. **Last Resort**: Owner can push directly if protection allows

## Security Considerations

The CI workflow includes:
- **Bandit**: Python security linter
- **Safety**: Dependency vulnerability scanner
- **Flake8**: Code quality checks
- **Application Tests**: Basic functionality verification

## Support

For detailed setup instructions, see `.github/BRANCH_PROTECTION_SETUP.md`

For questions about branch protection rules, see GitHub's official documentation:
https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/defining-the-mergeability-of-pull-requests/about-protected-branches
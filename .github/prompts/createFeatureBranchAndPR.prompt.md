---
name: createFeatureBranchAndPR
description: Create feature branch, commit changes, push, and open draft PR
argument-hint: feature description (optional - will auto-detect from changes)
---

# Create Feature Branch and Pull Request

Execute a complete git workflow following project conventions:

1. **Check Status**: Review current changes and untracked files
2. **Create Feature Branch**:
   - Get username from git config
   - Create branch following `dev/<username>/<feature-description>` format
   - Base branch on `develop` (or project's specified base)
3. **Stage Changes**: Add relevant files to git staging area
4. **Commit with Conventional Format**:
   - Analyze changes to determine appropriate type (feat, fix, docs, etc.)
   - Include scope based on affected area
   - Write clear, descriptive commit message
   - Use multi-line format with bullet points for details
5. **Push Branch**: Push to origin with upstream tracking
6. **Create Draft PR**:
   - Use repository management tools if available
   - Target the appropriate base branch (typically `develop`)
   - Include summary, changes list, and testing checklist
   - **Always create as draft** per project guidelines
   - Generate descriptive title following conventional commit format

Follow project-specific conventions for:

- Branch naming patterns
- Commit message formats
- PR templates and requirements
- Draft/ready status policies

If a feature description is provided, use it for branch naming. Otherwise, infer from the changes being committed.

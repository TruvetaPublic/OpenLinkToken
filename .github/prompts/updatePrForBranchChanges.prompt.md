---
name: updatePrForBranchChanges
description: Ensure the current PR reflects all branch changes versus its base.
argument-hint: base branch name (default: develop)
---

Check the current branch against the specified base branch to identify all commits and changes not yet reflected in the active pull request. Update the PR title and body so the Summary, Changes, Testing checklist, and Files Changed sections cover the full set of differences. If any discrepancies are found between the branch and PR description, revise the PR title/body to include them. Report what was updated and note any remaining review comments or gaps.

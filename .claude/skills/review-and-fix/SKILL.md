---
name: review-and-fix
description: Review a PR and fix all issues in a loop until clean, then ask if done
argument-hint: "[pr-number or branch]"
disable-model-invocation: false
---

Run a review-fix loop on the current PR or branch until there are no remaining issues or suggestions. Use $ARGUMENTS as the PR number or branch reference if provided; otherwise operate on the current branch.

## Loop Instructions

Repeat the following cycle until the review returns no actionable issues or suggestions, **up to a maximum of 6 iterations**. Track the current iteration count starting at 1.

### Step 1: Run PR Review

Run the following pr-review-toolkit skills **in sequence** (each via the Skill tool), passing $ARGUMENTS as the PR number or branch. Collect all issues and suggestions from their combined output:

1. `pr-review-toolkit:code-reviewer` — general code quality, logic, edge cases
2. `pr-review-toolkit:silent-failure-hunter` — error handling, swallowed errors, missing propagation
3. `pr-review-toolkit:type-design-analyzer` — type correctness, struct design, API surface

If all three reviews report **no issues and no suggestions**, exit the loop and go to **Done**.

### Step 2: Fix All Issues

For every issue or suggestion identified in the review:
- Fix the code as described
- Apply all fixes in this round before moving to the next step
- Do not skip any issue, even if it seems minor

### Step 3: Quality Gate

Run `just check` to verify the full quality gate passes (TypeScript typecheck + ESLint + Prettier + Clippy + cargo fmt).

If `just check` fails:
- Fix any errors it reports
- Re-run `just check` until it passes

### Step 4: Run Tests

Run `just test` to execute the full test suite.

If tests fail:
- Fix the failing tests or the code causing them
- Re-run `just test` until all tests pass

### Step 5: Commit

Commit all changes made in this round with a clear, conventional commit message describing what was fixed. Follow the project's commit conventions (conventional commits format, Polish-language bullet points for details).

Increment the iteration counter, then **return to Step 1** and run the review again — unless the limit has been reached (see below).

---

## Done

When the review finds no more issues or suggestions and all checks and tests pass, stop the loop and ask the user:

> "The review loop is complete — no more issues or suggestions found, `just check` passes, and all tests pass. Is there anything else you'd like me to do with this PR?"

## Loop Limit Reached

If 6 iterations complete and issues are still being found, stop the loop and report to the user:

> "Reached the 6-iteration limit. The last review still found issues. Here is a summary of the remaining issues: [list them]. Please review manually or ask me to continue."

---
name: mp
description: Commit, push, and open or update a pull request for the current ticket branch (the old m&p shortcut). Use when asked to wrap up, commit and push, or open the PR for the current issue.
---
# Commit, push and open the pull request

End-of-session routine for **ticket work on a branch**, never a direct commit to `main`.

1. Update `progress.md` with a short handoff note for this session and prune old session logs. Make sure the docs match the change.
2. If the current branch is `main` (or `master`), stop. Create or switch to `issue-N-short-slug` for the GitHub issue being worked, then continue.
3. Commit the relevant changes. Do not use `git add .` if it would pick up secrets or local files (`.env`, `settings.json`, `history.json`).
4. Push the branch (`git push -u origin HEAD` if it has no upstream).
5. Open a pull request if none exists (`gh pr create`), otherwise the push updates it. The PR body must include `Closes #N`.
6. Do not merge to `main` unless the user explicitly asks to merge that PR.

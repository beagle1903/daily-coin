---
name: m&p
description: Commit, push, and open or update a pull request for the current ticket branch.
---
# Merge, Commit, and Push

When the user triggers this skill, perform the end-of-session routine for **ticket work on a branch**, not a direct commit to `main`.

1. Update `progress.md` with short handoff notes describing what was done during the session. Prune old session logs.
2. If the current branch is `main` (or `master`), stop. Create or switch to `issue-N-short-slug` for the GitHub issue being worked, then continue. Do not commit ticket work directly to `main`.
3. Commit relevant changes on the current branch. Do not use `git add .` if that would include secrets or unrelated local files (for example `settings.json`, `.env`).
4. Push the branch (`git push -u origin HEAD` if it has no upstream).
5. Open a pull request if one does not exist (`gh pr create`), or push to update the existing PR. The PR body must include `Closes #N` for the issue.
6. Do not merge to `main` as part of this skill unless the user explicitly asks to merge that PR.

Make sure documentation is up to date before committing.

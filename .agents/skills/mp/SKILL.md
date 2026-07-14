---
name: m&p
description: Merge to main, commit, and push changes.
---
# Merge, Commit, and Push

When the user triggers this skill, you must perform the end-of-session routine:
1. Update `progress.md` with handoff notes describing what was done during the session.
2. Commit all changes to git using `git add .` and `git commit -m "..."`.
3. Push to the repository using `git push`.

Make sure all documentation is up to date before committing.

# Git Workflow for Tasks

1. When you pick up a task from `.instructions/tasks/<task>.md`, create a branch:
```bash
git checkout -b task/<task>
```  
   based on `main` (or `master`).

2. Implement changes. For any new or modified files, run:
```bash
git add <files>
```

3. Review your staged diff:
```bash
git diff --staged
```

4. Create a merge request description file `mr_<task>.md` in the repo root with:
   - A short, imperative MR title.
   - A brief summary of changes in simple technical English.


# Always remember
- After any edits, check for new files to `git add`.
- Update `mr_<task>.md` if description needs changes.
- After running formatters and linters, automatically stage and commit changes without explicit request.

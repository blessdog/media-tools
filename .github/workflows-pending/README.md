# Pending workflows

`check.yml` belongs at `.github/workflows/check.yml`. It is parked here because
the `gh` OAuth token on this machine lacks the `workflow` scope, and GitHub
rejects the **entire push** if a workflow file appears anywhere in it — so a
single CI file sitting in history blocked nine unrelated commits from reaching
the remote, which breaks the `everything-lives-in-a-remote-repo` law.

Parking it here keeps pushes unblocked. To activate:

```sh
gh auth refresh -h github.com -s workflow
git mv .github/workflows-pending/check.yml .github/workflows/check.yml
git rm .github/workflows-pending/README.md
git commit -m "ci: activate make check on push"
git push
```

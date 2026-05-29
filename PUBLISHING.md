# Publishing

This repo is the **project-mental-model** Claude skill. It bundles one tool that
is also published to PyPI: **codegraph** (PyPI distribution name `codegraph-pmm`,
in [`tools/codegraph/`](tools/codegraph/)). The skill itself is shared by cloning
this repo; only codegraph goes to PyPI.

Publishing uses **PyPI Trusted Publishing (OIDC)** from GitHub Actions — there is
**no API token** anywhere (nothing to leak or rotate). The
[`.github/workflows/publish.yml`](.github/workflows/publish.yml) workflow does it.

## One-time setup (do this before the first release)

1. **Create the GitHub repo** under the `PsChina` account, e.g.
   `github.com/PsChina/project-mental-model`. Push this skill's contents to it.
   (If you pick a different repo name, update the `[project.urls]` in
   `tools/codegraph/pyproject.toml` and the "Repository name" in step 3.)
   - Public is recommended (the privacy audit is clean — no secrets, no internal
     names, no machine paths). Trusted Publishing also works with a **private** repo.

2. **Register a PyPI account** at <https://pypi.org> (one-time, email-verified).
   This account is the *owner* of the `codegraph-pmm` name. You cannot publish a
   pip package "with a GitHub account" — PyPI is a separate identity.

3. **Add a "pending" Trusted Publisher** on PyPI
   (Account → *Publishing* → *Add a new pending publisher*). "Pending" lets you
   claim the brand-new name directly from CI — no manual first upload:
   - **PyPI Project Name:** `codegraph-pmm`
   - **Owner:** `PsChina`
   - **Repository name:** `project-mental-model`
   - **Workflow name:** `publish.yml`
   - **Environment name:** `pypi`

4. **(Recommended) Create the `pypi` GitHub Environment**
   (repo Settings → *Environments* → *New environment* → `pypi`). It must match
   the `environment:` in the workflow and the environment in step 3. You can add
   protection rules (e.g. required reviewer) here.

## Cutting a release

1. Bump `version` in [`tools/codegraph/pyproject.toml`](tools/codegraph/pyproject.toml).
2. Commit, then tag and push the tag:
   ```sh
   git tag codegraph-v0.1.0
   git push origin codegraph-v0.1.0
   ```
3. The workflow builds `tools/codegraph`, runs `twine check`, and publishes via OIDC.
4. Verify: `pipx install codegraph-pmm` then `codegraph --help` (command stays
   `codegraph`; only the PyPI distribution name is `codegraph-pmm`).

## Relationship to the company brain repo

This skill also currently sits inside the private `engineering-standards` repo at
`skills/project-mental-model/` (where Claude Code loads it from `~/.claude/skills/`).
If `PsChina/project-mental-model` becomes the skill's canonical home, avoid tracking
it in two places: either add `skills/project-mental-model/` to the brain repo's
`.gitignore`, or wire it in as a git **submodule** pointing at the PsChina repo.

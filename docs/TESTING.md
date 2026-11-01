# Testing

## Run everything

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

Expected on a clean v2 tree: 373 tests pass.

## Run one module

```bash
PYTHONPATH=src python3 -m unittest tests.test_core -v
PYTHONPATH=src python3 -m unittest tests.test_adapter -v
PYTHONPATH=src python3 -m unittest tests.test_drift -v
PYTHONPATH=src python3 -m unittest tests.test_mesh -v
PYTHONPATH=src python3 -m unittest tests.test_mediator -v
PYTHONPATH=src python3 -m unittest tests.test_cli -v
PYTHONPATH=src python3 -m unittest tests.test_installer -v
```

## Real host proof

The adapter tests use a fake host binary so CI does not spend money. A real Claude run was performed separately:

```bash
# create a project, plan a host step, approve it, then:
aperio run <task-id> --actor hermes
aperio verify <task-id>
```

The real run produced `site/index.html`, passed the acceptance check, and completed review and done. A real Claude reviewer then reviewed a separately verified task from a brief-only workspace and returned `confirmed`. A live Goose run failed with HTTP 500 from its local bridge; the Goose command path is tested with a fake binary only.

## Run the demo loop by hand

```bash
T="$(mktemp -d)"
export PYTHONPATH=src
python3 -m aperio --project "$T" init "$T" --name demo
python3 -m aperio --project "$T" ask "Build the demo site" --source owner
OUT="$(python3 -m aperio --project "$T" plan examples/demo-site-plan.json)"
TASK="$(printf '%s\n' "$OUT" | awk 'NR==1{print $1}')"
PLAN="$(printf '%s\n' "$OUT" | awk 'NR==1{print $2}')"
python3 -m aperio --project "$T" approve "$PLAN" --by owner --confirm "I approve this plan"
python3 -m aperio --project "$T" run "$TASK"
python3 -m aperio --project "$T" verify "$TASK"
python3 -m aperio --project "$T" review "$TASK" --reviewer qa --verdict confirmed
python3 -m aperio --project "$T" done "$TASK"
python3 -m aperio --project "$T" handoff "$TASK" --print
```

## What the tests actually cover

- state initialization and reinitialization refusal;
- append-only asks;
- plan approval requirement;
- allowed-path enforcement;
- path traversal and symlink refusal;
- write steps, shell steps, and timeout behavior;
- undeclared file changes detected as violations;
- verification pass and failure;
- independent reviewer enforcement;
- rollback of modified and created files;
- CLI end-to-end flow;
- installer dry run, install, reinstall, and uninstall.

## Installer exit-code contract

Both installers (`install.sh`, `install.ps1`) agree on these codes. Human-readable text may differ; codes must not.

- `0` — success, including `--check` when the installed version matches source, and completed `--dry-run` runs.
- `1` — a failure after work started: for example `--check` with a version mismatch, or an update that failed after its backup was taken — even when the backup could not be moved back into place (the moved-aside library is restored instead, so a working install remains).
- `2` — a refusal or failure before guarantees apply: unsafe prefix, missing or invalid backup, refusing to overwrite a foreign skill file, or a `--rollback` that could not complete.

## What the tests do not cover

- Host authentication, model access, or dispatch.
- CMS persistence, publishing, permissions, or rollback.
- SEO against built output.
- Real browser, mobile, or accessibility inspection.
- Deployment.
- Native Windows execution of `aperio.cmd`; the PowerShell installer itself is tested under `pwsh` on macOS.

Do not cite a passing test suite as proof of any item in that list.

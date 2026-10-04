# Prebuilt Assets

An app can publish its built JS, CSS, and SPA files from CI. Pilot then downloads them for the exact commit it deploys and skips the build. Apps that publish nothing are built on the server as before.

## Publish From CI

Add this workflow to the app repository, for example as `.github/workflows/assets.yml`:

```yaml
name: Assets

on:
  push:
    branches: [develop, version-16]

jobs:
  assets:
    uses: frappe/pilot/.github/workflows/app-assets.yml@develop
    permissions:
      contents: write
```

For each push, the workflow builds the app against the matching Frappe branch and uploads `<app>-<commit>.tar.gz` and `<app>-<commit>.tar.gz.sha256` to the release `assets-<branch>`. It keeps the assets of every tagged commit and of the newest 30 other commits. Set the `keep` input to change that number. Set the `frappe-branch` input when the app branch name does not tell the Frappe branch: `version-16` and `version-16-hotfix` build against `version-16`, and every other branch builds against `develop`.

## Declare SPAs

esbuild bundles in `<app>/public/dist` need no setting. An app that builds a SPA declares where the build writes, with the keys that Frappe Cloud also reads. Paths are relative to the repository root.

```toml
[tool.bench.assets]
build_dir = "./frontend"
out_dir = "./gameplan/public/frontend"
index_html_path = "./gameplan/www/g.html"
```

An app with several SPAs uses one table for each:

```toml
[[tool.bench.assets]]
build_dir = "./frontend"
out_dir = "./hrms/public/frontend"
index_html_path = "./hrms/www/hrms.html"

[[tool.bench.assets]]
build_dir = "./roster"
out_dir = "./hrms/public/roster"
index_html_path = "./hrms/www/roster.html"
```

The CI build fails when the app has a `build` script in `package.json` and declares no SPA, because the published files would not include the SPA.

## How Pilot Uses Them

When Pilot builds an app's assets without `--force` and the app has no local changes, it reads the checksum for the checked-out commit from the app's GitHub release.

| Result | Pilot does |
|---|---|
| No checksum for the commit, or the download fails | Builds on the server and logs why. |
| The archive matches its checksum and was built for this commit | Replaces each published path whole, so files that a newer build removed do not stay. |
| The checksum or the commit does not match | Stops with an error. A wrong archive is not hidden behind a build. |

Only public GitHub repositories are supported. To build locally, run `pilot build --force`.

## Build Locally

`scripts/build-app-assets.sh <app checkout> <frappe branch> <output dir>` is what the workflow runs. It needs git, Python 3.11 or later, Node.js 24, and yarn.

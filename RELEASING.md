# Releasing runlog-skills

This is a content/docs repo: SKILL.md bodies for the 9 vendor adapters
plus the JSON plugin manifests `npx @runlog/install` consumes. A
"release" is a tag downstream consumers can pin to. The
[`release`](.github/workflows/release.yml) workflow re-runs the same
gates [`ci.yml`](.github/workflows/ci.yml) applies on push/PR
(markdown-lint + dead-link-check) on the tag commit, then creates a
GitHub Release with auto-generated notes. There are no build artefacts
beyond the source archive GitHub auto-attaches.

<!-- TODO link runlog-docs/13-release-trains.md once T4 lands -->

## Cut a release

1. Make sure CI is green on `main` and you're on it:

       git checkout main && git pull --ff-only

2. Pick a version. Tag shape is `skills/vX.Y.Z` — the `skills/` path
   scope is part of the release-train discipline (see the runlog-docs
   convention page once T4 lands). Use semver (`skills/v0.MINOR.PATCH`
   while pre-1.0). See [Versioning policy](#versioning-policy) below
   for the bump rules.

3. Tag and push:

       git tag -a skills/v0.1.0 -m "Release skills/v0.1.0"
       git push origin skills/v0.1.0

   Tags matching `skills/v*-rc*`, `skills/v*-beta*`, or
   `skills/v*-alpha*` ship as **prereleases**; everything else ships
   as a normal release.

4. Watch the workflow on GitHub Actions. On success, the tag appears
   on the Releases page with auto-generated notes (commits + merged
   PRs since the previous tag) and the source `.tar.gz` / `.zip`
   GitHub attaches.

## Pinning from a consumer

The Claude Code plugin marketplace consumes this repo directly via
`/plugin marketplace add runlog-org/runlog-skills` (see the README's
install paths for the full list of host integrations including
`npx @runlog/install <vendor>`). For reproducible installs, pin to a
`skills/vX.Y.Z` tag rather than `main` — `main` works for development
but exposes consumers to mid-stream additions; tags are the supported
contract.

## Versioning policy

The skills repo is **pre-1.0**, so the bump rules are:

- **MINOR** — additive: adding a vendor adapter, adding a canonical
  body section under `runlog-author/` or `claude-code/`, adding a new
  field to a SKILL.md front-matter that consumers can ignore.
- **PATCH** — wording fixes, link repairs, dead-link-check
  exclusions, internal cleanup that doesn't change what consumers see.
- **MAJOR** — breaking: removing a vendor adapter, breaking the
  SKILL.md interface (front-matter shape, plugin manifest contract),
  or restructuring `skills/` in a way that invalidates existing
  consumer pin paths.

There is no `VERSION` file at the repo root: the git tag is the
authoritative version. If a script needs the current version
programmatically, `git describe --tags --match 'skills/v*' --abbrev=0`
reads it.

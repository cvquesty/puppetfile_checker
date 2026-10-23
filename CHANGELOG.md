# Changelog

## 1.0.2 - 2026-10-23

- The table is only modules whose Forge release is newer than the
  pin. A pin that matches the Forge version is not a row.

## 1.0.1 - 2026-10-23

- The report lists only modules that should be updated, and lookups
  that failed. Pins that already match the Forge are a count.

## 1.0.0 - 2026-10-23

First release.

- Report every Forge pin against the current Forge release.
- Treat `8.1.0` and `v8.1.0`, and `1.0` and `1.0.0`, as the same release.
- Skip a deleted Forge release and a value that is not a version.
- `-f` rewrites every behind pin after you type `update`.
- Backups go in `changes/` next to the Puppetfile. Five copies are kept.
- `--recover` restores one of those copies.

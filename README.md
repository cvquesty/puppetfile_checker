# puppetfile_checker

`check_puppetfile` reads a Puppetfile, asks the Puppet Forge for the
current release of each pinned module, and prints a table.

A pin is **current** when it is the same release as the Forge, including
`8.1.0` and `v8.1.0`, or `1.0` and `1.0.0`. A pin is **update** only when
the Forge release is newer. The table lists updates and failed lookups.
Pins that already match are counted and not printed. Git modules
(`:git`) are skipped. The Forge does not publish a version for those.

With no switches the script only prints. It does not edit the Puppetfile.

## Requirements

- Python 3.9 or newer
- Outbound HTTPS to `https://forgeapi.puppet.com`
- `git` on `PATH` only if you use `-f` or `--recover` inside a git checkout

There is nothing to install. The script uses the Python standard library.

## Install

Copy `check_puppetfile` onto your `PATH` and make it executable:

```bash
install -m 0755 check_puppetfile /usr/local/bin/check_puppetfile
```

Or run it from a clone of this repository:

```bash
git clone git@github.com:cvquesty/puppetfile_checker.git
./puppetfile_checker/check_puppetfile /path/to/Puppetfile
```

## Usage

```bash
check_puppetfile [Puppetfile] [--timeout SECONDS] [-f] [--recover]
```

| Command | What it does |
| --- | --- |
| `check_puppetfile` | Check `./Puppetfile` and print the table |
| `check_puppetfile /path/to/Puppetfile` | Check that file |
| `check_puppetfile --timeout 15` | Wait 15 seconds for each Forge request |
| `check_puppetfile -f` | Rewrite every behind pin, after you type `update` |
| `check_puppetfile --recover` | Restore one of the last five backups |

`-f` and `--recover` are the only switches that change a Puppetfile.
Do not pass both.

### The report

```text
module                  pinned   latest   status
puppetlabs-stdlib       9.6.0    9.7.0    update
puppetlabs-concat       9.0.2    9.0.2    current
```

Current pins are a count in the header. They are not rows. The last
lines say how many modules should be updated, and how many the Forge
could not resolve.

### Exit status

| Status | Meaning |
| --- | --- |
| 0 | Every Forge pin is current, or newer than the Forge |
| 1 | At least one pin is behind, or a Forge lookup failed |
| 2 | The Puppetfile cannot be read, or you cancelled a write |

Use status 1 in CI when you want the job to fail on a stale pin.
The Puppetfile is still not modified.

### Rewriting pins

`-f` rewrites every behind pin in one pass. It cannot update a single
module. A newer Forge release can drop support or change defaults.
Read the table first.

Before it writes, the script copies the Puppetfile to `changes/` in
the same directory as that file. Only the five newest copies are kept.
Type the word `update` to confirm. Any other answer cancels.

When that directory is inside a git checkout, the new backup is staged
and an aged backup is removed from the index. Commit that change
yourself. The script does not commit.

### Restoring a backup

```bash
check_puppetfile --recover
```

The script lists the five newest copies, newest first, with the date
each was saved. Choose a number. The Puppetfile you have now is copied
into `changes/` first, then the selected copy replaces it.

## What the script reads

A Forge pin is one line:

```puppet
mod 'puppetlabs-stdlib', '9.6.0'
```

Single or double quotes both work. A comment after the pin is kept
when `-f` rewrites the line. These lines are skipped:

```puppet
mod 'profiles',
  :git => 'git@github.com:example/profiles.git'
```

A deleted Forge release is not offered as an update. A value that is
not a version is not offered either.

## License

Apache-2.0. See [LICENSE](LICENSE).

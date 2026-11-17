---
date: 2026-11-17
slug: what-my-first-real-deploy-taught-my-tests
title: What my first real deploy taught my tests
description: My deploy tool passed hundreds of tests, then failed on its first real host. Three bugs the rehearsal missed, how I found them, and the tests I added.
authors: [lam]
categories: [Deploy]
tags: [testing, linux, deploy, debugging]
---

# What my first real deploy taught my tests

For one of my labs I wrote a small deploy tool. It installs a release of a Django app onto a
Linux server: unpack, set up a database, configure nginx and systemd, switch to the new version,
and roll back by itself if the health check fails. It had hundreds of passing tests, including a
full rehearsal of the install. The first time I ran it on a real server, the site answered
**502 Bad Gateway**. Behind that error were three bugs, and each one shows a different way a
test can agree with your assumptions instead of with reality.

<!-- more -->

## The rehearsal, and what it can't see

The deploy normally runs as root. To test it without root, the whole install runs as a normal
user into a temporary folder (a "DESTDIR", as in `make install DESTDIR=…`). Commands that need
privileges (`systemctl`, `nginx`, `mariadb`, `useradd`) are not executed but recorded by a fake
command runner, and the recorded list is compared with a reviewed "golden" list.

That catches most logic bugs. But it has two blind spots: a fake only knows what you told it,
and everything runs as **one user**. All three bugs lived there.

## Debugging from the outside in

I went from the symptom inwards, with read-only commands: nginx, then systemd, then the files on
disk, then the tool's own records.

1. **Is the app running?** `systemctl status` said the units **didn't exist**. So not a
   crashing app: it was never installed.
2. **What does nginx say?** Its error log: `connect() to unix:/run/tenantlab/gunicorn.sock
   failed (2: No such file or directory)`. The site was enabled and pointed at a socket nobody
   had created. That explains the 502, not why the deploy stopped.
3. **What did the tool record?** It keeps a state file with the result of every step. One
   read showed `"provision-db": "failed"` and every later step `skipped`.
4. **What did get created?** Listing the install folder turned up a second problem (below).
5. **The real error**, from the terminal output of the deploy:

```text
error: step 'provision-db' failed: grants are not least-privilege:
  tlab_app: no grant on `tlab\_%`.*
  tlab_ro: no grant on `tlab\_%`.*
nothing serving traffic was changed
```

## Bug 1: the fake printed what I expected, not what the client prints

After creating the databases and users, the tool checks that each user has exactly the
privileges it should. It runs `SHOW GRANTS` through the `mariadb` command-line client and looks
for the grant text.

The grants were correct. The check failed anyway, because in `--batch` mode the client
**escapes special characters in its output**: a backslash comes out as `\\`. Running the same
query twice made it obvious:

```text
$ sudo mariadb --batch --skip-column-names -e "SHOW GRANTS FOR 'tlab_ro'@'localhost'"
GRANT SELECT ON `tlab\\_%`.* TO `tlab_ro`@`localhost`

$ sudo mariadb --batch --skip-column-names --raw -e "SHOW GRANTS FOR 'tlab_ro'@'localhost'"
GRANT SELECT ON `tlab\_%`.* TO `tlab_ro`@`localhost`
```

**Why the tests missed it:** the fake runner answered `SHOW GRANTS` with the unescaped text,
the text I *expected* the client to print. The code and the fake agreed with each other, and
both were wrong about the real tool.

**Fix:** the client now always runs with `--raw`. More important, the fake now **behaves like
the real client**: it escapes its output unless `--raw` is passed.

```python
# like the real client: --batch without --raw escapes the output (\ -> \\)
return Result(0, out if "--raw" in argv else out.replace("\\", "\\\\"))
```

With the flag removed from the code, the rehearsal now fails with exactly the error the real
server printed. That's the check I want from a fake: it fails the same way reality does.

## Bug 2: a release folder only root could open

While looking around in step 4, I listed the releases folder:

```text
drwx------ root root  releases/0.0.0.dev11+gbf0bf31/
```

Mode `0700`: only root can enter it. The app runs as its own service user, so it couldn't have
read its own code. The deploy had stopped earlier, but the restart would have failed here.

**Root cause:** the release is unpacked into a folder from `tempfile.mkdtemp()`, which is always
created with mode `0700`, on purpose. It was then copied into place with `shutil.copytree`,
which **copies the source folder's mode too**. The files inside were fine; the folder itself
was locked.

**Why the tests missed it:** the rehearsal runs as one user, who owns the folder and can open it
whatever its mode. A test that runs as the owner can never be the one locked out.

**Fix:** the copy helper sets the mode of the destination explicitly, and the test asserts it:

```python
def copytree(self, src: Path, dest: str, mode: int = 0o755) -> None:
    """``mode`` is set on ``dest`` itself: ``copytree`` copies the source's mode, and a
    ``mkdtemp`` source is 0700 (the service user could not read the release)."""
    ...
    shutil.copytree(src, real, symlinks=True)
    real.chmod(mode)
```

```python
assert oct(rel.stat().st_mode & 0o777) == "0o755"
```

## Bug 3: "nothing serving traffic was changed" wasn't true

The deploy's failure message said nothing serving traffic had changed. On this server, that was
false: port 8088 now answered 502.

**Root cause:** the nginx steps run early. They write the site config, test it with `nginx -t`,
enable it and reload nginx, before the app exists. When a later step fails, the tool lifts
maintenance mode and marks the release as failed, but it doesn't undo the nginx site. On an
upgrade that's harmless, because the site points at the previous release, which is still
running. On a **first install** there is nothing behind it.

**Status:** honestly, this one is still open in the lab. The impact is small: only the tool's
own port is affected, and nginx's other sites are untouched. The fix I've chosen is the smallest
one: when a first install fails before the switch, remove the site link this run created and
reload nginx. The test is already clear: a first install that fails at the database step must
leave no enabled site behind.

## What I changed in how I test

- **A fake encodes an assumption about the real system.** When a fake stands in for an external
  tool, copy its real output, quirks included, from one manual run. Mine now escapes like
  `mariadb` does.
- **Tests that run as one user can't see permission bugs.** If a file will be read by a
  different user, assert its mode explicitly.
- **Copy helpers copy metadata.** `shutil.copytree` keeps the source's mode, and `mkdtemp` is
  always `0700`. Set the mode of anything that leaves a temporary folder.
- **Read the tool's own records first.** The per-step state pinned the failing step in one read.
  It didn't hold the error text, so I had to go back to the terminal; keeping the last error in
  the state file would save that step.
- **Test "nothing changed" on a first install separately.** "Failed before the switch" is only
  harmless when something is already serving.

## Lesson

A rehearsal proves the logic, not the host. Each real run that surprises you should end with a
fake that's closer to reality, and a test that fails the way the real system failed.

#!/usr/bin/env python3
"""Install isolated dotfile copies; close configuration-writing apps before apply.

Plan and check are read-only. Apply snapshots recognized legacy links before
detaching them. Backups and a recovery journal live in the private state directory;
migration backups remain local after source cleanup.
"""

import argparse
from contextlib import contextmanager
from copy import deepcopy
import fcntl
import hashlib
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import sys
import tempfile
import uuid

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent / "lib"))
from dotfile_composition import compose_claude_settings, reconcile_codex_hooks


class InstallError(ValueError):
    """A configuration or filesystem boundary needs operator attention."""


def absolute(path):
    return Path(os.path.abspath(path))


def within(path, parent):
    return path == parent or parent in path.parents


def exists(path):
    return path.exists() or path.is_symlink()


def signature(data, execute):
    return {"sha256": hashlib.sha256(data).hexdigest(), "execute": execute}


def file_signature(path):
    if path.is_symlink() or not path.is_file():
        return None
    return signature(path.read_bytes(), stat.S_IMODE(path.stat().st_mode) & 0o111)


def json_bytes(value):
    return (json.dumps(value, indent=2, ensure_ascii=False) + "\n").encode()


def load_json(path):
    try:
        return json.loads(path.read_bytes())
    except (ValueError, OSError) as error:
        # JSON decoder messages can contain local setting values.
        raise InstallError(f"cannot read JSON object: {path}") from error


def atomic_write(path, data, mode=0o600, expected=None):
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, name = tempfile.mkstemp(prefix=f".{path.name}.knapsack-", dir=path.parent)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(name, mode)
        if expected is not None and (exists(path), file_signature(path)) != expected:
            raise InstallError(f"destination changed before replacement: {path}")
        os.replace(name, path)
    finally:
        if os.path.lexists(name):
            os.unlink(name)


class Installer:
    """One checkout, home, and machine-local ownership ledger."""

    def __init__(self, root, home, state_dir=None):
        self.root = absolute(root).resolve()
        self.home = absolute(home)
        self.state = absolute(state_dir or self.home / ".local/state/knapsack")
        if within(self.state, self.root) or within(self.home, self.root):
            raise InstallError("home and state must be outside the checkout")
        self.shared = self.root / "dotfiles/shared"
        self.aliases = {
            self.shared / "codex/AGENTS.md": "../claude/CLAUDE.md",
            self.shared / "gemini/GEMINI.md": "../claude/CLAUDE.md",
            self.shared / "gemini/agents": "../claude/agents",
        }
        self.tracked = self.git("ls-files", "-z", "--", "dotfiles/shared", "dotfiles/seed").split(b"\0")
        self.tracked = [Path(os.fsdecode(item)) for item in self.tracked if item]
        self.legacy = self.legacy_mappings()
        self.conflicts = []
        self.actions = []
        self.preimages = {}
        self.owned_desired = None

    def git(self, *arguments):
        try:
            environment = dict(os.environ, GIT_OPTIONAL_LOCKS="0")
            return subprocess.check_output([
                "git", "-c", "core.fsmonitor=false", "-C", str(self.root), *arguments,
            ], stderr=subprocess.DEVNULL, env=environment)
        except subprocess.CalledProcessError as error:
            raise InstallError("cannot inspect checkout with Git") from error

    def legacy_mappings(self):
        mappings = {}
        relatives = [path.relative_to("dotfiles/shared") for path in self.tracked
                     if path.is_relative_to("dotfiles/shared")]
        for relative in relatives:
            parts = relative.parts
            mappings[self.home / ("." + parts[0])] = self.shared / parts[0]
            if len(parts) > 1:
                mappings[self.home / ("." + parts[0]) / parts[1]] = self.shared / parts[0] / parts[1]
            mappings[self.destination(relative)] = self.shared / relative
        # Runtime-owned skills were historically deployed even though excluded
        # from the new manifest. Do not infer arbitrary mappings from link text.
        mappings[self.home / ".claude/skills"] = self.shared / "claude/skills"
        mappings[self.home / ".agents/skills"] = (
            self.shared / "agents/skills", self.shared / "claude/skills",
        )
        mappings[self.home / ".claude/settings.json"] = self.shared / "claude/settings.json"
        return mappings

    def destination(self, relative):
        return self.home / ("." + relative.parts[0]) / Path(*relative.parts[1:])

    def allowed_legacy(self, path):
        if not path.is_symlink() or path not in self.legacy:
            return False
        expected = self.legacy[path]
        choices = expected if isinstance(expected, tuple) else (expected,)
        target = absolute(path.parent / os.readlink(path))
        return target in choices

    def source_path(self, path):
        """Resolve only the three declared repository aliases."""
        for component in reversed((path, *path.parents)):
            if not within(component, self.shared):
                continue
            if component.is_symlink():
                if component not in self.aliases or os.readlink(component) != self.aliases[component]:
                    raise InstallError(f"unsupported source symlink: {component.relative_to(self.root)}")
                replacement = absolute(component.parent / os.readlink(component))
                return self.source_path(replacement / path.relative_to(component))
        if not path.is_file():
            raise InstallError(f"tracked source is not a regular file: {path.relative_to(self.root)}")
        return path

    def manifest(self):
        managed, seeds = {}, {}
        for tracked in self.tracked:
            if "__pycache__" in tracked.parts or tracked.suffix in (".pyc", ".pyo"):
                continue
            if tracked.is_relative_to("dotfiles/seed"):
                relative = tracked.relative_to("dotfiles/seed")
                source = self.root / tracked
                if source.is_symlink() or not source.is_file():
                    raise InstallError(f"seed source must be a regular file: {tracked}")
                seeds[self.destination(relative)] = (source.read_bytes(), stat.S_IMODE(source.stat().st_mode))
                continue
            relative = tracked.relative_to("dotfiles/shared")
            if relative.is_relative_to("claude/skills") or relative.as_posix() in {
                "codex/hooks.json", "codex/hooks.json.bak", "claude/settings.json",
            }:
                continue
            if relative.as_posix() == "gemini/agents":
                alias = self.shared / relative
                if not alias.is_symlink() or os.readlink(alias) != self.aliases[alias]:
                    raise InstallError("gemini/agents must be the declared source alias")
                for agent in self.tracked:
                    if agent.is_relative_to("dotfiles/shared/claude/agents"):
                        leaf = agent.relative_to("dotfiles/shared/claude/agents")
                        source = self.source_path(self.root / agent)
                        managed[self.home / ".gemini/agents" / leaf] = (
                            source.read_bytes(), stat.S_IMODE(source.stat().st_mode),
                        )
                continue
            source = self.source_path(self.root / tracked)
            managed[self.destination(relative)] = (source.read_bytes(), stat.S_IMODE(source.stat().st_mode))
        if (self.root / "dotfiles/merge/claude/settings.json").exists():
            seeds[self.home / ".claude/settings.machine.json"] = (b"{}\n", 0o600)
        return managed, seeds

    def safe_ancestors(self, path, allow_legacy=False, include=False):
        """Refuse symlinks before any filesystem creation or write."""
        components = list(reversed((path, *path.parents))) if include else list(reversed(path.parents))
        for component in components:
            if component.is_symlink():
                if allow_legacy and self.allowed_legacy(component):
                    self.snapshot_digest(component.resolve(strict=True))
                    return
                raise InstallError(f"unexpected symlink boundary: {component}")
            if component.exists() and not component.is_dir():
                raise InstallError(f"non-directory ancestor: {component}")

    def preflight(self, paths, allow_legacy=False):
        self.safe_ancestors(self.home, include=True)
        self.safe_ancestors(self.state, include=True)
        for path in paths:
            if not within(path, self.home) or path == self.home:
                raise InstallError("destination escapes home")
            self.safe_ancestors(path, allow_legacy=allow_legacy)
            if allow_legacy and any(self.allowed_legacy(parent) for parent in path.parents):
                continue
            if path.is_symlink() and not (allow_legacy and self.allowed_legacy(path)):
                raise InstallError(f"unexpected destination symlink: {path}")

    def snapshot_digest(self, source, destination=None, active=()):
        """Fingerprint and optionally copy complete contents without following external links."""
        if source in active:
            raise InstallError(f"source symlink cycle: {source}")
        mode = source.lstat().st_mode
        digest = hashlib.sha256()
        if stat.S_ISLNK(mode):
            text = os.readlink(source)
            try:
                target = source.resolve(strict=True)
            except (OSError, RuntimeError) as error:
                # Resolve existing ancestors of dangling targets for boundary
                # classification, but never copy the resolved external chain.
                try:
                    target = source.resolve(strict=False)
                except (OSError, RuntimeError) as unresolved:
                    raise InstallError(f"cannot classify source symlink: {source}") from unresolved
                if within(target, self.root):
                    raise InstallError(f"dangling or cyclic internal link: {source}") from error
            if within(target, self.root):
                if source not in self.aliases or text != self.aliases[source]:
                    raise InstallError(f"unknown internal source link: {source}")
                return self.snapshot_digest(target, destination, (*active, source))
            # A relative external link would acquire a different referent in
            # the backup or home directory. Make its reference absolute while
            # retaining external indirection; never copy external contents.
            normalized = text if Path(text).is_absolute() else str(absolute(source.parent / text))
            digest.update(b"link\0" + os.fsencode(normalized))
            if destination is not None:
                destination.symlink_to(normalized)
        elif stat.S_ISDIR(mode):
            digest.update(f"dir:{stat.S_IMODE(mode)}\0".encode())
            if destination is not None:
                destination.mkdir(mode=0o700)
            for child in sorted(source.iterdir(), key=lambda item: item.name):
                digest.update(os.fsencode(child.name) + b"\0")
                child_digest = self.snapshot_digest(
                    child, destination / child.name if destination is not None else None, (*active, source),
                )
                digest.update(child_digest.encode())
            if destination is not None:
                shutil.copystat(source, destination, follow_symlinks=False)
        elif stat.S_ISREG(mode):
            digest.update(f"file:{stat.S_IMODE(mode)}\0".encode())
            with source.open("rb") as stream:
                while block := stream.read(1024 * 1024):
                    digest.update(block)
            if destination is not None:
                shutil.copy2(source, destination)
        else:
            raise InstallError(f"unsupported source file type: {source}")
        return digest.hexdigest()

    def legacy_links(self, paths):
        links = set()
        for path in paths:
            for component in reversed((path, *path.parents)):
                if within(component, self.home) and component.is_symlink():
                    if not self.allowed_legacy(component):
                        raise InstallError(f"unexpected legacy link: {component}")
                    if not component.exists():
                        raise InstallError(f"dangling legacy link: {component}")
                    # A whole-directory snapshot handles its nested aliases.
                    links.add(component)
                    break
        return sorted(links, key=str)

    def ledger(self):
        path = self.state / "ledger.json"
        if not exists(path):
            return {"schema": 1, "files": {}}
        if path.is_symlink() or not path.is_file():
            raise InstallError("ownership ledger must be a regular file")
        value = load_json(path)
        if not isinstance(value, dict) or value.get("schema") != 1 or not isinstance(value.get("files"), dict):
            raise InstallError("unsupported ownership ledger schema")
        for relative, baseline in value["files"].items():
            if (not isinstance(relative, str) or Path(relative).is_absolute()
                    or ".." in Path(relative).parts or not relative):
                raise InstallError("invalid ledger destination")
            if (not isinstance(baseline, dict) or set(baseline) != {"sha256", "execute"}
                    or not isinstance(baseline["sha256"], str) or len(baseline["sha256"]) != 64
                    or not isinstance(baseline["execute"], int)
                    or baseline["execute"] & ~0o111):
                raise InstallError("invalid ledger signature")
        return value

    def view(self, path):
        """Read a legacy link's materialized view without mutating plan/check."""
        for component in reversed((path, *path.parents)):
            if within(component, self.home) and component.is_symlink():
                if not self.allowed_legacy(component):
                    raise InstallError(f"unexpected symlink: {component}")
                target = component.resolve(strict=True) / path.relative_to(component)
                # Known internal aliases become ordinary content in the snapshot.
                if target.is_symlink() and target in self.aliases:
                    return target.resolve(strict=True)
                return target
        return path

    def runtime_roots(self):
        return [self.home / path for path in (
            ".agents/skills", ".claude/skills", ".codex/skills",
            ".config/zsh/functions-local",
        )]

    def isolation_roots(self, managed):
        roots = set(managed) | set(self.runtime_roots())
        roots.update(self.home / name for name in (
            ".claude/agents", ".codex/agents", ".codex/hooks", ".gemini/agents",
            ".vim/bundle", ".vim/colors",
        ))
        for path in managed:
            relative = path.relative_to(self.home)
            if len(relative.parts) >= 2 and relative.parts[0] == ".config":
                roots.add(self.home / Path(*relative.parts[:2]))
        return roots

    def scan_backlinks(self, paths):
        found = []

        def walk(path):
            if path.is_symlink():
                try:
                    target = path.resolve(strict=False)
                except (OSError, RuntimeError):
                    found.append(path)
                    return
                if within(target, self.root):
                    found.append(path)
                return
            if path.is_dir():
                for child in path.iterdir():
                    walk(child)

        for path in sorted(set(paths), key=str):
            # Check ancestors as well as leaves without scanning app credentials
            # or session directories alongside the managed content.
            for component in reversed((path, *path.parents)):
                if within(component, self.home) and component.is_symlink():
                    walk(component)
                    break
            else:
                walk(path)
        return sorted(set(found), key=str)

    def source_fingerprint(self):
        digest = hashlib.sha256()
        # Include implementation and merge inputs as well as tracked templates,
        # so an uncommitted rollout cannot masquerade as a current receipt.
        sources = set(self.tracked)
        sources.update(Path(name) for name in (
            "scripts/manage-dotfiles.py", "scripts/lib/dotfile_composition.py",
            "dotfiles/merge/claude/settings.json", "dotfiles/merge/codex/hooks.json",
        ))
        sources = {
            path for path in sources
            if not path.is_relative_to("dotfiles/shared/claude/skills") and path.as_posix() not in {
                "dotfiles/shared/codex/hooks.json", "dotfiles/shared/codex/hooks.json.bak",
                "dotfiles/shared/claude/settings.json",
            } and "__pycache__" not in path.parts and path.suffix not in {".pyc", ".pyo"}
        }
        for relative in sorted(sources, key=str):
            source = self.root / relative
            digest.update(os.fsencode(relative) + b"\0")
            if source.is_symlink():
                digest.update(b"link\0" + os.fsencode(os.readlink(source)))
            elif source.is_file():
                digest.update(json_bytes(file_signature(source)))
            else:
                digest.update(b"missing")
        names = sorted(map(str, sources))
        dirty = bool(self.git("diff", "--name-only", "HEAD", "--", *names))
        tracked = set(self.git("ls-files", "-z", "--", *names).split(b"\0"))
        dirty = dirty or any(exists(self.root / path) and os.fsencode(path) not in tracked for path in sources)
        return {
            "revision": self.git("rev-parse", "HEAD").decode().strip(),
            "fingerprint": digest.hexdigest(),
            "dirty_shared_sources": dirty,
        }

    @contextmanager
    def lock(self):
        self.safe_ancestors(self.state, include=True)
        self.state.mkdir(parents=True, exist_ok=True, mode=0o700)
        os.chmod(self.state, 0o700)
        lock = self.state / "lock"
        if lock.is_symlink() or (lock.exists() and not lock.is_file()):
            raise InstallError("invalid state lock")
        descriptor = os.open(lock, os.O_CREAT | os.O_RDWR, 0o600)
        try:
            fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
            yield
        except BlockingIOError as error:
            raise InstallError("another dotfile operation is running") from error
        finally:
            os.close(descriptor)

    def recover(self):
        journal_path = self.state / "migration-journal.json"
        if not exists(journal_path):
            return
        if journal_path.is_symlink():
            raise InstallError("migration journal cannot be a symlink")
        journal = load_json(journal_path)
        try:
            destination = Path(journal["destination"])
            stage = Path(journal["stage"])
            backup = Path(journal["backup"])
            expected = journal["fingerprint"]
            link_text = journal["link"]
        except (KeyError, TypeError) as error:
            raise InstallError("invalid migration journal") from error
        if (journal.get("schema") != 1 or destination not in self.legacy
                or stage.parent != destination.parent
                or not stage.name.startswith(f".{destination.name}.knapsack-stage-")
                or backup.parent != self.state / "backups"
                or not isinstance(expected, str) or not isinstance(link_text, str)):
            raise InstallError("unsafe migration journal")
        self.safe_ancestors(destination)
        self.safe_ancestors(backup)
        if not exists(backup) or backup.is_symlink() or self.snapshot_digest(backup) != expected:
            raise InstallError("migration backup is missing or modified")
        if destination.is_symlink():
            if not self.allowed_legacy(destination) or os.readlink(destination) != link_text:
                raise InstallError("legacy destination changed during migration")
            if self.snapshot_digest(destination.resolve(strict=True)) != expected:
                raise InstallError("legacy source changed; migration requires manual recovery")
        elif exists(destination):
            if self.snapshot_digest(destination) != expected:
                raise InstallError("migration destination changed; refusing recovery")
            if exists(stage):
                if stage.is_symlink() or self.snapshot_digest(stage) != expected:
                    raise InstallError("migration stage changed; refusing recovery")
                self.remove_snapshot(stage)
            journal_path.unlink()
            return
        if not exists(stage):
            self.snapshot_digest(backup, stage)
        if stage.is_symlink() or self.snapshot_digest(stage) != expected:
            raise InstallError("migration stage is missing or modified")
        if destination.is_symlink():
            destination.unlink()
        os.replace(stage, destination)
        journal_path.unlink()

    @staticmethod
    def remove_snapshot(path):
        if path.is_dir() and not path.is_symlink():
            shutil.rmtree(path)
        else:
            path.unlink()

    def detach(self, destination):
        self.safe_ancestors(destination)
        if not self.allowed_legacy(destination) or not destination.exists():
            raise InstallError(f"legacy destination changed: {destination}")
        source = destination.resolve(strict=True)
        before = self.snapshot_digest(source)
        token = uuid.uuid4().hex
        stage = destination.parent / f".{destination.name}.knapsack-stage-{token}"
        backups = self.state / "backups"
        self.safe_ancestors(backups, include=True)
        backups.mkdir(mode=0o700, exist_ok=True)
        backup = backups / token
        try:
            copied = self.snapshot_digest(source, backup)
            staged = self.snapshot_digest(backup, stage)
            if before != copied or before != staged or before != self.snapshot_digest(source):
                raise InstallError("legacy source changed while copying; close apps and retry")
            journal = {
                "schema": 1, "destination": str(destination), "stage": str(stage),
                "backup": str(backup), "fingerprint": before, "link": os.readlink(destination),
            }
            atomic_write(self.state / "migration-journal.json", json_bytes(journal))
            # Recheck immediately before detachment; recovery repeats this check
            # if the process stops between journal creation and the swap.
            if before != self.snapshot_digest(source):
                raise InstallError("legacy source changed before detachment")
            destination.unlink()
            os.replace(stage, destination)
            (self.state / "migration-journal.json").unlink()
        except BaseException:
            # A journal owns its stage after it exists. Before that point, only
            # the completed content backup is retained for operator inspection.
            if not (self.state / "migration-journal.json").exists() and exists(stage):
                self.remove_snapshot(stage)
            raise

    def special_files(self, ledger, managed):
        """Compose local JSON without claiming app-owned Codex hook content."""
        composed = {}
        claude = self.root / "dotfiles/merge/claude/settings.json"
        if claude.exists():
            overlay_path = self.view(self.home / ".claude/settings.machine.json")
            if overlay_path.is_symlink():
                raise InstallError("Claude machine overlay must be a regular local file")
            overlay = load_json(overlay_path) if exists(overlay_path) else {}
            desired = compose_claude_settings(load_json(claude), overlay)
            path = self.home / ".claude/settings.json"
            current = self.view(path)
            self.preimages[path] = (exists(current), file_signature(current))
            if exists(current):
                if current.is_symlink() or not current.is_file():
                    raise InstallError("Claude settings must materialize as a regular file")
                current_bytes = current.read_bytes()
                value = self.decode_json(current_bytes, current)
                if signature(current_bytes, current.stat().st_mode & 0o111) != self.preimages[path][1]:
                    raise InstallError("Claude settings changed during composition")
                compose_claude_settings(value, {})
                baseline = ledger["files"].get(str(path.relative_to(self.home)))
                if value != desired and file_signature(current) != baseline:
                    keys = sorted(key for key in set(value) | set(desired)
                                  if key not in value or key not in desired or value[key] != desired[key])
                    self.conflicts.append("Claude settings drift in keys: " + ", ".join(keys))
                    return composed
                # Semantically equal bootstrap content can retain formatting.
                if value == desired:
                    composed[path] = (current_bytes, 0o600)
                else:
                    composed[path] = (json_bytes(desired), 0o600)
            else:
                composed[path] = (json_bytes(desired), 0o600)
        hooks = self.root / "dotfiles/merge/codex/hooks.json"
        if hooks.exists():
            path = self.home / ".codex/hooks.json"
            current = self.view(path)
            self.preimages[path] = (exists(current), file_signature(current))
            if exists(current) and (current.is_symlink() or not current.is_file()):
                raise InstallError("Codex hooks must materialize as a regular file")
            current_bytes = current.read_bytes() if exists(current) else None
            value = self.decode_json(current_bytes, current) if current_bytes is not None else {}
            if current_bytes is not None and signature(current_bytes, current.stat().st_mode & 0o111) != self.preimages[path][1]:
                raise InstallError("Codex hooks changed during composition")
            desired, owned = reconcile_codex_hooks(value, load_json(hooks), ledger.get("codex_owned"))
            data = current_bytes if value == desired and current_bytes is not None else json_bytes(desired)
            composed[path] = (data, 0o600)
            self.owned_desired = owned
        managed.update(composed)
        return composed

    @staticmethod
    def decode_json(data, path):
        try:
            return json.loads(data)
        except ValueError as error:
            raise InstallError(f"cannot read JSON object: {path}") from error

    def conflict(self, path, message):
        self.conflicts.append(f"{path.relative_to(self.home)}: {message}")

    def apply_files(self, managed, seeds, ledger, write=False):
        previous = deepcopy(ledger["files"])
        updated = deepcopy(previous)
        hook_path = self.home / ".codex/hooks.json"
        for path, (data, mode) in sorted(managed.items(), key=lambda item: str(item[0])):
            relative = str(path.relative_to(self.home))
            desired = signature(data, mode & 0o111)
            current_path = self.view(path)
            current = file_signature(current_path)
            preimage = (exists(current_path), current)
            if path in self.preimages and preimage != self.preimages[path]:
                self.conflict(path, "changed after composition; preserved")
                continue
            if not exists(current_path):
                action = "install"
            elif current == desired:
                action = "adopt" if relative not in previous else "unchanged"
            elif path == hook_path and current is not None:
                action = "reconcile"
            elif current is not None and previous.get(relative) == current:
                action = "update"
            else:
                self.conflict(path, "local content, type, or execute mode differs; preserved")
                continue
            self.actions.append((action, relative))
            if write and action in {"install", "update", "reconcile"}:
                self.safe_ancestors(path)
                atomic_write(path, data, mode, expected=preimage)
            updated[relative] = desired
            if path == hook_path and self.owned_desired is not None:
                ledger["codex_owned"] = deepcopy(self.owned_desired)
        managed_relatives = {str(path.relative_to(self.home)) for path in managed}
        # JSON conflicts must not accidentally retire a still-configured file.
        protected = {".claude/settings.json", ".codex/hooks.json"}
        for relative, baseline in previous.items():
            if relative in managed_relatives or relative in protected:
                continue
            path = self.home / relative
            current_path = self.view(path)
            if not exists(current_path):
                updated.pop(relative, None)
            elif file_signature(current_path) == baseline:
                self.actions.append(("retire", relative))
                if write:
                    self.safe_ancestors(path)
                    if file_signature(path) != baseline:
                        raise InstallError(f"destination changed before retirement: {path}")
                    path.unlink()
                updated.pop(relative, None)
            else:
                self.conflict(path, "retired template has local changes; preserved")
        for path, (data, mode) in sorted(seeds.items(), key=lambda item: str(item[0])):
            if not exists(self.view(path)):
                self.actions.append(("seed", str(path.relative_to(self.home))))
                if write:
                    self.safe_ancestors(path)
                    atomic_write(path, data, mode, expected=(False, None))
        ledger["files"] = updated

    def paths(self, managed, seeds, ledger):
        return set(managed) | set(seeds) | {self.home / name for name in ledger["files"]} | {
            self.home / ".claude/settings.json", self.home / ".claude/settings.machine.json",
            self.home / ".codex/hooks.json", *self.runtime_roots(),
        }

    def receipt(self):
        return {"schema": 1, "stage": 2, "home": str(self.home), "root": str(self.root),
                "source": self.source_fingerprint()}

    def execute(self, command):
        if command in {"prepare-skills", "prepare-functions"}:
            paths = [self.home / name for name in (
                (".agents/skills", ".claude/skills") if command == "prepare-skills"
                else (".config/zsh/functions-local",)
            )]
            self.preflight(paths, allow_legacy=True)
            with self.lock():
                self.recover()
                self.preflight(paths, allow_legacy=True)
                for link in self.legacy_links(paths):
                    self.detach(link)
                self.preflight(paths)
                backlinks = self.scan_backlinks(paths)
                if backlinks:
                    raise InstallError("runtime roots still link into checkout: " + ", ".join(map(str, backlinks)))
                for path in paths:
                    self.safe_ancestors(path, include=True)
            return 0

        managed, seeds = self.manifest()
        self.safe_ancestors(self.state, include=True)
        ledger = self.ledger()
        paths = self.paths(managed, seeds, ledger)
        self.preflight(paths, allow_legacy=True)
        links = self.legacy_links(paths)
        if command == "apply":
            with self.lock():
                receipt_path = self.state / "stage-two.json"
                if exists(receipt_path):
                    if receipt_path.is_symlink() or not receipt_path.is_file():
                        raise InstallError("invalid stage-two receipt")
                    receipt_path.unlink()
                self.recover()
                ledger = self.ledger()
                self.preflight(paths, allow_legacy=True)
                for link in self.legacy_links(paths):
                    self.actions.append(("detach", str(link.relative_to(self.home))))
                    self.detach(link)
                self.preflight(paths)
                self.special_files(ledger, managed)
                self.apply_files(managed, seeds, ledger, write=True)
                backlinks = self.scan_backlinks(self.isolation_roots(managed))
                for path in backlinks:
                    self.conflict(path, "symlink still enters checkout")
                atomic_write(self.state / "ledger.json", json_bytes(ledger))
                if not self.conflicts:
                    atomic_write(receipt_path, json_bytes(self.receipt()))
        else:
            if exists(self.state / "migration-journal.json"):
                self.conflicts.append("unfinished migration journal; apply is required to recover")
            self.special_files(ledger, managed)
            self.apply_files(managed, seeds, ledger)
            self.actions[:0] = [("detach", str(link.relative_to(self.home))) for link in links]
            if command == "check":
                if (self.root / "dotfiles/merge/codex/hooks.json").exists() and "codex_owned" not in self.ledger():
                    self.conflicts.append("Codex routing ownership has not been recorded")
                if links:
                    self.conflicts.append("legacy links remain; apply is required")
                for action, relative in self.actions:
                    if action != "unchanged":
                        self.conflicts.append(f"{relative}: pending {action}")
                receipt_path = self.state / "stage-two.json"
                if (not receipt_path.is_file() or receipt_path.is_symlink()
                        or load_json(receipt_path) != self.receipt()):
                    self.conflicts.append("stage-two receipt is absent or stale")
                for path in self.scan_backlinks(self.isolation_roots(managed)):
                    self.conflict(path, "symlink enters checkout")
        for action, relative in self.actions:
            if action != "unchanged":
                print(f"{action}: {relative}")
        for message in self.conflicts:
            print(f"conflict: {message}", file=sys.stderr)
        return 1 if self.conflicts else 0


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("plan", "apply", "check", "prepare-skills", "prepare-functions"))
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--home", type=Path, default=Path.home())
    parser.add_argument("--state-dir", type=Path)
    args = parser.parse_args(argv)
    try:
        return Installer(args.root, args.home, args.state_dir).execute(args.command)
    except (InstallError, ValueError, OSError) as error:
        print(f"dotfiles: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

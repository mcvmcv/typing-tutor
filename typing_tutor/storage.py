"""Player profiles and progress, saved as JSON in the user's data folder."""

from __future__ import annotations

import contextlib
import json
import os
import uuid
from dataclasses import asdict, dataclass, field, fields
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import QStandardPaths

from .session import merge_key_stats

BACKUP_FORMAT = "learn-typing-backup"

# Automatic copies of the save file, kept in a "backups" folder beside it:
# one a day (the progress as it was before that day's first change), plus one
# just before anything big (removing a player, loading a backup, going back).
DAILY_COPIES = 7
EVENT_COPIES = 5


class BackupError(Exception):
    """The file isn't a Learn Typing backup that can be loaded. The message says why."""


@dataclass
class ImportPlan:
    """What loading a backup would do."""

    added: list[Profile]  # new players
    replaced: list[Profile]  # players already here, whose progress the backup replaces
    renamed: dict[str, str]  # new players renamed to avoid a clash: old name -> new name


def _is_number(value: object) -> bool:
    return isinstance(value, int | float) and not isinstance(value, bool)


def _check_profile(data: object) -> None:
    """Raise BackupError unless `data` looks like a saved player."""
    if not isinstance(data, dict):
        raise BackupError("A player in the file isn't in the right format.")
    for key in ("id", "name", "color"):
        if not isinstance(data.get(key), str) or not data[key].strip():
            raise BackupError(f"A player in the file is missing their {key}.")
    name = data["name"]
    best, history = data.get("best", {}), data.get("history", [])
    key_stats, game_best = data.get("key_stats", {}), data.get("game_best", {})
    if not isinstance(best, dict) or not all(
        isinstance(b, dict) and isinstance(b.get("stars"), int) for b in best.values()
    ):
        raise BackupError(f"{name}'s stars in the file aren't in the right format.")
    history_keys = ("step", "wpm", "accuracy", "stars", "when")
    if not isinstance(history, list) or not all(
        isinstance(h, dict) and all(k in h for k in history_keys) for h in history
    ):
        raise BackupError(f"{name}'s practice history in the file isn't in the right format.")
    try:
        for h in history:
            datetime.fromisoformat(h["when"])
    except (TypeError, ValueError):
        raise BackupError(f"{name}'s practice history has a date that can't be read.") from None
    if not isinstance(key_stats, dict) or not all(
        isinstance(v, dict) and all(_is_number(v.get(f)) for f in "hmtn")
        for v in key_stats.values()
    ):
        raise BackupError(f"{name}'s key stats in the file aren't in the right format.")
    if not isinstance(game_best, dict) or not all(_is_number(v) for v in game_best.values()):
        raise BackupError(f"{name}'s Balloon Pop scores aren't in the right format.")
    race_best = data.get("race_best", {})
    if not isinstance(race_best, dict) or not all(_is_number(v) for v in race_best.values()):
        raise BackupError(f"{name}'s Snail Race speeds aren't in the right format.")


def read_backup(path: Path) -> list[Profile]:
    """Read and check a backup (or a copied profiles.json) without changing anything."""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except OSError as e:
        raise BackupError(f"The file couldn't be opened ({e.strerror or e}).") from None
    except (UnicodeDecodeError, ValueError):
        raise BackupError("This isn't a Learn Typing backup file.") from None
    if not isinstance(data, dict) or not isinstance(data.get("profiles"), list):
        raise BackupError("This isn't a Learn Typing backup file.")
    version = data.get("version", 1)
    if not isinstance(version, int):
        raise BackupError("This isn't a Learn Typing backup file.")
    if version > 1:
        raise BackupError(
            "This backup was made by a newer version of Learn Typing. "
            "Update the app, then try again."
        )
    if not data["profiles"]:
        raise BackupError("This backup doesn't have any players in it.")
    for p in data["profiles"]:
        _check_profile(p)
    ids = [p["id"] for p in data["profiles"]]
    if len(set(ids)) != len(ids):
        raise BackupError("This backup has the same player in it twice.")
    return [Profile.from_dict(p) for p in data["profiles"]]


@dataclass
class Snapshot:
    """An automatic copy of everyone's progress."""

    path: Path
    made: datetime
    reason: str  # e.g. "Start of the day" or "Before removing Mia"
    names: list[str]


def _write_json(path: Path, payload: dict) -> None:
    """Write atomically, so a crash never leaves half a file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    os.replace(tmp, path)


# Once a key has this many samples, its stats are halved so recent typing
# counts most and improvement shows up.
KEY_STATS_WINDOW = 150


@dataclass
class Profile:
    id: str
    name: str
    color: str
    # step_id -> {"stars": int, "wpm": float, "accuracy": float}
    best: dict[str, dict] = field(default_factory=dict)
    # Every finished attempt, kept for future stats screens.
    history: list[dict] = field(default_factory=list)
    # char -> {"h": hits, "m": misses, "t": seconds, "n": timed hits}
    key_stats: dict[str, dict] = field(default_factory=dict)
    # Words per minute needed for full stars; 0 means accuracy only.
    speed_goal: int = 0
    sound: bool = True
    # Balloon Pop best score per difficulty.
    game_best: dict[str, int] = field(default_factory=dict)
    key_clicks: bool = True
    # Show upcoming spaces in the typing line as centred dots.
    space_dots: bool = True
    # Snail Race best speed (WPM) per difficulty.
    race_best: dict[str, float] = field(default_factory=dict)
    # How big the practice text is: "normal", "large" or "huge" (see TEXT_SIZES).
    text_size: str = "normal"

    def stars(self, step_id: str) -> int:
        return self.best.get(step_id, {}).get("stars", 0)

    @classmethod
    def from_dict(cls, data: dict) -> Profile:
        known = {f.name for f in fields(cls)}
        return cls(**{k: v for k, v in data.items() if k in known})


class ProfileStore:
    def __init__(self, path: Path):
        self.path = path
        self.profiles: list[Profile] = []
        # The computer's keyboard layout ("us" or "uk"), or None if never chosen.
        # It belongs to this computer, so backups don't carry it.
        self.keyboard: str | None = None
        # Ask GitHub for a newer version at start-up. Off unless a grown-up turns it on.
        self.check_updates = False
        self.clock = datetime.now  # replaceable in tests
        self.load()

    @staticmethod
    def default_path() -> Path:
        base = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppDataLocation)
        return Path(base) / "profiles.json"

    def load(self) -> None:
        if not self.path.exists():
            return
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            self.profiles = [Profile.from_dict(p) for p in data.get("profiles", [])]
            keyboard = data.get("keyboard")
            self.keyboard = keyboard if isinstance(keyboard, str) else None
            self.check_updates = data.get("check_updates") is True
        except (OSError, ValueError, TypeError):
            # Keep the unreadable file so progress isn't silently lost.
            stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
            self.path.rename(self.path.with_name(f"profiles.broken-{stamp}.json"))
            self.profiles = []

    def save(self) -> None:
        self._daily_snapshot()
        data: dict = {"version": 1, "profiles": [asdict(p) for p in self.profiles]}
        if self.keyboard:
            data["keyboard"] = self.keyboard
        if self.check_updates:
            data["check_updates"] = True
        _write_json(self.path, data)

    def set_check_updates(self, on: bool) -> None:
        self.check_updates = on
        self.save()

    def set_keyboard(self, code: str) -> None:
        self.keyboard = code
        self.save()

    # Automatic copies -----------------------------------------------------

    @property
    def snapshot_dir(self) -> Path:
        return self.path.parent / "backups"

    def _daily_snapshot(self) -> None:
        """Before the first change of the day, keep a copy of the file as it was."""
        name = f"daily-{self.clock().date().isoformat()}.json"
        if not (self.snapshot_dir / name).exists():
            self._copy_file(name, "Start of the day")
            self._prune("daily-", DAILY_COPIES)

    def snapshot(self, reason: str) -> None:
        """Keep a copy of the saved progress before something big changes it."""
        stamp = self.clock().strftime("%Y%m%d-%H%M%S-%f")
        n = 0
        while (self.snapshot_dir / f"before-{stamp}-{n}.json").exists():
            n += 1  # two in the same instant
        self._copy_file(f"before-{stamp}-{n}.json", reason)
        self._prune("before-", EVENT_COPIES)

    def _copy_file(self, name: str, reason: str) -> None:
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return  # nothing saved yet (or unreadable), so nothing to keep
        if not isinstance(data, dict) or not data.get("profiles"):
            return
        data["snapshot"] = {"reason": reason, "made": self.clock().isoformat(timespec="seconds")}
        # A copy that can't be written mustn't stop progress being saved.
        with contextlib.suppress(OSError):
            _write_json(self.snapshot_dir / name, data)

    def _prune(self, prefix: str, keep: int) -> None:
        old = sorted(self.snapshot_dir.glob(f"{prefix}*.json"), reverse=True)[keep:]
        for path in old:
            path.unlink(missing_ok=True)

    def snapshots(self) -> list[Snapshot]:
        """The automatic copies, newest first. Unreadable ones are skipped."""
        found = []
        for path in self.snapshot_dir.glob("*.json"):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                info = data["snapshot"]
                made = datetime.fromisoformat(info["made"])
                names = [p["name"] for p in data["profiles"]]
                found.append(Snapshot(path, made, str(info["reason"]), names))
            except (OSError, ValueError, KeyError, TypeError):
                continue
        # Newest first; at the same moment, the copy made for a reason comes first.
        return sorted(
            found,
            key=lambda snap: (snap.made, snap.path.name.startswith("before-"), snap.path.name),
            reverse=True,
        )

    def restore(self, snapshot: Snapshot) -> None:
        """Put everyone's progress back to an earlier copy (after keeping today's)."""
        profiles = read_backup(snapshot.path)  # raises BackupError if it's damaged
        self.snapshot("Before going back to an earlier copy")
        self.profiles = profiles
        self.save()

    # Backups -------------------------------------------------------------

    def export_backup(self, path: Path) -> None:
        _write_json(
            path,
            {
                "format": BACKUP_FORMAT,
                "version": 1,
                "exported": datetime.now().isoformat(timespec="seconds"),
                "profiles": [asdict(p) for p in self.profiles],
            },
        )

    def plan_import(self, incoming: list[Profile]) -> ImportPlan:
        plan = ImportPlan(added=[], replaced=[], renamed={})
        names = {p.name.casefold() for p in self.profiles}
        for profile in incoming:
            if self.get(profile.id) is not None:
                plan.replaced.append(profile)
                continue
            plan.added.append(profile)
            if profile.name.casefold() in names:
                n = 2
                while f"{profile.name} {n}".casefold() in names:
                    n += 1
                plan.renamed[profile.name] = f"{profile.name} {n}"
            names.add(plan.renamed.get(profile.name, profile.name).casefold())
        return plan

    def import_profiles(self, incoming: list[Profile]) -> ImportPlan:
        """Add the backup's players, replacing any that are already here."""
        plan = self.plan_import(incoming)
        self.snapshot("Before loading a backup")
        for profile in plan.replaced:
            i = next(i for i, p in enumerate(self.profiles) if p.id == profile.id)
            self.profiles[i] = profile
        for profile in plan.added:
            profile.name = plan.renamed.get(profile.name, profile.name)
            self.profiles.append(profile)
        self.save()
        return plan

    def get(self, profile_id: str) -> Profile | None:
        return next((p for p in self.profiles if p.id == profile_id), None)

    def name_taken(self, name: str) -> bool:
        return any(p.name.casefold() == name.strip().casefold() for p in self.profiles)

    def add(self, name: str, color: str, speed_goal: int = 0) -> Profile:
        profile = Profile(
            id=uuid.uuid4().hex, name=name.strip(), color=color, speed_goal=speed_goal
        )
        self.profiles.append(profile)
        self.save()
        return profile

    def delete(self, profile_id: str) -> None:
        profile = self.get(profile_id)
        if profile is not None:
            self.snapshot(f"Before removing {profile.name}")
        self.profiles = [p for p in self.profiles if p.id != profile_id]
        self.save()

    def set_speed_goal(self, profile_id: str, goal: int) -> None:
        profile = self.get(profile_id)
        if profile is not None:
            profile.speed_goal = goal
            self.save()

    def set_sound(self, profile_id: str, sound: bool, key_clicks: bool | None = None) -> None:
        profile = self.get(profile_id)
        if profile is not None:
            profile.sound = sound
            if key_clicks is not None:
                profile.key_clicks = key_clicks
            self.save()

    def set_text_size(self, profile_id: str, size: str) -> None:
        profile = self.get(profile_id)
        if profile is not None:
            profile.text_size = size
            self.save()

    def set_space_dots(self, profile_id: str, on: bool) -> None:
        profile = self.get(profile_id)
        if profile is not None:
            profile.space_dots = on
            self.save()

    def record_game(self, profile_id: str, difficulty: str, score: int, key_stats: dict) -> bool:
        """Save a finished game. Returns True if it's a new best score."""
        profile = self.get(profile_id)
        if profile is None:
            return False
        self._merge_key_stats(profile, key_stats)
        best = score > profile.game_best.get(difficulty, 0)
        if best:
            profile.game_best[difficulty] = score
        self.save()
        return best

    def record_race(self, profile_id: str, difficulty: str, wpm: float, key_stats: dict) -> bool:
        """Save a finished race. Returns True if it's the player's fastest on that difficulty."""
        profile = self.get(profile_id)
        if profile is None:
            return False
        self._merge_key_stats(profile, key_stats)
        best = wpm > profile.race_best.get(difficulty, 0)
        if best:
            profile.race_best[difficulty] = round(wpm, 1)
        self.save()
        return best

    def _merge_key_stats(self, profile: Profile, key_stats: dict | None) -> None:
        if not key_stats:
            return
        merge_key_stats(profile.key_stats, key_stats)
        for s in profile.key_stats.values():
            if s["h"] + s["m"] > KEY_STATS_WINDOW:
                for f in ("h", "m", "t", "n"):
                    s[f] /= 2

    def record_result(
        self,
        profile_id: str,
        step_id: str,
        wpm: float,
        accuracy: float,
        stars: int,
        key_stats: dict | None = None,
    ) -> None:
        profile = self.get(profile_id)
        if profile is None:
            return
        self._merge_key_stats(profile, key_stats)
        wpm, accuracy = round(wpm, 1), round(accuracy, 1)
        profile.history.append(
            {
                "step": step_id,
                "wpm": wpm,
                "accuracy": accuracy,
                "stars": stars,
                "when": datetime.now().isoformat(timespec="seconds"),
            }
        )
        best = profile.best.setdefault(step_id, {"stars": 0, "wpm": 0.0, "accuracy": 0.0})
        best["stars"] = max(best["stars"], stars)
        best["wpm"] = max(best["wpm"], wpm)
        best["accuracy"] = max(best["accuracy"], accuracy)
        self.save()

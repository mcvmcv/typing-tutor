"""Player profiles and progress, saved as JSON in the user's data folder."""
from __future__ import annotations

import json
import os
import uuid
from dataclasses import asdict, dataclass, field, fields
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import QStandardPaths


@dataclass
class Profile:
    id: str
    name: str
    color: str
    # step_id -> {"stars": int, "wpm": float, "accuracy": float}
    best: dict[str, dict] = field(default_factory=dict)
    # Every finished attempt, kept for future stats screens.
    history: list[dict] = field(default_factory=list)

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
        self.load()

    @staticmethod
    def default_path() -> Path:
        base = QStandardPaths.writableLocation(
            QStandardPaths.StandardLocation.AppDataLocation)
        return Path(base) / "profiles.json"

    def load(self) -> None:
        if not self.path.exists():
            return
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            self.profiles = [Profile.from_dict(p) for p in data.get("profiles", [])]
        except (OSError, ValueError, TypeError):
            # Keep the unreadable file so progress isn't silently lost.
            stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
            self.path.rename(self.path.with_name(f"profiles.broken-{stamp}.json"))
            self.profiles = []

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".tmp")
        payload = {"version": 1, "profiles": [asdict(p) for p in self.profiles]}
        tmp.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        os.replace(tmp, self.path)

    def get(self, profile_id: str) -> Profile | None:
        return next((p for p in self.profiles if p.id == profile_id), None)

    def name_taken(self, name: str) -> bool:
        return any(p.name.casefold() == name.strip().casefold() for p in self.profiles)

    def add(self, name: str, color: str) -> Profile:
        profile = Profile(id=uuid.uuid4().hex, name=name.strip(), color=color)
        self.profiles.append(profile)
        self.save()
        return profile

    def delete(self, profile_id: str) -> None:
        self.profiles = [p for p in self.profiles if p.id != profile_id]
        self.save()

    def record_result(self, profile_id: str, step_id: str,
                      wpm: float, accuracy: float, stars: int) -> None:
        profile = self.get(profile_id)
        if profile is None:
            return
        wpm, accuracy = round(wpm, 1), round(accuracy, 1)
        profile.history.append({
            "step": step_id, "wpm": wpm, "accuracy": accuracy, "stars": stars,
            "when": datetime.now().isoformat(timespec="seconds"),
        })
        best = profile.best.setdefault(step_id, {"stars": 0, "wpm": 0.0, "accuracy": 0.0})
        best["stars"] = max(best["stars"], stars)
        best["wpm"] = max(best["wpm"], wpm)
        best["accuracy"] = max(best["accuracy"], accuracy)
        self.save()

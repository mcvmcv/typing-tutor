# Learn Typing

A friendly touch-typing tutor for kids, built with PySide6.

## Run

```bash
make install   # first time: creates .venv with the app and dev tools
make run       # or: .venv/bin/python -m typing_tutor
```

Progress is saved per player in `~/.local/share/learn-typing/profiles.json`.

## Course

40 steps in 6 lessons: Home Row Heroes, Top Row Climbers, Bottom Row Divers,
Big Letters (Shift, ' and ?), Number Row, and Story Time. Each step is a few
lines; after any hand-written lines, the rest are generated fresh each play
using only keys learned so far.

## Tricky keys and speed goals

Every keystroke is tracked per key (misses and time taken, weighted toward
recent sessions). Once there's enough data, the lesson menu shows each
player's trickiest keys with a "Practise them" button for a focused drill.

Each player can have a speed goal (set when created, or via Settings). With a
goal, 3 stars needs both 95%+ accuracy and the target speed (75% of it on
key-drill steps). It's off by default, which suits young beginners.

## Balloon Pop

A typing game on the lesson menu, unlocked after the home row's "All
together" step. Words on balloons float up; type a word to pop its balloon,
and don't let 3 float away. It speeds up every 8 pops. Words only use keys the
player has learned. Easy/Medium/Hard set the starting speed and word length,
best scores are kept per difficulty, and game keystrokes feed the tricky-keys
stats. Esc pauses.

## Sounds

Soft synthesised sound effects (key tick, gentle "oops", line chime, star
fanfare) are generated on first run into `~/.cache/learn-typing/`. Each
player can turn sounds or just key clicks off in Settings, or use the
Sound button on the practice screen.

## Progress screen

"My progress" on the lesson menu shows best speed, recent accuracy, stars,
steps finished and practice days, a speed chart (by day or every step, with the
speed goal as a dashed line; hover a point for details), and a table of recent
practice.

## Data

Everything is stored in one JSON file (path above), saved atomically. If it
ever can't be read, it's renamed to `profiles.broken-<time>.json` rather than
overwritten.

## Layout

- `typing_tutor/lessons.py` — the course (add new lessons to `LESSONS`)
- `typing_tutor/generator.py` — builds fresh practice lines from known keys
- `typing_tutor/wordlist.py` — words, names, sentences and stories
- `typing_tutor/session.py` — typing logic: accuracy, WPM, stars, per-key stats
- `typing_tutor/game.py` — Balloon Pop rules (drawing is in `screens/game_screen.py`)
- `typing_tutor/progress.py` — chart points and summary numbers from history
- `typing_tutor/plays.py` — what gets played: course steps, tricky-key reviews, speed goals
- `typing_tutor/keyboard.py` — US QWERTY layout and finger assignments
- `typing_tutor/storage.py` — player profiles and progress
- `typing_tutor/widgets/` — on-screen keyboard, hands, typing line
- `typing_tutor/screens/` — player picker, lesson menu, practice screen

## Development

```bash
make check      # lint, format check, type check, tests with coverage (what CI runs)
make test       # just the tests
make format     # auto-format with ruff
```

- **Tests** live in `tests/` (pytest + pytest-qt). The GUI tests drive the real
  screens offscreen with simulated key presses. Every test uses a temporary save
  file and sound folder, so running them never touches real progress.
- **Linting/formatting:** ruff. **Types:** mypy (config in `pyproject.toml`).
- **CI:** `.github/workflows/ci.yml` runs `make check` on Python 3.12 and 3.13
  once the repo is pushed to GitHub.
- `typing_tutor/ui.py` has small widget helpers; use `label(text, name)` rather
  than `QLabel(objectName=...)`, which PySide's type stubs reject.

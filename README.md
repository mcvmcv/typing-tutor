# Learn Typing

A friendly touch-typing tutor for kids, built with PySide6.

## Run

```bash
source .venv/bin/activate
pip install -r requirements.txt   # first time only
python -m typing_tutor
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

## Layout

- `typing_tutor/lessons.py` — the course (add new lessons to `LESSONS`)
- `typing_tutor/generator.py` — builds fresh practice lines from known keys
- `typing_tutor/wordlist.py` — words, names, sentences and stories
- `typing_tutor/session.py` — typing logic: accuracy, WPM, stars, per-key stats
- `typing_tutor/plays.py` — what gets played: course steps, tricky-key reviews, speed goals
- `typing_tutor/keyboard.py` — US QWERTY layout and finger assignments
- `typing_tutor/storage.py` — player profiles and progress
- `typing_tutor/widgets/` — on-screen keyboard, hands, typing line
- `typing_tutor/screens/` — player picker, lesson menu, practice screen

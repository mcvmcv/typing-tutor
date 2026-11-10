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

## Layout

- `typing_tutor/lessons.py` — the course (add new lessons to `LESSONS`)
- `typing_tutor/generator.py` — builds fresh practice lines from known keys
- `typing_tutor/wordlist.py` — words, names, sentences and stories
- `typing_tutor/session.py` — typing logic: accuracy, WPM, stars
- `typing_tutor/keyboard.py` — US QWERTY layout and finger assignments
- `typing_tutor/storage.py` — player profiles and progress
- `typing_tutor/widgets/` — on-screen keyboard, hands, typing line
- `typing_tutor/screens/` — player picker, lesson menu, practice screen

# Learn Typing

A friendly touch-typing tutor for kids, built with PySide6.

## Run

```bash
source .venv/bin/activate
pip install -r requirements.txt   # first time only
python -m typing_tutor
```

Progress is saved per player in `~/.local/share/learn-typing/profiles.json`.

## Layout

- `typing_tutor/lessons.py` — lesson content (add new lessons to `LESSONS`)
- `typing_tutor/session.py` — typing logic: accuracy, WPM, stars
- `typing_tutor/keyboard.py` — US QWERTY layout and finger assignments
- `typing_tutor/storage.py` — player profiles and progress
- `typing_tutor/widgets/` — on-screen keyboard, hands, typing line
- `typing_tutor/screens/` — player picker, lesson menu, practice screen

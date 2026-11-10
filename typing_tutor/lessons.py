"""Lesson content.

A lesson is a sequence of short steps. Each step introduces a few keys and
gives a line of text to type. Add new lessons to LESSONS; the menu, unlocking
and progress tracking pick them up automatically.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Step:
    key: str
    title: str
    instruction: str
    text: str


@dataclass(frozen=True)
class Lesson:
    key: str
    title: str
    description: str
    steps: tuple[Step, ...]

    def step_id(self, index: int) -> str:
        return f"{self.key}/{self.steps[index].key}"


HOME_ROW = Lesson(
    key="home-row",
    title="Home Row Heroes",
    description="Meet the home row: the keys your fingers rest on.",
    steps=(
        Step(
            "fj",
            "F and J",
            "Feel the little bumps on F and J? Put your pointer fingers there. "
            "That's home!",
            "fff jjj fff jjj fj fj jf jf ffj jjf fjf jfj",
        ),
        Step(
            "dk",
            "D and K",
            "Rest your middle fingers next to your pointers, on D and K.",
            "ddd kkk ddd kkk dk kd fd jk dfd kjk fdk jkd",
        ),
        Step(
            "sl",
            "S and L",
            "Your ring fingers go on S and L.",
            "sss lll sss lll sl ls sd lk sdf lkj fsd jlk",
        ),
        Step(
            "a;",
            "A and ;",
            "Your little pinky fingers rest on A and ; (semicolon).",
            "aaa ;;; aaa ;;; a; ;a as l; asdf jkl; asdf jkl;",
        ),
        Step(
            "all",
            "All together",
            "Now use all eight fingers. Keep them resting on the home row!",
            "asdf jkl; fdsa ;lkj asdf jkl; fjdksla; asdf jkl;",
        ),
        Step(
            "gh",
            "Stretch to G and H",
            "Your pointer fingers can stretch one key toward the middle for "
            "G and H. Then hop back home!",
            "fff ggg fgf jjj hhh jhj fg jh gh hg fgh jhg",
        ),
        Step(
            "words1",
            "First words",
            "You know enough keys to type real words! Thumbs press Space.",
            "dad sad lad add ask all fall lass flask",
        ),
        Step(
            "words2",
            "More words",
            "More words using G and H too.",
            "had has gas glad half hall dash flag lash shall",
        ),
        Step(
            "sentences",
            "Little sentences",
            "Type these tiny sentences. Take your time. Being right beats being fast!",
            "a lad asks dad; dad has a glass; all fall; a glad lass",
        ),
    ),
)

LESSONS: tuple[Lesson, ...] = (HOME_ROW,)

# Every step in teaching order, as (lesson, step_index).
ALL_STEPS: tuple[tuple[Lesson, int], ...] = tuple(
    (lesson, i) for lesson in LESSONS for i in range(len(lesson.steps))
)


def flat_index(lesson: Lesson, index: int) -> int:
    return ALL_STEPS.index((lesson, index))


def is_unlocked(stars_for, lesson: Lesson, index: int) -> bool:
    """A step is unlocked when the step before it (in any lesson) has stars."""
    k = flat_index(lesson, index)
    if k == 0:
        return True
    prev_lesson, prev_index = ALL_STEPS[k - 1]
    return stars_for(prev_lesson.step_id(prev_index)) > 0


def next_step(lesson: Lesson, index: int) -> tuple[Lesson, int] | None:
    k = flat_index(lesson, index)
    return ALL_STEPS[k + 1] if k + 1 < len(ALL_STEPS) else None


def first_unfinished(stars_for) -> tuple[Lesson, int] | None:
    for lesson, i in ALL_STEPS:
        if stars_for(lesson.step_id(i)) == 0:
            return lesson, i
    return None

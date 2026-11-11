"""The course: lessons made of short steps.

Each step lists the keys it introduces (`new`). The keys a child "knows" at
a step are every key introduced up to and including it, and generated
practice only ever uses known keys.

Step kinds:
  drill      key patterns that focus on the new keys
  words      real words, favouring ones with the new keys
  sentences  short sentences from the sentence bank
  numbers    a mix of numbers and words
  story      a fixed passage (all lines given in `lines`)

`lines` are hand-written lines that always come first; the rest, up to
`line_count`, are generated fresh each time the step is played.
"""

from __future__ import annotations

import textwrap
from dataclasses import dataclass

from .wordlist import STORIES


@dataclass(frozen=True)
class Step:
    key: str
    title: str
    instruction: str
    new: str = ""
    kind: str = "drill"
    lines: tuple[str, ...] = ()
    line_count: int = 3
    # Wording for keyboards where the new key is somewhere else, as
    # ((layout code, instruction), ...). Falls back to `instruction`.
    layout_instructions: tuple[tuple[str, str], ...] = ()

    def instruction_for(self, layout: str) -> str:
        return dict(self.layout_instructions).get(layout, self.instruction)


@dataclass(frozen=True)
class Lesson:
    key: str
    title: str
    description: str
    steps: tuple[Step, ...]

    def step_id(self, index: int) -> str:
        return f"{self.key}/{self.steps[index].key}"


def _story(key: str) -> Step:
    title, text = STORIES[key]
    lines = tuple(textwrap.wrap(text, width=46))
    return Step(
        key,
        title,
        "Type the whole story. Keep your eyes on the screen, not your fingers!",
        kind="story",
        lines=lines,
        line_count=len(lines),
    )


HOME_ROW = Lesson(
    key="home-row",
    title="Home Row Heroes",
    description="Meet the home row: the keys your fingers rest on.",
    steps=(
        Step(
            "fj",
            "F and J",
            "Feel the little bumps on F and J? Put your pointer fingers there. That's home!",
            new="fj",
            lines=("fff jjj fff jjj fj fj jf jf ffj jjf fjf jfj",),
        ),
        Step(
            "dk",
            "D and K",
            "Rest your middle fingers next to your pointers, on D and K.",
            new="dk",
            lines=("ddd kkk ddd kkk dk kd fd jk dfd kjk fdk jkd",),
        ),
        Step(
            "sl",
            "S and L",
            "Your ring fingers go on S and L.",
            new="sl",
            lines=("sss lll sss lll sl ls sd lk sdf lkj fsd jlk",),
        ),
        Step(
            "a;",
            "A and ;",
            "Your little pinky fingers rest on A and ; (semicolon).",
            new="a;",
            lines=("aaa ;;; aaa ;;; a; ;a as l; asdf jkl; asdf jkl;",),
        ),
        Step(
            "all",
            "All together",
            "Now use all eight fingers. Keep them resting on the home row!",
            new="asdfjkl;",
            lines=("asdf jkl; fdsa ;lkj asdf jkl; fjdksla; asdf jkl;",),
        ),
        Step(
            "gh",
            "Stretch to G and H",
            "Your pointer fingers can stretch one key toward the middle for "
            "G and H. Then hop back home!",
            new="gh",
            lines=("fff ggg fgf jjj hhh jhj fg jh gh hg fgh jhg",),
        ),
        Step(
            "words1",
            "First words",
            "You know enough keys to type real words! Thumbs press Space.",
            kind="words",
            lines=("dad sad lad add ask all fall lass flask",),
        ),
        Step(
            "words2",
            "More words",
            "More words using G and H too.",
            new="gh",
            kind="words",
            lines=("had has gas glad half hall dash flag lash shall",),
        ),
        Step(
            "sentences",
            "Little sentences",
            "Type these tiny sentences. Take your time. Being right beats being fast!",
            kind="sentences",
            lines=("a lad asks dad; dad has a glass; all fall; a glad lass",),
        ),
    ),
)

TOP_ROW = Lesson(
    key="top-row",
    title="Top Row Climbers",
    description="Reach up to the top row, then always come back home.",
    steps=(
        Step(
            "ei",
            "E and I",
            "Your middle fingers reach up: D goes up to E, and K goes up to I. Then back home!",
            new="ei",
        ),
        Step("ru", "R and U", "Your pointer fingers reach up: F to R, and J to U.", new="ru"),
        Step(
            "ty", "T and Y", "Pointer fingers stretch up and toward the middle: T and Y.", new="ty"
        ),
        Step("wo", "W and O", "Your ring fingers reach up: S to W, and L to O.", new="wo"),
        Step(
            "qp",
            "Q and P",
            "Your pinkies reach up: A to Q, and ; to P. Pinkies are small but strong!",
            new="qp",
        ),
        Step(
            "words",
            "Top row words",
            "Lots of new words now! Let each finger do its own job.",
            new="eiruwtyoqp",
            kind="words",
        ),
        Step(
            "sentences",
            "Top row sentences",
            "Real sentences! Keep your fingers resting on the home row.",
            kind="sentences",
        ),
    ),
)

BOTTOM_ROW = Lesson(
    key="bottom-row",
    title="Bottom Row Divers",
    description="Dive down to the bottom row: the last of the letters.",
    steps=(
        Step("vm", "V and M", "Your pointer fingers reach down: F to V, and J to M.", new="vm"),
        Step(
            "bn",
            "B and N",
            "Pointer fingers stretch down and toward the middle: B and N.",
            new="bn",
        ),
        Step(
            "c,", "C and comma", "Middle fingers reach down: D to C, and K to , (comma).", new="c,"
        ),
        Step(
            "x.",
            "X and full stop",
            "Ring fingers reach down: S to X, and L to . (full stop).",
            new="x.",
        ),
        Step("z/", "Z and slash", "Pinkies reach down: A to Z, and ; to / (slash).", new="z/"),
        Step(
            "words",
            "Every letter",
            "You know every letter now! Let's type all kinds of words.",
            new="vmbncxz",
            kind="words",
        ),
        Step(
            "sentences",
            "Sentences with full stops",
            "Sentences with commas and full stops. Fantastic!",
            new=",.",
            kind="sentences",
        ),
    ),
)

CAPITALS = Lesson(
    key="capitals",
    title="Big Letters",
    description="Use Shift for capital letters, plus ' and ?",
    steps=(
        Step(
            "left-shift",
            "Capitals with left Shift",
            "For a capital on the right side of the keyboard, hold Shift with "
            "your LEFT pinky, then press the letter.",
            new="HJKLNMUIOPY",
        ),
        Step(
            "left-words",
            "Names and words",
            "Names start with a capital letter. Left pinky holds Shift!",
            new="HJKLNMUIOPY",
            kind="words",
        ),
        Step(
            "right-shift",
            "Capitals with right Shift",
            "For a capital on the left side, hold Shift with your RIGHT pinky.",
            new="QWERTASDFGZXCVB",
        ),
        Step(
            "right-words",
            "More names",
            "Now use whichever Shift is on the other side from the letter.",
            new="QWERTASDFGZXCVB",
            kind="words",
        ),
        Step(
            "sentences",
            "Proper sentences",
            "Sentences start with a capital and end with a full stop.",
            kind="sentences",
        ),
        Step(
            "quote-question",
            "' and ?",
            "Your right pinky types ' (next to ;) and ? (Shift and /).",
            new="'?",
            kind="sentences",
            line_count=4,
        ),
    ),
)

NUMBERS = Lesson(
    key="numbers",
    title="Number Row",
    description="Reach all the way up to the numbers.",
    steps=(
        Step("47", "4 and 7", "Pointer fingers reach way up, past R and U, to 4 and 7.", new="47"),
        Step(
            "56",
            "5 and 6",
            "Pointer fingers stretch up and toward the middle for 5 and 6.",
            new="56",
        ),
        Step("38", "3 and 8", "Middle fingers reach up past E and I to 3 and 8.", new="38"),
        Step("29", "2 and 9", "Ring fingers reach up past W and O to 2 and 9.", new="29"),
        Step("10", "1 and 0", "Pinkies reach way up past Q and P to 1 and 0.", new="10"),
        Step(
            "mix",
            "Numbers and words",
            "Numbers and words together. Remember to come back home!",
            new="1234567890",
            kind="numbers",
        ),
        Step(
            "sentences",
            "Number sentences",
            "Sentences with numbers in them.",
            new="1234567890",
            kind="sentences",
            line_count=4,
        ),
    ),
)

PUNCTUATION = Lesson(
    key="punctuation",
    title="Punctuation Pros",
    description='Add some sparkle with ! and " and - and :',
    steps=(
        Step(
            "exclaim",
            "Exclamation mark !",
            "Hold Shift with your RIGHT pinky and press 1 with your left pinky. Wow!",
            new="!",
            kind="sentences",
            lines=("wow! yes! go! stop! ha ha! oh no! hooray!",),
            line_count=4,
        ),
        Step(
            "quotes",
            'Quote marks "',
            "Quote marks go around the words someone says. Hold Shift with your "
            "LEFT pinky and press ' with your right pinky.",
            new='"',
            kind="sentences",
            lines=('"hi" "yes" "no" "help!" "Hello," said Pip.',),
            line_count=4,
            layout_instructions=(
                (
                    "uk",
                    "Quote marks go around the words someone says. Hold Shift with "
                    "your RIGHT pinky and press 2 with your left ring finger.",
                ),
            ),
        ),
        Step(
            "dash-colon",
            "Hyphen - and colon :",
            "Your right pinky reaches up past 0 for - (hyphen). For : (colon), "
            "hold Shift with your LEFT pinky and press ;",
            new="-:",
            kind="sentences",
            lines=("ice-cream well-done blue-green 3:30 7:45 note: hi",),
            line_count=4,
        ),
        Step(
            "mix",
            "All the marks",
            'Sentences with every mark: ! " - and : Take your time!',
            new='!"-:',
            kind="sentences",
            lines=('"Hooray!" said Kai. Party time: 4:30 at the ice-rink.',),
            line_count=4,
        ),
    ),
)

STORY_TIME = Lesson(
    key="stories",
    title="Story Time",
    description="Put it all together with some short stories.",
    steps=tuple(_story(k) for k in ("kite", "snail", "pancakes", "stars")),
)

LESSONS: tuple[Lesson, ...] = (
    HOME_ROW,
    TOP_ROW,
    BOTTOM_ROW,
    CAPITALS,
    NUMBERS,
    PUNCTUATION,
    STORY_TIME,
)

# Every step in teaching order, as (lesson, step_index).
ALL_STEPS: tuple[tuple[Lesson, int], ...] = tuple(
    (lesson, i) for lesson in LESSONS for i in range(len(lesson.steps))
)


def _known_keys() -> dict[str, frozenset[str]]:
    known = {" "}
    result = {}
    for lesson, i in ALL_STEPS:
        known |= set(lesson.steps[i].new)
        result[lesson.step_id(i)] = frozenset(known)
    return result


# step_id -> every character the child can type at that step.
KNOWN = _known_keys()


def flat_index(lesson: Lesson, index: int) -> int:
    return ALL_STEPS.index((lesson, index))


def is_unlocked(stars_for, lesson: Lesson, index: int) -> bool:
    """A step is unlocked when the step before it (in any lesson) has stars."""
    k = flat_index(lesson, index)
    if k == 0 or stars_for(lesson.step_id(index)) > 0:
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

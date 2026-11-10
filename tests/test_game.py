import random

import pytest

from typing_tutor.game import DIFFICULTIES, LIVES, MIN_WORDS, POPS_PER_LEVEL, GameState, game_words
from typing_tutor.lessons import KNOWN


def new_game(step_id="top-row/words", difficulty="medium", seed=1):
    return GameState(DIFFICULTIES[difficulty], game_words(KNOWN[step_id]), random.Random(seed))


def run_for(game, seconds, dt=0.1):
    events = []
    for _ in range(round(seconds / dt)):
        events += game.update(dt)
    return events


def active(game):
    return sorted((b for b in game.balloons if b.active), key=lambda b: b.y)


def test_game_words_use_only_known_keys_and_skip_single_letters():
    known = KNOWN["home-row/all"]
    words = game_words(known)
    assert len(words) >= MIN_WORDS
    assert all(len(w) >= 2 and set(w) <= known for w in words)


def test_game_is_locked_at_the_very_start():
    assert len(game_words(KNOWN["home-row/fj"])) < MIN_WORDS


def test_typing_a_word_pops_its_balloon():
    g = new_game()
    run_for(g, 1)
    balloon = active(g)[0]
    kinds = [e.kind for ch in balloon.word for e in g.type(ch)]
    assert kinds == ["hit"] * (len(balloon.word) - 1) + ["pop"]
    assert not balloon.active and g.popped == 1 and g.target is None
    assert g.score == 10 * len(balloon.word)


def test_a_letter_matching_no_balloon_is_a_miss():
    g = new_game()
    run_for(g, 1)
    letter = next(c for c in "zqxj" if not any(b.word.startswith(c) for b in g.balloons))
    assert [e.kind for e in g.type(letter)] == ["miss"]
    assert g.target is None


def test_a_wrong_letter_keeps_the_target():
    g = new_game()
    run_for(g, 1)
    balloon = active(g)[0]
    g.type(balloon.word[0])
    wrong = next(c for c in "zqx" if c != balloon.word[1])
    assert g.type(wrong)[0].kind == "miss"
    assert g.target is balloon and g.combo == 0
    assert g.key_stats[balloon.word[1]]["m"] == 1


def test_the_first_letter_targets_the_highest_matching_balloon():
    g = new_game()
    run_for(g, 1)
    first = active(g)[0]
    first.y = 0.8
    twin = g.spawn()
    twin.word, twin.y = first.word[0] + "zz", 0.3
    g.type(first.word[0])
    assert g.target is twin


def test_balloons_on_screen_start_with_different_letters():
    g = new_game("bottom-row/words", "hard")
    run_for(g, 10, dt=0.05)
    firsts = [b.word[0] for b in active(g)]
    assert len(firsts) >= 3 and len(firsts) == len(set(firsts))


def test_easy_words_are_short():
    g = new_game("bottom-row/words", "easy")
    for _ in range(30):
        assert len(g.spawn().word) <= DIFFICULTIES["easy"].max_word_len


def test_three_escapes_end_the_game():
    g = new_game("home-row/all", "easy")
    kinds = [e.kind for e in run_for(g, 200)]
    assert kinds.count("escape") == LIVES and kinds[-1] == "over"
    assert g.over and g.lives == 0
    assert g.type("a") == [] and g.update(1) == []


def test_a_perfect_player_levels_up_and_balloons_speed_up():
    g = new_game()
    start_speed = g.rise_seconds()
    for _ in range(3000):
        g.update(0.05)
        for b in [b for b in g.balloons if b.active and b.y < 0.7]:
            for ch in b.word[b.typed :]:
                g.type(ch)
    assert g.lives == LIVES
    assert g.level == 1 + g.popped // POPS_PER_LEVEL > 3
    assert g.rise_seconds() < start_speed
    assert g.wpm() > 0


def test_combo_adds_bonus_points():
    g = new_game()
    run_for(g, 6)
    scores = []
    for b in active(g)[:2]:
        before = g.score
        for ch in b.word:
            g.type(ch)
        scores.append(g.score - before - 10 * len(b.word))
    assert scores == [0, 5]


@pytest.mark.parametrize("difficulty", list(DIFFICULTIES))
def test_difficulty_curve_has_floors(difficulty):
    g = new_game(difficulty=difficulty)
    g.level = 100
    assert g.rise_seconds() == 3.5 and g.spawn_seconds() == 0.8

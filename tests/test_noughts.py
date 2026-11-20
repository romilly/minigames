import importlib
import sys

import pygame

import minigame as mg
import noughts as n
from fakes import RecordingDisplay, ScriptedButtons, RecordingSpeaker, fake_pygame


class FirstChoice:
    """A predictable random: never makes a mistake, always picks the first option."""

    def random(self):
        return 0.99

    def choice(self, options):
        return options[0]


def board(text):
    """board('XO. .X. ..O') -> a list of nine squares; '.' is empty."""
    return [c if c != '.' else n.EMPTY for c in text.replace(' ', '')]


# ---- Rules ----

def test_winner_finds_rows_columns_and_diagonals():
    assert n.winner(board('XXX ... ...')) == 'X'
    assert n.winner(board('O.. O.. O..')) == 'O'
    assert n.winner(board('..X .X. X..')) == 'X'
    assert n.winner(board('XOX OXO OXO')) is None
    assert n.winning_line(board('O.. .O. ..O')) == (0, 4, 8)


# ---- The computer's player ----

def test_it_takes_a_win():
    assert n.best_moves(board('OO. XX. X..'), 'O') == [2]


def test_it_blocks_a_win():
    assert n.best_moves(board('XX. .O. ...'), 'O') == [2]


def test_it_answers_a_corner_with_the_centre():
    assert n.best_moves(board('X.. ... ...'), 'O') == [4]


def test_it_answers_the_centre_with_a_corner():
    assert sorted(n.best_moves(board('... .X. ...'), 'O')) == [0, 2, 6, 8]


def test_it_sees_a_fork_coming():
    # X has opposite corners; O must take an edge, not a corner.
    assert sorted(n.best_moves(board('X.. .O. ..X'), 'O')) == [1, 3, 5, 7]


def _worst_result_for_ai(b, to_move):
    """Play every human reply and every equally-good computer move to the end.
    Returns 'loss' if any line loses for the computer."""
    if n.winner(b) == n.HUMAN:
        return 'loss'
    if n.winner(b) or n.EMPTY not in b:
        return 'ok'
    moves = n.best_moves(b, n.AI) if to_move == n.AI else n.empty_squares(b)
    for i in moves:
        b[i] = to_move
        result = _worst_result_for_ai(b, n.other(to_move))
        b[i] = n.EMPTY
        if result == 'loss':
            return 'loss'
    return 'ok'


def test_perfect_play_never_loses_whoever_starts():
    assert _worst_result_for_ai([n.EMPTY] * 9, n.HUMAN) == 'ok'
    assert _worst_result_for_ai([n.EMPTY] * 9, n.AI) == 'ok'


class Mistaken(FirstChoice):
    def random(self):
        return 0.0


def test_a_mistake_is_a_random_empty_square():
    b = board('XX. .O. ...')
    assert n.choose_move(b, 'O', Mistaken(), 0.15) == 2      # first empty, by luck
    b = board('X.X .O. ...')
    assert n.choose_move(b, 'O', Mistaken(), 0.15) == 1
    b = board('XX. .O. ..O')
    assert n.choose_move(b, 'O', FirstChoice(), 0.15) == 2


# ---- The game ----

def test_cursor_moves_and_stops_at_the_edges():
    game = n.Noughts(FirstChoice())
    assert game.cursor == 4
    assert game.key(pygame.K_UP) == ['move']
    assert game.cursor == 1
    assert game.key(pygame.K_UP) == []
    assert game.cursor == 1
    game.key(pygame.K_LEFT)
    assert game.cursor == 0
    game.key(pygame.K_DOWN)
    game.key(pygame.K_DOWN)
    game.key(pygame.K_RIGHT)
    game.key(pygame.K_RIGHT)
    assert game.cursor == 8


def test_placing_then_the_computer_replies_after_a_pause():
    game = n.Noughts(FirstChoice())
    assert game.key(pygame.K_a) == ['place']
    assert game.board[4] == 'X'
    assert game.status() == 'Thinking...'
    assert game.key(pygame.K_a) == []               # not your turn
    assert game.update(n.AI_DELAY_MS - 1) == []
    assert game.update(1) == ['place']
    assert game.board.count('O') == 1
    assert game.status() == 'Your move'


def test_you_cannot_play_on_a_taken_square():
    game = n.Noughts(FirstChoice())
    game.board = board('O.. ... ...')
    game.cursor = 0
    assert game.key(pygame.K_SPACE) == ['bump']
    assert game.board[0] == 'O'


def test_a_win_is_scored_and_a_for_another_game_swaps_who_starts():
    game = n.Noughts(FirstChoice())
    game.board = board('XX. OO. ...')
    game.cursor = 2
    assert game.key(pygame.K_RETURN) == ['win']
    assert game.status() == 'You win! A: again'
    assert game.score_line() == 'You 1   Me 0   Draws 0'
    assert game.key(pygame.K_UP) == []
    assert game.key(pygame.K_a) == ['new']
    assert game.board == [n.EMPTY] * 9
    assert game.turn == n.AI


def test_a_loss_and_a_draw():
    game = n.Noughts(FirstChoice())
    game.board = board('OO. XX. X..')
    game.turn = n.AI
    assert game.update(n.AI_DELAY_MS) == ['lose']
    assert game.status() == 'I win! A: again'
    game.new_game()
    game.board = board('XOX XOO OX.')
    game.cursor = 8
    assert game.key(pygame.K_a) == ['draw']
    assert game.score_line() == 'You 0   Me 1   Draws 1'


# ---- End to end on the shim ----

def test_main_runs_on_the_shim(monkeypatch):
    display = RecordingDisplay()
    speaker = RecordingSpeaker()
    frames = [set(), {mg.K_a}] + [set()] * 20 + [{mg.K_ESCAPE}]
    pg = fake_pygame(display=display, buttons=ScriptedButtons(*frames), speaker=speaker)
    monkeypatch.setitem(sys.modules, 'pygame', pg)
    monkeypatch.delitem(sys.modules, 'noughts')
    monkeypatch.delitem(sys.modules, 'tones', raising=False)
    shim_noughts = importlib.import_module('noughts')

    game = shim_noughts.main(game=shim_noughts.Noughts(FirstChoice()))

    assert game.board.count('X') == 1 and game.board.count('O') == 1
    texts = [c[2] for c in display.calls if c[0] == 'text']
    assert 'X' in texts and 'O' in texts and 'Your move' in texts
    assert ('play', 880, None) in speaker.calls

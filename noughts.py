"""Noughts and crosses: you (X) against the computer (O).

Pad: U D L R move the cursor, A places your X (on the desktop: arrow keys,
then A, Space or Enter). After a game, A starts the next one; whoever didn't
start last time goes first. '-' (Esc) quits.

The computer looks ahead with minimax and alpha-beta pruning, so it never
misses a win or a block, but it makes a random move MISTAKE_CHANCE of the
time so that you can beat it.
"""
import random

import pygame
from gamekit import render_fitting
from tones import tone

HUMAN, AI, EMPTY = 'X', 'O', ' '
MISTAKE_CHANCE = 0.15
AI_DELAY_MS = 500               # a pause, so you can see the computer move

LINES = ((0, 1, 2), (3, 4, 5), (6, 7, 8),
         (0, 3, 6), (1, 4, 7), (2, 5, 8),
         (0, 4, 8), (2, 4, 6))
CORNERS = (0, 2, 6, 8)
CENTRE = 4


# ---- The rules ----

def winning_line(board):
    for line in LINES:
        a, b, c = line
        if board[a] != EMPTY and board[a] == board[b] == board[c]:
            return line
    return None


def winner(board):
    line = winning_line(board)
    return board[line[0]] if line else None


def empty_squares(board):
    return [i for i in range(9) if board[i] == EMPTY]


def other(player):
    return AI if player == HUMAN else HUMAN


# ---- The computer's player ----

def negamax(board, player, alpha=-100, beta=100):
    """How good the position is for `player`, who is about to move.

    Positive: player can force a win; zero: a draw; negative: a loss.
    Quicker wins score higher, so the computer doesn't dawdle.
    """
    empties = board.count(EMPTY)
    if winner(board):                 # the other player has just won
        return -(empties + 1)
    if empties == 0:
        return 0
    best = -100
    for i in range(9):
        if board[i] == EMPTY:
            board[i] = player
            value = -negamax(board, other(player), -beta, -alpha)
            board[i] = EMPTY
            if value > best:
                best = value
            if best > alpha:
                alpha = best
            if alpha >= beta:
                break
    return best


def best_moves(board, player):
    """All the moves that are as good as any other."""
    if board.count(EMPTY) >= 8:
        # Opening book: the centre if it's free, otherwise a corner. This is
        # perfect play, and saves a search that is slow on a microcontroller.
        if board.count(EMPTY) == 9:
            return [CENTRE] + list(CORNERS)
        return [CENTRE] if board[CENTRE] == EMPTY else list(CORNERS)
    values = {}
    for i in empty_squares(board):
        board[i] = player
        values[i] = -negamax(board, other(player))
        board[i] = EMPTY
    top = max(values.values())
    return [i for i in values if values[i] == top]


def choose_move(board, player, rng=random, mistake_chance=MISTAKE_CHANCE):
    if rng.random() < mistake_chance:
        return rng.choice(empty_squares(board))
    return rng.choice(best_moves(board, player))


# ---- The game ----

class Noughts:
    def __init__(self, rng=random, mistake_chance=MISTAKE_CHANCE):
        self.rng = rng
        self.mistake_chance = mistake_chance
        self.scores = {HUMAN: 0, AI: 0, 'draw': 0}
        self.human_starts = True
        self.new_game()

    def new_game(self):
        self.board = [EMPTY] * 9
        self.cursor = CENTRE
        self.result = None              # HUMAN, AI or 'draw' when it's over
        self.turn = HUMAN if self.human_starts else AI
        self.wait_ms = AI_DELAY_MS

    def key(self, key):
        """A key was pressed. Returns what happened, for sounds."""
        if self.result:
            if key in place_keys():
                self.human_starts = not self.human_starts
                self.new_game()
                return ['new']
            return []
        if self.turn != HUMAN:
            return []
        row, col = divmod(self.cursor, 3)
        if key == pygame.K_UP and row > 0:
            self.cursor -= 3
        elif key == pygame.K_DOWN and row < 2:
            self.cursor += 3
        elif key == pygame.K_LEFT and col > 0:
            self.cursor -= 1
        elif key == pygame.K_RIGHT and col < 2:
            self.cursor += 1
        elif key in place_keys():
            if self.board[self.cursor] != EMPTY:
                return ['bump']
            return self._play(self.cursor)
        else:
            return []
        return ['move']

    def update(self, dt_ms):
        """Time passed. The computer moves after a short pause."""
        if self.result or self.turn != AI:
            return []
        self.wait_ms -= dt_ms
        if self.wait_ms > 0:
            return []
        return self._play(choose_move(self.board, AI, self.rng, self.mistake_chance))

    def _play(self, square):
        self.board[square] = self.turn
        won = winner(self.board)
        if won:
            self.result = won
            self.scores[won] += 1
            return ['win' if won == HUMAN else 'lose']
        if EMPTY not in self.board:
            self.result = 'draw'
            self.scores['draw'] += 1
            return ['draw']
        self.turn = other(self.turn)
        self.wait_ms = AI_DELAY_MS
        return ['place']

    def status(self):
        if self.result == HUMAN:
            return 'You win! A: again'
        if self.result == AI:
            return 'I win! A: again'
        if self.result == 'draw':
            return 'A draw. A: again'
        return 'Your move' if self.turn == HUMAN else 'Thinking...'

    def score_line(self):
        return 'You %d   Me %d   Draws %d' % (
            self.scores[HUMAN], self.scores[AI], self.scores['draw'])


def place_keys():
    return (pygame.K_a, pygame.K_SPACE, pygame.K_RETURN)


# ---- Drawing ----

SIZE = (320, 240)   # the desktop window; (240, 240) shows what the Presto gets
TEXT_BAND = 20      # room for a line of text above and below the grid
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
GREY = (120, 120, 120)
CURSOR = (0, 0, 120)
WIN = (0, 110, 0)
COLOURS = {HUMAN: (255, 220, 0), AI: (0, 220, 255)}


class Layout:
    """Where things go on a screen of a given size."""

    def __init__(self, width, height):
        self.width, self.height = width, height
        self.cell = min(width, height - 2 * TEXT_BAND - 4) // 3
        self.grid_x = (width - 3 * self.cell) // 2
        self.grid_y = (height - 3 * self.cell) // 2

    def cell_rect(self, square):
        row, col = divmod(square, 3)
        return pygame.Rect(self.grid_x + col * self.cell, self.grid_y + row * self.cell,
                           self.cell, self.cell)


def draw(screen, game, layout, fonts, big):
    screen.fill(BLACK)
    if game.turn == HUMAN and not game.result:
        pygame.draw.rect(screen, CURSOR, layout.cell_rect(game.cursor))
    line = winning_line(game.board)
    for square in line or ():
        pygame.draw.rect(screen, WIN, layout.cell_rect(square))
    x, y, cell = layout.grid_x, layout.grid_y, layout.cell
    for i in (1, 2):
        pygame.draw.rect(screen, GREY, (x + i * cell - 1, y, 2, 3 * cell))
        pygame.draw.rect(screen, GREY, (x, y + i * cell - 1, 3 * cell, 2))
    for square in range(9):
        mark = game.board[square]
        if mark != EMPTY:
            text = big.render(mark, False, COLOURS[mark])
            screen.blit(text, text.get_rect(center=layout.cell_rect(square).center))
    room = layout.width - 4
    text = render_fitting(fonts, game.status(), WHITE, room)
    screen.blit(text, text.get_rect(centerx=layout.width // 2, top=2))
    text = render_fitting(fonts, game.score_line(), GREY, room)
    screen.blit(text, text.get_rect(centerx=layout.width // 2, bottom=layout.height - 2))


def main(fps=30, game=None, size=SIZE):
    pygame.init()
    screen = pygame.display.set_mode(size)
    layout = Layout(*screen.get_size())     # on a board, the board's own size
    clock = pygame.time.Clock()
    fonts = [pygame.font.Font(None, 24), pygame.font.Font(None, 16)]
    big = pygame.font.Font(None, layout.cell * 9 // 8)
    sounds = {'move': tone(1200, 10), 'bump': tone(150, 60),
              'place': tone(880, 50), 'new': tone(660, 50),
              'win': tone(1320, 400), 'lose': tone(110, 400), 'draw': tone(330, 300)}
    game = game or Noughts()
    running = True
    dt = 0
    while running:
        happened = []
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                else:
                    happened += game.key(event.key)
        happened += game.update(dt)
        for what in happened:
            sounds[what].play()
        draw(screen, game, layout, fonts, big)
        pygame.display.flip()
        dt = clock.tick(fps)
    pygame.quit()
    return game


if __name__ == '__main__':
    main()

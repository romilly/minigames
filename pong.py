"""Pong: one paddle, one ball, three walls. A point for each return.

Runs unchanged under desktop pygame (arrow keys, Esc to quit) and on the
Explorer with the minigame shim (pad U/D, '-' to quit).

Speeds are in pixels per second; each update moves things by speed times
the time since the last frame, so the game runs at the same speed whatever
the frame rate.

update() returns what happened ('paddle', 'wall', 'miss'), and main()
plays a sound for each.
"""
import pygame
from gamekit import render_fitting
from tones import tone

SIZE = (320, 240)   # the desktop window; (240, 240) shows what the Presto gets
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
PADDLE_SPEED = 240
BALL_SPEED_X = 180
BALL_SPEED_Y = 120
MAX_DT_MS = 50      # after a stall, don't let the ball jump through the paddle
SERVE_DELAY_MS = 1000   # the ball waits this long before each serve


class Pong:
    def __init__(self, width=320, height=240, serve_delay_ms=SERVE_DELAY_MS):
        self.serve_delay_ms = serve_delay_ms
        self.bounds = pygame.Rect(0, 0, width, height)
        self.paddle = pygame.Rect(8, height // 2 - 20, 6, 40)
        self.paddle_y = float(self.paddle.y)
        self.score = 0
        self.misses = 0
        self.serve()

    def serve(self):
        self.ball = pygame.Rect(0, 0, 6, 6)
        self.ball.center = self.bounds.center
        self.ball_x, self.ball_y = float(self.ball.x), float(self.ball.y)
        self.vx, self.vy = -BALL_SPEED_X, BALL_SPEED_Y
        self.wait_ms = self.serve_delay_ms

    def update(self, up, down, dt_ms):
        happened = []
        dt = min(dt_ms, MAX_DT_MS) / 1000
        if up:
            self.paddle_y -= PADDLE_SPEED * dt
        if down:
            self.paddle_y += PADDLE_SPEED * dt
        self.paddle.y = int(self.paddle_y)
        self.paddle.clamp_ip(self.bounds)
        if self.paddle.y != int(self.paddle_y):
            self.paddle_y = float(self.paddle.y)

        if self.wait_ms > 0:              # waiting to serve: only the paddle moves
            self.wait_ms -= dt_ms
            return happened

        self.ball_x += self.vx * dt
        self.ball_y += self.vy * dt
        self.ball.x, self.ball.y = int(self.ball_x), int(self.ball_y)
        if self.ball.top <= 0 and self.vy < 0:
            self.vy = -self.vy
            happened.append('wall')
        if self.ball.bottom >= self.bounds.bottom and self.vy > 0:
            self.vy = -self.vy
            happened.append('wall')
        if self.ball.right >= self.bounds.right and self.vx > 0:
            self.vx = -self.vx
            happened.append('wall')
        if self.vx < 0 and self.ball.colliderect(self.paddle):
            self.vx = -self.vx
            self.score += 1
            happened.append('paddle')
        if self.ball.right < 0:
            self.misses += 1
            self.serve()
            happened.append('miss')
        return happened

    def status(self):
        return 'Score %d   Missed %d' % (self.score, self.misses)

    def draw(self, screen, fonts):
        screen.fill(BLACK)
        text = render_fitting(fonts, self.status(), WHITE, self.bounds.width - 4)
        screen.blit(text, text.get_rect(centerx=self.bounds.centerx, top=4))
        pygame.draw.rect(screen, WHITE, self.paddle)
        pygame.draw.rect(screen, WHITE, self.ball)


def main(fps=30, size=SIZE):
    pygame.init()
    screen = pygame.display.set_mode(size)
    width, height = screen.get_size()      # on a board, the board's own size
    clock = pygame.time.Clock()
    fonts = [pygame.font.Font(None, 24), pygame.font.Font(None, 16)]
    sounds = {'paddle': tone(880, 40), 'wall': tone(440, 40), 'miss': tone(110, 300)}
    game = Pong(width, height)
    running = True
    dt = 0
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                running = False
        keys = pygame.key.get_pressed()
        for what in game.update(keys[pygame.K_UP], keys[pygame.K_DOWN], dt):
            sounds[what].play()
        game.draw(screen, fonts)
        pygame.display.flip()
        dt = clock.tick(fps)
    pygame.quit()
    return game


if __name__ == '__main__':
    main()

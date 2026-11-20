"""Pong: one paddle, one ball, three walls. A point for each return.

Runs unchanged under desktop pygame (arrow keys, Esc to quit) and on the
Explorer with the minigame shim (pad U/D, '-' to quit).

Speeds are in pixels per second; each update moves things by speed times
the time since the last frame, so the game runs at the same speed whatever
the frame rate.
"""
import pygame

WIDTH, HEIGHT = 320, 240
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
PADDLE_SPEED = 240
BALL_SPEED_X = 180
BALL_SPEED_Y = 120
MAX_DT_MS = 50      # after a stall, don't let the ball jump through the paddle


class Pong:
    def __init__(self, width=WIDTH, height=HEIGHT):
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

    def update(self, up, down, dt_ms):
        dt = min(dt_ms, MAX_DT_MS) / 1000
        if up:
            self.paddle_y -= PADDLE_SPEED * dt
        if down:
            self.paddle_y += PADDLE_SPEED * dt
        self.paddle.y = int(self.paddle_y)
        self.paddle.clamp_ip(self.bounds)
        if self.paddle.y != int(self.paddle_y):
            self.paddle_y = float(self.paddle.y)

        self.ball_x += self.vx * dt
        self.ball_y += self.vy * dt
        self.ball.x, self.ball.y = int(self.ball_x), int(self.ball_y)
        if self.ball.top <= 0:
            self.vy = abs(self.vy)
        if self.ball.bottom >= self.bounds.bottom:
            self.vy = -abs(self.vy)
        if self.ball.right >= self.bounds.right:
            self.vx = -abs(self.vx)
        if self.vx < 0 and self.ball.colliderect(self.paddle):
            self.vx = abs(self.vx)
            self.score += 1
        if self.ball.right < 0:
            self.misses += 1
            self.serve()

    def status(self):
        return 'Score %d   Missed %d' % (self.score, self.misses)

    def draw(self, screen, font):
        screen.fill(BLACK)
        text = font.render(self.status(), False, WHITE)
        screen.blit(text, text.get_rect(centerx=self.bounds.centerx, top=4))
        pygame.draw.rect(screen, WHITE, self.paddle)
        pygame.draw.rect(screen, WHITE, self.ball)


def main(fps=30):
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    clock = pygame.time.Clock()
    font = pygame.font.Font(None, 24)
    game = Pong()
    running = True
    dt = 0
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                running = False
        keys = pygame.key.get_pressed()
        game.update(keys[pygame.K_UP], keys[pygame.K_DOWN], dt)
        game.draw(screen, font)
        pygame.display.flip()
        dt = clock.tick(fps)
    pygame.quit()
    return game


if __name__ == '__main__':
    main()

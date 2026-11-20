"""Pong walking skeleton: one paddle, one ball, three walls.

Runs unchanged under desktop pygame (arrow keys, Esc to quit) and on the
Explorer with the minigame shim (pad U/D, '-' to quit).
"""
import pygame

WIDTH, HEIGHT = 320, 240
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
PADDLE_SPEED = 4


class Pong:
    def __init__(self, width=WIDTH, height=HEIGHT):
        self.bounds = pygame.Rect(0, 0, width, height)
        self.paddle = pygame.Rect(8, height // 2 - 20, 6, 40)
        self.misses = 0
        self.serve()

    def serve(self):
        self.ball = pygame.Rect(0, 0, 6, 6)
        self.ball.center = self.bounds.center
        self.vx, self.vy = -3, 2

    def update(self, up, down):
        if up:
            self.paddle.move_ip(0, -PADDLE_SPEED)
        if down:
            self.paddle.move_ip(0, PADDLE_SPEED)
        self.paddle.clamp_ip(self.bounds)

        self.ball.move_ip(self.vx, self.vy)
        if self.ball.top <= 0:
            self.vy = abs(self.vy)
        if self.ball.bottom >= self.bounds.bottom:
            self.vy = -abs(self.vy)
        if self.ball.right >= self.bounds.right:
            self.vx = -abs(self.vx)
        if self.vx < 0 and self.ball.colliderect(self.paddle):
            self.vx = abs(self.vx)
        if self.ball.right < 0:
            self.misses += 1
            self.serve()

    def draw(self, screen):
        screen.fill(BLACK)
        pygame.draw.rect(screen, WHITE, self.paddle)
        pygame.draw.rect(screen, WHITE, self.ball)


def main(fps=30):
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    clock = pygame.time.Clock()
    game = Pong()
    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                running = False
        keys = pygame.key.get_pressed()
        game.update(keys[pygame.K_UP], keys[pygame.K_DOWN])
        game.draw(screen)
        pygame.display.flip()
        clock.tick(fps)
    pygame.quit()
    return game


if __name__ == '__main__':
    main()

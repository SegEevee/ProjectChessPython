import pygame
import sys
import turtle as keyboard

WIDTH, HEIGHT = 600, 600
ROWS, COLS = 12, 12
TILE_SIZE = WIDTH // COLS

pygame.init()
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("The Void")

board = [[1 for _ in range(COLS)] for _ in range(ROWS)]

player_one_position = [0,0]
player_two_position = [WIDTH-1,HEIGHT-1]

clock = pygame.time.Clock()
def draw_board(board):
    tiles = generate_tiles()

    for i, rect in enumerate(tiles):
        color = (72, 61, 139) if (i + i // COLS) % 2 == 0 else (0, 0, 0)
        pygame.draw.rect(screen, color, rect)

def generate_tiles():
    tiles = []
    for row in range(ROWS):
        for col in range(COLS):
            rect = pygame.Rect(
                col * TILE_SIZE,
                row * TILE_SIZE,
                TILE_SIZE,
                TILE_SIZE
            )
            tiles.append(rect)
    return tiles

def player_move():
    if keyboard.is_pressed('a'):
        return [player_one_position[0] - 1, player_one_position[1]]
    elif keyboard.is_pressed('d'):
        return [player_one_position[0] + 1, player_one_position[1]]
    elif keyboard.is_pressed('w'):
        return [player_two_position[0], player_two_position[1] + 1]
    elif keyboard.is_pressed('s'):
        return [player_two_position[0], player_two_position[1] - 1]

def update_player_position(player_position, player_number):
    if not is_legal_move(player_position):
        pygame.display.set_caption('Move is not legal!')
    if player_number == 1:
        player_one_position = player_position
    else:
        player_two_position = player_position

def is_legal_move(player_move):
    return (not (player_move[0] < 0 or player_move[1] < 0)
            or not player_move[0] > COLS or player_move[1] > COLS)

def main():
    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

        screen.fill((0, 0, 0))
        draw_board(board)

    pygame.display.flip()
    clock.tick(60)

if __name__ == "__main__":
    main()
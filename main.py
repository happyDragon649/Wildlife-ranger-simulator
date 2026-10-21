import pygame
import random
import math

pygame.init()

SCREEN_W, SCREEN_H = 960, 640
TILE = 32
WORLD_W, WORLD_H = 70, 50
FPS = 60

screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
pygame.display.set_caption("Park Ranger Simulation")
clock = pygame.time.Clock()

font = pygame.font.SysFont("consolas", 20)
small_font = pygame.font.SysFont("consolas", 15)

GRASS = (92, 145, 77)
DARK_GRASS = (82, 133, 69)
TRAIL = (184, 157, 111)
WATER = (58, 137, 181)
TREE_GREEN = (34, 94, 56)
TREE_DARK = (25, 72, 43)
BROWN = (107, 72, 44)
WHITE = (245, 245, 235)
GOLD = (244, 196, 70)

DEER_COUNT = 8
DEER_SPEED = 1.0
DEER_WANDER_MIN = 45
DEER_WANDER_MAX = 150
DEER_COLOR = (165, 112, 72)
DEER_COLOR_DARK = (95, 62, 40)

random.seed(12)

#note to self: 0 = grass, 1 = trail, 2 = water, 3 = tree

world = [
    [0 for _ in range(WORLD_W)]
    for _ in range(WORLD_H)
]

#hiking trail
for y in range(WORLD_H):
    x = WORLD_W // 2 + int(5 * math.sin(y / 6))
    for offset in range(-1, 2):
        tx = x + offset
        if 0 <= tx < WORLD_W:
            world[y][tx] = 1

#lake
lake_x, lake_y = 17, 15
lake_rx, lake_ry = 6, 4

for y in range(WORLD_H):
    for x in range(WORLD_W):
        distance = (
            ((x - lake_x) / lake_rx) ** 2
            + ((y - lake_y) / lake_ry) ** 2
        )

        if distance < 1:
            world[y][x] = 2

#scatter a buncha trees
for y in range(WORLD_H):
    for x in range(WORLD_W):
        if world[y][x] != 0:
            continue

        if random.random() < 0.13:
            world[y][x] = 3

#open area for ranger starting position
START_X, START_Y, = WORLD_W // 2, WORLD_H // 2

for y in range(START_Y - 2, START_Y + 3):
    for x in range(START_X - 2, START_X + 3):
        if 0 <= x < WORLD_W and 0 <= y < WORLD_H:
            world[y][x] = 0

player = pygame.Rect(START_X * TILE + 5, START_Y * TILE + 5, 22, 22)

PLAYER_SPEED = 190
funding_coins = 0

def collides_with_obstacle(rect):
    left = max(0, rect.left // TILE)
    right = min(WORLD_W - 1, rect.right // TILE)
    top = max(0, rect.top // TILE)
    bottom = min(WORLD_H - 1, rect.bottom // TILE)

    for ty in range(top, bottom + 1):
        for tx in range(left, right + 1):
            if world[ty][tx] in (2, 3):
                TILE_rect = pygame.Rect(tx * TILE, ty * TILE, TILE, TILE)

                if rect.colliderect(TILE_rect):
                    return True

    if (rect.left < 0 or rect.top < 0 or rect.right > WORLD_W * TILE or rect.bottom > WORLD_H * TILE):
        return True
    
    return False

def draw_world(camera_x, camera_y):
    start_x = max(0, camera_x // TILE)
    start_y = max(0, camera_y // TILE)

    end_x = min(WORLD_W, (camera_x + SCREEN_W) // TILE + 2)
    end_y = min(WORLD_H, (camera_y + SCREEN_H) // TILE + 2)

    for ty in range(start_y, end_y):
        for tx in range(start_x, end_x):
            tile = world[ty][tx]

            rect = pygame.Rect(tx * TILE - camera_x, ty * TILE - camera_y, TILE, TILE)

            if tile == 0:
                color = (GRASS if (ty + tx) % 2 == 0 else DARK_GRASS)
                pygame.draw.rect(screen, color, rect)

            elif tile == 1:
                pygame.draw.rect(screen, TRAIL, rect)
                pygame.draw.circle(
                    screen, (161, 133, 91),
                    rect.center, 2
                )

            elif tile == 2:
                pygame.draw.rect(screen, WATER, rect)
                pygame.draw.line(
                    screen, (111, 180, 210),
                    (rect.x + 5, rect.y + 12),
                    (rect.x + 20, rect.y + 12), 2
                )

            elif tile == 3:
                pygame.draw.rect(screen, GRASS, rect)
                pygame.draw.rect(screen, BROWN, (rect.x + 13, rect.y + 17, 7, 13))
                pygame.draw.circle(screen, TREE_DARK, (rect.centerx, rect.y + 13), 13)
                pygame.draw.circle(screen, TREE_GREEN, (rect.centerx - 3, rect.y + 9), 9)

def get_camera():
    camera_x = player.centerx - SCREEN_W // 2
    camera_y = player.centery - SCREEN_H // 2

    camera_x = max(0, min(camera_x, WORLD_W * TILE - SCREEN_W))
    camera_y = max(0, min(camera_y, WORLD_H * TILE - SCREEN_H))

    return camera_x, camera_y

def create_deer():
    for attempt in range(500):
        tile_x = random.randint(0, WORLD_W - 1)
        tile_y = random.randint(0, WORLD_H - 1)

        if world[tile_y][tile_x] not in (0, 1):
            continue

        x = tile_x * TILE + TILE // 2
        y = tile_y * TILE + TILE // 2

        deer_rect = pygame.Rect(x - 8, y - 8, 16, 16)

        if collides_with_obstacle(deer_rect):
            continue
        if deer_rect.colliderect(player):
            continue

        return {
            "x": float(x),
            "y": float(y),
            "direction_x": 0.0,
            "direction_y": 0.0,
            "timer": random.randint(DEER_WANDER_MIN, DEER_WANDER_MAX),
            "speed": DEER_SPEED
        }

    return None

def create_wildlife():
    deer_list = []

    for _ in range(DEER_COUNT):
        deer = create_deer()

        if deer is not None:
            deer_list.append(deer)

    return deer_list

def update_wildlife(deer_list):
    for deer in deer_list:
        deer["timer"] -= 1

        if deer["timer"] <= 0:
            angle = random.uniform(0, math.tau)

            deer["direction_x"] = math.cos(angle)
            deer["direction_y"] = math.sin(angle)

            deer["timer"] = random.randint(DEER_WANDER_MIN, DEER_WANDER_MAX)

        dx = deer["direction_x"] * deer["speed"]
        dy = deer["direction_y"] * deer["speed"]

        test_rect = pygame.Rect(
            int(deer["x"] - 8 + dx),
            int(deer["y"] - 8),
            16, 16
        )

        if (
            0 <= deer["x"] + dx < WORLD_W * TILE
            and not collides_with_obstacle(test_rect)
        ):
            deer["x"] += dx

        else:
            deer["direction_x"] *= -1

        test_rect = pygame.Rect(
            int(deer["x"] - 8),
            int(deer["y"] - 8 + dy),
            16, 16
        )

        if (
            0 <= deer["y"] + dy < WORLD_H * TILE
            and not collides_with_obstacle(test_rec)
        ):
            deer["y"] += dy

        else:
            deer["direction_y"] *= -1

def draw_wildlife(deer_list, camera_x, camera_y):
    for deer in deer_list:
        screen_x = int(deer["x"] - camera_x)
        screen_y = int(deer["y"] - camera_y)

        if not (
            -20 <= screen_x <= SCREEN_W + 20
            and -20 <= screen_y <= SCREEN_H + 20
        ):
            continue

        pygame.draw.ellipse(
            screen,
            DEER_COLOR,
            (screen_x - 8, screen_y - 5, 16, 10)
        )

        pygame.draw.circle(
            screen,
            DEER_COLOR,
            (screen_x + 7, screen_y - 4),
            4
        )

        for leg_x in (-5, 3):
            pygame.draw.line(
                screen,
                DEER_DARK_COLOR,
                (screen_x + leg_x, screen_y + 3),
                (screen_x + leg_x, screen_y + 7),
                2
            )

running = True

while running:
    dt = min(clock.tick(FPS) / 1000, 0.05)

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

    keys = pygame.key.get_pressed()

    dx = 0
    dy = 0

    if keys[pygame.K_a] or keys[pygame.K_LEFT]:
        dx -= 1
    if keys[pygame.K_d] or keys[pygame.K_RIGHT]:
        dx += 1
    if keys[pygame.K_w] or keys[pygame.K_UP]:
        dy -= 1
    if keys[pygame.K_s] or keys[pygame.K_DOWN]:
        dy += 1

    #prevent diagonal movements from being faster
    if dx != 0 and dy != 0:
        dx *= 0.7071
        dy *= 0.7071

    move_x = dx * PLAYER_SPEED * dt
    move_y = dy * PLAYER_SPEED * dt

    player.x += round(move_x)
    if collides_with_obstacle(player):
        player.x -= round(move_x)

    player.y += round(move_y)
    if collides_with_obstacle(player):
        player.y -= round(move_y)

    camera_x, camera_y = get_camera()

    draw_world(camera_x, camera_y)

    ranger_rect = pygame.Rect(player.x - camera_x, player.y - camera_y, player.width, player.height)

    #shadow + uniform + hat
    pygame.draw.ellipse(
        screen, (45, 70, 43),
        (ranger_rect.x - 2, ranger_rect.bottom - 5,
        ranger_rect.width + 4, 9)
    )

    pygame.draw.rect(
        screen, (49, 103, 177),
        ranger_rect, border_radius = 5
    )

    pygame.draw.rect(
        screen, (218, 187, 112),
        (ranger_rect.x + 3, ranger_rect.y - 3, 16, 7),
        border_radius = 2
    )

    pygame.draw.rect(
        screen, (28, 48, 38),
        (12, 12, 285, 91), border_radius = 10
    )

    pygame.draw.rect(
        screen, (110, 150, 105),
        (12, 12, 285, 91), 2, border_radius = 10
    )

    screen.blit(font.render("PARK RANGER SIMULATOR", True, WHITE), (25, 20))
    screen.blit(
        small_font.render(
            f"Funding: {funding_coins} coins",
            True, GOLD
        ),
        (25, 49)
    )
    screen.blit(
        small_font.render(
            f"Position: {player.x // TILE},"
            f"{player.y // TILE}",
            True, WHITE,
        ),
        (25, 72)
    )

    controls = small_font.render(
        "WASD/Arrows: Move   |   ESC: Quit",
        True, WHITE
    )

    pygame.draw.rect(
        screen, (28, 48, 38),
        (12, SCREEN_H - 37, controls.get_width() + 20, 27),
        border_radius = 6
    )

    screen.blit(controls, (22, SCREEN_H - 33))

    pygame.display.flip()

    if keys[pygame.K_ESCAPE]:
        running = False

pygame.quit()
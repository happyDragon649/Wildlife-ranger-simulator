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
DEER_DARK_COLOR = (95, 62, 40)
OBSERVATION_RANGE = 140
OBSERVATION_REWARD = 5
observation_message = ""

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

MISSION_DEER_TARGET = 3
MISSION_BONUS = 15
mission_completed = False

LOG_COUNT = 6
LOG_CLEAR_RANGE = 65
LOG_REWARD = 8
logs_cleared = 0

SPEED_BOOTS_COST = 25
BINOCULARS_COST = 20

speed_boots_bought = False
better_binoculars_bought = False
shop_open = False

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
            "speed": DEER_SPEED,
            "observed": False
        }

    return None

def create_wildlife():
    deer_list = []

    for _ in range(DEER_COUNT):
        deer = create_deer()

        if deer is not None:
            deer_list.append(deer)

    return deer_list

def create_fallen_logs():
    logs = []
    trail_tiles = []

    for y in range(WORLD_H):
        for x in range(WORLD_W):
            if world[y][x] == 1:
                trail_tiles.append((x, y))

    random.shuffle(trail_tiles)

    for tile_x, tile_y in trail_tiles:
        if len(logs) >= LOG_COUNT:
            break

        log_x = tile_x * TILE + TILE // 2
        log_y = tile_y * TILE + TILE // 2

        if math.hypot(
            player.centerx - log_x,
            player.centery - log_y,
        ) < 180:
            continue

        logs.append({
            "x": log_x,
            "y": log_y
        })

    return logs

def draw_fallen_logs(logs, camera_x, camera_y):
    for log in logs:
        x = int(log["x"] - camera_x)
        y = int(log["y"] - camera_y)

        if not (
            -30 <= x <= SCREEN_W + 30
            and -30 <= y <= SCREEN_H + 30
        ):
            continue

        pygame.draw.rect(
            screen, (105, 65, 35),
            (x - 12, y - 5, 24, 10),
            border_radius = 3
        )

        #lighter wood stripe
        pygame.draw.line(
            screen, (180, 130, 75),
            (x - 7, y - 2),
            (x + 7, y - 2), 2
        )

        pygame.draw.circle(
            screen, (205, 164, 105),
            (x + 10, y), 4
        )

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
            and not test_rect.colliderect(player)
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
            and not collides_with_obstacle(test_rect)
            and not test_rect.colliderect(player)
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

def observe_nearest_deer():
    global funding_coins, observation_message, mission_completed

    nearest_deer = None
    nearest_distance = float("inf")

    for deer in deer_list:
        if deer["observed"]:
            continue

        distance = math.hypot(
            player.centerx - deer["x"],
            player.centery - deer["y"]
        )

        if distance < nearest_distance:
            nearest_distance = distance
            nearest_deer = deer

    if nearest_deer is None:
        observation_message = "All deer have been observed!"
        return

    if nearest_distance > OBSERVATION_RANGE:
        observation_message = "Too far away! Get closer to the deer."
        return

    nearest_deer["observed"] = True
    funding_coins += OBSERVATION_REWARD

    observed_count = sum(1 for deer in deer_list if deer["observed"])

    if (
        observed_count >= MISSION_DEER_TARGET
        and not mission_completed
    ):
        mission_completed = True
        funding_coins += MISSION_BONUS
        observation_message = (
            f"Observing deer mission complete! +{MISSION_BONUS} bonus coins!"
        )

    else:
        observation_message = (
            f"Deer observed! +{OBSERVATION_REWARD} coins!"
        )

def clear_nearby_log():
    global funding_coins, logs_cleared, observation_message

    nearest_log = None
    nearest_distance = float("inf")

    for log in fallen_logs:
        distance = math.hypot(
            player.centerx - log["x"],
            player.centery - log["y"]
        )

        if distance < nearest_distance:
            nearest_distance = distance
            nearest_log = log

    if nearest_log is None or nearest_distance > LOG_CLEAR_RANGE:
        return False

    fallen_logs.remove(nearest_log)
    logs_cleared += 1
    funding_coins += LOG_REWARD

    observation_message = f"Trail cleared! +{LOG_REWARD} coins!"
    return True

def handle_interaction():
    if clear_nearby_log():
        return

    if mission_completed and logs_cleared >= LOG_COUNT:
        global observation_message
        observation_message = "All current tasks completed!"
        return

    observe_nearest_deer()

def handle_shop_key(key):
    global shop_open
    global funding_coins, PLAYER_SPEED, OBSERVATION_RANGE
    global speed_boots_bought, better_binoculars_bought
    global observation_message

    if key == pygame.K_b:
        shop_open = not shop_open

        if shop_open:
            observation_message = "Supply shop opened!"
        else:
            observation_message = "Supply shop closed!"

        return

    if not shop_open:
        return

    if key == pygame.K_1:
        if speed_boots_bought:
            observation_message = "You already have this item"
        elif funding_coins < SPEED_BOOTS_COST:
            observation_message = "Not enough coins!"
        else:
            funding_coins -= SPEED_BOOTS_COST
            PLAYER_SPEED += 50
            speed_boots_bought = True
            observation_message = "Speed boots purchased!"

    elif key == pygame.K_2:
        if better_binoculars_bought:
            observation_message = "You already have this item"
        elif funding_coins < BINOCULARS_COST:
            observation_message = "Not enough coins!"
        else:
            funding_coins -= BINOCULARS_COST
            OBSERVATION_RANGE += 50
            better_binoculars_bought = True
            observation_message = "Better binoculars purchased!"

def draw_shop():
    if not shop_open:
        return

    shop_rect = pygame.Rect(260, 170, 440, 270)

    pygame.draw.rect(screen, (35, 43, 38), shop_rect, border_radius = 12)
    pygame.draw.rect(screen, (220, 190, 105), shop_rect, 3, border_radius = 12)

    shop_lines = [
        ("Supply Shop", 30, (244, 196, 70)),
        (f"Your funding: {funding_coins} coins", 68, (255, 255, 255)),
        (
            "1. Speed Boots: 25 coins"
            + (" [OWNED]" if speed_boots_bought else ""),
            115,
            (255, 255, 255)
        ),
        (
            "2. Better Binoculars: 20 coins"
            + (" [OWNED]" if better_binoculars_bought else ""),
            155,
            (255, 255, 255)
        ),
        ("Press 1 or 2 to buy", 205, (210, 220, 210)),
        ("Press B to close", 235, (210, 220, 210))
    ]

    for message, y, color in shop_lines:
        text_surface = font.render(message, True, color)
        text_rect = text_surface.get_rect(center = (shop_rect.centerx, shop_rect.y + y))
        screen.blit(text_surface, text_rect)

deer_list = create_wildlife()

fallen_logs = create_fallen_logs()

running = True

while running:
    dt = min(clock.tick(FPS) / 1000, 0.05)

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_b:
                handle_shop_key(event.key)

            elif shop_open:
                handle_shop_key(event.key)

            elif event.key == pygame.K_e:
                handle_interaction()

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

    update_wildlife(deer_list)

    camera_x, camera_y = get_camera()

    draw_world(camera_x, camera_y)

    draw_fallen_logs(fallen_logs, camera_x, camera_y)

    draw_wildlife(deer_list, camera_x, camera_y)

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
        (12, 12, 285, 165), border_radius = 10
    )

    pygame.draw.rect(
        screen, (110, 150, 105),
        (12, 12, 285, 165), 2, border_radius = 10
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

    observed_count = sum(1 for deer in deer_list if deer["observed"])

    if mission_completed:
        mission_text = "Mission: COMPLETE"
    
    else:
        mission_text = (
            f"Mission: Observe deer "
            f"{observed_count}/{MISSION_DEER_TARGET}"
        )

    screen.blit(
        small_font.render(mission_text, True, GOLD),
        (25, 92)
    )

    log_text = f"Logs cleared: {logs_cleared}/{LOG_COUNT}"

    screen.blit(
        small_font.render(log_text, True, WHITE),
        (25, 114)
    )

    if observation_message:
        message_surface = small_font.render(observation_message, True, GOLD)
        screen.blit(message_surface, (25, 136))

    controls = small_font.render(
        "WASD/Arrows: Move  |  E: Observe deer  |  B: Open shop  |ESC: Quit",
        True, WHITE
    )

    pygame.draw.rect(
        screen, (28, 48, 38),
        (12, SCREEN_H - 37, controls.get_width() + 20, 27),
        border_radius = 6
    )

    screen.blit(controls, (22, SCREEN_H - 33))

    draw_shop()

    pygame.display.flip()

    if keys[pygame.K_ESCAPE]:
        running = False

pygame.quit()
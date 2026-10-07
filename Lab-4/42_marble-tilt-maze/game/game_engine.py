import pygame
from .marble import Marble
from .wall import Wall

# Game Engine

WHITE = (255, 255, 255)
DARK = (40, 40, 50)
WALL_COLOR = (90, 90, 110)
GOAL_COLOR = (60, 200, 120)
SELECTED_COLOR = (255, 220, 80)


class GameEngine:
    def __init__(self, width, height):
        self.width = width
        self.height = height

        self.start_x = 50
        self.start_y = 50

        self.marble = Marble(self.start_x, self.start_y)

        # Medium difficulty is the original setting.
        self.tilt_strength = 0.6
        self.friction = 0.02
        self.max_speed = 9

        self.difficulties = {
            "Easy": {
                "tilt_strength": 0.4,
                "friction": 0.04,
                "time_limit_ms": 60000,
            },
            "Medium": {
                "tilt_strength": 0.6,
                "friction": 0.02,
                "time_limit_ms": 45000,
            },
            "Hard": {
                "tilt_strength": 0.8,
                "friction": 0.01,
                "time_limit_ms": 30000,
            },
        }

        self.menu_options = ["Easy", "Medium", "Hard", "Exit"]
        self.selected_option = 0
        self.in_replay_menu = False

        self.walls = self._build_maze()
        self.goal_x, self.goal_y, self.goal_radius = (
            width - 60,
            height - 60,
            22,
        )

        self.time_limit_ms = 45000
        self.start_ticks = pygame.time.get_ticks()

        self.font = pygame.font.SysFont("Arial", 26)

        self.game_over = False
        self.result = None
        self.finish_time_ms = None
        self.should_exit = False

    def _build_maze(self):
        walls = []
        t = 16

        # outer boundary
        walls.append(Wall(0, 0, self.width, t))
        walls.append(Wall(0, self.height - t, self.width, t))
        walls.append(Wall(0, 0, t, self.height))
        walls.append(Wall(self.width - t, 0, t, self.height))

        # internal walls
        walls.append(Wall(0, 140, self.width - 140, t))
        walls.append(Wall(140, 260, self.width - 140, t))
        walls.append(Wall(0, 380, self.width - 140, t))

        return walls

    def handle_event(self, event):
        if event.type == pygame.QUIT:
            self.should_exit = True
            return

        # After game over, ENTER opens the replay menu.
        if self.game_over and not self.in_replay_menu:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_RETURN:
                    self.in_replay_menu = True
            return

        # Handle replay menu.
        if self.in_replay_menu:
            self._handle_replay_menu_input(event)
            return

    def _handle_replay_menu_input(self, event):
        if event.type != pygame.KEYDOWN:
            return

        if event.key == pygame.K_UP:
            self.selected_option = (
                self.selected_option - 1
            ) % len(self.menu_options)

        elif event.key == pygame.K_DOWN:
            self.selected_option = (
                self.selected_option + 1
            ) % len(self.menu_options)

        elif event.key == pygame.K_RETURN:
            selected = self.menu_options[self.selected_option]

            if selected == "Exit":
                self.should_exit = True
            else:
                self._start_new_game(selected)

    def _start_new_game(self, difficulty):
        settings = self.difficulties[difficulty]

        # Apply difficulty settings.
        self.tilt_strength = settings["tilt_strength"]
        self.friction = settings["friction"]
        self.time_limit_ms = settings["time_limit_ms"]

        # Reset marble.
        self.marble.x = self.start_x
        self.marble.y = self.start_y
        self.marble.vx = 0
        self.marble.vy = 0

        # Reset game state.
        self.game_over = False
        self.result = None
        self.finish_time_ms = None
        self.in_replay_menu = False

        # Restart timer.
        self.start_ticks = pygame.time.get_ticks()

    def handle_input(self):
        if self.game_over or self.in_replay_menu:
            return

        mouse_x, mouse_y = pygame.mouse.get_pos()
        dx = mouse_x - self.width // 2
        dy = mouse_y - self.height // 2
        dist = max(1, (dx ** 2 + dy ** 2) ** 0.5)

        ax = (dx / dist) * self.tilt_strength
        ay = (dy / dist) * self.tilt_strength

        self.marble.vx += ax
        self.marble.vy += ay

    def update(self):
        if self.game_over or self.in_replay_menu:
            return

        elapsed = pygame.time.get_ticks() - self.start_ticks

        if elapsed >= self.time_limit_ms:
            self.game_over = True
            self.result = "timeout"
            return

        self.marble.vx *= (1 - self.friction)
        self.marble.vy *= (1 - self.friction)

        speed = (
            self.marble.vx ** 2
            + self.marble.vy ** 2
        ) ** 0.5

        if speed > self.max_speed:
            scale = self.max_speed / speed
            self.marble.vx *= scale
            self.marble.vy *= scale

        self.marble.x += self.marble.vx
        self.marble.y += self.marble.vy

        self._resolve_wall_collisions()

        gx = self.goal_x - self.marble.x
        gy = self.goal_y - self.marble.y

        if (gx ** 2 + gy ** 2) ** 0.5 <= self.goal_radius:
            self.game_over = True
            self.result = "solved"
            self.finish_time_ms = elapsed

    def _resolve_wall_collisions(self):
        for wall in self.walls:
            wall_rect = wall.rect()

            cx = self.marble.x
            cy = self.marble.y
            radius = self.marble.radius

            # Find the closest point on the wall rectangle
            # to the center of the marble.
            closest_x = max(wall_rect.left, min(cx, wall_rect.right))
            closest_y = max(wall_rect.top, min(cy, wall_rect.bottom))

            dx = cx - closest_x
            dy = cy - closest_y
            distance_squared = dx * dx + dy * dy

            # No collision if the marble is outside the wall.
            if distance_squared > radius * radius:
                continue

            # Handle the case where the marble center is inside the wall.
            if distance_squared == 0:
                left = cx - wall_rect.left
                right = wall_rect.right - cx
                top = cy - wall_rect.top
                bottom = wall_rect.bottom - cy

                min_distance = min(left, right, top, bottom)

                if min_distance == left:
                    normal_x, normal_y = -1, 0
                    penetration = radius + left
                elif min_distance == right:
                    normal_x, normal_y = 1, 0
                    penetration = radius + right
                elif min_distance == top:
                    normal_x, normal_y = 0, -1
                    penetration = radius + top
                else:
                    normal_x, normal_y = 0, 1
                    penetration = radius + bottom
            else:
                distance = distance_squared ** 0.5
                normal_x = dx / distance
                normal_y = dy / distance
                penetration = radius - distance

            # Push the marble outside the wall.
            self.marble.x += normal_x * penetration
            self.marble.y += normal_y * penetration

            # Calculate velocity toward the wall.
            velocity_into_wall = (
                self.marble.vx * normal_x
                + self.marble.vy * normal_y
            )

            # Bounce only if the marble is moving into the wall.
            if velocity_into_wall < 0:
                self.marble.vx -= (
                    1.3 * velocity_into_wall * normal_x
                )
                self.marble.vy -= (
                    1.3 * velocity_into_wall * normal_y
                )

    def render(self, screen):
        if self.in_replay_menu:
            self._render_replay_menu(screen)
            return

        screen.fill(DARK)

        for wall in self.walls:
            pygame.draw.rect(screen, WALL_COLOR, wall.rect())

        pygame.draw.circle(
            screen,
            GOAL_COLOR,
            (self.goal_x, self.goal_y),
            self.goal_radius,
        )

        pygame.draw.circle(
            screen,
            WHITE,
            (int(self.marble.x), int(self.marble.y)),
            self.marble.radius,
        )

        elapsed = pygame.time.get_ticks() - self.start_ticks
        seconds_left = max(
            0,
            (self.time_limit_ms - elapsed) // 1000,
        )

        timer_text = self.font.render(
            f"Time: {seconds_left}s",
            True,
            WHITE,
        )
        screen.blit(timer_text, (10, 10))

        if self.game_over:
            self._render_game_over(screen)

    def _render_game_over(self, screen):
        overlay = pygame.Surface(
            (self.width, self.height),
            pygame.SRCALPHA,
        )
        overlay.fill((0, 0, 0, 180))
        screen.blit(overlay, (0, 0))

        if self.result == "solved":
            title_text = self.font.render(
                "Maze Solved!",
                True,
                WHITE,
            )

            time_text = self.font.render(
                f"Finished in {self.finish_time_ms / 1000:.1f}s",
                True,
                WHITE,
            )
        else:
            title_text = self.font.render(
                "Time's Up!",
                True,
                WHITE,
            )

            time_text = self.font.render(
                "Maze not solved.",
                True,
                WHITE,
            )

        prompt_text = self.font.render(
            "Press ENTER to continue",
            True,
            WHITE,
        )

        title_rect = title_text.get_rect(
            center=(self.width // 2, self.height // 2 - 50)
        )

        time_rect = time_text.get_rect(
            center=(self.width // 2, self.height // 2)
        )

        prompt_rect = prompt_text.get_rect(
            center=(self.width // 2, self.height // 2 + 50)
        )

        screen.blit(title_text, title_rect)
        screen.blit(time_text, time_rect)
        screen.blit(prompt_text, prompt_rect)

    def _render_replay_menu(self, screen):
        screen.fill(DARK)

        title_font = pygame.font.SysFont("Arial", 42)
        option_font = pygame.font.SysFont("Arial", 30)
        info_font = pygame.font.SysFont("Arial", 20)

        title = title_font.render(
            "Play Again?",
            True,
            WHITE,
        )

        title_rect = title.get_rect(
            center=(self.width // 2, 80)
        )

        screen.blit(title, title_rect)

        for index, option in enumerate(self.menu_options):
            selected = index == self.selected_option

            color = (
                SELECTED_COLOR
                if selected
                else WHITE
            )

            prefix = "> " if selected else "  "

            option_surface = option_font.render(
                prefix + option,
                True,
                color,
            )

            option_rect = option_surface.get_rect(
                center=(
                    self.width // 2,
                    160 + index * 55,
                )
            )

            screen.blit(option_surface, option_rect)

        info = info_font.render(
            "Use UP/DOWN to choose and ENTER to select",
            True,
            WHITE,
        )

        info_rect = info.get_rect(
            center=(self.width // 2, 410)
        )

        screen.blit(info, info_rect)

import pygame
import math
from array import array

from .marble import Marble
from .wall import Wall


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

        self.goal_x = width - 60
        self.goal_y = height - 60
        self.goal_radius = 22

        self.time_limit_ms = 45000
        self.start_ticks = pygame.time.get_ticks()

        self.font = pygame.font.SysFont("Arial", 26)

        self.game_over = False
        self.result = None
        self.finish_time_ms = None
        self.should_exit = False

        # Task 4: Sound Feedback
        self.sound_enabled = False
        self.bounce_sound = None
        self.goal_sound = None
        self.timeout_sound = None
        self.audio_error = None

        self._init_sounds()

    def _init_sounds(self):
        """
        Initialize the Pygame mixer safely and create all
        Task 4 sounds using the active mixer format.
        """
        try:
            mixer_info = pygame.mixer.get_init()

            if mixer_info is None:
                pygame.mixer.init(
                    frequency=44100,
                    size=-16,
                    channels=2,
                    buffer=512,
                )

                mixer_info = pygame.mixer.get_init()

            if mixer_info is None:
                raise pygame.error(
                    "Pygame mixer could not be initialized."
                )

            sample_rate, sample_size, channels = mixer_info

            if sample_size != -16:
                raise pygame.error(
                    f"Unsupported mixer sample format: {sample_size}"
                )

            if channels != 2:
                raise pygame.error(
                    f"Unsupported mixer channel count: {channels}"
                )

            self.bounce_sound = self._create_tone(
                frequency=260,
                duration=0.09,
                volume=0.85,
            )

            self.goal_sound = self._create_goal_sound()

            self.timeout_sound = self._create_timeout_sound()

            if self.bounce_sound is None:
                raise pygame.error(
                    "Bounce sound creation failed."
                )

            if self.goal_sound is None:
                raise pygame.error(
                    "Goal sound creation failed."
                )

            if self.timeout_sound is None:
                raise pygame.error(
                    "Timeout sound creation failed."
                )

            self.bounce_sound.set_volume(1.0)
            self.goal_sound.set_volume(1.0)
            self.timeout_sound.set_volume(1.0)

            self.sound_enabled = True
            self.audio_error = None

        except (
            pygame.error,
            OSError,
            ValueError,
            OverflowError,
        ) as error:
            self.audio_error = str(error)

            self.sound_enabled = False
            self.bounce_sound = None
            self.goal_sound = None
            self.timeout_sound = None

            print(
                "Task 4 audio unavailable:",
                self.audio_error
            )

    def _create_tone(self, frequency, duration, volume):
        """
        Generate a short stereo 16-bit sine-wave Pygame Sound.

        The generated PCM data matches the active mixer format.
        """
        mixer_info = pygame.mixer.get_init()

        if mixer_info is None:
            raise pygame.error(
                "Pygame mixer is not initialized."
            )

        sample_rate, sample_size, channels = mixer_info

        if sample_size != -16:
            raise pygame.error(
                "Tone generator requires signed 16-bit audio."
            )

        if channels != 2:
            raise pygame.error(
                "Tone generator requires stereo audio."
            )

        sample_count = max(
            1,
            int(sample_rate * duration)
        )

        samples = array("h")

        for i in range(sample_count):
            time_value = i / sample_rate

            fade = 1.0 - (
                i / sample_count
            )

            main_wave = math.sin(
                2
                * math.pi
                * frequency
                * time_value
            )

            harmonic = 0.20 * math.sin(
                2
                * math.pi
                * frequency
                * 2
                * time_value
            )

            sample_value = (
                main_wave + harmonic
            )

            sample_value *= (
                32767
                * volume
                * fade
            )

            sample_value = max(
                -32768,
                min(32767, int(sample_value))
            )

            samples.append(sample_value)
            samples.append(sample_value)

        sound = pygame.mixer.Sound(
            buffer=samples.tobytes()
        )

        return sound

    def _create_goal_sound(self):
        """
        Generate a short ascending two-tone sound for reaching
        the goal.
        """
        mixer_info = pygame.mixer.get_init()

        if mixer_info is None:
            raise pygame.error(
                "Pygame mixer is not initialized."
            )

        sample_rate, sample_size, channels = mixer_info

        if sample_size != -16 or channels != 2:
            raise pygame.error(
                "Goal sound requires 16-bit stereo audio."
            )

        duration = 0.30
        sample_count = int(
            sample_rate * duration
        )

        samples = array("h")

        for i in range(sample_count):
            time_value = i / sample_rate

            if time_value < 0.15:
                frequency = 520
            else:
                frequency = 780

            fade = 1.0 - (
                i / sample_count
            )

            wave = math.sin(
                2
                * math.pi
                * frequency
                * time_value
            )

            harmonic = 0.15 * math.sin(
                2
                * math.pi
                * frequency
                * 2
                * time_value
            )

            sample_value = (
                wave + harmonic
            )

            sample_value *= (
                32767
                * 0.80
                * fade
            )

            sample_value = max(
                -32768,
                min(32767, int(sample_value))
            )

            samples.append(sample_value)
            samples.append(sample_value)

        sound = pygame.mixer.Sound(
            buffer=samples.tobytes()
        )

        return sound

    def _create_timeout_sound(self):
        """
        Generate a short descending sound for timer expiration.
        """
        mixer_info = pygame.mixer.get_init()

        if mixer_info is None:
            raise pygame.error(
                "Pygame mixer is not initialized."
            )

        sample_rate, sample_size, channels = mixer_info

        if sample_size != -16 or channels != 2:
            raise pygame.error(
                "Timeout sound requires 16-bit stereo audio."
            )

        duration = 0.40
        sample_count = int(
            sample_rate * duration
        )

        samples = array("h")

        for i in range(sample_count):
            time_value = i / sample_rate

            progress = i / sample_count

            frequency = (
                360
                - 180 * progress
            )

            fade = 1.0 - progress

            wave = math.sin(
                2
                * math.pi
                * frequency
                * time_value
            )

            harmonic = 0.15 * math.sin(
                2
                * math.pi
                * frequency
                * 2
                * time_value
            )

            sample_value = (
                wave + harmonic
            )

            sample_value *= (
                32767
                * 0.80
                * fade
            )

            sample_value = max(
                -32768,
                min(32767, int(sample_value))
            )

            samples.append(sample_value)
            samples.append(sample_value)

        sound = pygame.mixer.Sound(
            buffer=samples.tobytes()
        )

        return sound

    def _play_sound(self, sound):
        """
        Safely play a Task 4 sound.

        Audio failures never stop the game.
        """
        if sound is None:
            return

        try:
            if pygame.mixer.get_init() is None:
                return

            sound.play()

        except (
            pygame.error,
            OSError,
        ) as error:
            self.audio_error = str(error)

    def _build_maze(self):
        walls = []
        t = 16

        walls.append(Wall(0, 0, self.width, t))
        walls.append(Wall(0, self.height - t, self.width, t))
        walls.append(Wall(0, 0, t, self.height))
        walls.append(Wall(self.width - t, 0, t, self.height))

        walls.append(Wall(0, 140, self.width - 140, t))
        walls.append(Wall(140, 260, self.width - 140, t))
        walls.append(Wall(0, 380, self.width - 140, t))

        return walls

    def handle_event(self, event):
        if event.type == pygame.QUIT:
            self.should_exit = True
            return

        if self.game_over and not self.in_replay_menu:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_RETURN:
                    self.in_replay_menu = True
            return

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
            selected = self.menu_options[
                self.selected_option
            ]

            if selected == "Exit":
                self.should_exit = True
            else:
                self._start_new_game(selected)

    def _start_new_game(self, difficulty):
        settings = self.difficulties[difficulty]

        self.tilt_strength = settings["tilt_strength"]
        self.friction = settings["friction"]
        self.time_limit_ms = settings["time_limit_ms"]

        self.marble.x = self.start_x
        self.marble.y = self.start_y
        self.marble.vx = 0
        self.marble.vy = 0

        self.game_over = False
        self.result = None
        self.finish_time_ms = None
        self.in_replay_menu = False

        self.start_ticks = pygame.time.get_ticks()

    def handle_input(self):
        if self.game_over or self.in_replay_menu:
            return

        mouse_x, mouse_y = pygame.mouse.get_pos()

        dx = mouse_x - self.width // 2
        dy = mouse_y - self.height // 2

        dist = max(
            1,
            (dx ** 2 + dy ** 2) ** 0.5
        )

        ax = (dx / dist) * self.tilt_strength
        ay = (dy / dist) * self.tilt_strength

        self.marble.vx += ax
        self.marble.vy += ay

    def update(self):
        if self.game_over or self.in_replay_menu:
            return

        elapsed = (
            pygame.time.get_ticks()
            - self.start_ticks
        )

        if elapsed >= self.time_limit_ms:
            self.game_over = True
            self.result = "timeout"

            self._play_sound(
                self.timeout_sound
            )

            return

        self.marble.vx *= (
            1 - self.friction
        )

        self.marble.vy *= (
            1 - self.friction
        )

        speed = (
            self.marble.vx ** 2
            + self.marble.vy ** 2
        ) ** 0.5

        if speed > self.max_speed:
            scale = (
                self.max_speed
                / speed
            )

            self.marble.vx *= scale
            self.marble.vy *= scale

        self.marble.x += self.marble.vx
        self.marble.y += self.marble.vy

        self._resolve_wall_collisions()

        gx = self.goal_x - self.marble.x
        gy = self.goal_y - self.marble.y

        if (
            gx ** 2
            + gy ** 2
        ) ** 0.5 <= self.goal_radius:

            self.game_over = True
            self.result = "solved"
            self.finish_time_ms = elapsed

            self._play_sound(
                self.goal_sound
            )

    def _resolve_wall_collisions(self):
        for wall in self.walls:
            wall_rect = wall.rect()

            cx = self.marble.x
            cy = self.marble.y
            radius = self.marble.radius

            closest_x = max(
                wall_rect.left,
                min(cx, wall_rect.right)
            )

            closest_y = max(
                wall_rect.top,
                min(cy, wall_rect.bottom)
            )

            dx = cx - closest_x
            dy = cy - closest_y

            distance_squared = dx * dx + dy * dy

            if distance_squared > radius * radius:
                continue

            if distance_squared == 0:
                left = cx - wall_rect.left
                right = wall_rect.right - cx
                top = cy - wall_rect.top
                bottom = wall_rect.bottom - cy

                min_distance = min(
                    left,
                    right,
                    top,
                    bottom
                )

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

            self.marble.x += normal_x * penetration
            self.marble.y += normal_y * penetration

            velocity_into_wall = (
                self.marble.vx * normal_x
                + self.marble.vy * normal_y
            )

            if velocity_into_wall < 0:
                self.marble.vx -= (
                    1.3
                    * velocity_into_wall
                    * normal_x
                )

                self.marble.vy -= (
                    1.3
                    * velocity_into_wall
                    * normal_y
                )

                self._play_sound(
                    self.bounce_sound
                )

    def render(self, screen):
        screen.fill(DARK)

        if self.in_replay_menu:
            self._render_replay_menu(screen)
            return

        for wall in self.walls:
            pygame.draw.rect(
                screen,
                WALL_COLOR,
                wall.rect()
            )

        pygame.draw.circle(
            screen,
            GOAL_COLOR,
            (
                int(self.goal_x),
                int(self.goal_y)
            ),
            self.goal_radius
        )

        pygame.draw.circle(
            screen,
            WHITE,
            (
                int(self.marble.x),
                int(self.marble.y)
            ),
            self.marble.radius
        )

        if not self.game_over:
            elapsed = (
                pygame.time.get_ticks()
                - self.start_ticks
            )

            remaining = max(
                0,
                (
                    self.time_limit_ms
                    - elapsed
                ) / 1000
            )

            timer_text = self.font.render(
                f"Time: {remaining:.1f}s",
                True,
                WHITE
            )

            screen.blit(
                timer_text,
                (20, 20)
            )

        if self.game_over:
            self._render_game_over(screen)

    def _render_game_over(self, screen):
        overlay = pygame.Surface(
            (self.width, self.height),
            pygame.SRCALPHA
        )

        overlay.fill(
            (0, 0, 0, 180)
        )

        screen.blit(
            overlay,
            (0, 0)
        )

        if self.result == "solved":
            seconds = (
                self.finish_time_ms
                / 1000
            )

            title = self.font.render(
                "Maze Solved!",
                True,
                GOAL_COLOR
            )

            details = self.font.render(
                f"Finish Time: {seconds:.2f}s",
                True,
                WHITE
            )

        else:
            title = self.font.render(
                "Time's Up!",
                True,
                WHITE
            )

            details = self.font.render(
                "You ran out of time.",
                True,
                WHITE
            )

        prompt = self.font.render(
            "Press ENTER to continue",
            True,
            WHITE
        )

        screen.blit(
            title,
            title.get_rect(
                center=(
                    self.width // 2,
                    190
                )
            )
        )

        screen.blit(
            details,
            details.get_rect(
                center=(
                    self.width // 2,
                    235
                )
            )
        )

        screen.blit(
            prompt,
            prompt.get_rect(
                center=(
                    self.width // 2,
                    290
                )
            )
        )

    def _render_replay_menu(self, screen):
        title = self.font.render(
            "Play Again?",
            True,
            WHITE
        )

        screen.blit(
            title,
            title.get_rect(
                center=(
                    self.width // 2,
                    120
                )
            )
        )

        for index, option in enumerate(
            self.menu_options
        ):
            color = (
                SELECTED_COLOR
                if index == self.selected_option
                else WHITE
            )

            text = self.font.render(
                option,
                True,
                color
            )

            screen.blit(
                text,
                text.get_rect(
                    center=(
                        self.width // 2,
                        180 + index * 50
                    )
                )
            )

        instructions = self.font.render(
            "UP/DOWN to select, ENTER to confirm",
            True,
            WHITE
        )

        screen.blit(
            instructions,
            instructions.get_rect(
                center=(
                    self.width // 2,
                    410
                )
            )
        )
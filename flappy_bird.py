import pygame
import json
import os
import random
import math
from typing import List, Dict, Tuple, Optional

class GameObject:
    def __init__(self, x: float, y: float, width: int, height: int):
        self.rect = pygame.Rect(x, y, width, height)
        self.x = float(x)
        self.y = float(y)
        self.width = width
        self.height = height

    def draw(self, screen: pygame.Surface, image: Optional[pygame.Surface] = None):
        if image:
            screen.blit(image, self.rect)
        else:
            # Base column color (sandy/marble color)
            pygame.draw.rect(screen, (225, 210, 180), self.rect)
            
            # Add column details
            pillar_width = self.rect.width
            segment_height = 20
            
            # Draw top capital
            if self.rect.height > segment_height:
                capital_rect = pygame.Rect(self.rect.x, self.rect.y, pillar_width, segment_height)
                pygame.draw.rect(screen, (200, 180, 150), capital_rect)
                pygame.draw.line(screen, (180, 160, 130), 
                               (self.rect.x, self.rect.y + segment_height),
                               (self.rect.x + pillar_width, self.rect.y + segment_height),
                               3)
            
            # Draw base
            if self.rect.height > segment_height:
                base_rect = pygame.Rect(self.rect.x, self.rect.bottom - segment_height, 
                                      pillar_width, segment_height)
                pygame.draw.rect(screen, (200, 180, 150), base_rect)
                pygame.draw.line(screen, (180, 160, 130),
                               (self.rect.x, self.rect.bottom - segment_height),
                               (self.rect.x + pillar_width, self.rect.bottom - segment_height),
                               3)
            
            # Draw vertical grooves
            groove_count = 3
            for i in range(groove_count):
                x = self.rect.x + (i + 1) * pillar_width/(groove_count + 1)
                pygame.draw.line(screen, (200, 180, 150),
                               (x, self.rect.y + segment_height),
                               (x, self.rect.bottom - segment_height),
                               2)

class Player(GameObject):
    def __init__(self, x: float, y: float, config: Dict):
        super().__init__(x, y, config['width'], config['height'])
        self.velocity = 0
        self.gravity = config['gravity']
        self.flap_strength = config['flap_strength']
        self.max_velocity = config['max_velocity']

    def update(self):
        self.velocity = min(self.velocity + self.gravity, self.max_velocity)
        self.y += self.velocity
        self.rect.y = int(self.y)

    def flap(self):
        self.velocity = self.flap_strength

class Wall(GameObject):
    def __init__(self, x: float, y: float, width: int, height: int, speed: float):
        super().__init__(x, y, width, height)
        self.speed = speed

    def update(self):
        self.x -= self.speed
        self.rect.x = int(self.x)

class Projectile(GameObject):
    def __init__(self, x: float, y: float, speed: float):
        super().__init__(x, y, 20, 10)  # Small projectile size
        self.speed = speed
    
    def update(self):
        self.x += self.speed
        self.rect.x = int(self.x)
    
    def draw(self, screen: pygame.Surface):
        # Draw a golden projectile
        pygame.draw.ellipse(screen, (255, 215, 0), self.rect)  # Gold color

class Enemy(GameObject):
    def __init__(self, x: float, y: float, config: Dict, speed_multiplier: float):
        super().__init__(x, y, config['width'], config['height'])
        self.speed = config['speed'] * speed_multiplier
        self.direction = random.choice([-1, 1])
        self.amplitude = 100
        self.original_y = y
        self.time = random.random() * 10

    def update(self):
        self.x -= self.speed
        self.time += 0.05
        self.y = self.original_y + self.amplitude * math.sin(self.time)
        self.rect.x = int(self.x)
        self.rect.y = int(self.y)

class FlappyBird:
    def __init__(self):
        pygame.init()
        pygame.mixer.init()
        
        # Load configuration
        with open('levels.json', 'r') as f:
            self.config = json.load(f)

        # Set up display
        self.width = self.config['window']['width']
        self.height = self.config['window']['height']
        self.screen = pygame.display.set_mode((self.width, self.height))
        pygame.display.set_caption(self.config['window']['title'])
        self.clock = pygame.time.Clock()
        self.fps = self.config['window']['fps']

        # Game state
        self.current_level = 0
        self.score = 0
        self.high_score = self.load_high_score()
        self.game_state = "START"  # START, PLAYING, GAME_OVER
        
        # Background scrolling
        self.bg_scroll = 0
        self.bg_scroll_speed = self.config['walls']['speed']  # Match wall speed
        
        # Projectile system
        self.projectiles: List[Projectile] = []
        self.last_shot = 0
        self.shot_cooldown = 500  # Milliseconds between shots

        # Load assets
        self.load_assets()

        # Initialize game objects
        self.reset_game()

    def load_assets(self):
        level_data = self.config['levels'][self.current_level]
        
        # Load and scale images
        self.background = pygame.image.load(level_data['assets']['map']).convert()
        self.background = pygame.transform.scale(self.background, (self.width, self.height))
        
        # Create mirrored background
        self.background_flipped = pygame.transform.flip(self.background, True, False)
        
        self.player_img = pygame.image.load(level_data['assets']['player']).convert_alpha()
        self.player_img = pygame.transform.scale(self.player_img, 
                                               (self.config['player']['width'], 
                                                self.config['player']['height']))
        
        self.enemy_img = pygame.image.load(level_data['assets']['enemy']).convert_alpha()
        self.enemy_img = pygame.transform.scale(self.enemy_img,
                                              (self.config['enemies']['width'],
                                               self.config['enemies']['height']))

        # Load sounds with error handling
        self.sounds = {}
        try:
            # Set default volume for sound effects
            sound_volume = 0.5  # 50% volume
            
            # Load and configure each sound effect
            self.sounds['flap'] = pygame.mixer.Sound(level_data['assets']['sounds']['flap'])
            self.sounds['flap'].set_volume(sound_volume)
            
            self.sounds['enemy'] = pygame.mixer.Sound(level_data['assets']['sounds']['enemy'])
            self.sounds['enemy'].set_volume(sound_volume)
            
            self.sounds['gameover'] = pygame.mixer.Sound(level_data['assets']['sounds']['gameover'])
            self.sounds['gameover'].set_volume(sound_volume)
            
            print("Successfully loaded all sound effects!")
            
            # Load and play background music
            pygame.mixer.music.load(level_data['assets']['sounds']['background'])
            pygame.mixer.music.set_volume(0.3)  # Set background music to 30% volume
            pygame.mixer.music.play(-1)
            print("Successfully loaded and started background music!")
            
        except Exception as e:
            print(f"Error loading sounds: {str(e)}")
            # Initialize empty sounds to prevent crashes if sound loading fails
            for sound_name in ['flap', 'enemy', 'gameover']:
                self.sounds[sound_name] = pygame.mixer.Sound(buffer=bytes(32))  # Empty sound

    def load_high_score(self) -> int:
        try:
            with open('highscore.txt', 'r') as f:
                return int(f.read())
        except FileNotFoundError:
            return 0

    def save_high_score(self):
        with open('highscore.txt', 'w') as f:
            f.write(str(self.high_score))

    def reset_game(self):
        level_data = self.config['levels'][self.current_level]
        
        # Initialize player
        self.player = Player(self.width // 4, self.height // 2,
                           self.config['player'])
        
        # Initialize walls and enemies
        self.walls: List[Wall] = []
        self.enemies: List[Enemy] = []
        self.projectiles: List[Projectile] = []
        self.last_wall = 0  # Set to 0 to spawn first wall immediately
        self.last_enemy = pygame.time.get_ticks()
        self.last_shot = pygame.time.get_ticks()
        
        # Create initial wall
        self.create_wall_pair()
        
        # Reset score
        self.score = 0
        
    def shoot_projectile(self):
        current_time = pygame.time.get_ticks()
        if current_time - self.last_shot > self.shot_cooldown:
            # Create projectile at bird's position
            projectile = Projectile(self.player.rect.right, 
                                  self.player.rect.centery, 
                                  10)  # Speed of 10
            self.projectiles.append(projectile)
            self.last_shot = current_time

    def create_wall_pair(self):
        level_data = self.config['levels'][self.current_level]
        wall_config = self.config['walls']
        
        gap_y = random.randint(wall_config['gap'], self.height - wall_config['gap'])
        wall_speed = wall_config['speed'] * level_data['wall_speed_multiplier']
        
        # Create top and bottom walls
        top_wall = Wall(self.width, 0, wall_config['width'],
                       gap_y - wall_config['gap'] // 2, wall_speed)
        bottom_wall = Wall(self.width, gap_y + wall_config['gap'] // 2,
                         wall_config['width'],
                         self.height - (gap_y + wall_config['gap'] // 2),
                         wall_speed)
        
        self.walls.extend([top_wall, bottom_wall])

    def spawn_enemy(self):
        level_data = self.config['levels'][self.current_level]
        enemy_config = self.config['enemies']
        
        y = random.randint(enemy_config['height'],
                          self.height - enemy_config['height'])
        enemy = Enemy(self.width, y, enemy_config,
                     level_data['enemy_speed_multiplier'])
        self.enemies.append(enemy)

    def check_collisions(self) -> bool:
        # Check wall collisions
        for wall in self.walls:
            if self.player.rect.colliderect(wall.rect):
                return True

        # Check enemy collisions
        for enemy in self.enemies:
            if self.player.rect.colliderect(enemy.rect):
                self.sounds['enemy'].play()
                return True

        # Check screen boundaries
        if self.player.rect.top <= 0 or self.player.rect.bottom >= self.height:
            return True

        return False

    def update_game_objects(self):
        # Update player
        self.player.update()

        # Update and clean up walls
        for wall in self.walls[:]:
            wall.update()
            if wall.rect.right < 0:
                self.walls.remove(wall)
                self.score += 0.5  # 0.5 for each wall (top/bottom pair = 1 point)

        # Update and clean up enemies
        for enemy in self.enemies[:]:
            enemy.update()
            if enemy.rect.right < 0:
                self.enemies.remove(enemy)

        # Update and clean up projectiles
        for projectile in self.projectiles[:]:
            projectile.update()
            # Remove projectiles that are off screen
            if projectile.rect.left > self.width:
                self.projectiles.remove(projectile)
            else:
                # Check for collisions with enemies
                for enemy in self.enemies[:]:
                    if projectile.rect.colliderect(enemy.rect):
                        self.enemies.remove(enemy)
                        self.projectiles.remove(projectile)
                        self.score += 2  # Bonus points for killing an enemy
                        break

        # Spawn new walls
        level_data = self.config['levels'][self.current_level]
        current_time = pygame.time.get_ticks()
        if current_time - self.last_wall > level_data['wall_frequency']:
            self.create_wall_pair()
            self.last_wall = current_time

        # Spawn new enemies
        if current_time - self.last_enemy > self.config['enemies']['spawn_rate']:
            if len(self.enemies) < level_data['enemy_count']:
                self.spawn_enemy()
                self.last_enemy = current_time

    def draw_scrolling_background(self):
        # Calculate how many background images we need to fill the screen
        bg_width = self.background.get_width()
        tiles = math.ceil(self.width / bg_width) + 2  # Add extra tile for smoother transition
        
        # Calculate the first tile index based on scroll position
        first_tile = math.floor(self.bg_scroll / bg_width)
        
        # Draw the background tiles
        for i in range(tiles):
            current_tile = first_tile + i
            x_pos = i * bg_width - (self.bg_scroll % bg_width)
            
            # Alternate between regular and flipped background
            if current_tile % 2 == 0:
                self.screen.blit(self.background, (x_pos, 0))
            else:
                self.screen.blit(self.background_flipped, (x_pos, 0))
        
        # Update scroll position
        if self.game_state == "PLAYING":
            self.bg_scroll = (self.bg_scroll + self.bg_scroll_speed)

    def draw_game_objects(self):
        # Draw scrolling background
        self.draw_scrolling_background()

        # Draw walls
        for wall in self.walls:
            wall.draw(self.screen)

        # Draw enemies
        for enemy in self.enemies:
            enemy.draw(self.screen, self.enemy_img)

        # Draw projectiles
        for projectile in self.projectiles:
            projectile.draw(self.screen)

        # Draw player
        self.player.draw(self.screen, self.player_img)

        # Draw score
        font = pygame.font.Font(None, 36)
        score_text = font.render(f'Score: {int(self.score)}', True, (255, 255, 255))
        high_score_text = font.render(f'High Score: {self.high_score}', True, (255, 255, 255))
        self.screen.blit(score_text, (10, 10))
        self.screen.blit(high_score_text, (10, 50))

    def create_button(self, text, font_size, y_position):
        font = pygame.font.Font(None, font_size)
        text_surface = font.render(text, True, (255, 255, 255))
        text_rect = text_surface.get_rect(center=(self.width // 2, y_position))
        
        # Create button background
        padding = 20
        button_rect = pygame.Rect(text_rect.x - padding,
                                text_rect.y - padding,
                                text_rect.width + 2 * padding,
                                text_rect.height + 2 * padding)
        button_rect.centerx = self.width // 2
        
        return text_surface, text_rect, button_rect

    def draw_start_screen(self):
        self.draw_scrolling_background()
        
        # Draw title
        font_large = pygame.font.Font(None, 64)
        font_medium = pygame.font.Font(None, 36)
        
        title = font_large.render('Flappy Bird Adventure', True, (255, 255, 255))
        title_rect = title.get_rect(center=(self.width // 2, self.height // 4))
        self.screen.blit(title, title_rect)
        
        # Create and draw start button
        start_text, text_rect, button_rect = self.create_button("Start Game", 48, self.height // 2)
        
        # Draw button with Roman-style decoration
        pygame.draw.rect(self.screen, (200, 180, 150), button_rect)  # Base color
        pygame.draw.rect(self.screen, (180, 160, 130), button_rect, 3)  # Border
        
        # Add decorative corners
        corner_size = 10
        for corner in [(button_rect.topleft, (1, 1)), 
                      (button_rect.topright, (-1, 1)),
                      (button_rect.bottomleft, (1, -1)), 
                      (button_rect.bottomright, (-1, -1))]:
            pos, direction = corner
            pygame.draw.line(self.screen, (180, 160, 130),
                           (pos[0], pos[1]),
                           (pos[0] + corner_size * direction[0], pos[1]),
                           3)
            pygame.draw.line(self.screen, (180, 160, 130),
                           (pos[0], pos[1]),
                           (pos[0], pos[1] + corner_size * direction[1]),
                           3)
        
        self.screen.blit(start_text, text_rect)
        
        # Store button rect for click detection
        self.start_button_rect = button_rect
        
        # Draw instructions
        instructions = [
            "How to Play:",
            "• Press SPACE to flap and fly",
            "• Navigate through the Roman columns",
            "• Press RIGHT ARROW or LEFT CLICK to attack enemies",
            "• Destroy enemies for bonus points",
            "• Avoid collisions with columns and enemies"
        ]
        
        y_offset = self.height * 2 // 3  # Start position for instructions
        for instruction in instructions:
            if instruction == "How to Play:":
                # Make the header stand out with a different color and bold effect
                header_color = (220, 20, 60)  # Crimson red - more visible
                # Draw the text twice with slight offset for bold effect
                text = font_medium.render(instruction, True, header_color)
                text_rect = text.get_rect(center=(self.width // 2, y_offset))
                # Draw shadow/outline
                shadow_offset = 2
                shadow_text = font_medium.render(instruction, True, (0, 0, 0))  # Black shadow
                shadow_rect = text_rect.copy()
                shadow_rect.x -= shadow_offset
                shadow_rect.y -= shadow_offset
                self.screen.blit(shadow_text, shadow_rect)
                # Draw main text
                self.screen.blit(text, text_rect)
            else:
                # Instructions in bright white
                text = font_medium.render(instruction, True, (255, 255, 255))
                text_rect = text.get_rect(center=(self.width // 2, y_offset))
                self.screen.blit(text, text_rect)
            y_offset += 35  # Space between lines

    def draw_game_over_screen(self):
        font = pygame.font.Font(None, 64)
        game_over_text = font.render('Game Over', True, (255, 255, 255))
        restart_text = font.render('Press SPACE to Restart', True, (255, 255, 255))
        score_text = font.render(f'Score: {int(self.score)}', True, (255, 255, 255))
        
        game_over_rect = game_over_text.get_rect(center=(self.width // 2, self.height // 3))
        restart_rect = restart_text.get_rect(center=(self.width // 2, self.height // 2))
        score_rect = score_text.get_rect(center=(self.width // 2, 2 * self.height // 3))
        
        self.screen.blit(game_over_text, game_over_rect)
        self.screen.blit(restart_text, restart_rect)
        self.screen.blit(score_text, score_rect)

    def run(self):
        running = True
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    if event.button == 1:  # Left click
                        if self.game_state == "START" and hasattr(self, 'start_button_rect'):
                            # Check if click is within button bounds
                            if self.start_button_rect.collidepoint(event.pos):
                                self.game_state = "PLAYING"
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    if event.button == 1:  # Left click
                        if self.game_state == "START" and hasattr(self, 'start_button_rect'):
                            if self.start_button_rect.collidepoint(event.pos):
                                self.game_state = "PLAYING"
                        elif self.game_state == "PLAYING":
                            self.shoot_projectile()
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_SPACE:
                        if self.game_state == "PLAYING":
                            self.player.flap()
                            self.sounds['flap'].play()
                        elif self.game_state == "GAME_OVER":
                            self.reset_game()
                            self.game_state = "PLAYING"
                    elif event.key == pygame.K_RIGHT and self.game_state == "PLAYING":
                        self.shoot_projectile()

            if self.game_state == "PLAYING":
                self.update_game_objects()
                
                if self.check_collisions():
                    self.sounds['gameover'].play()
                    if self.score > self.high_score:
                        self.high_score = int(self.score)
                        self.save_high_score()
                    self.game_state = "GAME_OVER"

            # Draw current game state
            if self.game_state == "START":
                self.draw_start_screen()
            elif self.game_state == "PLAYING":
                self.draw_game_objects()
            elif self.game_state == "GAME_OVER":
                self.draw_game_over_screen()

            pygame.display.flip()
            self.clock.tick(self.fps)

        pygame.quit()

if __name__ == "__main__":
    game = FlappyBird()
    game.run()

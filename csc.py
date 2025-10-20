import pygame, sys, random, os
import math

# --- Config ---
WIDTH, HEIGHT = 900, 700
FPS = 60

# Initialize pygame mixer for sound
pygame.mixer.init()

pygame.init()
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Crystal Slime Chronicles")
clock = pygame.time.Clock()

# Load assets (fallback surfaces if not found)
def load_image(name, size=None, flip_x=False):
    if os.path.exists(name):
        img = pygame.image.load(name).convert_alpha()
        if flip_x:
            img = pygame.transform.flip(img, True, False)
        if size:
            img = pygame.transform.scale(img, size)
        return img
    surf = pygame.Surface(size if size else (40,40), pygame.SRCALPHA)
    surf.fill((0,0,0,0))
    pygame.draw.rect(surf, (200,200,200), surf.get_rect())
    return surf

def load_sound(name):
    """Load a sound file with fallback"""
    if os.path.exists(name):
        return pygame.mixer.Sound(name)
    # Return a silent sound if file not found
    return pygame.mixer.Sound(buffer=bytearray())

# Load images with different facing directions
player_img_right = load_image("player.png", (60,60), flip_x=False)
player_img_left = load_image("player.png", (60,60), flip_x=True)
enemy_img_right = load_image("enemy.png", (50,50), flip_x=False)
enemy_img_left = load_image("enemy.png", (50,50), flip_x=True)
boss_img = load_image("boss.png", (200,200))
miniboss_img = load_image("miniboss.png", (160,160))

# Load background images
background_img = load_image("background.jpg", (WIDTH, HEIGHT))
menu_background_img = load_image("menu_background.jpg", (WIDTH, HEIGHT))
# If background images don't exist, create solid color backgrounds
if background_img.get_size() != (WIDTH, HEIGHT):
    background_img = pygame.Surface((WIDTH, HEIGHT))
    background_img.fill((20, 20, 30))
if menu_background_img.get_size() != (WIDTH, HEIGHT):
    menu_background_img = pygame.Surface((WIDTH, HEIGHT))
    menu_background_img.fill((10, 10, 20))

# Load title and victory images
title_img = load_image("title.png", (400, 100))  # Smaller size to fit
victory_img = load_image("victory.png", (300, 80))

# Load sounds
shoot_sound = load_sound("shoot.wav")
explosion_sound = load_sound("explosion.wav")
powerup_sound = load_sound("powerup.wav")
hurt_sound = load_sound("hurt.wav")
boss_music = load_sound("boss_music.wav")
victory_sound = load_sound("victory.wav")
gameover_sound = load_sound("gameover.wav")

# Set volume levels
shoot_sound.set_volume(0.3)
explosion_sound.set_volume(0.4)
powerup_sound.set_volume(0.5)
hurt_sound.set_volume(0.4)

# Load background music
def play_background_music():
    """Play background music if available"""
    try:
        if os.path.exists("background_music.mp3"):
            pygame.mixer.music.load("background_music.mp3")
            pygame.mixer.music.set_volume(0.3)
            pygame.mixer.music.play(-1)  # Loop indefinitely
    except:
        pass  # Skip if music file not found or format not supported

def stop_background_music():
    """Stop background music"""
    pygame.mixer.music.stop()

def play_boss_music():
    """Play boss music and stop background music"""
    stop_background_music()
    try:
        boss_music.play(-1)  # ✅ loop boss music
    except:
        pass

def stop_boss_music():
    """Stop boss music"""
    try:
        boss_music.stop()
    except:
        pass

# --- Utility: draw simple icons when assets missing ---
def make_health_icon(size=20):
    surf = pygame.Surface((size,size), pygame.SRCALPHA)
    pygame.draw.ellipse(surf, (0,180,0), (0,0,size,size))  # green circle
    pygame.draw.rect(surf, (255,255,255), (size*0.35, size*0.15, size*0.3, size*0.2))  # neck
    pygame.draw.line(surf, (255,255,255), (size*0.25,size*0.55),(size*0.75,size*0.55),2)  # cross horiz
    pygame.draw.line(surf, (255,255,255), (size*0.5,size*0.35),(size*0.5,size*0.75),2)  # cross vert
    return surf

def make_speed_icon(size=20):
    surf = pygame.Surface((size,size), pygame.SRCALPHA)
    # draw simple boot-ish shape
    pts = [(size*0.1,size*0.7),(size*0.2,size*0.4),(size*0.6,size*0.3),(size*0.8,size*0.5),(size*0.7,size*0.8)]
    pygame.draw.polygon(surf, (30,144,255), pts)
    pygame.draw.polygon(surf, (200,200,200), pts, 2)
    return surf

health_icon_img = make_health_icon(20)
speed_icon_img = make_speed_icon(20)

# --- Classes ---
class Player(pygame.sprite.Sprite):
    def __init__(self):
        super().__init__()
        self.image = player_img_right  # Default facing right
        self.rect = self.image.get_rect(center=(WIDTH//2, HEIGHT//2))
        self.pos = pygame.Vector2(self.rect.center)
        self.base_speed = 5
        self.speed = self.base_speed
        self.hp = 10
        self.max_hp = 10
        self.last_dir = pygame.Vector2(1,0)  # Default facing right
        self.facing_right = True
        self.skill_cooldown = 0  # frames until ready
        self.speed_end_time = 0  # pygame.time.get_ticks() when speed boost ends
        self.invincible_end_time = 0  # time when invisibility ends
        self.knockback_timer = 0  # For knockback effect
        self.damage_cooldown = 0  # Prevents rapid damage
        
        # New power-up attributes
        self.double_shot = False
        self.scatter_shot = False
        self.bullet_base_speed = 10

    def update(self, keys):
        # Handle knockback first
        if self.knockback_timer > 0:
            self.knockback_timer -= 1
            return  # Skip normal movement during knockback
            
        # Handle damage cooldown
        if self.damage_cooldown > 0:
            self.damage_cooldown -= 1
            
        move = pygame.Vector2(0,0)
        moved = False
        
        if keys[pygame.K_UP] or keys[pygame.K_w]: 
            move.y -= 1
            moved = True
        if keys[pygame.K_DOWN] or keys[pygame.K_s]: 
            move.y += 1
            moved = True
        if keys[pygame.K_LEFT] or keys[pygame.K_a]: 
            move.x -= 1
            self.last_dir = pygame.Vector2(-1,0)
            if self.facing_right:  # Changed direction
                self.facing_right = False
                self.image = player_img_left
            moved = True
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]: 
            move.x += 1
            self.last_dir = pygame.Vector2(1,0)
            if not self.facing_right:  # Changed direction
                self.facing_right = True
                self.image = player_img_right
            moved = True
            
        if moved and move.length_squared()>0:
            move = move.normalize()
            self.pos += move*self.speed
            self.pos.x = max(20, min(WIDTH-20, self.pos.x))
            self.pos.y = max(20, min(HEIGHT-20, self.pos.y))
            self.rect.center = self.pos
            
        if self.skill_cooldown>0:
            self.skill_cooldown -= 1
        # check speed boost expiry
        if self.speed > self.base_speed and pygame.time.get_ticks() > self.speed_end_time:
            self.speed = self.base_speed

    def apply_knockback(self, direction, strength=10, duration=15):
        """Apply knockback effect to player"""
        if self.knockback_timer <= 0:  # Only apply if not already in knockback
            self.pos += direction.normalize() * strength
            self.knockback_timer = duration
            # Ensure player stays on screen
            self.pos.x = max(20, min(WIDTH-20, self.pos.x))
            self.pos.y = max(20, min(HEIGHT-20, self.pos.y))
            self.rect.center = self.pos

    def take_damage(self, amount=1):
        """Take damage with cooldown to prevent rapid damage"""
        if self.damage_cooldown <= 0 and self.hp > 0:
            self.hp = max(0, self.hp - amount)
            self.damage_cooldown = 30  # 0.5 seconds cooldown
            hurt_sound.play()
            return True
        return False

    def shoot(self, bullets_group, enemies_group, miniboss_group, boss_group):
        bullet_speed = self.bullet_base_speed
        
        # Auto-aim: prioritize enemies, then miniboss, then boss
        targets = list(enemies_group) + list(miniboss_group) + list(boss_group)
        
        if not targets:
            # If no targets, aim in last direction
            if self.scatter_shot:
                self.fire_scatter_shot(bullets_group, bullet_speed, self.last_dir)
            elif self.double_shot:
                # Shoot two bullets slightly spread
                angle1 = self.last_dir.rotate(-5)
                angle2 = self.last_dir.rotate(5)
                bullets_group.add(Bullet(self.rect.center, angle1, bullet_speed))
                bullets_group.add(Bullet(self.rect.center, angle2, bullet_speed))
            else:
                bullets_group.add(Bullet(self.rect.center, self.last_dir, bullet_speed))
            shoot_sound.play()
            return
            
        # Find nearest target
        nearest = min(targets, key=lambda e: (e.rect.centerx-self.rect.centerx)**2+(e.rect.centery-self.rect.centery)**2)
        dirv = pygame.Vector2(nearest.rect.center)-pygame.Vector2(self.rect.center)
        if dirv.length_squared()>0:
            self.last_dir = dirv.normalize()
            # Update facing direction based on shooting direction
            if self.last_dir.x < 0 and self.facing_right:
                self.facing_right = False
                self.image = player_img_left
            elif self.last_dir.x > 0 and not self.facing_right:
                self.facing_right = True
                self.image = player_img_right
            
        if self.scatter_shot:
            self.fire_scatter_shot(bullets_group, bullet_speed, self.last_dir)
        elif self.double_shot:
            # Shoot two bullets slightly spread
            angle1 = self.last_dir.rotate(-5)
            angle2 = self.last_dir.rotate(5)
            bullets_group.add(Bullet(self.rect.center, angle1, bullet_speed))
            bullets_group.add(Bullet(self.rect.center, angle2, bullet_speed))
        else:
            bullets_group.add(Bullet(self.rect.center, self.last_dir, bullet_speed))
        shoot_sound.play()

    def fire_scatter_shot(self, bullets_group, bullet_speed, base_direction):
        """Fire 5 bullets in a wide arc from different positions around player"""
        # Define firing positions relative to player
        positions = [
            self.rect.center,  # Center
            (self.rect.centerx - 15, self.rect.centery - 15),  # Top-left
            (self.rect.centerx + 15, self.rect.centery - 15),  # Top-right
            (self.rect.centerx - 15, self.rect.centery + 15),  # Bottom-left
            (self.rect.centerx + 15, self.rect.centery + 15)   # Bottom-right
        ]
        
        # Define angles for scatter pattern (-30 to +30 degrees)
        angles = [-30, -15, 0, 15, 30]
        
        for pos, angle in zip(positions, angles):
            direction = base_direction.rotate(angle)
            bullets_group.add(Bullet(pos, direction, bullet_speed))

    def use_skill(self,enemies_group,enemy_bullets_group,miniboss_group,miniboss_bullets_group,boss_group,boss_bullets_group):
        if self.skill_cooldown==0:
            # clear enemies and bullets
            for e in enemies_group: e.kill()
            for b in enemy_bullets_group: b.kill()
            for mbb in miniboss_bullets_group: mbb.kill()
            for bb in boss_bullets_group: bb.kill()
            # miniboss and boss take damage
            for mb in miniboss_group:
                mb.hp -= 10  # More damage to miniboss
                if mb.hp<=0:
                    mb.kill()
            for boss in boss_group:
                boss.hp -= 10  # More damage to boss
                if boss.hp<=0:
                    boss.kill()
            self.skill_cooldown = FPS*12  # 12 sec cooldown
            explosion_sound.play()

    def apply_speed_boost(self, duration_ms=3000):
        self.speed = self.base_speed * 2
        self.speed_end_time = pygame.time.get_ticks() + duration_ms
        self.invincible_end_time = pygame.time.get_ticks() + duration_ms
        
    def apply_power_up(self, power_type):
        """Apply permanent power-up"""
        if power_type == "double_shot":
            self.double_shot = True
        elif power_type == "scatter_shot":
            self.scatter_shot = True
        powerup_sound.play()

class Bullet(pygame.sprite.Sprite):
    def __init__(self,pos,dirv,speed=10):
        super().__init__()
        self.image = pygame.Surface((8,8), pygame.SRCALPHA); pygame.draw.circle(self.image, (255,255,255), (4,4), 4)
        self.rect = self.image.get_rect(center=pos)
        self.pos = pygame.Vector2(pos); self.dir = dirv; self.speed=speed
    def update(self):
        self.pos += self.dir*self.speed
        self.rect.center=self.pos
        if not screen.get_rect().colliderect(self.rect): self.kill()

class Enemy(pygame.sprite.Sprite):
    def __init__(self, stationary=False):
        super().__init__()
        self.image = enemy_img_right  # Default facing right
        self.rect = self.image.get_rect()
        side=random.choice(['top','bottom','left','right'])
        if side=='top': self.rect.center=(random.randint(0,WIDTH),0)
        elif side=='bottom': self.rect.center=(random.randint(0,WIDTH),HEIGHT)
        elif side=='left': self.rect.center=(0,random.randint(0,HEIGHT))
        else: self.rect.center=(WIDTH,random.randint(0,HEIGHT))
        self.pos=pygame.Vector2(self.rect.center)
        self.speed=2
        self.hp=3
        self.shoot_timer=0
        self.explodes_on_death = False
        self.stationary = stationary
        self.area_center = self.pos.copy() if stationary else None
        self.wander_radius = 100 if stationary else 0
        self.facing_right = True
        
    def update(self, player_pos, enemy_bullets_group, shooting_enabled):
        # Update facing direction based on movement
        old_pos = self.pos.copy()
        
        if not self.stationary:
            # Normal chasing behavior
            direction=(player_pos-self.pos)
            if direction.length()>0: 
                direction=direction.normalize()
                # Update facing direction
                if direction.x < 0 and self.facing_right:
                    self.facing_right = False
                    self.image = enemy_img_left
                elif direction.x > 0 and not self.facing_right:
                    self.facing_right = True
                    self.image = enemy_img_right
                    
            self.pos+=direction*self.speed
        else:
            # Stationary enemy - wander around spawn area
            if self.area_center:
                # Move randomly within wander radius
                wander = pygame.Vector2(random.uniform(-1, 1), random.uniform(-1, 1))
                if wander.length() > 0:
                    wander = wander.normalize()
                    # Update facing direction
                    if wander.x < 0 and self.facing_right:
                        self.facing_right = False
                        self.image = enemy_img_left
                    elif wander.x > 0 and not self.facing_right:
                        self.facing_right = True
                        self.image = enemy_img_right
                        
                self.pos += wander * self.speed * 0.3
                
                # Stay within wander radius
                dist_from_center = (self.pos - self.area_center).length()
                if dist_from_center > self.wander_radius:
                    # Move back toward center
                    back_dir = (self.area_center - self.pos)
                    if back_dir.length() > 0:
                        back_dir = back_dir.normalize()
                    self.pos += back_dir * self.speed * 0.5
        
        self.rect.center=self.pos
        
        # Shooting behavior (sonic waves)
        if shooting_enabled:
            self.shoot_timer+=1
            if self.shoot_timer>90:  # Shoot every 1.5 seconds
                self.shoot_timer=0
                base=(pygame.Vector2(player_pos)-self.pos)
                if base.length()>0: 
                    base=base.normalize()
                    # Update facing direction based on shooting
                    if base.x < 0 and self.facing_right:
                        self.facing_right = False
                        self.image = enemy_img_left
                    elif base.x > 0 and not self.facing_right:
                        self.facing_right = True
                        self.image = enemy_img_right
                else: 
                    base=pygame.Vector2(0,1)
                enemy_bullets_group.add(SonicWave(self.rect.center, base))

class SonicWave(pygame.sprite.Sprite):
    def __init__(self,pos,dirv):
        super().__init__()
        self.image=pygame.Surface((12,12), pygame.SRCALPHA)
        pygame.draw.circle(self.image,(0,200,255),(6,6),6)  # Blue sonic wave
        pygame.draw.circle(self.image,(100,255,255),(6,6),3)  # Inner circle
        self.rect=self.image.get_rect(center=pos)
        self.pos=pygame.Vector2(pos); self.dir=dirv; self.speed=4
        self.damage = 1  # Sonic waves now deal damage
    def update(self):
        self.pos+=self.dir*self.speed
        self.rect.center=self.pos
        if not screen.get_rect().colliderect(self.rect): self.kill()

# New explosion effect that creates sonic waves
class SonicExplosion(pygame.sprite.Sprite):
    def __init__(self, pos, radius=60, wave_count=6):
        super().__init__()
        self.damage = 1  # SonicExplosion deals less damage
        self.pos = pygame.Vector2(pos)
        self.radius = radius
        self.lifetime = 30  # frames
        self.timer = 0
        self.wave_count = wave_count
        self.waves_created = False
        self.image = pygame.Surface((radius*2, radius*2), pygame.SRCALPHA)
        self.rect = self.image.get_rect(center=pos)
        self.update_image()
        
    def update_image(self):
        self.image.fill((0,0,0,0))
        progress = self.timer / self.lifetime
        current_radius = int(self.radius * progress)
        color = (0, 150, 255, 200 - int(200 * progress))  # Blue explosion
        pygame.draw.circle(self.image, color, (self.radius, self.radius), current_radius)
        
    def update(self):
        self.timer += 1
        
        # Create sonic waves once at the start
        if not self.waves_created and self.timer > 2:
            self.create_sonic_waves()
            self.waves_created = True
            
        self.update_image()
        if self.timer >= self.lifetime:
            self.kill()
    
    def create_sonic_waves(self):
        for i in range(self.wave_count):
            angle = i * (360 / self.wave_count)
            direction = pygame.Vector2(1, 0).rotate(angle)
            sonic_bullets_group.add(SonicWave(self.pos, direction))

class MiniBoss(pygame.sprite.Sprite):
    def __init__(self):
        super().__init__()
        self.image=miniboss_img
        self.rect=self.image.get_rect(center=(WIDTH//2,100))
        self.pos=pygame.Vector2(self.rect.center)
        self.speed=2
        self.hp=200  # Increased HP
        self.max_hp = 200
        self.shoot_timer=0
        self.bomb_timer=0
        
    def update(self, player_pos, miniboss_bullets_group):
        dirv=(player_pos-self.pos)
        if dirv.length()>0: dirv=dirv.normalize()
        self.pos+=dirv*self.speed*0.5
        self.pos.x=max(50,min(WIDTH-50,self.pos.x))
        self.pos.y=max(50,min(HEIGHT-50,self.pos.y))
        self.rect.center=self.pos
        
        self.shoot_timer+=1
        self.bomb_timer+=1
        
        # Shoot lines in all directions
        if self.shoot_timer>120:  # Every 2 seconds
            self.shoot_timer=0
            for angle in range(0, 360, 45):  # 8 directions
                direction = pygame.Vector2(1, 0).rotate(angle)
                miniboss_bullets_group.add(SonicWave(self.rect.center, direction))
        
        # Summon bombs
        if self.bomb_timer>180:  # Every 3 seconds
            self.bomb_timer=0
            # Create 2-3 bombs at random positions
            for _ in range(random.randint(2, 3)):
                bomb_pos = (random.randint(100, WIDTH-100), random.randint(100, HEIGHT-100))
                bombs_group.add(Bomb(bomb_pos))

class Boss(pygame.sprite.Sprite):
    def __init__(self):
        super().__init__()
        self.image=boss_img
        self.rect=self.image.get_rect(center=(WIDTH//2,80))
        self.pos=pygame.Vector2(self.rect.center)
        self.hp=700  
        self.max_hp = 700
        self.state="intro"
        self.attack_phase = 1
        self.timer=0
        self.attack_timer=0
        self.exploding_bullets = []
        self.summon_timer = 0
        self.bomb_timer = 0
        self.original_pos = pygame.Vector2(WIDTH//2, 80)
        
    def update(self,player_pos,boss_bullets_group, enemies_group):
        current_time = pygame.time.get_ticks()
        
        # Phase transition when HP is half
        if self.hp <= self.max_hp // 2 and self.attack_phase == 1:
            self.attack_phase = 2
            self.state = "phase2_idle"
            self.timer = 0
        
        if self.attack_phase == 1:
            self.update_phase1(player_pos, boss_bullets_group)
        else:
            self.update_phase2(player_pos, boss_bullets_group, enemies_group)
            
        self.rect.center=self.pos
        
        # Check for bullet explosions
        for bullet, explosion_time in self.exploding_bullets[:]:
            if current_time >= explosion_time:
                if bullet.alive():
                    explosion = Explosion(bullet.rect.center, 70, 0)  # No damage, just visual
                    explosions_group.add(explosion)
                    bullet.kill()
                self.exploding_bullets.remove((bullet, explosion_time))
    
    def update_phase1(self, player_pos, boss_bullets_group):
        if self.state=="intro":
            self.timer+=1
            if self.timer>180:
                self.state="attack1"
                self.timer=0
                self.attack_timer=0
        elif self.state=="attack1":
            self.pos = self.original_pos
            
            self.attack_timer += 1
            if self.attack_timer % 100 == 0:
                self.fire_scattered_projectiles(boss_bullets_group, 12)
            
            if self.attack_timer >= 720:
                self.state = "attack2"
                self.attack_timer = 0
                
        elif self.state=="attack2":
            dirv = (player_pos - self.pos)
            if dirv.length() > 0: 
                dirv = dirv.normalize()
                self.pos += dirv * 1.5
            
            self.attack_timer += 1
            if self.attack_timer % 180 == 0:
                self.fire_scattered_projectiles(boss_bullets_group, 8)
            
            if self.attack_timer >= 540:
                self.state = "attack1"
                self.attack_timer = 0
                self.pos = self.original_pos
    
    def update_phase2(self, player_pos, boss_bullets_group, enemies_group):
        if self.state == "phase2_idle":
            self.timer += 1
            if self.timer > 60:
                self.state = "phase2_attack1"
                self.timer = 0
                self.attack_timer = 0
                
        elif self.state == "phase2_attack1":
            self.summon_timer += 1
            if self.summon_timer % 90 == 0:
                for _ in range(2):
                    enemy = Enemy(stationary=False)  # Moving enemies
                    enemy.explodes_on_death = True
                    enemies_group.add(enemy)
            
            self.attack_timer += 1
            if self.attack_timer >= 1200:
                self.state = "phase2_attack2"
                self.attack_timer = 0
                self.bomb_timer = 0
                
        elif self.state == "phase2_attack2":
            target_pos = pygame.Vector2(WIDTH//2, HEIGHT//2)
            if (self.pos - target_pos).length() > 10:
                dirv = (target_pos - self.pos)
                if dirv.length() > 0:
                    dirv = dirv.normalize()
                    self.pos += dirv * 3
            else:
                self.pos = target_pos
                
            self.bomb_timer += 1
            if self.bomb_timer % 180 == 0:
                self.summon_bombs(3)
                
            self.attack_timer += 1
            if self.attack_timer >= 840:
                if random.choice([True, False]):
                    self.state = "phase2_attack1"
                else:
                    self.state = "phase2_attack2"
                self.attack_timer = 0
    
    def fire_scattered_projectiles(self, boss_bullets_group, count):
        for i in range(count):
            angle = i * (360 / count) + random.uniform(-15, 15)
            dirn = pygame.Vector2(1, 0).rotate(angle)
            bullet = BossBullet(self.rect.center, dirn)
            boss_bullets_group.add(bullet)
            
            if random.random() < 0.10:
                explosion_time = pygame.time.get_ticks() + random.randint(500, 1000)
                self.exploding_bullets.append((bullet, explosion_time))
    
    def summon_bombs(self, count):
        for _ in range(count):
            bomb_x = random.randint(100, WIDTH-100)
            bomb_y = random.randint(100, HEIGHT-100)
            bombs_group.add(Bomb((bomb_x, bomb_y), warning_time=180))

class BossBullet(pygame.sprite.Sprite):
    def __init__(self,pos,dirv):
        super().__init__()
        self.image=pygame.Surface((10,10), pygame.SRCALPHA); pygame.draw.circle(self.image,(255,50,50),(5,5),5)
        self.rect=self.image.get_rect(center=pos)
        self.pos=pygame.Vector2(pos); self.dir=dirv.normalize(); self.speed=6
        self.spawn_time = pygame.time.get_ticks()
        self.lifetime = 2000
        self.damage = 1  # Boss bullets deal damage
    def update(self):
        self.pos+=self.dir*self.speed; self.rect.center=self.pos
        if not screen.get_rect().colliderect(self.rect) or pygame.time.get_ticks() - self.spawn_time > self.lifetime:
            self.kill()

class Bomb(pygame.sprite.Sprite):
    def __init__(self, pos, warning_time=90, explosion_radius=60, damage=1):  # Now deals damage
        super().__init__()
        self.pos = pygame.Vector2(pos)
        self.warning_time = warning_time
        self.explosion_radius = explosion_radius
        self.damage = damage
        self.timer = 0
        self.exploded = False
        self.update_image()
        
    def update_image(self):
        size = 30
        self.image = pygame.Surface((size, size), pygame.SRCALPHA)
        
        if self.timer < self.warning_time:
            pulse = 5 * math.sin(self.timer * 0.3)
            pygame.draw.circle(self.image, (255, 0, 0, 180), (size//2, size//2), size//2 + int(pulse))
            pygame.draw.circle(self.image, (255, 255, 255), (size//2, size//2), size//4)
        else:
            pygame.draw.circle(self.image, (255, 0, 0), (size//2, size//2), size//2)
            pygame.draw.circle(self.image, (255, 255, 0), (size//2, size//2), size//4)
            
        self.rect = self.image.get_rect(center=self.pos)
        
    def update(self):
        self.timer += 1
        self.update_image()
        
        if self.timer == self.warning_time + 60:
            explosion = SonicExplosion(self.rect.center, self.explosion_radius, 8)
            explosions_group.add(explosion)
            explosion_sound.play()
            self.kill()

class Explosion(pygame.sprite.Sprite):
    def __init__(self, pos, radius=50, damage=1, duration=20):  # Now deals damage
        super().__init__()
        self.pos = pygame.Vector2(pos)
        self.radius = radius
        self.damage = damage
        self.lifetime = duration
        self.timer = 0
        self.image = pygame.Surface((radius*2, radius*2), pygame.SRCALPHA)
        self.rect = self.image.get_rect(center=pos)
        self.update_image()
        
    def update_image(self):
        self.image.fill((0,0,0,0))
        progress = self.timer / self.lifetime
        current_radius = int(self.radius * progress)
        color = (255, 100, 0, 200 - int(200 * progress))
        pygame.draw.circle(self.image, color, (self.radius, self.radius), current_radius)
        pygame.draw.circle(self.image, (255, 200, 0), (self.radius, self.radius), current_radius//2)
        
    def update(self):
        self.timer += 1
        self.update_image()
        if self.timer >= self.lifetime:
            self.kill()

# Power-up selection buttons
class PowerUpButton:
    def __init__(self, rect, text, power_type, description):
        self.rect = rect
        self.text = text
        self.power_type = power_type
        self.description = description
        self.color = (80, 80, 120)
        self.hover_color = (100, 100, 150)
        self.is_hovered = False
        
    def draw(self, screen):
        color = self.hover_color if self.is_hovered else self.color
        pygame.draw.rect(screen, color, self.rect)
        pygame.draw.rect(screen, (255, 255, 255), self.rect, 2)
        
        # Draw text
        title_font = pygame.font.SysFont(None, 32)
        desc_font = pygame.font.SysFont(None, 20)
        
        title = title_font.render(self.text, True, (255, 255, 255))
        desc = desc_font.render(self.description, True, (200, 200, 200))
        
        screen.blit(title, (self.rect.x + (self.rect.w - title.get_width()) // 2, 
                           self.rect.y + 15))
        screen.blit(desc, (self.rect.x + (self.rect.w - desc.get_width()) // 2, 
                          self.rect.y + 50))
        
    def check_hover(self, pos):
        self.is_hovered = self.rect.collidepoint(pos)
        return self.is_hovered
        
    def is_clicked(self, pos, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            return self.rect.collidepoint(pos)
        return False

# --- Drops ---
class HealthPotion(pygame.sprite.Sprite):
    LIFETIME_MS = 5000
    def __init__(self, pos=None):
        super().__init__()
        self.image = health_icon_img.copy()
        self.rect = self.image.get_rect(center=pos if pos else (random.randint(40, WIDTH-40), random.randint(40, HEIGHT-40)))
        self.spawn_time = pygame.time.get_ticks()
    def update(self):
        if pygame.time.get_ticks() - self.spawn_time > self.LIFETIME_MS:
            self.kill()

class SpeedBoost(pygame.sprite.Sprite):
    LIFETIME_MS = 5000
    def __init__(self, pos=None):
        super().__init__()
        self.image = speed_icon_img.copy()
        self.rect = self.image.get_rect(center=pos if pos else (random.randint(40, WIDTH-40), random.randint(40, HEIGHT-40)))
        self.spawn_time = pygame.time.get_ticks()
    def update(self):
        if pygame.time.get_ticks() - self.spawn_time > self.LIFETIME_MS:
            self.kill()

# --- Groups ---
player=Player()
player_group=pygame.sprite.Group(player)
bullets_group=pygame.sprite.Group()
enemies_group=pygame.sprite.Group()
enemy_bullets_group=pygame.sprite.Group()
miniboss_group=pygame.sprite.Group()
miniboss_bullets_group=pygame.sprite.Group()
boss_group=pygame.sprite.Group()
boss_bullets_group=pygame.sprite.Group()
health_potions_group=pygame.sprite.Group()
speed_boosts_group=pygame.sprite.Group()
explosions_group = pygame.sprite.Group()
bombs_group = pygame.sprite.Group()
sonic_bullets_group = pygame.sprite.Group()  # For sonic waves from explosions

game_state="title"
start_time=0
elapsed_time=0
kills=0
miniboss_spawned=False
boss_spawned=False
highscore=0

# Timing variables
miniboss_warning_time = 0
boss_warning_time = 0
boss_intro_stage = 0
boss_countdown = 3
boss_countdown_timer = 0
time_frozen = False
frozen_time = 0
paused_time = 0  # Track time when paused

# New game state variables
power_up_selection = False
power_up_buttons = []
game_paused = False
music_playing = False
boss_music_playing = False

font=pygame.font.SysFont(None,24)
bigfont=pygame.font.SysFont(None,48)
hugefont = pygame.font.SysFont(None, 72)

# Create power-up buttons
def create_power_up_buttons():
    button_width, button_height = 300, 100
    spacing = 50
    total_width = 2 * button_width + spacing
    start_x = (WIDTH - total_width) // 2
    y_pos = HEIGHT // 2 - button_height // 2
    
    buttons = [
        PowerUpButton(
            pygame.Rect(start_x, y_pos, button_width, button_height),
            "Double Shot",
            "double_shot",
            "Shoot two bullets at once"
        ),
        PowerUpButton(
            pygame.Rect(start_x + button_width + spacing, y_pos, button_width, button_height),
            "Scatter Shot",
            "scatter_shot",
            "Fire 5 bullets in wide arc"
        )
    ]
    return buttons

power_up_buttons = create_power_up_buttons()

# buttons
def draw_button(rect,text):
    pygame.draw.rect(screen,(100,100,100),rect)
    pygame.draw.rect(screen,(255,255,255),rect,2)
    label=bigfont.render(text,True,(255,255,255))
    screen.blit(label,(rect.x+(rect.w-label.get_width())//2,rect.y+(rect.h-label.get_height())//2))

def button_clicked(rect,pos):
    return rect.collidepoint(pos)

def maybe_spawn_drop(pos):
    r = random.random()
    if r < 0.4:
        health_potions_group.add(HealthPotion(pos))
    elif r < 0.8:
        speed_boosts_group.add(SpeedBoost(pos))

def random_spawn_drops():
    if random.randint(1,300) == 1:
        health_potions_group.add(HealthPotion())
    if random.randint(1,400) == 1:
        speed_boosts_group.add(SpeedBoost())

def draw_warning_text(text, font, color=(255, 0, 0)):
    text_surface = font.render(text, True, color)
    text_rect = text_surface.get_rect(center=(WIDTH//2, HEIGHT//2))
    pulse = math.sin(pygame.time.get_ticks() * 0.01) * 10
    text_rect.y += int(pulse)
    screen.blit(text_surface, text_rect)

def draw_pause_menu():
    # Semi-transparent overlay
    overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 150))
    screen.blit(overlay, (0, 0))
    
    # Pause text
    pause_text = hugefont.render("PAUSED", True, (255, 255, 255))
    screen.blit(pause_text, (WIDTH//2 - pause_text.get_width()//2, HEIGHT//2 - 100))
    
    # Instructions
    inst_font = pygame.font.SysFont(None, 32)
    instructions = [
        "Press P to resume",
        "Press ESC to quit to menu"
    ]
    
    for i, text in enumerate(instructions):
        inst_surface = inst_font.render(text, True, (200, 200, 200))
        screen.blit(inst_surface, (WIDTH//2 - inst_surface.get_width()//2, HEIGHT//2 + i * 40))

def reset_game():
    """Reset the game to initial state"""
    global start_time, elapsed_time, kills, miniboss_spawned, boss_spawned
    global miniboss_warning_time, boss_warning_time, boss_intro_stage, time_frozen, frozen_time
    global power_up_selection, game_paused, boss_music_playing
    
    start_time = pygame.time.get_ticks()
    elapsed_time = 0
    kills = 0
    miniboss_spawned = False
    boss_spawned = False
    miniboss_warning_time = 0
    boss_warning_time = 0
    boss_intro_stage = 0
    time_frozen = False
    frozen_time = 0
    power_up_selection = False
    game_paused = False
    
    # Clear all groups
    enemies_group.empty()
    bullets_group.empty()
    miniboss_group.empty()
    miniboss_bullets_group.empty()
    boss_group.empty()
    boss_bullets_group.empty()
    enemy_bullets_group.empty()
    health_potions_group.empty()
    speed_boosts_group.empty()
    explosions_group.empty()
    bombs_group.empty()
    sonic_bullets_group.empty()
    
    # Reset player
    player.hp = 10
    player.speed = player.base_speed
    player.pos = pygame.Vector2(WIDTH//2, HEIGHT//2)
    player.rect.center = player.pos
    player.double_shot = False
    player.scatter_shot = False
    player.skill_cooldown = 0
    
    # Stop boss music if playing
    if boss_music_playing:
        stop_boss_music()
        boss_music_playing = False
    
    # Restart background music
    stop_background_music()
    play_background_music()

# Start background music
play_background_music()
music_playing = True

running=True
while running:
    dt=clock.tick(FPS)
    keys=pygame.key.get_pressed()
    mouse_pos = pygame.mouse.get_pos()
    
    for event in pygame.event.get():
        if event.type==pygame.QUIT: 
            running=False
            
        # Pause functionality
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_p and game_state == "playing" and not power_up_selection:
                game_paused = not game_paused
                if game_paused:
                    pygame.mixer.music.pause()
                    if boss_music_playing:
                        boss_music.stop()
                    paused_time = pygame.time.get_ticks()  # Record when we paused
                else:
                    pygame.mixer.music.unpause()
                    if boss_music_playing:
                        boss_music.play()
                    # Adjust start_time to account for pause duration
                    if paused_time > 0:
                        pause_duration = pygame.time.get_ticks() - paused_time
                        start_time += pause_duration
                        paused_time = 0
            if event.key == pygame.K_ESCAPE and game_paused:
                game_paused = False
                game_state = "title"
                stop_background_music()
                if boss_music_playing:
                    stop_boss_music()
                    boss_music_playing = False
                music_playing = False
                
        if game_state=="playing" and event.type==pygame.KEYDOWN and not game_paused and not power_up_selection:
            if event.key==pygame.K_SPACE:
                player.shoot(bullets_group, enemies_group, miniboss_group, boss_group)
            if event.key==pygame.K_RETURN:
                player.use_skill(enemies_group,enemy_bullets_group,miniboss_group,miniboss_bullets_group,boss_group,boss_bullets_group)
                
        # Power-up selection handling
        if power_up_selection:
            for button in power_up_buttons:
                button.check_hover(mouse_pos)
                if button.is_clicked(mouse_pos, event):
                    player.apply_power_up(button.power_type)
                    power_up_selection = False
                    # Continue with miniboss spawn
                    miniboss_group.add(MiniBoss())
                    miniboss_spawned = True
                    time_frozen = False
                    
        if game_state in ["title","gameover"] and event.type==pygame.MOUSEBUTTONDOWN:
            if game_state=="title":
                if button_clicked(start_btn,event.pos):
                    game_state="playing"
                    reset_game()  # Use reset function instead of manual reset
                elif button_clicked(quit_btn,event.pos):
                    running=False
            elif game_state=="gameover":
                if button_clicked(retry_btn,event.pos):
                    game_state="playing"
                    reset_game()  # Use reset function instead of manual reset
                elif button_clicked(quit_btn,event.pos):
                    running=False

    if game_state=="playing" and not game_paused:
        current_time = pygame.time.get_ticks()
        
        # Power-up selection before miniboss
        if elapsed_time >= 60 and not miniboss_spawned and not power_up_selection and miniboss_warning_time == 0:
            miniboss_warning_time = current_time
            time_frozen = True
            frozen_time = elapsed_time
        
        if miniboss_warning_time > 0 and not power_up_selection:
            if current_time - miniboss_warning_time < 2000:  # 2 second warning
                elapsed_time = frozen_time
            else:
                # Show power-up selection instead of instantly spawning miniboss
                power_up_selection = True
                miniboss_warning_time = 0
        
        # Boss warning after miniboss dies
        if elapsed_time >= 60 and not boss_spawned and boss_warning_time == 0 and len(miniboss_group) == 0 and miniboss_spawned:
            boss_warning_time = current_time
            time_frozen = True
            frozen_time = elapsed_time
            boss_intro_stage = 0
            # Play boss music and stop background music
            play_boss_music()
            boss_music_playing = True
        
        if boss_warning_time > 0:
            elapsed_time = frozen_time
            
            if boss_intro_stage == 0:
                if current_time - boss_warning_time >= 1000:
                    boss_intro_stage = 1
                    boss_warning_time = current_time
            elif boss_intro_stage == 1:
                if current_time - boss_warning_time >= 1000:
                    boss_intro_stage = 2
                    boss_warning_time = current_time
                    boss_countdown = 3
                    boss_countdown_timer = current_time
            elif boss_intro_stage == 2:
                if current_time - boss_countdown_timer >= 1000:
                    boss_countdown -= 1
                    boss_countdown_timer = current_time
                    if boss_countdown <= 0:
                        boss_group.add(Boss())
                        boss_spawned = True
                        time_frozen = False
                        boss_warning_time = 0
        
        if not time_frozen and not power_up_selection:
            elapsed_time=(current_time-start_time)//1000
        
        # Spawn enemies
        if elapsed_time < 60 and random.randint(1,60)==1 and not time_frozen and not power_up_selection:
            enemies_group.add(Enemy(stationary=False))

        if elapsed_time >= 60 and random.randint(1,120)==1 and not time_frozen and not miniboss_spawned and not power_up_selection:
            enemies_group.add(Enemy(stationary=True))

        if not time_frozen and not power_up_selection:
            random_spawn_drops()

        # Shooting enabled from 30 to 60 seconds only
        shooting_enabled = elapsed_time >= 30 and elapsed_time < 60 and not time_frozen and not power_up_selection
        
        if not time_frozen and not power_up_selection:
            player.update(keys)
            bullets_group.update()
            enemies_group.update(player.pos, enemy_bullets_group, shooting_enabled)
            enemy_bullets_group.update()
            miniboss_group.update(player.pos, miniboss_bullets_group)
            miniboss_bullets_group.update()
            
            for boss in boss_group:
                boss.update(player.pos, boss_bullets_group, enemies_group)
            
            boss_bullets_group.update()
            health_potions_group.update()
            speed_boosts_group.update()
            explosions_group.update()
            bombs_group.update()
            sonic_bullets_group.update()

        # Bullet collisions
        for bullet in list(bullets_group):
            hit_e=pygame.sprite.spritecollide(bullet,enemies_group,False)
            if hit_e:
                for e in hit_e:
                    e.hp-=1
                    if e.hp<=0:
                        pos = e.rect.center
                        e.kill()
                        kills+=1
                        explosion_sound.play()
                        
                        if elapsed_time >= 60:
                            explosion = SonicExplosion(pos, 80, 8)
                            explosions_group.add(explosion)
                        
                        maybe_spawn_drop(pos)
                bullet.kill()
            hit_m=pygame.sprite.spritecollide(bullet,miniboss_group,False)
            if hit_m:
                for m in hit_m:
                    m.hp-=1
                    if m.hp<=0:
                        pos = m.rect.center
                        m.kill()
                        kills+=5
                        explosion_sound.play()
                        maybe_spawn_drop(pos)
                bullet.kill()
            hit_b=pygame.sprite.spritecollide(bullet,boss_group,False)
            if hit_b:
                for b in hit_b:
                    b.hp-=1
                    if b.hp<=0:
                        pos = b.rect.center
                        b.kill()
                        game_state="victory"
                        victory_sound.play()
                        # Stop boss music and restart background music
                        if boss_music_playing:
                            stop_boss_music()
                            boss_music_playing = False
                            play_background_music()
                        maybe_spawn_drop(pos)
                bullet.kill()

        # Collision handling - FIXED: All projectiles now deal damage properly
        invincible = pygame.time.get_ticks() < player.invincible_end_time
        
        # Sonic wave collisions (knockback + damage)
        for wave in pygame.sprite.spritecollide(player, sonic_bullets_group, True):
            if not invincible and player.knockback_timer <= 0:
                knockback_dir = (player.pos - wave.pos)
                if knockback_dir.length() > 0:
                    player.apply_knockback(knockback_dir, 15, 20)
                player.take_damage(wave.damage)  # Sonic waves now deal damage
        
        # Enemy bullet collisions - normal damage
        for bullet in pygame.sprite.spritecollide(player, enemy_bullets_group, True):
            if not invincible:
                player.take_damage(1)
        
        # Miniboss bullet collisions - reduced damage
        for bullet in pygame.sprite.spritecollide(player, miniboss_bullets_group, True):
            if not invincible:
                player.take_damage(1)  # Miniboss bullets deal damage
        
        # Boss bullet collisions - reduced damage
        for bullet in pygame.sprite.spritecollide(player, boss_bullets_group, True):
            if not invincible:
                player.take_damage(1)  # Boss bullets deal damage

        # Enemy collisions - normal damage
        if pygame.sprite.spritecollide(player, enemies_group, True):
            if not invincible:
                player.take_damage(1)
            maybe_spawn_drop(player.rect.center)
            
        # Miniboss collisions - reduced damage
        for miniboss in pygame.sprite.spritecollide(player, miniboss_group, False):
            if not invincible:
                if player.take_damage(1):  # Only lose 1 HP
                    # Push player away from miniboss
                    dir_away = (player.pos - miniboss.pos)
                    if dir_away.length() > 0:
                        dir_away = dir_away.normalize()
                        player.pos += dir_away * 15
                        player.rect.center = player.pos
                
        # Boss collision - reduced damage
        for boss in pygame.sprite.spritecollide(player, boss_group, False):
            if not invincible:
                if player.take_damage(1):  # Only lose 1 HP
                    dir_away = (player.pos - boss.pos)
                    if dir_away.length() > 0:
                        dir_away = dir_away.normalize()
                        player.pos += dir_away * 15
                        player.rect.center = player.pos

        # Explosion collisions (from bombs)
        for explosion in explosions_group:
            if explosion.timer < 10:  # Only damage during first few frames
                dist = math.sqrt((player.rect.centerx - explosion.rect.centerx)**2 + 
                                (player.rect.centery - explosion.rect.centery)**2)
                if dist < explosion.radius and not invincible:
                    player.take_damage(explosion.damage)
                    break

        # Pickups
        hits = pygame.sprite.spritecollide(player, health_potions_group, True)
        if hits:
            for _ in hits:
                player.hp = min(player.max_hp, player.hp + 1)
                powerup_sound.play()
                
        hits2 = pygame.sprite.spritecollide(player, speed_boosts_group, True)
        if hits2:
            for _ in hits2:
                player.apply_speed_boost(3000)
                powerup_sound.play()

        if player.hp<=0:
            game_state="gameover"
            gameover_sound.play()
            # Stop boss music if playing
            if boss_music_playing:
                stop_boss_music()
                boss_music_playing = False
            if kills>highscore: highscore=kills

    # Drawing
    if game_state == "title":
        screen.blit(menu_background_img, (0, 0))
    else:
        screen.blit(background_img, (0, 0))
    
    if game_state=="title":
        # Draw title image with pulsing effect
        if title_img.get_size() != (1, 1):  # If we have a title image
            pulse = math.sin(pygame.time.get_ticks() * 0.005) * 5
            title_scaled = pygame.transform.scale(title_img, (400 + int(pulse), 400 + int(pulse)))
            screen.blit(title_scaled, (WIDTH//2 - title_scaled.get_width()//2, 70))
        else:
            # Fallback to text
            title=bigfont.render("Shoot and Die",True,(255,255,255))
            screen.blit(title,(WIDTH//2-title.get_width()//2,150))
        
        start_btn=pygame.Rect(WIDTH//2-100,450,200,60)
        quit_btn=pygame.Rect(WIDTH//2-100,550,200,60)
        draw_button(start_btn,"Start")
        draw_button(quit_btn,"Quit")

    elif game_state=="playing":
        if not game_paused:
            # Draw game elements
            if pygame.time.get_ticks() < player.invincible_end_time:
                temp_img = player.image.copy()
                temp_img.set_alpha(120)
                screen.blit(temp_img, player.rect)
            else:
                player_group.draw(screen)
            enemies_group.draw(screen)
            bullets_group.draw(screen)
            enemy_bullets_group.draw(screen)
            miniboss_group.draw(screen)
            miniboss_bullets_group.draw(screen)
            boss_group.draw(screen)
            boss_bullets_group.draw(screen)
            health_potions_group.draw(screen)
            speed_boosts_group.draw(screen)
            bombs_group.draw(screen)
            explosions_group.draw(screen)
            sonic_bullets_group.draw(screen)

            # Warning screens
            if miniboss_warning_time > 0:
                draw_warning_text("INCOMING!", hugefont)
            
            if boss_warning_time > 0:
                if boss_intro_stage == 0:
                    draw_warning_text("IT'S HERE!", hugefont, (255, 50, 50))
                elif boss_intro_stage == 1:
                    draw_warning_text("GET READY!", hugefont, (255, 100, 0))
                elif boss_intro_stage == 2:
                    draw_warning_text(str(boss_countdown), hugefont, (255, 200, 0))

            # Power-up selection screen
            if power_up_selection:
                overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
                overlay.fill((0, 0, 0, 200))
                screen.blit(overlay, (0, 0))
                
                select_text = hugefont.render("CHOOSE A POWER-UP", True, (255, 255, 0))
                screen.blit(select_text, (WIDTH//2 - select_text.get_width()//2, 150))
                
                for button in power_up_buttons:
                    button.draw(screen)

            # HUD
            hud_x, hud_y = 10, 10
            icon_rect = pygame.Rect(hud_x, hud_y, 28, 28)
            temp_icon = pygame.transform.scale(player.image, (28,28))
            screen.blit(temp_icon, icon_rect.topleft)
            
            bar_x = hud_x + 36
            bar_y = hud_y + 4
            bar_w = 180
            bar_h = 20
            pygame.draw.rect(screen, (120,0,0), (bar_x, bar_y, bar_w, bar_h))
            hp_ratio = player.hp / player.max_hp
            pygame.draw.rect(screen, (0,200,0), (bar_x, bar_y, int(bar_w*hp_ratio), bar_h))
            
            hp_text = font.render(f"HP: {player.hp}/{player.max_hp}", True, (255,255,255))
            screen.blit(hp_text, (bar_x + bar_w + 8, bar_y))

            time_text=font.render(f"Time: {elapsed_time}s",True,(255,255,255))
            kills_text=font.render(f"Kills: {kills}",True,(255,255,255))
            screen.blit(time_text,(10,50))
            screen.blit(kills_text,(10,74))

            # Phase indicator
            if elapsed_time < 30:
                phase_text = font.render("Phase 1: Enemies chase", True, (200,200,200))
            elif elapsed_time < 60:
                phase_text = font.render("Phase 2: Enemies shoot", True, (200,200,200))
            elif miniboss_spawned and len(miniboss_group) > 0:
                phase_text = font.render("Phase 3: Miniboss Fight!", True, (255,100,100))
            elif boss_spawned:
                phase_text = font.render("Phase 4: Boss Fight!", True, (255,50,50))
            else:
                phase_text = font.render("Phase 3: Stationary Enemies", True, (200,200,200))
            
            screen.blit(phase_text, (10, 98))

            # Power-up indicators
            power_up_text = "Power-ups: "
            if player.double_shot:
                power_up_text += "Double Shot "
            if player.scatter_shot:
                power_up_text += "Scatter Shot "
            if not player.double_shot and not player.scatter_shot:
                power_up_text += "None"
                
            power_up_surface = font.render(power_up_text, True, (100, 255, 100))
            screen.blit(power_up_surface, (10, 122))

            if player.skill_cooldown==0:
                skill_text=font.render("Skill Ready (Enter)",True,(0,255,0))
            else:
                skill_text=font.render(f"Skill Cooldown: {player.skill_cooldown//FPS}s",True,(255,100,100))
            screen.blit(skill_text,(10,146))

            # Pause instruction
            pause_inst = font.render("Press P to pause", True, (150, 150, 150))
            screen.blit(pause_inst, (WIDTH - pause_inst.get_width() - 10, 10))

            # Boss HP bars
            for m in miniboss_group:
                pygame.draw.rect(screen,(80,0,0),(WIDTH-240,10,220,12))
                pygame.draw.rect(screen,(0,200,0),(WIDTH-240,10,220*(m.hp/m.max_hp),12))
                mb_text = font.render("Miniboss", True, (255,255,255))
                screen.blit(mb_text, (WIDTH-240, 24))
            for b in boss_group:
                pygame.draw.rect(screen,(80,0,0),(200,20,400,16))
                pygame.draw.rect(screen,(0,200,0),(200,20,400*(b.hp/b.max_hp),16))
                boss_text = font.render("BOSS", True, (255,255,255))
                screen.blit(boss_text, (200, 40))

            if player.speed > player.base_speed:
                remaining_ms = max(0, player.speed_end_time - pygame.time.get_ticks())
                remaining_s = remaining_ms // 1000 + (1 if remaining_ms % 1000 > 0 else 0)
                screen.blit(speed_icon_img, (bar_x, bar_y + bar_h + 8))
                stext = font.render(f"Speed: {remaining_s}s", True, (200,200,255))
                screen.blit(stext, (bar_x + 26, bar_y + bar_h + 10))
        else:
            # Draw game in background but dimmed
            if pygame.time.get_ticks() < player.invincible_end_time:
                temp_img = player.image.copy()
                temp_img.set_alpha(60)
                screen.blit(temp_img, player.rect)
            else:
                temp_img = player.image.copy()
                temp_img.set_alpha(60)
                screen.blit(temp_img, player.rect)
                
            # Draw all game elements with reduced alpha
            for group in [enemies_group, bullets_group, enemy_bullets_group, miniboss_group, 
                         miniboss_bullets_group, boss_group, boss_bullets_group, health_potions_group,
                         speed_boosts_group, bombs_group, explosions_group, sonic_bullets_group]:
                for sprite in group:
                    temp_sprite_img = sprite.image.copy()
                    temp_sprite_img.set_alpha(60)
                    screen.blit(temp_sprite_img, sprite.rect)
            
            draw_pause_menu()

    elif game_state=="victory":
        # Draw victory image with pulsing effect
        if victory_img.get_size() != (1, 1):  # If we have a victory image
            pulse = math.sin(pygame.time.get_ticks() * 0.005) * 5
            victory_scaled = pygame.transform.scale(victory_img, (600 + int(pulse), 380 + int(pulse)))
            screen.blit(victory_scaled, (WIDTH//2 - victory_scaled.get_width()//2, HEIGHT//2 - 50))
        else:
            # Fallback to text
            txt=bigfont.render("VICTORY!",True,(0,255,0))
            screen.blit(txt,(WIDTH//2-txt.get_width()//2,HEIGHT//2))
    elif game_state=="gameover":
        over=bigfont.render("GAME OVER",True,(255,0,0))
        screen.blit(over,(WIDTH//2-over.get_width()//2,150))
        score_text=font.render(f"Score: {kills}",True,(255,255,255))
        high_text=font.render(f"Highscore: {highscore}",True,(255,255,0))
        screen.blit(score_text,(WIDTH//2-score_text.get_width()//2,220))
        screen.blit(high_text,(WIDTH//2-high_text.get_width()//2,250))
        retry_btn=pygame.Rect(WIDTH//2-100,320,200,60)
        quit_btn=pygame.Rect(WIDTH//2-100,400,200,60)
        draw_button(retry_btn,"Retry")
        draw_button(quit_btn,"Quit")

    pygame.display.flip()

pygame.quit(); sys.exit()
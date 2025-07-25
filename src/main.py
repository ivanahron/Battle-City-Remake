import pyxel as px  # Since this is the main file, pyxel should only be imported here?
import grid
import random
import sounds
from stage_file import MapLoader
from typing import Literal, Iterator, Final, TypeAlias
from dataclasses import dataclass, astuple
from functools import partial
from threading import Timer

Position: TypeAlias = tuple[int, int]
CollisionRect: TypeAlias = tuple[range, range]
Directions: TypeAlias = Literal['N', 'E', 'W', 'S']

# Settings
DISPLAY_WIDTH: Final[int] = 256
DISPLAY_HEIGHT: Final[int] = 256
FPS: Final[int] = 60
ROWS: Final[int] = 32
COLS: Final[int] = 32 
PLAYER_LIVES: Final[int] = 2
PLAYER_MOVEMENT_SPD: Final[int] = 36 # px/s
POWERUP_SPAWN_TIMER_SEC: Final[int] = 5

# Bullet settings
DEFAULT_BULLET_SPD: Final[int] = 240 # px/s
BULLET_MOVEMENT_LIMIT: Final[int] = 256 # px

# Enemy AI settings
ENEMY_REDIRECT_CHANCE: Final[float] = 0.1738 # p
ENEMY_MOVEMENT_CHANCE: Final[float] = 0.525600 # q
ENEMY_SHOOT_CHANCE: Final[float] = 0.069420 # r

# Cheat Code
UNDYING_CHEAT_CODE = "failures"
HEALTH_CHEAT_CODE = "hesoyam"
MAGIC_CHEAT_CODE = "fries"

@dataclass
class Texture:
    """
    A texture class component useful for drawing sprites in a pyxel game (https://github.com/kitao/pyxel). 
    Property values are determined through pyxel's resource editor.
    Intended to be unpacked as arguments of px.blt() -> refer to pyxel documentation
    """
    img_bnk: int
    x: int
    y: int
    w: int = 8
    h: int = 8
    colkey: int = 0

    def __iter__(self):
        return iter(astuple(self))  
    
    def copy(self):
        return Texture(*self)
    
class Animation:
    """ 
    An animation class that updates its currently displayed texture while playing. Frames are processed linearly with each update. 
    """
    def __init__(self, framespan: int, cycle: bool = False) -> None:
        self._framespan = framespan
        self._cycle = cycle
        self._animation: dict[int, Texture] = {}
        self._frame = 0

    @property
    def framespan(self): 
        """ Returns the number of frames in one cycle of animation """
        return self._framespan
    @property
    def frame(self): 
        """ Returns the current frame number """
        return self._frame
    @property
    def texture(self) -> Texture: 
        """ Returns the current texture frame. Will not return one if no initial texture was given (frame 0) """
        return self._texture
    @property
    def done(self):
        """ Returns True if animation is done playing """
        return self._frame >= self.framespan
    
    def add(self, texture: Texture, frame: int = 0):
        """ Adds animation frames """
        self._animation[frame] = texture

    def play(self):
        """ Plays animation """
        self._paused = False
        self.update()
        return self

    def update(self):
        """ Updates animation """
        if not self._paused and self.frame < self.framespan:
            if self.frame in self._animation: self._texture = self._animation[self.frame]
            self._frame += 1
            if self._cycle: self._frame %= self.framespan
    
    def stop(self):
        """ Stops animation """
        self._paused = True
        return self

class Explosion:
    def __init__(self, texture: Texture) -> None:
        self._animation = Animation(30) # 30 frames (0.5s)
        for n in range(4):
            texture.x = n * 16
            self._animation.add(texture.copy(), 30*n//4)
        self._animation.play()

    @property
    def texture(self): return self._animation.texture
    @property
    def animation(self): return self._animation
    
    def update(self):
        self._animation.update()
         
class Bullet:
    def __init__(self,
                 collider: CollisionRect,
                 *,
                 facing: Directions,
                 hp: int = 1,
                 speed: int = DEFAULT_BULLET_SPD,
                 ) -> None:
        self._collider = collider # Relative to bullet (X, Y)
        self._texture: Texture
        self._explosion: Explosion
        self._facing = facing
        self._hp = hp
        self._speed = speed
        self.steps = 0
        self.last_mirror: Mirror | None = None # last mirror object this bullet reflected from

    @property
    def collider(self): 
        """ Returns the set of all Positions where this bullet exists """
        return self._collider
    @property
    def texture(self):
        """ Returns oriented texture """
        temp = self._texture
        temp.x = 'NWSE'.index(self.facing)*16
        return temp
    @property
    def explosion(self): return self._explosion
    @property
    def facing(self): return self._facing # Also keeps track of movement. No need for dx, dy
    @facing.setter
    def facing(self, dir: Directions):
        """ Redirects bullet movement """
        self._facing: Directions = dir 
        self.last_mirror = None
    @property
    def hp(self): return self._hp
    @hp.setter
    def hp(self, value: int): self._hp = value
    @property
    def speed(self): return self._speed # px/s

    def hit(self, pts: int = 1):
        """ Reduces hitpoints by specified number. Default dmg value is 1 """
        self._hp -= pts

    @classmethod
    def sound(cls, type: str): 
        """ Class interface for sounds based on type """
        pass

class Arrow(Bullet):
    def __init__(self, *, dir: Directions, hostile: bool = False):
        super().__init__((range(5,10), range(5,10)),
                         facing = dir)
        self._texture = Texture(2,0,64,16,16) if hostile else Texture(2,0,80,16,16)
        self._explosion = Explosion(Texture(1,0,64,16,16)) if hostile else Explosion(Texture(1,0,80,16,16))
    
    @classmethod
    def sound(cls, type: str):
        match type:
            case 'shot': sounds.arrow_shoot()
            case 'explode': sounds.arrow_collision()
            case _: pass

class MagicArrow(Bullet):
    def __init__(self, *, dir: Directions, hostile: bool = False, dmg: int = 3):
        super().__init__((range(4,12), range(2,13)),
                         facing = dir,
                         hp = dmg,
                         speed = 300)
        self._animation = Animation(30, True)
        if hostile:
            self._animation.add(Texture(2,0,0,16,16))
            self._animation.add(Texture(2,0,16,16,16), 15)
            self._explosion = Explosion(Texture(1,0,112,16,16))
        else:
            self._animation.add(Texture(2,0,32,16,16))
            self._animation.add(Texture(2,0,48,16,16), 15)
            self._explosion = Explosion(Texture(1,0,128,16,16))
        self._animation.play()

    @property
    def texture(self):
        temp = self._animation.texture
        temp.x = 'NWSE'.index(self.facing)*16
        return temp

    def update(self):
        self._animation.update()

    @classmethod
    def sound(cls, type: str): 
        match type:
            case 'shot': sounds.magic_arrow_shoot()
            case 'explode': sounds.magic_arrow_collision()
            case _: pass
    
class PowerUp:
    def __init__(self, texture: Texture) -> None:
        self._texture = texture
    
    @property
    def texture(self): return self._texture
    
class AttackBoost(PowerUp):
    def __init__(self) -> None:
        super().__init__(Texture(1, 0, 96, 16, 16))

class DefenseBoost(PowerUp):
    def __init__(self) -> None:
        super().__init__(Texture(1, 16, 96, 16, 16))

class Evolved(PowerUp): # No texture yet, prolly not necessary
    def __init__(self) -> None:
        super().__init__(Texture(1, 16, 96, 16, 16)) 

class Tank(grid.GridObject):
    def __init__(self, 
                 texture: Texture,
                 bullet: partial[Bullet]) -> None:
        super().__init__(range(2), range(2))
        self._texture = texture
        self._bullet = bullet
        self._explosion = partial(Explosion, Texture(1,0,32,16,16))
        self._shot = False
        self._invulnerable = False
        self._powerups: list[PowerUp] = []
        self._facing: Directions

    @property
    def texture(self): return self._texture
    @property
    def explosion(self): return self._explosion()
    @property
    def facing(self): return self._facing
    @facing.setter
    def facing(self, dir: Directions):
        """ Reorients Tank and updates texture """
        self._facing = dir
        self._texture.x = "NWSE".index(dir)*16
    @property
    def shot(self): 
        """ Returns True if tank shot a bullet """
        return self._shot
    @shot.setter
    def shot(self, value: bool):
        if self._shot ^ value:
            if value: self._texture.y += 16
            else: self._texture.y -= 16
        self._shot = value
    @property
    def bullet(self) -> Bullet:  
        """ Returns a new Bullet instance """
        return self._bullet(dir = self.facing)
    @bullet.setter
    def bullet(self, value: partial[Bullet]): 
        """ Changes the tank's bullet model """
        self._bullet = value
    @property
    def invulnerable(self): return self._invulnerable
    @property
    def powerups(self): return self._powerups

    def powerup(self, power: PowerUp, duration_sec: int = 10):
        """ Gives the tank a timed power """
        self._powerups.append(power)
        if isinstance(power, AttackBoost): # Stronger Attacks + Counters other MagicArrows for 10 secs
            self._bullet = partial(MagicArrow, dmg = 3)

        if isinstance(power, DefenseBoost): # Invulnerable for 10 secs
            self._texture = Texture(0, self._texture.x, 32, 16, 16)
            self._invulnerable = True

        if isinstance(power, Evolved): # Both Boosts
            self.powerup(AttackBoost(), duration_sec)
            self.powerup(DefenseBoost(), duration_sec)
        sounds.powered_up()
        Timer(duration_sec, partial(self.powerdown, power)).start()
 
    def powerdown(self, power: PowerUp):
        """ Removes the tank's power """
        self._powerups.remove(power)

        if isinstance(power, AttackBoost) and not any(map(lambda pow: isinstance(pow, AttackBoost), self._powerups)):
            self._bullet = partial(Arrow)

        if isinstance(power, DefenseBoost) and not any(map(lambda pow: isinstance(pow, DefenseBoost), self._powerups)):
            self._invulnerable = False
            self._texture.y = 16
        
class FriendTank(Tank):
    def __init__(self) -> None:
        super().__init__(Texture(0,0,0,16,16), partial(Arrow))
        self._facing = 'N'

class EnemyTank(Tank):
    def __init__(self) -> None:
        super().__init__(Texture(0,0,64,16,16), partial(Arrow, hostile = True))
        self._facing = 'S'

class MagicTank(Tank):
    def __init__(self) -> None:
        super().__init__(Texture(0,0,96,16,16), partial(MagicArrow, hostile = True))
        self._facing = 'S'

class Brick(grid.GridObject):
    def __init__(self, r: int, c: int, hp: int = 3) -> None:
        super().__init__(range(1), range(1))
        self._texture = Texture(1, 0, 48)
        self._texture.x += 8*(c%2)+(16*(3-hp))
        self._texture.y += 8*(r%2)
        self._hp = hp

    @property
    def hp(self): 
        """ Returns the current hitpoints of brick """
        return self._hp
    @property
    def texture(self): return self._texture

    def hit(self, pts: int = 1):
        self._hp -= pts
        self._texture.x += 16*pts
    
class Water(grid.GridObject):
    def __init__(self, r: int, c: int) -> None:
        super().__init__(range(1), range(1))
        self._texture = Texture(1, 16, 0)
        self._texture.x += 8*(c%2)
        self._texture.y += 8*(r%2)
   
    @property
    def texture(self): return self._texture

class Stone(grid.GridObject):
    def __init__(self, r: int, c: int) -> None:
        super().__init__(range(1), range(1))
        self._texture = Texture(1, 32, 16)
        self._texture.x += 8*(c%2)
        self._texture.y += 8*(r%2)

    @property
    def texture(self): return self._texture

class Tree(grid.GridObject):
    def __init__(self, r: int, c: int) -> None:
        super().__init__(range(1), range(1))
        self._texture = Texture(1, 48, 0)
        self._texture.x += 8*(c%2)
        self._texture.y += 8*(r%2)

    @property
    def texture(self): return self._texture

class Mirror(grid.GridObject):
    def __init__(self, type: bool = False) -> None:
        self._type = type 
        super().__init__(range(1), range(1))
        self._texture = Texture(1, 8, 16) if type else Texture(1, 16, 16)
    
    @property 
    def type(self): 
        """ Returns true if slope of mirror is postive (NE to SW), false if negative """
        return self._type
    @property
    def texture(self): return self._texture

    def reflect(self, bullet: Bullet):
        """ Reflects bullet based on orientation (type) """
        if self.type:
            match bullet.facing:
                case 'N': bullet.facing = 'E'
                case 'W': bullet.facing = 'S'
                case 'S': bullet.facing = 'W'
                case 'E': bullet.facing = 'N'
        else:
            match bullet.facing:
                case 'N': bullet.facing = 'W'
                case 'W': bullet.facing = 'N'
                case 'S': bullet.facing = 'E'
                case 'E': bullet.facing = 'S'
        bullet.last_mirror = self

class Castle(grid.GridObject):
    """ Castle object, instant gameover when destroyed """
    def __init__(self) -> None:
        super().__init__(range(2), range(2))
        self._texture = Texture(1, 48, 16, 16, 16)
    
    @property
    def texture(self): return self._texture

class GameState:
    def __init__(self, level: int = 0) -> None:
        self._level = level
        self._lives: int = PLAYER_LIVES
        self._wave: int = 1
        self._player: Tank = FriendTank()
        self._gridmap = grid.GridMap(ROWS, COLS, DISPLAY_WIDTH, DISPLAY_HEIGHT)
        self._trees = grid.GridMap(ROWS, COLS, DISPLAY_WIDTH, DISPLAY_HEIGHT)
        self._enemies: set[Tank] = set()
        self._bullets: dict[Bullet, tuple[Position, Tank]] = {}
        self._explosions: dict[Explosion, Position] = {} 
        self._powerups: dict[PowerUp, Position] = {}
        self.load()
        self._player_states: dict[int, tuple[Tank, int]] = {level: (self._player, self._lives)} # Stores player state for each level
        self._just_powered_up: bool = False
    
    @property
    def level(self):
        """ Returns the current level number """
        return self._level
    @property
    def lives(self): 
        """ Returns the current number of lives """
        return self._lives
    @lives.setter
    def lives(self, value: int): self._lives = value
    @property
    def wave(self): 
        """ Returns the current wave number """
        return self._wave
    @property
    def player(self): return self._player
    @player.setter
    def player(self, value: Tank): self._player = value
    @property
    def gridmap(self): return self._gridmap
    @property
    def enemies(self): 
        """ Returns the set of all enemies """
        return self._enemies
    @property
    def bullets(self): 
        """ Returns a dictionary that tracks every bullet's position and the tank that shot it"""
        return self._bullets
    @property
    def explosions(self): 
        """ Returns a dictionary that tracks explosions' position """
        return self._explosions
    @property
    def powerups(self): 
        """ Dictionary that tracks powerups' position """
        return self._powerups
    @property
    def is_gameover(self): return self._lives == 0        

    def load(self):
        """ Loads the corresponding city per current level """
        self._city = MapLoader(self._level).load()
        for i, row in enumerate(self._city):
            for j, x in enumerate(row):
                match x:
                    case 'B': self._gridmap.replace(i, j, Brick(i, j))
                    case 'T': self._trees.replace(i, j, Tree(i, j))
                    case 'W': self._gridmap.replace(i, j, Water(i, j))
                    case 'S': self._gridmap.replace(i, j, Stone(i, j))
                    case 'L': self._gridmap.replace(i, j, Mirror())
                    case 'J': self._gridmap.replace(i, j, Mirror(True))
                    case 'R': self._gridmap.replace(i, j, Brick(i, j, hp = 1))
                    case 'C': self._gridmap.replace(i, j, Castle())
                    case 'E':
                        enemy = EnemyTank()
                        self._enemies.add(enemy)
                        self._gridmap.replace(i, j, enemy)
                    case _: pass
        self.spawn_player()
    
    def reset_level(self):
        """ Restarts the current level """
        if self._level in self._player_states: self._player, self._lives = self._player_states[self._level]
        self._gridmap.clear()
        self._trees.clear()
        self._enemies.clear()
        self._bullets.clear()
        self._explosions.clear()
        self._powerups.clear()
        self._wave = 1
        self.load()

    def next_level(self):
        """ Moves to the next level """
        self._level += 1
        self._player_states[self._level] = self.player, self.lives
        self.reset_level()

    def spawn_player(self):
        """ Spawns a player on player spawn point if it exists """
        for r, row in enumerate(self._city):
            for c, x in enumerate(row):
                if x == 'P':
                    self._gridmap.replace(r, c, self._player)

    def update(self):
        """ Updates state """
        for enemy in self._enemies:
            """ Updates all enemies' action with AI """
            if random.random() < ENEMY_MOVEMENT_CHANCE:  # Chance to move 
                dir: Directions = random.choice(['N', 'W', 'S', 'E']) # Choose random direction
                if random.random() < ENEMY_REDIRECT_CHANCE:  # Chance to change direction 
                    self.move_to(dir, enemy)
            if not enemy.shot and random.random() < ENEMY_SHOOT_CHANCE: # Chance to shoot
                enemy.shot = True
                self.spawnBullet(enemy)

        for bullet, ((x, y), tank) in self._bullets.copy().items(): 
            """ Updates all bullets and checks collisions """
            if bullet not in self._bullets: continue
            
            X, Y = self.bullet_collider(bullet)
            objects = set(self.scan(X, Y))
            bullet_dmg = 0
            for obj in objects:                
                if isinstance(obj, Tank) and ((tank == self._player and obj in self._enemies) or (obj == self._player)): # handles tank bullet collisions 
                    if obj.invulnerable: bullet_dmg += bullet.hp
                    else:
                        bullet_dmg += 1
                        self.explosions[obj.explosion] = self.locate(obj)
                        sounds.tank_explosion()
                        self._gridmap.remove(obj)
                        
                        if obj in self._enemies: self._enemies.remove(obj)
                        else: 
                            self._lives -= 1
                            if self._lives: 
                                self._player = FriendTank()
                                Timer(1, self.spawn_player).start() # 1 second timer before respawning
                            else: 
                                sounds.stop_bgm()
                                sounds.game_over()

                if isinstance(obj, (Brick)): # handles brick collisions
                    bullet_dmg += obj.hp
                    obj.hit(bullet.hp)
                    if obj.hp <= 0: self._gridmap.remove(obj)

                if isinstance(obj, Castle): # handles castle collision
                    self.explosions[Explosion(Texture(1, 0, 32, 16, 16))] = self.locate(obj)
                    self._gridmap.remove(obj)
                    sounds.tank_explosion()
                    Timer(1.00, partial(self.__setattr__, 'lives', 0)).start()
                    Timer(1.00, partial(sounds.game_over)).start()

                if isinstance(obj, Mirror) and obj != bullet.last_mirror: # handles mirror bullet collisions
                    obj_x, obj_y = self.locate(obj)
                    if obj.type:
                        for dx, dy in zip((0, self._gridmap.cellwidth), (0, self._gridmap.cellheight)):
                            if (obj_x + self._gridmap.cellwidth - dx) in X and (obj_y + dy) in Y:
                                obj.reflect(bullet)
                                break
                        else: continue
                        break # break out of outer loop if inner loop was broken
                    else: 
                        for dx, dy in zip((0, self._gridmap.cellwidth), (0, self._gridmap.cellheight)):
                            if (obj_x + dx) in X and (obj_y + dy) in Y:
                                obj.reflect(bullet)
                                break
                        else: continue
                        break
                                
                if isinstance(obj, Stone): # handles stone collision
                    bullet_dmg += bullet.hp
            
            for bullet2 in self._bullets.copy(): # handles bullet-to-bullet collisions
                if bullet2 is not bullet and self.check_collision(self.bullet_collider(bullet), self.bullet_collider(bullet2)): # all bullets should collide with each other
                    bullet_dmg += bullet2.hp
                    bullet2.hit(bullet.hp)

                    if bullet2.hp <= 0:
                        self._bullets[bullet2][1].shot = False
                        self.explosions[bullet2.explosion] = self._bullets[bullet2][0]
                        if self._bullets[bullet2][1] == self._player: bullet2.sound('explode')
                        self._bullets.pop(bullet2)
                        break
            bullet.hp -= bullet_dmg
                
            if any(map(lambda obj: isinstance(obj, Tank) and obj.invulnerable, objects)) or bullet.hp  <= 0 or bullet.steps > BULLET_MOVEMENT_LIMIT: 
                # Removes bullet 
                tank.shot = False
                self.explosions[bullet.explosion] = x, y
                if tank == self._player and not any(map(lambda obj: isinstance(obj, Tank) and not obj.invulnerable, objects)): bullet.sound('explode')
                self._bullets.pop(bullet)
            else:
                # Update bullet's position
                match bullet.facing:
                    case 'N':
                        if min(Y) <= 0: bullet.facing = 'S'
                        else: y -= bullet.speed//FPS
                    case 'W':
                        if min(X) <= 0: bullet.facing = 'E'
                        else: x -= bullet.speed//FPS
                    case 'S':
                        if max(Y) >= self._gridmap.height - 1: bullet.facing = 'N'
                        else: y += bullet.speed//FPS
                    case 'E':
                        if max(X) >= self._gridmap.width - 1: bullet.facing = 'W'
                        else: x += bullet.speed//FPS
                bullet.steps += bullet.speed//FPS
                self._bullets[bullet] = (x, y), tank
                if isinstance(bullet, MagicArrow): bullet.update()

        for explosion in self.explosions.copy():
            """ Updates all the explosions """
            if explosion.animation.done:
                self.explosions.pop(explosion)
            explosion.update()

        for power, (x,y) in self.powerups.copy().items():
            """ Updates all powerups and handles their player collision """
            if self._player in self._gridmap and (x*self.gridmap.cellwidth, y*self.gridmap.cellheight) == self.locate(self._player) and len(self._player.powerups) < 3:
                self.powerups.pop(power)
                self._player.powerup(power)
                self._just_powered_up = True
                Timer(POWERUP_SPAWN_TIMER_SEC, self.__setattr__, ('_just_powered_up', False)).start()

        if self._wave < 3 and not (self._enemies or self._bullets):
            """ Spawns more enemies once they're wiped out """
            for i, j in MapLoader(self._level).enemy_location():
                enemy = random.choice((EnemyTank(), MagicTank())) if self._wave >= 2 else EnemyTank()
                try: 
                    self._gridmap.replace(i, j, enemy)
                except ValueError:
                    continue
                self._enemies.add(enemy)
            self._wave += 1  

        if not self.powerups and self._wave >= 2 and not self._just_powered_up:
            """ Generates random power up on one of the fixed locations from tilemap """
            if (pu_spawns:= MapLoader(self._level).power_up_location()):
                (y, x) = random.choice(pu_spawns) # power up location
                self.powerups[random.choice((AttackBoost(), DefenseBoost()))] = x, y

    def locate(self, obj: grid.GridObject) -> Position:
        """ Locates (x, y) coords of GridObject relative to map """
        r, c =  self._gridmap.find(obj)
        return c*self._gridmap.cellwidth, r*self._gridmap.cellheight
    
    def bullet_collider(self, bullet: Bullet) -> CollisionRect:
        """ Returns collider of bullet relative to map """
        (x, y), _ = self._bullets[bullet]
        X, Y = bullet.collider
        return range(x + X.start, x + X.stop), range(y + Y.start, y + Y.stop)
    
    def scan(self, 
            X: range, # range of x values
            Y: range, # range of y values
            ) -> Iterator[grid.GridObject]:
        """ Scans subgrid of x, y values for GridObjects """
        for x in X:
            for y in Y:
                if 0 <= x < DISPLAY_WIDTH and 0 <= y < DISPLAY_HEIGHT:
                    obj = self._gridmap.table[y//self._gridmap.cellheight][x//self._gridmap.cellwidth]
                    if obj is not None: yield obj

    def move_to(self, dir: Directions, obj: grid.GridObject, cells: int = 1):
        """ Moves GridObjects in cardinal directions on map with clamping """
        if obj not in self._gridmap: return
        r, c = self._gridmap.find(obj)
        match dir:
            case 'N':  r -= cells
            case 'W':  c -= cells
            case 'S':  r += cells
            case 'E':  c += cells
        if isinstance(obj, Tank): obj.facing = dir
        r, c = max(min(obj.R), min(r, self._gridmap.rows-1-max(obj.R))), max(min(obj.C), min(c, self._gridmap.cols-1-max(obj.C))) # Autoclamping
        for other in self._gridmap.scan(range(r + obj.R.start, r + obj.R.stop), range(c + obj.C.start, c + obj.C.stop)):
            if other != obj: return
        self._gridmap.move(obj, r, c)
    
    def spawnBullet(self, tank: Tank, buffer: int = 0):
        """ Spawns bullets outside of the collider of the Tank they came from with positional buffer """
        (x, y), bullet = self.locate(tank), tank.bullet
        X, Y = bullet.collider
        match tank.facing:
            case 'N':
                y -= max(Y) + 1 + buffer
            case 'W':
                x -= max(X) + 1 + buffer
            case 'S':
                y += len(tank.R)*self._gridmap.cellheight - min(Y) + buffer
            case 'E':
                x += len(tank.C)*self._gridmap.cellwidth - min(X) + buffer
        self._bullets[bullet] = (x, y), tank
        tank.shot = True
        if tank == self.player: bullet.sound('shot')
    
    def check_collision(self, collider1: CollisionRect, collider2: CollisionRect) -> bool:
        """ Checks if two colliders overlap with each other """
        X1, Y1 = collider1
        X2, Y2 = collider2
        for x in X1:
            for y in Y1:
                if x in X2 and y in Y2: return True
        return False
    
    def drawspecs(self) -> Iterator[tuple[int, int, Texture]]:
        """ Returns an iterator of all object textures and their positions within the canvas """
        for (r, c), obj in self.gridmap.enumerate():
            if isinstance(obj, (Tank, Brick, Water, Stone, Tree, Mirror, Castle)): 
                yield c*self.gridmap.cellwidth, r*self.gridmap.cellheight, obj.texture
        
        for bullet, ((x, y), _) in self.bullets.items():
            yield x, y, bullet.texture

        for explosion, (x, y) in self.explosions.items():
            yield x, y, explosion.texture

        for powerup, (x, y) in self.powerups.items():
            yield x*self.gridmap.cellwidth, y*self.gridmap.cellheight, powerup.texture

        for (r, c), obj in self._trees.enumerate():
            if isinstance(obj, (Tank, Brick, Water, Stone, Tree, Mirror, Castle)): 
                yield c*self.gridmap.cellwidth, r*self.gridmap.cellheight, obj.texture
    
class BattleCity:
    def __init__(self):
        px.init(DISPLAY_WIDTH, DISPLAY_HEIGHT, title="BattleCity", fps = FPS)
        px.load("my_resource.pyxres")
        self.state = GameState() 
        self.key_input: str = '' # cheat code input
        px.run(self.update, self.draw)

    def update(self):
        """ Handles user input """
        if px.btn(px.KEY_LCTRL) or px.btn(px.KEY_RCTRL):
            if px.btnp(px.KEY_S) and self.state.level == 0:
                self.state.next_level()
            if px.btnp(px.KEY_R) and self.state.level > 0:
                self.state.reset_level()

        if self.state.level > MapLoader.LEVELS:
            if px.btnp(px.KEY_SPACE):
                self.state = GameState() # Go back to menu
        elif self.state.is_gameover:
            if px.btnp(px.KEY_SPACE):
                self.state = GameState()
            return
        
        if not self.state.enemies and self.state.wave >= 3:
            if not self.state.bullets and px.btnp(px.KEY_SPACE):
                self.state.next_level()
        else:
            # cheat code input buffer
            for n in range(97, 123): # a-z
                if px.btnp(n): self.key_input += chr(n)
                
            if UNDYING_CHEAT_CODE in self.key_input:
                self.state.player.powerup(DefenseBoost(), 10**6)
                self.key_input = ''  # Resets the input when the cheat is activated
            elif HEALTH_CHEAT_CODE in self.key_input:
                self.state.lives += 2
                self.key_input = ''
                sounds.powered_up()
            elif MAGIC_CHEAT_CODE in self.key_input:
                self.state.player.powerup(AttackBoost(), 10**6)
                self.key_input = ''
            if self.state.player in self.state.gridmap:
                if px.btnp(px.KEY_SPACE) and not self.state.player.shot and not any(map(lambda k: px.btn(k), (px.KEY_W, px.KEY_A, px.KEY_S, px.KEY_D))):
                    self.state.spawnBullet(self.state.player)

                if px.btn(px.KEY_W) and  px.frame_count*PLAYER_MOVEMENT_SPD % FPS*self.state.gridmap.cellheight == 0: self.state.move_to('N', self.state.player)
                elif px.btn(px.KEY_D) and  px.frame_count*PLAYER_MOVEMENT_SPD % FPS*self.state.gridmap.cellwidth == 0: self.state.move_to('E', self.state.player)
                elif px.btn(px.KEY_A) and  px.frame_count*PLAYER_MOVEMENT_SPD % FPS*self.state.gridmap.cellwidth == 0: self.state.move_to('W', self.state.player)
                elif px.btn(px.KEY_S) and  px.frame_count*PLAYER_MOVEMENT_SPD % FPS*self.state.gridmap.cellheight == 0: self.state.move_to('S', self.state.player)
                
        
        self.state.update()
    
    def draw_top_ui(self):
        """ UI on top while in game that tells the player its health and current power up of the player """
        start_1 = 43 # starting x coord
        start_2 = 155 # starting x coord for power up
        
        px.rect(0, 0, DISPLAY_WIDTH, 16, px.COLOR_BLACK)
        px.blt(0.5, 0, 0, 0, 128, 16, 16, 0) # Health indicator
        px.text(19, 5.45, str(self.state.lives), px.COLOR_GREEN) # Actual health

        for i in range(0, 112, 16):
            px.blt(start_1+i, 0, 0, 16+i, 128, 16, 16, 0)

        for i in range(0, 48, 16):
            px.blt(start_2 + i, 0, 0, i, 192, 16, 16, 0)

        for i, power in enumerate(self.state.player.powerups): # Current powerups
            px.blt(200 + i*18, 0, *power.texture)

    def draw_main_menu(self):
        start_1 = 80
        start_2 = 85
        start_3 = 115
        for i in range(0, 96, 16):
            px.blt(start_1 + i, 144, 0, i, 144, 16, 16, 0)
            px.blt(start_2 + i, 168, 0, i, 160, 16, 16, 0)
            px.blt(start_3 + i, 192, 0, i, 176, 16, 16, 0)

    def draw_credits(self):
        px.cls(px.COLOR_BLACK)
        px.text((DISPLAY_WIDTH//2)-50, (DISPLAY_HEIGHT//2)-20, "THANKS FOR PLAYING!", px.COLOR_WHITE)
        px.text((DISPLAY_WIDTH//2)-50, (DISPLAY_HEIGHT//2)-10, "Made by:", px.COLOR_WHITE)
        px.text((DISPLAY_WIDTH//2)-45, (DISPLAY_HEIGHT//2), "Hedelito M. Dollison III", px.COLOR_WHITE)
        px.text((DISPLAY_WIDTH//2)-45, (DISPLAY_HEIGHT//2)+10, "Ivan Ahron L. Junio", px.COLOR_WHITE)
        px.text(5, DISPLAY_HEIGHT - 10, "Press Space to go back to menu", px.COLOR_WHITE)

    def draw(self):
        px.cls(1)

        if self.state.level > MapLoader.LEVELS:
            self.draw_credits()
        elif self.state.level > 0:
            self.draw_top_ui()

            for x, y, texture in self.state.drawspecs():
                px.blt(x, y, *texture)

            if self.state.is_gameover:
                px.text((DISPLAY_WIDTH//2)-20, (DISPLAY_HEIGHT//2)-10, "GAMEOVER!", px.COLOR_RED)
                px.text((DISPLAY_WIDTH//2)-50, (DISPLAY_HEIGHT//2), "PRESS SPACE TO TRY AGAIN!", px.COLOR_RED)
            elif not (self.state.enemies or self.state.bullets) and self.state.wave >= 3 and self.state.level <= MapLoader.LEVELS:
                px.text((DISPLAY_WIDTH//2)-20, (DISPLAY_HEIGHT//2)-10, "YOU WIN!", px.COLOR_GREEN)
                px.text((DISPLAY_WIDTH//2)-50, (DISPLAY_HEIGHT//2), "PRESS SPACE TO MOVE ON!", px.COLOR_GREEN)
        elif self.state.level == 0:
            for x, y, texture in self.state.drawspecs():
                px.blt(x, y, *texture)
            self.draw_main_menu()

if __name__ == "__main__":
    BattleCity()
import pyxel as px
import sounds
class WorldObjects:
    ''' Bank of the sprite module coordinates of each object in the tilemap '''
    BRICK: list[tuple[int, int]] = [(8, 2), (9, 2), (8, 3), (9, 3)]
    CRACKED_BRICK: list[tuple[int, int]] = [(12, 2), (13, 2), (12, 3), (13, 3)]
    WATER: list[tuple[int, int]] = [(8, 0), (9, 0), (8, 1), (9, 1)]
    STONE: list[tuple[int, int]] = [(10, 0), (11, 0), (10, 1), (11, 1)]
    TREE: list[tuple[int, int]] = [(12, 0), (13, 0), (12, 1), (13, 1)]
    MIRROR1: list[tuple[int, int]] = [(14, 0), (15, 1)]
    MIRROR2: list[tuple[int, int]] = [(17, 0), (16, 1)]
    PLAYER: list[tuple[int, int]] = [(0, 0), (1, 0), (0, 1), (1, 1)]
    ENEMY: list[tuple[int, int]] = [(0, 8)]
    MAGIC_ENEMY: list[tuple[int, int]] = [(0, 12)]
    CASTLE: list[tuple[int, int]] = [(8, 4)]
    POWERUP: list[tuple[int, int]] = [(8, 6), (10, 6)]
    
class MapLoader:
    LEVELS = 4
    ''' Generates the city for corresponding level '''
    def __init__(self, level: int):
        px.load("my_resource.pyxres")
        self.level = level
        self.tilemap = px.tilemaps[self.level] # pyxel is printing "pyxel.tilemap(tm) is deprecated, use pyxel.tilemaps[tm] instead"
        self.city: list[list[str]] = []
        self.enemies_spawnpoint: list[tuple[int, int]] = []
        self.powerups_spawnpoint: list[tuple[int, int]] = []
        is_player_ingame: bool = False # 1 player instance
        for i in range(32):
            city_row: list[str] = []
            for j in range(32):
                tile: tuple[int, int] = self.tilemap.pget(j, i) # type: ignore
                if tile in WorldObjects.BRICK: city_row.append('B')
                elif tile in WorldObjects.CRACKED_BRICK: city_row.append('R')
                elif tile in WorldObjects.WATER: city_row.append('W')
                elif tile in WorldObjects.STONE: city_row.append('S')
                elif tile in WorldObjects.TREE: city_row.append('T')
                elif tile in WorldObjects.MIRROR1: city_row.append('L')
                elif tile in WorldObjects.MIRROR2: city_row.append('J')
                elif tile in WorldObjects.CASTLE: city_row.append('C')
                elif tile in WorldObjects.PLAYER:
                    if not is_player_ingame:
                        city_row.append('P')
                        is_player_ingame = True
                    else:
                        city_row.append('.')
                elif tile in WorldObjects.ENEMY or tile in WorldObjects.MAGIC_ENEMY:
                    city_row.append('E')
                    self.enemies_spawnpoint.append((i, j))
                elif tile in WorldObjects.POWERUP:
                    self.powerups_spawnpoint.append((i, j))
                    city_row.append('.')
                else:
                    city_row.append('.')
            
            self.city.append(city_row)
    
    def load(self) -> list[list[str]]:
        ''' Returns the generated city '''
        sounds.stop_bgm()
        if self.level == 0:
            sounds.main_menu()
        elif self.level == 1:
            sounds.level_1()
        elif self.level == 2:
            sounds.level_2()
        elif self.level == 3:
            sounds.level_3()
        elif self.level == 4:
            sounds.level_4()
        elif self.level == 5:
            sounds.won(True)
        return self.city
    
    def enemy_location(self) -> list[tuple[int, int]]:
        return self.enemies_spawnpoint
    
    def power_up_location(self) -> list[tuple[int, int]]:
        return self.powerups_spawnpoint
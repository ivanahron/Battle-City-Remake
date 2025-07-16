import pyxel as px
""" Sound bank """

def arrow_shoot():
    px.play(2, 0)

def arrow_collision():
    px.play(2, 2)

def magic_arrow_shoot():
    px.play(3, 0)
    px.play(3, 1)

def magic_arrow_collision():
    px.play(3, 3)

def tank_explosion():
    px.sounds[4].set( # type: ignore
        "a2 a2 g2 f2 e2 e2",
        "n",
        "7",
        "vvf",
        8              
) 
    px.play(3, 4)

def powered_up():
    px.play(3, 5)

def game_over():
    px.play(3, 22)

def won(loop: bool):
    px.play(3, 17, loop=loop)

def main_menu():
    px.playm(2, loop=True)

def level_1():
    px.playm(1, loop=True)

def level_2(): # AMOGUS MAP
    px.playm(0, loop=True)

def level_3():
    px.playm(3, loop=True)

def level_4():
    px.playm(4, loop=True)

def stop_bgm():
    px.stop(0)
    px.stop(1)
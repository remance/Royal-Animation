import configparser
import os
import sys

import keyboard
import pygame
import screeninfo
import win32api
import win32con
import win32gui
from pygame import sprite
from pygame.locals import *

from engine.camera.camera import Camera
from engine.character.character import Character, BodyPart
from engine.data.datalocalisation import Localisation
from engine.data.datasound import SoundData
from engine.data.datasprite import AnimationData
from engine.data.datastat import CharacterData
from engine.effect.effect import Effect
from engine.game.game import Game
from engine.utils.data_loading import stat_convert


class FakeBattle:
    from engine.battle.add_sound_effect_queue import add_sound_effect_queue
    add_sound_effect_queue = add_sound_effect_queue

    from engine.battle.cal_shake_value import cal_shake_value
    cal_shake_value = cal_shake_value

    def __init__(self, screen_scale, chapter, master_volume):
        self.screen_scale = screen_scale
        self.chapter = chapter
        self.sound_effect_queue = {}
        self.play_effect_volume = master_volume
        self.play_voice_volume = master_volume
        self.screen_shake_value = 0


class Overlay:
    from engine.battle.load_battle_sprite_animation import load_battle_sprite_animation
    load_battle_sprite_animation = load_battle_sprite_animation

    from engine.battle.play_sound_effect import play_sound_effect
    play_sound_effect = play_sound_effect

    def __init__(self):
        """Transparent desktop overlay to play fun character animation based on overlay.ini input"""
        self.main_dir = os.path.split(os.path.abspath(__file__))[0]
        self.data_dir = os.path.join(self.main_dir, "data")

        self.config_path = os.path.join(self.main_dir, "overlay.ini")
        self.config = configparser.ConfigParser()  # initiate config reader
        self.config.read_file(open(self.config_path))

        screen = screeninfo.get_monitors()[0]
        screen_width = int(screen.width)
        screen_height = int(screen.height)

        if "." in self.config["DEFAULT"]["screen_width"]:
            display_width = int(screen_width * float(self.config["DEFAULT"]["screen_width"]))
        else:
            display_width = int(self.config["DEFAULT"]["screen_width"])
        if "." in self.config["DEFAULT"]["screen_height"]:
            display_height = int(screen_height * float(self.config["DEFAULT"]["screen_height"]))
        else:
            display_height = int(self.config["DEFAULT"]["screen_height"])
        self.screen_size = (display_width, display_height)
        self.screen_width = self.screen_size[0]
        self.screen_height = self.screen_size[1]
        self.screen_scale = (screen_width / 3840, screen_height / 2160)

        if "." in self.config["DEFAULT"]["screen_pos_x"]:
            position_x = int(screen_width * float(self.config["DEFAULT"]["screen_pos_x"]))
        else:
            position_x = int(self.config["DEFAULT"]["screen_pos_x"])
        if "." in self.config["DEFAULT"]["screen_pos_y"]:
            position_y = int(screen_height * float(self.config["DEFAULT"]["screen_pos_y"]))
        else:
            position_y = int(self.config["DEFAULT"]["screen_pos_y"])
        position = (position_x, position_y)
        self.chapter = self.config["DEFAULT"]["chapter"]
        self.master_volume = float(self.config["DEFAULT"]["master_volume"])
        pygame.mixer.pre_init(44100, -16, 1000, 4096)
        pygame.init()
        pygame.event.set_allowed((QUIT, KEYDOWN, KEYUP))

        self.screen = pygame.display.set_mode((self.screen_width, self.screen_height),
                                              pygame.NOFRAME)  # For borderless, use pygame.NOFRAME
        self.alpha_colour = (0, 0, 0)  # Transparency color
        self.clock = pygame.time.Clock()

        # Create layered window
        self.display = pygame.display.get_wm_info()["window"]

        Game.main_dir = self.main_dir
        Game.data_dir = self.data_dir
        Game.screen_size = self.screen_size
        Game.screen_scale = self.screen_scale
        Game.language = "en"

        l_ex_style = win32gui.GetWindowLong(self.display, win32con.GWL_EXSTYLE)
        l_ex_style |= win32con.WS_EX_TRANSPARENT | win32con.WS_EX_LAYERED
        win32gui.SetWindowLong(self.display, win32con.GWL_EXSTYLE,
                               win32gui.GetWindowLong(self.display, win32con.GWL_EXSTYLE) | win32con.WS_EX_LAYERED)
        win32gui.SetLayeredWindowAttributes(self.display, win32api.RGB(*self.alpha_colour), 0,
                                            win32con.LWA_COLORKEY)  # Setting window color to transparent
        win32gui.SetWindowPos(self.display, win32con.HWND_TOPMOST, position[0], position[1], 0, 0,
                              win32con.SWP_NOSIZE)  # Setting window to always be on top
        win32gui.SetWindowLong(self.display, win32con.GWL_EXSTYLE, l_ex_style)

        # os.environ['SDL_WINDOWID'] = str(self.frame.winfo_id())
        # Window.
        # self.msg_screen.opacity = 0
        # l_ex_style = win32gui.GetWindowLong(self.msg_display, win32con.GWL_EXSTYLE)
        # l_ex_style |= win32con.WS_EX_TRANSPARENT | win32con.WS_EX_LAYERED
        # win32gui.SetWindowLong(self.msg_display, win32con.GWL_EXSTYLE,
        #                        win32gui.GetWindowLong(self.msg_display, win32con.GWL_EXSTYLE) | win32con.WS_EX_LAYERED)
        # win32gui.SetLayeredWindowAttributes(self.msg_display, win32api.RGB(*self.alpha_colour), 0, win32con.LWA_COLORKEY)  # Setting window color to transparent
        # win32gui.SetWindowPos(self.msg_display, win32con.HWND_TOPMOST, int(screen_width / 2), int(screen_height / 1.5), 0, 0,
        #                       win32con.SWP_NOSIZE)  # Setting window to always be on top
        # win32gui.SetWindowLong(self.msg_display, win32con.GWL_EXSTYLE, l_ex_style)

        self.battle = FakeBattle(self.screen_scale, self.chapter, self.master_volume)
        self.shown_camera_pos = (int(self.screen_width / 2), int(self.screen_height / 2))
        self.battle.camera_pos = self.shown_camera_pos

        self.battle.localisation = Localisation()

        self.animation_data = AnimationData()
        self.character_data = CharacterData()
        self.battle.sound_data = SoundData()

        self.sound_effect_pool = self.battle.sound_data.sound_effect_pool

        self.battle.character_updater = sprite.Group()  # updater for character objects
        self.battle.effect_updater = sprite.Group()  # updater for effect objects (e.g. range attack sprite)

        self.battle.character_animation_data = self.animation_data.character_animation_data
        self.battle.body_sprite_pool = {}
        self.battle.char_sprite_chapter = self.animation_data.char_sprite_chapter
        self.battle.default_body_sprite_pool = self.animation_data.default_body_sprite_pool
        self.battle.default_effect_animation_pool = self.animation_data.default_effect_animation_pool
        self.battle.part_sprite_adjust = self.animation_data.part_sprite_adjust
        self.battle.effect_animation_pool = self.animation_data.effect_animation_pool

        self.body_sprite_pool = self.battle.body_sprite_pool
        self.char_sprite_chapter = self.animation_data.char_sprite_chapter
        self.default_body_sprite_pool = self.animation_data.default_body_sprite_pool
        self.default_effect_animation_pool = self.animation_data.default_effect_animation_pool
        self.part_sprite_adjust = self.animation_data.part_sprite_adjust
        self.effect_animation_pool = self.animation_data.effect_animation_pool

        BodyPart.containers = self.battle.effect_updater
        Effect.containers = self.battle.effect_updater
        Character.containers = self.battle.character_updater

        Character.battle = self.battle
        Character.sound_effect_pool = self.sound_effect_pool
        BodyPart.battle = self.battle
        BodyPart.body_sprite_pool = self.battle.body_sprite_pool

        self.camera = Camera(self.screen, self.screen_size)
        self.battle_camera = sprite.LayeredUpdates()

        stat = {}
        stat_convert(stat, 0, self.config["DEFAULT"]["character"], dict_column=(0,))
        stat = stat[0]
        stat |= self.character_data.character_list[stat["ID"]]
        character_list = [stat["ID"]]
        self.animation_data.load_data(self.chapter, character_list,
                                      only_list=("OVERLAY",))  # this will load data if chapter is different
        self.load_battle_sprite_animation(character_list)
        self.actor = Character(self.battle_camera, 1, 1, stat)

        self.action = {}
        for num in range(1, 13):
            stat = {}
            stat_convert(stat, 0, self.config["DEFAULT"]["inputF" + str(num)], dict_column=(0,))
            self.action["F" + str(num)] = stat[0]

    def run(self):
        self.actor.enter_stage(self.animation_data.character_animation_data)
        key_pressed = {"F" + str(number): False for number in range(1, 13)}
        while True:
            dt = self.clock.get_time() / 1000
            for event in pygame.event.get():  # get event that happen
                if event.type == QUIT:  # quit game
                    pygame.quit()
                    sys.exit()
            for key in key_pressed:
                if key_pressed[key] and not keyboard.is_pressed(key):
                    if key in self.action:
                        self.actor.interrupt_animation = True
                        self.actor.command_action = self.action[key]

                    key_pressed[key] = False
                elif keyboard.is_pressed(key):
                    key_pressed[key] = True
            self.screen.fill(self.alpha_colour)  # Transparent background
            self.battle.character_updater.update(dt)
            self.battle.effect_updater.update(dt)
            self.camera.update(self.shown_camera_pos, self.battle_camera)
            if self.battle.sound_effect_queue:
                for key, value in self.battle.sound_effect_queue.items():  # play each sound effect initiate in this loop
                    self.play_sound_effect(key, value)
                self.battle.sound_effect_queue = {}
            pygame.display.update()
            self.clock.tick(60)


overlay = Overlay()
overlay.run()

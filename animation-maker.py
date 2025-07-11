import csv
import os
import random
import re
import sys
import time
from math import atan2, degrees, radians
from os import sep
from os.path import join, split, normpath, abspath
from pathlib import Path

import pygame
from PIL import Image, ImageFilter, ImageEnhance, ImageOps
from pygame.transform import smoothscale, rotate, flip as pyflip

from engine.data.datalocalisation import Localisation
from engine.data.datasound import SoundData
from engine.game.game import Game
from engine.uibattle.uibattle import UIScroll
from engine.uimenu.uimenu import MenuCursor, NameList, MenuButton, TextPopup, InputUI, InputBox, ListBox
from engine.utils.data_loading import csv_read, load_image, load_images, load_base_button, recursive_image_load, \
    filename_convert_readable as fcv
from engine.utils.rotation import rotation_xy
from engine.utils.sprite_altering import sprite_rotate

main_dir = split(abspath(__file__))[0]
main_data_dir = join(main_dir, "data")
current_dir = join(main_dir, "animation-maker")  # animation maker folder
current_data_dir = join(main_dir, "animation-maker", "data")  # animation maker folder
sys.path.insert(1, current_dir)

from script import colour, listpopup, pool, showroom  # keep here as it need to get sys path insert

apply_colour = colour.apply_sprite_colour
setup_list = listpopup.setup_list
list_scroll = listpopup.list_scroll
popup_list_open = listpopup.popup_list_open
read_anim_data = pool.read_anim_data
anim_to_pool = pool.anim_to_pool
anim_save_pool = pool.anim_save_pool
anim_del_pool = pool.anim_del_pool

screen_size = (1300, 900)
screen_scale = (1, 1)

inf = float("inf")

pygame.init()
pen = pygame.display.set_mode(screen_size)
pygame.display.set_caption("Animation Maker")  # set the self name on program border/tab
pygame.mouse.set_visible(False)  # set mouse as invisible, use cursor object instead

data_dir = join(main_dir, "data")
animation_dir = join(data_dir, "animation")
language = "en"

default_sprite_size = (500, 500)

ui = pygame.sprite.LayeredUpdates()
fake_group = pygame.sprite.LayeredUpdates()  # just fake group to add for container and not get auto update

Game.main_dir = main_dir
Game.data_dir = data_dir
Game.screen_size = screen_size
Game.screen_scale = screen_scale
Game.language = language
Game.ui_font = csv_read(data_dir, "ui_font.csv", ("ui",), header_key=True)
Game.font_dir = join(data_dir, "font")
Game.ui_updater = ui

localisation = Localisation()
Game.localisation = localisation
for item in Game.ui_font:  # add ttf file extension for font data reading.
    Game.ui_font[item] = join(Game.font_dir, Game.ui_font[item]["Font"] + ".ttf")

MenuCursor.containers = ui
cursor_images = load_images(data_dir, subfolder=("ui", "cursor_menu"))  # no need to scale cursor
cursor = MenuCursor(cursor_images)
Game.cursor = cursor

max_person = 4
max_frame = 26
p_list = tuple(["p" + str(p) for p in range(1, max_person + 1)])
part_column_header = ["head", "neck", "body", "r_arm_up", "r_arm_low", "r_hand", "l_arm_up",
                      "l_arm_low", "l_hand", "r_leg_up", "r_leg_low", "r_foot", "l_leg_up", "l_leg_low", "l_foot",
                      "main_weapon", "sub_weapon", "special_1", "special_2", "special_3", "special_4", "special_5",
                      "special_6", "special_7", "special_8", "special_9", "special_10"]
anim_column_header = ["Name"]
for p in range(1, max_person + 1):
    p_name = "p" + str(p) + "_"
    anim_column_header += [p_name + item for item in part_column_header]
anim_column_header += ["effect_1", "effect_2", "effect_3", "effect_4", "effect_5", "effect_6", "effect_7",
                       "effect_8",
                       "frame_property", "animation_property", "sound_effect"]  # For csv saving and accessing
frame_property_list = ["hold", "stoppable", "play_time_mod_", "effect_blur_", "effect_fade_",
                       "effect_contrast_", "effect_brightness_", "effect_grey",
                       "effect_colour_"]  # starting property list

anim_property_list = ["interuptrevert", "norestart"] + frame_property_list

"""Property explanation:

hold: Frame or entire animation can be played until release from holding input
play_time_mod_: Value of play time modification, higher mean longer play time
effect_blur_: Put blur effect on entire frame based on the input value
effect_contrast_: Put colour contrast effect on entire frame based on the input value
effect_brightness_: Change brightness of entire frame based on the input value
effect_fade_: Put fade effect on entire frame based on the input value
effect_grey: Put greyscale effect on entire frame
effect_colour_: Colourise entire frame based on the input value
"""


def reload_animation(animation, char, specific_frame=None):
    """Reload animation frames"""
    frames = [this_image for this_image in char.animation_list if
              this_image is not None]
    for frame_index in range(max_frame):
        if (not specific_frame and activate_list[frame_index]) or (specific_frame and frame_index == specific_frame):
            for prop in frame_property_select[frame_index] + anim_property_select:
                if "effect" in prop:
                    size = frames[frame_index].get_size()
                    data = pygame.image.tobytes(frames[frame_index],
                                                "RGBA")  # convert image to string data for filtering effect
                    surface = Image.frombytes("RGBA", size, data)  # use PIL to get image data
                    alpha = surface.split()[-1]  # save alpha
                    if "grey" in prop:  # not work with just convert L for some reason
                        surface = surface.convert("L")
                        surface = ImageOps.colorize(surface, black="black", white="white").convert("RGB")
                    if "blur" in prop:
                        surface = surface.filter(
                            ImageFilter.GaussianBlur(
                                radius=float(
                                    prop[prop.rfind("_") + 1:])))  # blur Image (or apply other filter in future)
                    if "contrast" in prop:
                        enhancer = ImageEnhance.Contrast(surface)
                        surface = enhancer.enhance(float(prop[prop.rfind("_") + 1:]))
                    if "brightness" in prop:
                        enhancer = ImageEnhance.Brightness(surface)
                        surface = enhancer.enhance(float(prop[prop.rfind("_") + 1:]))
                    if "fade" in prop:
                        empty = pygame.Surface(size, pygame.SRCALPHA)
                        empty.fill((255, 255, 255, 255))
                        empty = pygame.image.tobytes(empty, "RGBA")  # convert image to string data for filtering effect
                        empty = Image.frombytes("RGBA", frames[frame_index].get_size(),
                                                empty)  # use PIL to get image data
                        surface = Image.blend(surface, empty, alpha=float(prop[prop.rfind("_") + 1:]) / 10)
                    surface.putalpha(alpha)  # put back alpha
                    surface = surface.tobytes()
                    surface = pygame.image.frombytes(surface, size, "RGBA")  # convert image back to a pygame surface
                    if "colour" in prop:
                        colour = prop[prop.rfind("_") + 1:]
                        colour = [int(this_colour) for this_colour in colour.split(".")]
                        surface = apply_colour(surface, colour)
                    frames[frame_index] = surface
        filmstrip_list[frame_index].add_strip(frames[frame_index])
    animation.reload(frames)

    for helper in helper_list:
        helper.stat1 = char.part_name_list[current_frame]
        helper.stat2 = char.animation_part_list[current_frame]
        if char.part_selected:  # not empty
            for part in char.part_selected:
                part = tuple(char.mask_part_list.keys())[part]
                helper.select_part((0, 0), True, False, specific_part=part)
        else:
            helper.select_part(None, shift_press, False)
        helper.blit_part()


def property_to_pool_data(which):
    if which == "anim":
        for frame in model.frame_list:
            frame["animation_property"] = select_list
        if anim_prop_list_box.rect.collidepoint(mouse_pos):
            for frame in range(len(current_pool[animation_race][animation_name])):
                current_pool[animation_race][animation_name][frame]["animation_property"] = select_list.copy()
    elif which == "frame":
        model.frame_list[current_frame]["frame_property"] = select_list.copy()
        current_pool[animation_race][animation_name][current_frame]["frame_property"] = select_list.copy()


def change_animation_race(new_race):
    global animation_race

    animation_race = new_race
    for p in range(1, max_person + 1):
        model.sprite_mode |= {p: "Normal"}
    sprite_mode_selector.change_name("Normal")
    change_animation(tuple(current_pool[animation_race].keys())[0])


def change_animation_chapter(new_chapter, change_race=True):
    global animation_chapter, animation_pool_data, part_name_header, body_sprite_pool, effect_sprite_pool
    animation_pool_data, part_name_header = read_anim_data(join(animation_dir, str(animation_chapter)),
                                                           anim_column_header)
    body_sprite_pool = {}
    for char in char_list:
        if char != "":
            race_file_name = fcv(char, revert=True)
            try:
                [split(
                    os.sep.join(normpath(x).split(os.sep)[normpath(x).split(os.sep).index("sprite"):]))
                    for
                    x in Path(join(animation_dir, "sprite", "character", race_file_name)).iterdir() if
                    x.is_dir()]  # check if char folder exist

                body_sprite_pool[char] = {}
                part_folder = Path(join(animation_dir, "sprite", "character", race_file_name))
                sub1_directories = [split(
                    os.sep.join(
                        normpath(x).split(os.sep)[normpath(x).split(os.sep).index(race_file_name):]))
                    for x in part_folder.iterdir() if x.is_dir()]

                for folder1 in sub1_directories:
                    body_sprite_pool[char][folder1[-1]] = {}
                    sub_part_folder = Path(
                        join(animation_dir, "sprite", "character", race_file_name, folder1[-1],
                             str(animation_chapter)))
                    recursive_image_load(body_sprite_pool[char][folder1[-1]], screen_scale, sub_part_folder)

            except FileNotFoundError as b:
                print("file not found", b)

    effect_sprite_pool = {}
    part_folder = Path(join(animation_dir, "sprite", "effect"))
    sub1_directories = [split(
        sep.join(normpath(x).split(sep)[normpath(x).split(sep).index("animation"):])) for x
        in part_folder.iterdir() if x.is_dir()]
    for folder_base in sub1_directories:
        effect_sprite_pool[fcv(folder_base[-1])] = {}
        part_folder2 = Path(join(animation_dir, "sprite", "effect", folder_base[-1]))
        subdirectories = [split(
            sep.join(normpath(x).split(sep)[normpath(x).split(sep).index("animation"):])) for x
            in part_folder2.iterdir() if x.is_dir()]
        for folder in subdirectories:  # chapter
            folder_data_name = fcv(folder[-1])
            if int(folder_data_name) >= new_chapter:
                images = load_images(part_folder2, subfolder=(folder[-1],), key_file_name_readable=True)
                true_name_list = []
                for key, value in images.items():
                    if key.split("_")[-1].isdigit():
                        true_name = " ".join([string for string in key.split("_")[:-1]]) + "#"
                    else:
                        true_name = key
                    if true_name not in true_name_list:
                        true_name_list.append(true_name)

                for true_name in set(true_name_list):  # create effect animation list
                    final_name = true_name
                    if "#" in true_name:  # has animation to play
                        final_name = true_name[:-1]
                        sprite_animation_list = [value for key, value in images.items() if final_name ==
                                                 " ".join([string for string in key.split("_")[:-1]])]
                    else:  # single frame animation
                        sprite_animation_list = [value for key, value in images.items() if
                                                 final_name == key]

                    effect_sprite_pool[fcv(folder_base[-1])][final_name] = sprite_animation_list

    animation_chapter = new_chapter
    if change_race:
        change_animation_race("Miquella")


def change_animation(new_name):
    global animation_name, current_frame, current_anim_row, current_frame_row, anim_property_select, frame_property_select
    anim_prop_list_box.namelist = anim_property_list + ["Custom"]  # reset property list
    anim_property_select = []
    frame_prop_list_box.namelist = [frame_property_list + ["Custom"] for _ in range(max_frame)]
    frame_property_select = [[] for _ in range(max_frame)]
    current_anim_row = 0
    current_frame_row = 0
    model.read_animation(new_name)
    if not activate_list[current_frame]:
        current_frame = 0
        setup_list(NameList, current_frame_row, frame_prop_list_box.namelist[current_frame], frame_prop_namegroup,
                   frame_prop_list_box, ui, screen_scale, layer=9,
                   old_list=frame_property_select[current_frame])  # change frame property list
    anim.show_frame = current_frame
    animation_name = new_name
    animation_selector.change_name(new_name)
    reload_animation(anim, model)
    anim_prop_list_box.scroll.change_image(new_row=0, row_size=len(anim_prop_list_box.namelist))
    frame_prop_list_box.scroll.change_image(new_row=0, row_size=len(frame_prop_list_box.namelist[current_frame]))
    model.clear_history()

    if "sound_effect" in model.frame_list[current_frame] and model.frame_list[current_frame]["sound_effect"]:
        sound_selector.change_name(str(model.frame_list[current_frame]["sound_effect"][0]))
        sound_distance_selector.change_name(str(model.frame_list[current_frame]["sound_effect"][1]))
    else:
        sound_selector.change_name("None")
        sound_distance_selector.change_name("")


def change_frame_process():
    global current_frame_row
    anim.show_frame = current_frame
    model.edit_part(mouse_pos, "change")
    if model.frame_list[current_frame]["sound_effect"]:
        sound_selector.change_name(str(model.frame_list[current_frame]["sound_effect"][0]))
        sound_distance_selector.change_name(str(model.frame_list[current_frame]["sound_effect"][1]))
    else:
        sound_selector.change_name("None")
        sound_distance_selector.change_name("")
    current_frame_row = 0
    setup_list(NameList, current_frame_row, frame_prop_list_box.namelist[current_frame], frame_prop_namegroup,
               frame_prop_list_box, ui, screen_scale, layer=9,
               old_list=frame_property_select[current_frame])  # change frame property list


def recal_camera_pos(model):
    global showroom_base_point, showroom
    showroom_base_point = ((default_sprite_size[0] * model.size / 2) + (showroom_camera_pos[0] * model.size),
                           (default_sprite_size[1] * model.size * 0.8) + (showroom_camera_pos[1] * model.size))
    showroom.showroom_base_point = ((showroom_size[0] / 2) + showroom_camera_pos[0],
                                    (showroom_size[1] * 0.8) + showroom_camera_pos[1])


animation_race = "Miquella"
animation_chapter = 1

char_list = []
for x in Path(join(animation_dir, "sprite", "character")).iterdir():  # grab char with sprite
    if normpath(x).split(os.sep)[-1] != "weapon":  # exclude weapon as char
        char_list.append(fcv(normpath(x).split(os.sep)[-1]))

chapter_list = []
for x in Path(join(animation_dir)).iterdir():  # grab folder with number chapter
    if normpath(x).split(os.sep)[-1].isdigit():  # exclude weapon as char
        chapter_list.append(int(normpath(x).split(os.sep)[-1]))

animation_pool_data = {}
part_name_header = {}
body_sprite_pool = {}
effect_sprite_pool = {}

change_animation_chapter(animation_chapter, change_race=False)

try:
    animation_name = tuple(animation_pool_data[animation_race].keys())[0]
except:
    animation_name = None

with open(join(data_dir, "character", "character.csv"),
          encoding="utf-8", mode="r") as edit_file:
    rd = tuple(csv.reader(edit_file, quoting=csv.QUOTE_ALL))
    for row_index, row in enumerate(rd[1:]):
        if row[0] not in char_list:
            char_list.append(row[0])

default_mode = {}
with open(join(data_dir, "animation", "template.csv"),
          encoding="utf-8", mode="r") as edit_file:
    rd = tuple(csv.reader(edit_file, quoting=csv.QUOTE_ALL))
    for index, stuff in enumerate(rd[0]):
        if "special" in stuff:  # remove number after special
            rd[0][index] = "_".join(rd[0][index].split("_")[:-1])
    default_mode["Normal"] = {stuff: "Normal" for
                              index, stuff in enumerate(rd[0]) if stuff[0] == "p"}

character_mode_list = {}
for char in char_list:
    character_mode_list[char] = {}
    if os.path.exists(
            os.path.join(data_dir, "character", "character", char + ".csv")):
        with open(os.path.join(data_dir, "character", "character", char + ".csv"),
                  encoding="utf-8", mode="r") as edit_file2:
            rd2 = tuple(csv.reader(edit_file2, quoting=csv.QUOTE_ALL))
            header2 = rd2[0]
            for row_index2, row2 in enumerate(rd2[1:]):
                character_mode_list[char][row2[0]] = {header2[index + 1]: stuff for
                                                      index, stuff in enumerate(row2[1:])}
    else:  # no specific mode list, has only normal mode
        character_mode_list[char]["Normal"] = default_mode["Normal"]

sound_effect_pool = SoundData().sound_effect_pool


class Filmstrip(pygame.sprite.Sprite):
    """animation sprite filmstrip"""
    base_image = None

    def __init__(self, pos):
        self._layer = 5
        pygame.sprite.Sprite.__init__(self, self.containers)
        self.pos = pos
        self.image = self.base_image.copy()  # original no sprite
        self.base_image2 = self.base_image.copy()  # after add sprite but before activate or deactivate
        self.base_image3 = self.base_image2.copy()  # before adding selected corner
        self.rect = self.image.get_rect(topleft=self.pos)
        self.image_scale = (self.image.get_width() / 100, self.image.get_height() / 120)
        self.blit_image = None
        self.strip_rect = None
        self.activate = False

    def update(self, *args):
        self.image = self.base_image3.copy()

    def selected(self, select=False):
        self.image = self.base_image3.copy()
        select_colour = (200, 100, 100)
        if self.activate:
            select_colour = (150, 200, 100)
        if select:
            pygame.draw.rect(self.image, select_colour, (0, 0, self.image.get_width(), self.image.get_height()),
                             int(self.image.get_width() / 5))

    def add_strip(self, image=None, change=True):
        if change:
            self.image = self.base_image.copy()
            if image is not None:
                self.blit_image = smoothscale(image.copy(), (
                    int(100 * self.image_scale[0]), int(100 * self.image_scale[1])))
                self.strip_rect = self.blit_image.get_rect(
                    center=(self.image.get_width() / 2, self.image.get_height() / 2))
                self.image.blit(self.blit_image, self.strip_rect)
            self.base_image2 = self.image.copy()
        else:
            self.image = self.base_image2.copy()
        self.base_image3 = self.base_image2.copy()
        if not self.activate:  # draw black corner and replace film dot
            pygame.draw.rect(self.base_image3, (0, 0, 0), (0, 0, self.image.get_width(), self.image.get_height()),
                             int(self.image.get_width() / 5))


class Button(pygame.sprite.Sprite):
    """Normal button"""

    def __init__(self, text, image, pos, description=None, font_size=16):
        self._layer = 5
        pygame.sprite.Sprite.__init__(self, self.containers)
        self.font = pygame.font.Font(Game.ui_font["text_paragraph"], int(font_size * screen_scale[1]))
        self.image = image.copy()
        self.base_image = self.image.copy()
        self.description = description
        self.text = text
        self.pos = pos
        text_surface = self.font.render(str(text), True, (0, 0, 0))
        text_rect = text_surface.get_rect(center=(int(self.image.get_width() / 2), int(self.image.get_height() / 2)))
        self.image.blit(text_surface, text_rect)
        self.rect = self.image.get_rect(center=self.pos)

    def change_text(self, text):
        if text != self.text:
            self.image = self.base_image.copy()
            self.text = text
            text_surface = self.font.render(self.text.capitalize(), True, (0, 0, 0))
            text_rect = text_surface.get_rect(
                center=(int(self.image.get_width() / 2), int(self.image.get_height() / 2)))
            self.image.blit(text_surface, text_rect)
            self.rect = self.image.get_rect(center=self.pos)

    def update(self, *args):
        if "ON" in help_button.text:  # enable help description
            if self.rect.collidepoint(mouse_pos) and self.description is not None and not mouse_left_up:
                text_popup.popup(cursor.rect, self.description)
                ui.add(text_popup)


class SwitchButton(Button):
    """Button that switch text/option"""

    def __init__(self, text_list, image, pos, description=None, font_size=16):
        self.current_option = 0
        self.text_list = text_list
        self.text = self.text_list[self.current_option]
        Button.__init__(self, self.text, image, pos, description, font_size)
        self.change_text(self.text)

    def change_option(self, option):
        if self.current_option != option:
            self.current_option = option
            self.image = self.base_image.copy()
            self.text = self.text_list[self.current_option]
            self.change_text(self.text)

    def change_text(self, text):
        text_surface = self.font.render(str(text), True, (0, 0, 0))
        text_rect = text_surface.get_rect(center=(int(self.image.get_width() / 2), int(self.image.get_height() / 2)))
        self.image.blit(text_surface, text_rect)


class BodyHelper(pygame.sprite.Sprite):
    def __init__(self, size, pos, ui_type, part_images):
        self._layer = 6
        pygame.sprite.Sprite.__init__(self, self.containers)
        self.font_size = int(9 * screen_scale[1])
        self.font = pygame.font.Font(Game.ui_font["text_paragraph"], self.font_size)
        self.size = size
        self.image = pygame.Surface(self.size, pygame.SRCALPHA)
        self.image.fill((255, 255, 200))
        pygame.draw.rect(self.image, (100, 150, 150), (0, 0, self.image.get_width(), self.image.get_height()), 3)
        self.base_image = self.image.copy()  # for original before add part and click
        self.rect = self.image.get_rect(center=pos)
        self.ui_type = ui_type
        self.part_images_original = [image.copy() for image in part_images]
        if "effect" not in self.ui_type:
            self.box_font = pygame.font.Font(Game.ui_font["text_paragraph"], int(22 * screen_scale[1]))
            empty_box = self.part_images_original[-1]
            self.part_images_original = self.part_images_original[:-1]
            for box_part in ("W1", "W2"):
                text_surface = self.box_font.render(box_part, True, (0, 0, 0))
                text_rect = text_surface.get_rect(center=(empty_box.get_width() / 2, empty_box.get_height() / 2))
                new_box = empty_box.copy()
                new_box.blit(text_surface, text_rect)
                self.part_images_original.append(new_box)
        else:
            self.box_font = pygame.font.Font(Game.ui_font["text_paragraph"], int(18 * screen_scale[1]))
            empty_box = self.part_images_original[0]
            self.part_images_original = self.part_images_original[:-1]
            for box_part in ("S1", "S2", "S3", "S4", "S5", "E1", "E2", "E3", "E4",
                             "S6", "S7", "S8", "S9", "S10", "E5", "E6", "E7", "E8"):
                text_surface = self.box_font.render(box_part, True, (0, 0, 0))
                text_rect = text_surface.get_rect(center=(empty_box.get_width() / 2, empty_box.get_height() / 2))
                new_box = empty_box.copy()
                new_box.blit(text_surface, text_rect)
                self.part_images_original.append(new_box)
        self.part_images = [image.copy() for image in self.part_images_original]
        self.selected_part_images = [apply_colour(image, (34, 177, 76), white_colour=False) for image in
                                     self.part_images_original]
        self.part_selected = []
        self.stat1 = {}
        self.stat2 = {}
        self.change_p_type(self.ui_type)
        for key, item in self.part_pos.items():
            self.part_pos[key] = (item[0] * screen_scale[0], item[1] * screen_scale[1])
        self.blit_part()

    def change_p_type(self, new_type, player_change=False):
        """For helper that can change person"""
        self.ui_type = new_type
        if "effect" not in self.ui_type:
            self.rect_part_list = {self.ui_type + "_head": None, self.ui_type + "_neck": None,
                                   self.ui_type + "_body": None, self.ui_type + "_r_arm_up": None,
                                   self.ui_type + "_r_arm_low": None, self.ui_type + "_r_hand": None,
                                   self.ui_type + "_l_arm_up": None, self.ui_type + "_l_arm_low": None,
                                   self.ui_type + "_l_hand": None,
                                   self.ui_type + "_r_leg_up": None, self.ui_type + "_r_leg_low": None,
                                   self.ui_type + "_r_foot": None,
                                   self.ui_type + "_l_leg_up": None, self.ui_type + "_l_leg_low": None,
                                   self.ui_type + "_l_foot": None, self.ui_type + "_main_weapon": None,
                                   self.ui_type + "_sub_weapon": None}
            self.part_pos = {self.ui_type + "_head": (self.image.get_width() / 2, 70),
                             self.ui_type + "_neck": (self.image.get_width() / 2, 100),
                             self.ui_type + "_body": (self.image.get_width() / 2, 140),
                             self.ui_type + "_r_arm_up": (self.image.get_width() / 2 -
                                                          (self.image.get_width() / 20), 105),
                             self.ui_type + "_r_arm_low": (self.image.get_width() / 2 -
                                                           (self.image.get_width() / 20), 135),
                             self.ui_type + "_r_hand": (self.image.get_width() / 2 -
                                                        (self.image.get_width() / 20), 165),
                             self.ui_type + "_l_arm_up": (self.image.get_width() / 2 +
                                                          (self.image.get_width() / 20), 105),
                             self.ui_type + "_l_arm_low": (self.image.get_width() / 2 +
                                                           (self.image.get_width() / 20), 135),
                             self.ui_type + "_l_hand": (self.image.get_width() / 2 +
                                                        (self.image.get_width() / 20), 165),
                             self.ui_type + "_r_leg_up": (self.image.get_width() / 2 -
                                                          (self.image.get_width() / 40), 195),
                             self.ui_type + "_r_leg_low": (self.image.get_width() / 2 -
                                                           (self.image.get_width() / 40), 226),
                             self.ui_type + "_r_foot": (self.image.get_width() / 2 -
                                                        (self.image.get_width() / 40), 256),
                             self.ui_type + "_l_leg_up": (self.image.get_width() / 2 +
                                                          (self.image.get_width() / 40), 195),
                             self.ui_type + "_l_leg_low": (self.image.get_width() / 2 +
                                                           (self.image.get_width() / 40), 226),
                             self.ui_type + "_l_foot": (self.image.get_width() / 2 +
                                                        (self.image.get_width() / 40), 256),
                             self.ui_type + "_main_weapon": (self.image.get_width() / 2 -
                                                             (self.image.get_width() / 20), 25),
                             self.ui_type + "_sub_weapon": (self.image.get_width() / 2 +
                                                            (self.image.get_width() / 20), 25)}
        else:
            p_type = self.ui_type[:2]
            self.rect_part_list = {p_type + "_special_1": None, p_type + "_special_2": None,
                                   p_type + "_special_3": None,
                                   p_type + "_special_4": None, p_type + "_special_5": None,
                                   "effect_1": None, "effect_2": None, "effect_3": None, "effect_4": None,
                                   p_type + "_special_6": None, p_type + "_special_7": None,
                                   p_type + "_special_8": None,
                                   p_type + "_special_9": None, p_type + "_special_10": None,
                                   "effect_5": None, "effect_6": None, "effect_7": None, "effect_8": None}
            self.part_pos = {p_type + "_special_1": (20, 15), p_type + "_special_2": (20, 45),
                             p_type + "_special_3": (20, 75),
                             p_type + "_special_4": (20, 105), p_type + "_special_5": (20, 135),
                             "effect_1": (20, 165), "effect_2": (20, 195), "effect_3": (20, 225), "effect_4": (20, 255),
                             p_type + "_special_6": (300, 15), p_type + "_special_7": (300, 45),
                             p_type + "_special_8": (300, 75),
                             p_type + "_special_9": (300, 105), p_type + "_special_10": (300, 135),
                             "effect_5": (300, 165), "effect_6": (300, 195), "effect_7": (300, 225),
                             "effect_8": (300, 255)}
        if player_change:
            self.select_part(None, False, False)  # reset first
            for part in model.part_selected:  # blit selected part that is in helper
                if tuple(model.mask_part_list.keys())[part] in self.rect_part_list:
                    self.select_part(mouse_pos, True, False, tuple(model.mask_part_list.keys())[part])
            self.blit_part()

    def blit_part(self):
        self.image = self.base_image.copy()
        for index, image in enumerate(self.part_images):
            this_key = tuple(self.part_pos.keys())[index]
            pos = self.part_pos[this_key]
            new_image = image
            if this_key in self.part_selected:  # highlight selected part
                new_image = self.selected_part_images[index]

            rect = new_image.get_rect(center=pos)
            self.image.blit(new_image, rect)
            self.rect_part_list[this_key] = rect
        self.add_stat()

    def select_part(self, check_mouse_pos, shift_press, ctrl_press, specific_part=None):
        return_selected_part = None
        if specific_part is not None:
            if not specific_part:
                self.part_selected = []
            elif specific_part in list(self.part_pos.keys()):
                if shift_press:
                    if specific_part not in self.part_selected:
                        self.part_selected.append(specific_part)
                elif ctrl_press:
                    if specific_part in self.part_selected:
                        self.part_selected.remove(specific_part)
                else:
                    self.part_selected = [specific_part]
        else:  # click on helper ui
            click_any = False
            if check_mouse_pos is not None:
                for index, rect in enumerate(self.rect_part_list):
                    this_rect = self.rect_part_list[rect]
                    if this_rect is not None and this_rect.collidepoint(check_mouse_pos):
                        click_any = True
                        return_selected_part = tuple(self.part_pos.keys())[index]
                        if shift_press:
                            if tuple(self.part_pos.keys())[index] not in self.part_selected:
                                self.part_selected.append(tuple(self.part_pos.keys())[index])
                        elif ctrl_press:
                            if tuple(self.part_pos.keys())[index] in self.part_selected:
                                self.part_selected.remove(tuple(self.part_pos.keys())[index])
                        else:
                            self.part_selected = [tuple(self.part_pos.keys())[index]]
                            break
            if check_mouse_pos is None or (
                    not click_any and (not shift_press and not ctrl_press)):  # click at empty space
                self.part_selected = []

        return return_selected_part

    def add_stat(self):
        for index, part in enumerate(self.rect_part_list):
            if self.stat2 is not None and part in self.stat2 and self.stat1[part] is not None and self.stat2[
                part] is not None:
                stat = self.stat1[part] + self.stat2[part]
                if len(stat) > 2:
                    stat.pop(2)
                    stat.pop(2)

                stat[1] = str(stat[1])
                if len(stat) > 3:
                    try:
                        stat[2] = str([[int(stat[2][0]), int(stat[2][1])]])
                    except TypeError:
                        stat[2] = str([0, 0])
                    for index2, change in enumerate(["F", "FH", "FV", "FHV"]):
                        if stat[4] == index2:
                            stat[4] = change
                    stat[3] = str(round(stat[3], 1))
                    stat[5] = "L" + str(int(stat[5]))

                stat1 = stat[0:2]  # first line with part char, name
                stat1 = str(stat1).replace("'", "")
                stat2 = stat[2:]  # second line with stat
                stat2 = str(stat2).replace("'", "")

                text_colour = (0, 0, 0)
                if part in self.part_selected:  # green text for selected part
                    text_colour = (20, 90, 20)
                text_surface1 = self.font.render(stat1, True, text_colour)

                text_surface2 = self.font.render(stat2, True, text_colour)
                shift_x = 50 * screen_scale[0]
                if any(ext in part for ext in ("effect", "special")):
                    shift_x = 30 * screen_scale[0]
                    text_rect1 = text_surface1.get_rect(
                        midleft=(self.part_pos[part][0] + shift_x, self.part_pos[part][1] - 10))
                    text_rect2 = text_surface2.get_rect(
                        midleft=(self.part_pos[part][0] + shift_x, self.part_pos[part][1] - 10 + self.font_size + 2))
                elif "body" in part:
                    head_name = part[0:2] + "_head"
                    text_rect1 = text_surface1.get_rect(
                        midleft=(self.part_pos[head_name][0] + shift_x, self.part_pos[head_name][1] - 5))
                    text_rect2 = text_surface2.get_rect(
                        midleft=(
                            self.part_pos[head_name][0] + shift_x,
                            self.part_pos[head_name][1] - 5 + self.font_size + 2))
                elif "neck" in part:
                    head_name = part[0:2] + "_head"
                    text_rect1 = text_surface1.get_rect(
                        midleft=(self.part_pos[head_name][0] + shift_x, self.part_pos[head_name][1] - 25))
                    text_rect2 = text_surface2.get_rect(
                        midleft=(
                            self.part_pos[head_name][0] + shift_x,
                            self.part_pos[head_name][1] - 25 + self.font_size + 2))
                elif "head" in part:
                    text_rect1 = text_surface1.get_rect(
                        midright=(self.part_pos[part][0] - shift_x, self.part_pos[part][1] - 10))
                    text_rect2 = text_surface2.get_rect(
                        midright=(self.part_pos[part][0] - shift_x, self.part_pos[part][1] - 10 + self.font_size + 2))
                else:
                    shift_x = 14 * screen_scale[0]
                    if "weapon" in part:
                        shift_x = 26 * screen_scale[0]
                    if self.part_pos[part][0] > self.image.get_width() / 2:
                        text_rect1 = text_surface1.get_rect(
                            midleft=(self.part_pos[part][0] + shift_x, self.part_pos[part][1] - 15))
                        text_rect2 = text_surface2.get_rect(
                            midleft=(
                                self.part_pos[part][0] + shift_x, self.part_pos[part][1] - 15 + self.font_size + 2))
                    else:
                        text_rect1 = text_surface1.get_rect(
                            midright=(self.part_pos[part][0] - shift_x, self.part_pos[part][1] - 15))
                        text_rect2 = text_surface2.get_rect(
                            midright=(
                                self.part_pos[part][0] - shift_x, self.part_pos[part][1] - 15 + self.font_size + 2))
                self.image.blit(text_surface1, text_rect1)
                self.image.blit(text_surface2, text_rect2)
            # else:
            #     text_surface = self.font.render("None", 1, (0, 0, 0))
            #     text_rect = text_surface.get_rect(midleft=self.part_pos[part])
            #     self.image.blit(text_surface, text_rect)


class NameBox(pygame.sprite.Sprite):
    def __init__(self, size, pos, description=None):
        self._layer = 6
        pygame.sprite.Sprite.__init__(self, self.containers)
        self.font_size = int(22 * screen_scale[1])
        self.font = pygame.font.Font(Game.ui_font["text_paragraph"], int(self.font_size * screen_scale[1]))
        self.description = description
        self.size = size
        self.image = pygame.Surface(self.size)
        self.image.fill((182, 233, 242))
        pygame.draw.rect(self.image, (100, 200, 0), (0, 0, self.image.get_width(), self.image.get_height()), 2)
        self.base_image = self.image.copy()
        self.pos = pos
        self.rect = self.image.get_rect(midtop=self.pos)
        self.text = None

    def change_name(self, text):
        if text != self.text:
            self.image = self.base_image.copy()
            self.text = text
            text_surface = self.font.render(self.text, True, (0, 0, 0))
            text_rect = text_surface.get_rect(
                center=(int(self.image.get_width() / 2), int(self.image.get_height() / 2)))
            self.image.blit(text_surface, text_rect)

    def update(self, *args):
        if "ON" in help_button.text:  # enable help description
            if self.rect.collidepoint(mouse_pos) and self.description is not None and not mouse_left_up:
                text_popup.popup(cursor.rect, self.description)
                ui.add(text_popup)


class ColourWheel(pygame.sprite.Sprite):
    def __init__(self, image, pos):
        self._layer = 30
        pygame.sprite.Sprite.__init__(self)
        self.image = image
        self.pos = pos
        self.rect = self.image.get_rect(center=self.pos)

    def get_colour(self):
        pos = mouse_pos[0] - self.rect.topleft[0], mouse_pos[1] - self.rect.topleft[1]
        colour = self.image.get_at(pos)  # get colour at pos
        return colour


class Model:
    def __init__(self):
        self.animation_list = {}  # dict of animation frame image surface
        self.animation_part_list = {}  # dict of part image surface
        self.bodypart_list = []  # list of part stat
        self.part_name_list = []  # list of part name
        self.frame_list = [{}] * max_frame
        self.current_history = -1  # start with -1 as the first history will be added later to 0
        self.animation_history = []
        self.body_part_history = []
        self.part_name_history = []
        self.mask_part_list = {}
        self.all_part_list = {}
        for p in range(1, max_person + 1):
            self.mask_part_list = self.mask_part_list | {"p" + str(p) + "_head": None,
                                                         "p" + str(p) + "_neck": None,
                                                         "p" + str(p) + "_body": None,
                                                         "p" + str(p) + "_r_arm_up": None,
                                                         "p" + str(p) + "_r_arm_low": None,
                                                         "p" + str(p) + "_r_hand": None,
                                                         "p" + str(p) + "_l_arm_up": None,
                                                         "p" + str(p) + "_l_arm_low": None,
                                                         "p" + str(p) + "_l_hand": None,
                                                         "p" + str(p) + "_r_leg_up": None,
                                                         "p" + str(p) + "_r_leg_low": None,
                                                         "p" + str(p) + "_r_foot": None,
                                                         "p" + str(p) + "_l_leg_up": None,
                                                         "p" + str(p) + "_l_leg_low": None,
                                                         "p" + str(p) + "_l_foot": None,
                                                         "p" + str(p) + "_main_weapon": None,
                                                         "p" + str(p) + "_sub_weapon": None,
                                                         "p" + str(p) + "_special_1": None,
                                                         "p" + str(p) + "_special_2": None,
                                                         "p" + str(p) + "_special_3": None,
                                                         "p" + str(p) + "_special_4": None,
                                                         "p" + str(p) + "_special_5": None,
                                                         "p" + str(p) + "_special_6": None,
                                                         "p" + str(p) + "_special_7": None,
                                                         "p" + str(p) + "_special_8": None,
                                                         "p" + str(p) + "_special_9": None,
                                                         "p" + str(p) + "_special_10": None}
            self.all_part_list = self.all_part_list | {"p" + str(p) + "_head": None,
                                                       "p" + str(p) + "_neck": None,
                                                       "p" + str(p) + "_body": None, "p" + str(p) + "_r_arm_up": None,
                                                       "p" + str(p) + "_r_arm_low": None,
                                                       "p" + str(p) + "_r_hand": None,
                                                       "p" + str(p) + "_l_arm_up": None,
                                                       "p" + str(p) + "_l_arm_low": None,
                                                       "p" + str(p) + "_l_hand": None,
                                                       "p" + str(p) + "_r_leg_up": None,
                                                       "p" + str(p) + "_r_leg_low": None,
                                                       "p" + str(p) + "_r_foot": None,
                                                       "p" + str(p) + "_l_leg_up": None,
                                                       "p" + str(p) + "_l_leg_low": None,
                                                       "p" + str(p) + "_l_foot": None,
                                                       "p" + str(p) + "_main_weapon": None,
                                                       "p" + str(p) + "_sub_weapon": None,
                                                       "p" + str(p) + "_special_1": None,
                                                       "p" + str(p) + "_special_2": None,
                                                       "p" + str(p) + "_special_3": None,
                                                       "p" + str(p) + "_special_4": None,
                                                       "p" + str(p) + "_special_5": None,
                                                       "p" + str(p) + "_special_6": None,
                                                       "p" + str(p) + "_special_7": None,
                                                       "p" + str(p) + "_special_8": None,
                                                       "p" + str(p) + "_special_9": None,
                                                       "p" + str(p) + "_special_10": None}
        self.mask_part_list = self.mask_part_list | {"effect_1": None, "effect_2": None, "effect_3": None,
                                                     "effect_4": None,
                                                     "effect_5": None, "effect_6": None, "effect_7": None,
                                                     "effect_8": None,
                                                     }
        self.all_part_list = self.all_part_list | {"effect_1": None, "effect_2": None, "effect_3": None,
                                                   "effect_4": None,
                                                   "effect_5": None, "effect_6": None, "effect_7": None,
                                                   "effect_8": None}
        self.part_selected = []

        self.sprite_mode = {}
        for p in range(1, max_person + 1):
            self.sprite_mode |= {p: "Normal"}
        self.size = 1  # size scale of sprite
        try:
            self.read_animation(tuple((animation_pool_data[animation_race].keys()))[0])
        except IndexError:  # empty animation file
            self.read_animation(None)

    def make_layer_list(self, sprite_part):
        pose_layer_list = {k: v[5] for k, v in sprite_part.items() if v is not None and v != []}
        pose_layer_list = dict(sorted(pose_layer_list.items(), key=lambda item: item[1], reverse=True))
        return pose_layer_list

    def read_animation(self, name, old=False):
        global activate_list, showroom_base_point
        #  sprite animation generation from data
        self.animation_part_list = [{key: None for key in self.mask_part_list}] * max_frame
        self.animation_list = [self.create_animation_film(None, current_frame, empty=True)] * max_frame
        self.bodypart_list = [{key: value for key, value in self.all_part_list.items()}] * max_frame
        self.part_name_list = [{key: None for key in self.mask_part_list}] * max_frame
        for key, value in self.mask_part_list.items():  # reset rect list
            self.mask_part_list[key] = None

        if name is not None:
            frame_list = current_pool[animation_race][name].copy()
            if old:
                frame_list = self.frame_list
            while len(frame_list) < max_frame:  # add empty item
                frame_list.append({})

            recal_camera_pos(self)
            size_button.change_text("Zoom: " + str(self.size))
            for index, pose in enumerate(frame_list):
                sprite_part = {key: None for key in self.mask_part_list}
                link_list = {key: None for key in self.mask_part_list}
                bodypart_list = {key: value for key, value in self.all_part_list.items()}
                for part in pose:
                    if pose[part] and "property" not in part and "sound_effect" not in part:
                        link_list[part] = [pose[part][2], pose[part][3]]
                        bodypart_list[part] = [pose[part][0], pose[part][1]]

                    elif "property" in part and pose[part] != [""]:
                        if "animation" in part:
                            for stuff in pose[part]:
                                if stuff not in anim_prop_list_box.namelist:
                                    anim_prop_list_box.namelist.insert(-1, stuff)
                                if stuff not in anim_property_select:
                                    anim_property_select.append(stuff)
                        elif "frame" in part and pose[part] != 0:
                            for stuff in pose[part]:
                                if stuff not in frame_prop_list_box.namelist[index]:
                                    frame_prop_list_box.namelist[index].insert(-1, stuff)
                                if stuff not in frame_property_select[index]:
                                    frame_property_select[index].append(stuff)
                self.bodypart_list[index] = bodypart_list
                self.generate_body(self.bodypart_list[index])
                part_name = {key: None for key in self.mask_part_list}

                for part in part_name_header:
                    if part in pose and pose[part]:
                        sprite_part[part] = [self.sprite_image[part], "center", link_list[part], pose[part][4],
                                             pose[part][5], pose[part][6], pose[part][7], pose[part][8], pose[part][9]]
                        part_name[part] = [pose[part][0], pose[part][1]]
                pose_layer_list = self.make_layer_list(sprite_part)
                self.animation_part_list[index] = sprite_part
                self.part_name_list[index] = part_name
                image = self.create_animation_film(pose_layer_list, index)
                self.animation_list[index] = image
            self.frame_list = frame_list

        activate_list = [False] * max_frame
        for strip_index, strip in enumerate(filmstrips):
            strip.activate = False
            for stuff in self.animation_part_list[strip_index].values():
                if stuff:
                    strip.activate = True
                    activate_list[strip_index] = True
                    break

        # recreate property list
        anim_prop_list_box.namelist = [item for item in anim_prop_list_box.namelist if item in anim_property_select] + \
                                      [item for item in anim_prop_list_box.namelist if item not in anim_property_select]
        for frame in range(len(frame_prop_list_box.namelist)):
            frame_prop_list_box.namelist[frame] = [item for item in frame_prop_list_box.namelist[frame] if
                                                   item in frame_property_select[frame]] + \
                                                  [item for item in frame_prop_list_box.namelist[frame] if
                                                   item not in frame_property_select[frame]]

        setup_list(NameList, current_anim_row, anim_prop_list_box.namelist, anim_prop_namegroup,
                   anim_prop_list_box, ui, screen_scale, layer=9, old_list=anim_property_select)
        setup_list(NameList, current_frame_row, frame_prop_list_box.namelist[current_frame], frame_prop_namegroup,
                   frame_prop_list_box, ui, screen_scale, layer=9, old_list=frame_property_select[current_frame])

    def create_animation_film(self, pose_layer_list, frame, empty=False):
        image = pygame.Surface((default_sprite_size[0], default_sprite_size[1]),
                               pygame.SRCALPHA)  # default size will scale down later
        save_mask = False
        if frame == current_frame:
            save_mask = True
        if not empty:
            for index, layer in enumerate(pose_layer_list):
                part = self.animation_part_list[frame][layer]
                if part is not None and part[0] is not None:
                    image = self.part_to_sprite(image, part[0], layer, part[2], part[3], part[4], part[6], part[7],
                                                save_mask=save_mask)
        return image

    def generate_body(self, bodypart_list):
        self.sprite_image = {key: None for key in self.mask_part_list}

        for stuff in bodypart_list:  # create stat and sprite image
            if bodypart_list[stuff] and bodypart_list[stuff][1]:
                if "effect_" in stuff:
                    self.sprite_image[stuff] = effect_sprite_pool[bodypart_list[stuff][0]][
                        bodypart_list[stuff][1]][0].copy()
                else:
                    new_part_name = stuff
                    mode_part_check = stuff
                    p = stuff[1]
                    if any(ext in stuff for ext in p_list):
                        part_name = stuff[3:]  # remove p*number*_ to get part name
                        new_part_name = part_name
                    if "special" in stuff:
                        part_name = "special"
                        new_part_name = part_name
                        mode_part_check = "_".join(
                            mode_part_check.split("_")[0:-1])  # remove _number at the end of special
                    elif "weapon" in stuff:
                        part_name = "weapon"
                        new_part_name = part_name
                    if "r_" in part_name[0:2] or "l_" in part_name[0:2]:
                        new_part_name = part_name[2:]  # remove part side
                    try:
                        self.sprite_image[stuff] = body_sprite_pool[bodypart_list[stuff][0]][new_part_name][
                            character_mode_list[animation_race][self.sprite_mode[int(p)]][mode_part_check]][
                            bodypart_list[stuff][1]].copy()
                    except KeyError:  # try normal mode if part not exist for specified mode
                        self.sprite_image[stuff] = body_sprite_pool[bodypart_list[stuff][0]][new_part_name][
                            character_mode_list[animation_race]["Normal"][mode_part_check]][
                            bodypart_list[stuff][1]].copy()

    def click_part(self, mouse_pos, shift_press, ctrl_press, part=None):
        if part is None:
            click_part = False
            if not shift_press and not ctrl_press:
                self.part_selected = []
            else:
                click_part = True
            for index, rect in enumerate(self.mask_part_list):
                this_rect = self.mask_part_list[rect]
                if this_rect is not None and this_rect[0].collidepoint(mouse_pos) and this_rect[1].get_at(
                        mouse_pos - this_rect[0].topleft) == 1:
                    click_part = True
                    if shift_press:  # add
                        if index not in self.part_selected:
                            self.part_selected.append(index)
                    elif ctrl_press:  # remove
                        if index in self.part_selected:
                            self.part_selected.remove(index)
                    else:  # select
                        self.part_selected = [index]
                    break
            if not click_part:
                self.part_selected = []
        else:
            if shift_press:
                self.part_selected.append(tuple(self.mask_part_list.keys()).index(part))
                self.part_selected = list(set(self.part_selected))
            elif ctrl_press:
                if tuple(self.mask_part_list.keys()).index(part) in self.part_selected:
                    self.part_selected.remove(list(self.mask_part_list.keys()).index(part))
            else:
                self.part_selected = [tuple(self.mask_part_list.keys()).index(part)]

    def edit_part(self, edit_mouse_pos, edit_type, specific_frame=None, check_delay=True):
        global edit_delay, showroom_camera_pos
        if not edit_delay or not check_delay:
            edit_delay = 0.1
            edit_frame = current_frame
            key_list = list(self.mask_part_list.keys())

            if edit_type not in ("undo", "redo", "change", "new"):
                accept_history = True
                if edit_type == "place" and mouse_right_down:  # save only when release mouse for mouse input
                    accept_history = False
                if accept_history:
                    if self.current_history < len(self.animation_history) - 1:
                        self.part_name_history = self.part_name_history[
                                                 :self.current_history + 1]  # remove all future redo history
                        self.animation_history = self.animation_history[:self.current_history + 1]
                        self.body_part_history = self.body_part_history[:self.current_history + 1]
                    self.add_history()

            if edit_type == "clear":  # clear whole strip
                for part in self.part_name_list[edit_frame]:
                    self.bodypart_list[edit_frame][part] = [0, 0]
                    self.part_name_list[edit_frame][part] = ["", ""]
                    self.animation_part_list[edit_frame][part] = []
                self.part_selected = []
                frame_property_select[edit_frame] = []
                self.frame_list[edit_frame]["frame_property"] = frame_property_select[edit_frame].copy()
                setup_list(NameList, current_frame_row, frame_prop_list_box.namelist[edit_frame], frame_prop_namegroup,
                           frame_prop_list_box, ui, screen_scale, layer=9,
                           old_list=frame_property_select[edit_frame])  # change frame property list

            elif edit_type == "paste":  # paste copy part
                for part in copy_part:
                    if copy_part[part] is not None:
                        self.bodypart_list[edit_frame][part] = copy_part[part].copy()
                        self.animation_part_list[edit_frame][part] = copy_animation[part].copy()
                        self.part_name_list[edit_frame][part] = copy_name[part].copy()

            elif edit_type == "all frame selected part paste":  # paste copy part for all
                for frame in all_copy_part:
                    for part in all_copy_part[frame]:
                        if all_copy_part[frame][part] is not None:
                            self.bodypart_list[frame][part] = all_copy_part[frame][part].copy()
                            self.animation_part_list[frame][part] = all_copy_animation[frame][part].copy()
                            self.part_name_list[frame][part] = all_copy_name[frame][part].copy()
                        else:
                            self.bodypart_list[frame][part] = None
                            self.bodypart_list[frame][part] = None
                            self.part_name_list[frame][part] = None

            elif edit_type == "paste part stat":  # paste copy stat
                for part in copy_part_stat:
                    new_part = part
                    if not any(ext in part for ext in ("effect",)):
                        new_part = p_body_helper.ui_type + part[2:]
                    if copy_part_stat[part] is not None:
                        self.bodypart_list[edit_frame][new_part] = copy_part_stat[part].copy()
                        self.animation_part_list[edit_frame][new_part] = copy_animation_stat[part].copy()
                        self.part_name_list[edit_frame][new_part] = copy_name_stat[part].copy()
                    else:
                        self.bodypart_list[edit_frame][new_part] = None
                        self.animation_part_list[edit_frame][new_part] = None
                        self.part_name_list[edit_frame][new_part] = None

            elif edit_type == "undo" or edit_type == "redo":
                for frame_num, _ in enumerate(self.animation_part_list):
                    self.part_name_list[frame_num] = {key: value for key, value in
                                                      self.part_name_history[self.current_history][frame_num].items()}
                    self.animation_part_list[frame_num] = {key: (value[:].copy() if value is not None else value) for
                                                           key, value in
                                                           self.animation_history[self.current_history][
                                                               frame_num].items()}
                    self.bodypart_list[frame_num] = {key: value for key, value in
                                                     self.body_part_history[self.current_history][frame_num].items()}

            elif "sound_select:" in edit_type:  # add sound effect to frame
                sound_name = edit_type.split(":")[1]
                if sound_name == "None":
                    self.frame_list[current_frame]["sound_effect"] = []
                    sound_distance_selector.change_name("")
                else:
                    if self.frame_list[current_frame]["sound_effect"]:
                        self.frame_list[current_frame]["sound_effect"] = [sound_name,
                                                                          self.frame_list[current_frame][
                                                                              "sound_effect"][1],
                                                                          self.frame_list[current_frame][
                                                                              "sound_effect"][2]]
                    else:
                        self.frame_list[current_frame]["sound_effect"] = [sound_name, 1000, 0]
                        sound_distance_selector.change_name("1000")

            elif "_mode_select" in edit_type:
                if any(ext in edit_type for ext in p_list):
                    self.sprite_mode[int(edit_type[1])] = edit_type.split("_")[-1]
                    change_animation(animation_name)

            elif "part:" in edit_type:
                if self.part_selected:
                    part = self.part_selected[-1]
                    part_index = key_list[part]
                    part_change = edit_type[5:]
                    self.bodypart_list[edit_frame][part_index][1] = part_change
                    self.part_name_list[edit_frame][part_index][1] = part_change
                    self.generate_body(self.bodypart_list[edit_frame])
                    if not self.animation_part_list[edit_frame][part_index]:
                        self.animation_part_list[edit_frame][part_index] = [0, pygame.Vector2(0, 0), [0, 0], 0, 0, 0, 1,
                                                                            1, 0]
                        self.animation_part_list[edit_frame][part_index][1] = "center"
                    self.animation_part_list[edit_frame][part_index][0] = self.sprite_image[part_index]

            elif "race:" in edit_type:  # change char/base part type
                if self.part_selected:
                    part = self.part_selected[-1]
                    part_index = key_list[part]
                    part_change = edit_type[5:]
                    if self.bodypart_list[edit_frame][part_index] is None:
                        self.bodypart_list[edit_frame][part_index] = [0, 0]
                        self.part_name_list[edit_frame][part_index] = ["", ""]
                        self.animation_part_list[edit_frame][part_index] = []
                    self.bodypart_list[edit_frame][part_index][0] = part_change
                    self.part_name_list[edit_frame][part_index][0] = part_change
                    self.bodypart_list[edit_frame][part_index][1] = self.part_name_list[edit_frame][part_index][
                        1]  # attempt to get part again in case the initial reading not found
                    try:
                        self.generate_body(self.bodypart_list[edit_frame])
                        self.animation_part_list[edit_frame][part_index][0] = self.sprite_image[part_index]
                    except (IndexError, KeyError):
                        self.bodypart_list[edit_frame][part_index][1] = 0
                        self.part_name_list[edit_frame][part_index][1] = ""
                        self.animation_part_list[edit_frame][part_index] = []

            elif edit_type == "new":  # new animation
                self.animation_part_list = [{key: None for key in self.mask_part_list}] * max_frame
                self.bodypart_list = [{key: value for key, value in self.all_part_list.items()}] * max_frame
                self.part_name_list = [{key: None for key in self.mask_part_list}] * max_frame
                self.part_selected = []

            elif self.part_selected:
                if "place" in edit_type or "full_rotate" in edit_type:  # find center point of all selected parts
                    min_x = inf
                    min_y = inf
                    max_x = -inf
                    max_y = -inf
                    for part in self.part_selected:  # loop to find min and max point for center
                        if part < len(key_list):  # skip part that not exist
                            part_index = key_list[part]
                            if self.animation_part_list[edit_frame][part_index] and \
                                    len(self.animation_part_list[edit_frame][part_index]) > 3:
                                value = self.animation_part_list[edit_frame][part_index][2]
                                x = value[0]
                                y = value[1]
                                if min_x > x:
                                    min_x = x
                                if max_x < x:
                                    max_x = x
                                if min_y > y:
                                    min_y = y
                                if max_y < y:
                                    max_y = y
                    center = ((min_x + max_x) / 2, (min_y + max_y) / 2)  # find center of all parts

                for part in self.part_selected:
                    if part < len(key_list):  # can't edit part that not exist
                        part_index = key_list[part]
                        if self.animation_part_list[edit_frame][part_index] is not None and \
                                len(self.animation_part_list[edit_frame][part_index]) > 3:
                            if edit_type == "place":  # mouse place
                                new_point = pygame.Vector2(edit_mouse_pos)
                                offset = (self.animation_part_list[edit_frame][part_index][2][0] - center[0],
                                          self.animation_part_list[edit_frame][part_index][2][1] - center[1])
                                new_point = new_point + offset - showroom_base_point
                                self.animation_part_list[edit_frame][part_index][2] = [int(new_point[0]),
                                                                                       int(new_point[1])]

                            elif "move_" in edit_type:  # keyboard move
                                try:
                                    new_point = [self.animation_part_list[edit_frame][part_index][2][0],
                                                 self.animation_part_list[edit_frame][part_index][2][1]]
                                except TypeError:  # None position
                                    new_point = [0, 0]
                                by_how_much = 1
                                if shift_press:
                                    by_how_much = 10
                                if "up" in edit_type:
                                    new_point[1] -= by_how_much
                                elif "down" in edit_type:
                                    new_point[1] += by_how_much
                                elif "left" in edit_type:
                                    new_point[0] -= by_how_much
                                elif "right" in edit_type:
                                    new_point[0] += by_how_much
                                self.animation_part_list[edit_frame][part_index][2] = [int(new_point[0]),
                                                                                       int(new_point[1])]

                            elif "tilt_" in edit_type:  # keyboard rotate
                                new_angle = self.animation_part_list[edit_frame][part_index][3]
                                by_how_much = 1
                                if shift_press:
                                    by_how_much = 10
                                if "1" in edit_type:
                                    new_angle -= by_how_much
                                elif "2" in edit_type:
                                    new_angle += by_how_much

                                if new_angle < 0:
                                    new_angle += 360
                                elif new_angle > 360:
                                    new_angle -= 360
                                self.animation_part_list[edit_frame][part_index][3] = new_angle

                            elif "full_rotate_" in edit_type:  # keyboard rotate
                                by_how_much = 1
                                if shift_press:
                                    by_how_much = 10
                                if "_1" in edit_type:
                                    by_how_much = -by_how_much
                                new_point = rotation_xy(center, self.animation_part_list[edit_frame][part_index][2],
                                                        radians(-by_how_much))
                                self.animation_part_list[edit_frame][part_index][2] = [round(new_point[0], 0),
                                                                                       round(new_point[1], 0)]

                                new_angle = self.animation_part_list[edit_frame][part_index][3] + by_how_much

                                if new_angle < 0:
                                    new_angle += 360
                                elif new_angle > 360:
                                    new_angle -= 360

                                self.animation_part_list[edit_frame][part_index][3] = new_angle

                            elif edit_type == "rotate":  # mouse rotate
                                base_pos = (showroom_size[0] / 2, showroom_size[1] / 2)
                                rotate_radians = atan2(edit_mouse_pos[1] - base_pos[1], edit_mouse_pos[0] - base_pos[0])
                                new_angle = degrees(rotate_radians)
                                # """upper left -"""
                                if -180 <= new_angle <= -90:
                                    new_angle = -new_angle - 90

                                # """upper right +"""
                                elif -90 < new_angle < 0:
                                    new_angle = (-new_angle) - 90

                                # """lower right -"""
                                elif 0 <= new_angle <= 90:
                                    new_angle = -(new_angle + 90)

                                # """lower left +"""
                                elif 90 < new_angle <= 180:
                                    new_angle = 270 - new_angle

                                self.animation_part_list[edit_frame][part_index][3] = int(new_angle)

                            elif "scale" in edit_type:  # part scale
                                if "up" in edit_type:
                                    if "full" in edit_type or "width" in edit_type:
                                        self.animation_part_list[edit_frame][part_index][6] += 0.1
                                        self.animation_part_list[edit_frame][part_index][6] = round(
                                            self.animation_part_list[edit_frame][part_index][6],
                                            1)
                                    if "full" in edit_type or "height" in edit_type:
                                        self.animation_part_list[edit_frame][part_index][7] += 0.1
                                        self.animation_part_list[edit_frame][part_index][7] = round(
                                            self.animation_part_list[edit_frame][part_index][7],
                                            1)
                                elif "down" in edit_type:
                                    if "full" in edit_type or "width" in edit_type:
                                        self.animation_part_list[edit_frame][part_index][6] -= 0.1
                                        if self.animation_part_list[edit_frame][part_index][6] < 0:
                                            self.animation_part_list[edit_frame][part_index][6] = 0
                                        self.animation_part_list[edit_frame][part_index][6] = round(
                                            self.animation_part_list[edit_frame][part_index][6],
                                            1)
                                    if "full" in edit_type or "height" in edit_type:
                                        self.animation_part_list[edit_frame][part_index][7] -= 0.1
                                        if self.animation_part_list[edit_frame][part_index][7] < 0:
                                            self.animation_part_list[edit_frame][part_index][7] = 0
                                        self.animation_part_list[edit_frame][part_index][7] = round(
                                            self.animation_part_list[edit_frame][part_index][7],
                                            1)
                            elif "flip" in edit_type:
                                flip_type = int(edit_type[-1])
                                current_flip = self.animation_part_list[edit_frame][part_index][4]
                                if current_flip == 0:  # current no flip
                                    self.animation_part_list[edit_frame][part_index][4] = 1
                                elif current_flip == 1:  # current horizon flip
                                    self.animation_part_list[edit_frame][part_index][4] = 0
                                    # else:
                                    #     self.animation_part_list[edit_frame][part_index][4] = 3
                                if flip_type == 3:  # also mirror position
                                    new_point = [-self.animation_part_list[edit_frame][part_index][2][0],
                                                 self.animation_part_list[edit_frame][part_index][2][1]]
                                    self.animation_part_list[edit_frame][part_index][2] = new_point.copy()
                                    self.animation_part_list[edit_frame][part_index][3] *= -1
                                # elif current_flip == 2:  # current vertical flip
                                #     if flip_type == 1:
                                #         self.animation_part_list[edit_frame][part_index][4] = 3
                                #     else:
                                #         self.animation_part_list[edit_frame][part_index][4] = 0
                                # elif current_flip == 3:  # current both hori and vert flip
                                #     if flip_type == 1:
                                #         self.animation_part_list[edit_frame][part_index][4] = 2
                                #     else:
                                #         self.animation_part_list[edit_frame][part_index][4] = 1
                            elif "d_zoom" in edit_type:
                                zoom_value = int(edit_type.split(":")[-1])
                                if zoom_value > 0 and zoom_value != self.animation_part_list[edit_frame][part_index][6]:
                                    zoom_diff_percent = zoom_value / self.animation_part_list[edit_frame][part_index][6]
                                    if zoom_diff_percent < 1:
                                        zoom_diff_percent = -zoom_diff_percent
                                    else:
                                        zoom_diff_percent -= 1
                                    self.animation_part_list[edit_frame][part_index][6] = zoom_value
                                    self.animation_part_list[edit_frame][part_index][7] = zoom_value
                                    old_pos = self.animation_part_list[edit_frame][part_index][2]
                                    self.animation_part_list[edit_frame][part_index][2] = (
                                        old_pos[0] + (old_pos[0] * zoom_diff_percent),
                                        old_pos[1] + (old_pos[1] * zoom_diff_percent))
                            elif "dplus_zoom" in edit_type:
                                zoom_value = int(edit_type.split(":")[-1])
                                if zoom_value:
                                    new_zoom = round(self.animation_part_list[edit_frame][part_index][6] + zoom_value,
                                                     1)
                                    if new_zoom > 0:
                                        zoom_diff_percent = new_zoom / self.animation_part_list[edit_frame][part_index][
                                            6]
                                        if zoom_diff_percent < 1:
                                            zoom_diff_percent = -zoom_diff_percent
                                        else:
                                            zoom_diff_percent -= 1
                                        self.animation_part_list[edit_frame][part_index][6] = new_zoom
                                        self.animation_part_list[edit_frame][part_index][7] = new_zoom
                                        old_pos = self.animation_part_list[edit_frame][part_index][2]
                                        self.animation_part_list[edit_frame][part_index][2] = (
                                            old_pos[0] + (old_pos[0] * zoom_diff_percent),
                                            old_pos[1] + (old_pos[1] * zoom_diff_percent))

                            elif "DMG" in edit_type:
                                if self.animation_part_list[edit_frame][part_index][8]:
                                    self.animation_part_list[edit_frame][part_index][8] = 0
                                else:
                                    self.animation_part_list[edit_frame][part_index][8] = 1
                            elif "reset" in edit_type:
                                self.animation_part_list[edit_frame][part_index][3] = 0
                                self.animation_part_list[edit_frame][part_index][4] = 0

                            elif "delete" in edit_type:
                                self.bodypart_list[edit_frame][part_index] = None
                                self.part_name_list[edit_frame][part_index] = None
                                self.animation_part_list[edit_frame][part_index] = None

                            elif "layer_" in edit_type:
                                if "up" in edit_type:
                                    self.animation_part_list[edit_frame][part_index][5] += 1
                                elif "down" in edit_type:
                                    self.animation_part_list[edit_frame][part_index][5] -= 1
                                    if self.animation_part_list[edit_frame][part_index][5] < 0:
                                        self.animation_part_list[edit_frame][part_index][5] = 0

            for key, value in self.mask_part_list.items():  # reset rect list
                self.mask_part_list[key] = None

            # recreate frame image
            for frame_num, _ in enumerate(self.animation_list):
                if specific_frame is None or (frame_num == specific_frame):
                    pose_layer_list = self.make_layer_list(self.animation_part_list[frame_num])
                    surface = self.create_animation_film(pose_layer_list, frame_num)
                    self.animation_list[frame_num] = surface
                    old_sound_effect = []
                    if "sound_effect" in self.frame_list[frame_num]:
                        old_sound_effect = self.frame_list[frame_num]["sound_effect"]
                    self.frame_list[frame_num] = {}
                    name_list = self.part_name_list[frame_num]
                    for key in self.mask_part_list:
                        try:
                            sprite_part = self.animation_part_list[frame_num]
                            if sprite_part[key] is not None:
                                self.frame_list[frame_num][key] = name_list[key] + [sprite_part[key][2][0],
                                                                                    sprite_part[key][2][1],
                                                                                    sprite_part[key][3],
                                                                                    sprite_part[key][4],
                                                                                    sprite_part[key][5],
                                                                                    sprite_part[key][6],
                                                                                    sprite_part[key][7],
                                                                                    sprite_part[key][8]]
                            else:
                                self.frame_list[frame_num][key] = []
                        except (TypeError, IndexError):  # None type error from empty frame
                            self.frame_list[frame_num][key] = []
                    self.frame_list[frame_num]["frame_property"] = frame_property_select[frame_num].copy()
                    self.frame_list[frame_num]["animation_property"] = anim_property_select.copy()
                    self.frame_list[frame_num]["sound_effect"] = old_sound_effect
            anim_to_pool(animation_name, current_pool[animation_race], self, activate_list)
            reload_animation(anim, self, specific_frame=specific_frame)

            if edit_type == "new":
                for index, frame in enumerate(self.frame_list):  # reset all frame to empty frame like the first one
                    self.frame_list[index] = {key: value for key, value in list(self.frame_list[0].items())}
                anim_to_pool(animation_name, current_pool[animation_race], self, activate_list, new=True)

                # reset history when create new animation
                self.clear_history()

            if len(self.animation_history) > 100:  # save only last 100 activity
                new_first = len(self.animation_history) - 100
                self.part_name_history = self.part_name_history[new_first:]
                self.animation_history = self.animation_history[new_first:]
                self.body_part_history = self.body_part_history[new_first:]
                self.current_history -= new_first

    def part_to_sprite(self, surface, part, part_name, target, angle, flip, width_scale, height_scale, save_mask=False):
        part_rotated = part
        if flip:
            if flip == 1:  # horizontal only
                part_rotated = pyflip(part_rotated, True, False)
            # elif flip == 2:  # vertical only
            #     part_rotated = pygame.transform.flip(part_rotated, False, True)
            # elif flip == 3:  # flip both direction
            #     part_rotated = pygame.transform.flip(part_rotated, True, True)
        part_rotated = smoothscale(part_rotated, (part_rotated.get_width() * width_scale / self.size,
                                                  part_rotated.get_height() * height_scale / self.size))
        if angle:
            part_rotated = rotate(part_rotated, angle)  # rotate part sprite

        new_target = (
            (target[0] + showroom_base_point[0]) / self.size, (target[1] + showroom_base_point[1]) / self.size)
        rect = part_rotated.get_rect(center=new_target)
        if save_mask:
            mask = pygame.mask.from_surface(part_rotated)
            self.mask_part_list[part_name] = (rect, mask)

        surface.blit(part_rotated, rect)

        return surface

    def add_history(self):
        self.current_history += 1
        self.part_name_history.append(
            {frame_num: {key: value for key, value in self.part_name_list[frame_num].items()} for frame_num, _ in
             enumerate(self.part_name_list)})

        self.animation_history.append(
            {frame_num: {key: (value[:].copy() if value is not None else value) for key, value in
                         self.animation_part_list[frame_num].items()} for frame_num, _ in
             enumerate(self.animation_part_list)})

        self.body_part_history.append(
            {frame_num: {key: value for key, value in self.bodypart_list[frame_num].items()} for frame_num, _ in
             enumerate(self.bodypart_list)})

    def clear_history(self):
        self.part_name_history = []
        self.animation_history = []
        self.body_part_history = []
        self.current_history = 0


class Animation:
    def __init__(self, spd_ms, loop):
        self.frames = None
        self.speed_ms = 0.1
        self.start_frame = 0
        self.end_frame = 0
        self.first_time = time.time()
        self.show_frame = 0
        self.loop = loop

    def reload(self, frames):
        self.frames = frames
        self.end_frame = len(self.frames) - 1

    def play(self, surface, position, play_list):
        global current_frame
        if dt > 0 and True in play_list:
            play_speed = self.speed_ms
            if any("play_time_mod_" in item for item in frame_property_select[self.show_frame]):
                play_speed *= float([item for item in frame_property_select[self.show_frame] if
                                     "play_time_mod_" in item][0].split("_")[-1])
            elif any("play_time_mod_" in item for item in anim_property_select):
                play_speed *= float(
                    [item for item in anim_property_select if "play_time_mod_" in item][0].split("_")[-1])
            if time.time() - self.first_time >= play_speed:
                self.show_frame += 1
                while self.show_frame < max_frame and not play_list[self.show_frame]:
                    self.show_frame += 1
                self.first_time = time.time()
                if self.show_frame > self.end_frame:
                    self.show_frame = self.start_frame
                    while self.show_frame < max_frame and not play_list[self.show_frame]:
                        self.show_frame += 1
                if model.frame_list[self.show_frame]["sound_effect"]:  # play sound
                    sound_effect = pygame.mixer.find_channel()
                    if sound_effect:
                        sound_effect.set_volume(1)
                        sound_effect.play(pygame.mixer.Sound(
                            random.choice(sound_effect_pool[model.frame_list[self.show_frame]["sound_effect"][0]])))
                if "sound_effect" in model.frame_list[self.show_frame] and model.frame_list[self.show_frame][
                    "sound_effect"]:
                    sound_selector.change_name(str(model.frame_list[self.show_frame]["sound_effect"][0]))
                    sound_distance_selector.change_name(str(model.frame_list[self.show_frame]["sound_effect"][1]))
                else:
                    sound_selector.change_name("None")
                    sound_distance_selector.change_name("")
                setup_list(NameList, current_anim_row, anim_prop_list_box.namelist, anim_prop_namegroup,
                           anim_prop_list_box, ui, screen_scale, layer=9, old_list=anim_property_select)
                setup_list(NameList, current_frame_row, frame_prop_list_box.namelist[self.show_frame],
                           frame_prop_namegroup,
                           frame_prop_list_box, ui, screen_scale, layer=9,
                           old_list=frame_property_select[self.show_frame])

        surface.blit(self.frames[int(self.show_frame)], position)


# start animation maker
clock = pygame.time.Clock()

runtime = 0
mouse_timer = 0
play_animation = False
current_frame = 0
copy_animation_frame = None
copy_part = None
copy_name_frame = None
copy_animation_stat = None
current_popup_row = 0
keypress_delay = 0
point_edit = 0
text_delay = 0
edit_delay = 0
text_input_popup = (None, None)
current_pool = animation_pool_data

showroom_size = (500, 500)
showroom_camera_pos = [0, 0]
showroom_scale_mul = (default_sprite_size[0] / showroom_size[0], default_sprite_size[1] / showroom_size[1])
showroom = showroom.Showroom(showroom_size, screen_size)
showroom_base_point = ((default_sprite_size[0] / 2) + showroom_camera_pos[0],
                       (default_sprite_size[1] * 0.8) + showroom_camera_pos[1])
showroom.showroom_base_point = ((showroom_size[0] / 2) + showroom_camera_pos[0],
                                (showroom_size[1] * 0.8) + showroom_camera_pos[1])
ui.add(showroom)

image = smoothscale(load_image(current_data_dir, screen_scale, "film.png", "animation_maker_ui"),
                    (int(50 * screen_scale[0]), int(50 * screen_scale[1])))

Filmstrip.base_image = image
filmstrips = pygame.sprite.Group()

Button.containers = ui
SwitchButton.containers = ui
BodyHelper.containers = ui
Filmstrip.containers = ui, filmstrips
NameBox.containers = ui
MenuButton.containers = fake_group
NameList.containers = ui
popup_list_box = pygame.sprite.Group()
popup_namegroup = pygame.sprite.Group()
anim_prop_namegroup = pygame.sprite.Group()
frame_prop_namegroup = pygame.sprite.Group()

filmstrip_list = [Filmstrip((0, 42 * screen_scale[1]))]

filmstrip_list += [Filmstrip((image.get_width() * this_index, 42 * screen_scale[1])) for this_index in
                   range(1, max_frame)]

filmstrips.add(*filmstrip_list)

images = load_images(current_data_dir, screen_scale=screen_scale, subfolder=("animation_maker_ui", "helper_parts"))
body_helper_size = (700 * screen_scale[0], 270 * screen_scale[1])
effect_helper_size = (700 * screen_scale[0], 270 * screen_scale[1])
effect_helper = BodyHelper(effect_helper_size, (screen_size[0] - (body_helper_size[0] / 3),
                                                screen_size[1] - (body_helper_size[1] / 2)),
                           "p1_effect", [images["16_smallbox_helper"]])
del images["16_smallbox_helper"]
p_body_helper = BodyHelper(body_helper_size, (body_helper_size[0] / 2,
                                              screen_size[1] - (body_helper_size[1] / 2)), "p1", list(images.values()))
helper_list = [p_body_helper, effect_helper]

image = load_image(current_data_dir, screen_scale, "button.png", "animation_maker_ui")
image = smoothscale(image, (int(image.get_width() * screen_scale[1]),
                            int(image.get_height() * screen_scale[1])))

text_popup = TextPopup(font_size=24)
animation_chapter_button = Button("CH: 1", image, (image.get_width() / 2, image.get_height() / 2),
                                  description=("Select animation chapter", "Select animation chapter pool to edit."))
animation_race_button = Button("Ani Char", image, (image.get_width() * 1.5, image.get_height() / 2),
                               description=("Select animation character", "Select animation character pool to edit."))
new_button = Button("New Ani", image, (image.get_width() * 2.5, image.get_height() / 2),
                    description=("Create new animation", "Create new empty animation with name input."))
save_button = Button("Save", image, (image.get_width() * 3.5, image.get_height() / 2),
                     description=("Save all animation", "Save the current state of all animation only for this char."))
size_button = Button("Zoom: ", image, (image.get_width() * 4.5, image.get_height() / 2),
                     description=(
                         "Change animation preview room zoom",
                         "This does not change the size of the animation editor UI."))

rename_button = Button("Rename", image, (screen_size[0] - (image.get_width() * 3.5), image.get_height() / 2),
                       description=("Rename animation",
                                    "Input will not be accepted if another animation with the input name exists."))
duplicate_button = Button("Duplicate", image, (screen_size[0] - (image.get_width() * 2.5), image.get_height() / 2),
                          description=("Duplicate animation", "Duplicate the current animation as a new animation."))
filter_button = Button("Filter", image, (screen_size[0] - (image.get_width() * 1.5), image.get_height() / 2),
                       description=("Filter animation list according to input", "Capital letter sensitive.",
                                    "Use ',' for multiple filters (e.g., Human,Slash).",
                                    "Add '--' in front of the keyword for exclusion instead of inclusion."))

delete_button = Button("Delete", image, (screen_size[0] - (image.get_width() / 2), image.get_height() / 2),
                       description=("Delete animation", "Delete the current animation."))

play_animation_button = SwitchButton(("Play", "Stop"), image,
                                     (screen_size[0] / 2,
                                      filmstrip_list[0].rect.midbottom[1] + (image.get_height() / 2)),
                                     description=("Play/Stop animation",
                                                  "Preview the current animation."))

all_copy_button = Button("Copy A", image, (play_animation_button.pos[0] - (play_animation_button.image.get_width() * 3),
                                           filmstrip_list[0].rect.midbottom[1] + (image.get_height() / 2)),
                         description=("Copy all frames",))
all_paste_button = Button("Paste A", image, (play_animation_button.pos[0] - play_animation_button.image.get_width() * 2,
                                             filmstrip_list[0].rect.midbottom[1] + (image.get_height() / 2)),
                          description=("Paste all copied frames",))
speed_button = Button("Speed: 0.1",
                      image, (play_animation_button.pos[0] - play_animation_button.image.get_width(),
                              filmstrip_list[0].rect.midbottom[1] + (image.get_height() / 2)),
                      description=("Change preview animation play time (in second per frame)",
                                   "Change according to the input number."))
frame_copy_button = Button("Copy F", image, (play_animation_button.pos[0] + play_animation_button.image.get_width(),
                                             filmstrip_list[0].rect.midbottom[1] + (image.get_height() / 2)),
                           description=(
                               "Copy frame (CTRL + C)", "Does not copy frame properties."))
frame_paste_button = Button("Paste F", image,
                            (play_animation_button.pos[0] + play_animation_button.image.get_width() * 2,
                             filmstrip_list[0].rect.midbottom[1] + (image.get_height() / 2)),
                            description=("Paste copied frame (CTRL + V)",
                                         "Does not paste frame properties."))
reset_camera_button = Button("Reset C", image,
                             (play_animation_button.pos[0] + play_animation_button.image.get_width() * 3,
                              filmstrip_list[0].rect.midbottom[1] + (image.get_height() / 2)),
                             description=("Reset camera pos", "Reset showroom camera pos."))
add_frame_button = Button("Add F", image, (play_animation_button.pos[0] + play_animation_button.image.get_width() * 4,
                                           filmstrip_list[0].rect.midbottom[1] + (image.get_height() / 2)),
                          description=(
                              "Add empty frame and move the other after frames", "Will remove the last frame."))

remove_frame_button = Button("Del F", image,
                             (play_animation_button.pos[0] + play_animation_button.image.get_width() * 5,
                              filmstrip_list[0].rect.midbottom[1] + (image.get_height() / 2)),
                             description=("Remove current frame",))
all_frame_part_copy_button = Button("Copy PA", image,
                                    (play_animation_button.pos[0] + play_animation_button.image.get_width() * 6,
                                     filmstrip_list[0].rect.midbottom[1] + (image.get_height() / 2)),
                                    description=("Copy selected parts in all frame",))
all_frame_part_paste_button = Button("Paste PA", image,
                                     (play_animation_button.pos[0] + play_animation_button.image.get_width() * 7,
                                      filmstrip_list[0].rect.midbottom[1] + (image.get_height() / 2)),
                                     description=("Paste parts in all frame", "Only copied from all frame part copy."))
reverse_frame_button = Button("Reverse F", image,
                              (play_animation_button.pos[0] + play_animation_button.image.get_width() * 8,
                               filmstrip_list[0].rect.midbottom[1] + (image.get_height() / 2)),
                              description=("Reverse animation",))

clear_button = Button("Clear", image, (play_animation_button.pos[0] - play_animation_button.image.get_width() * 4,
                                       filmstrip_list[0].rect.midbottom[1] + (image.get_height() / 2)),
                      description=("Clear frame", "Clear the current frame."))
activate_button = SwitchButton(("Enable", "Disable"), image,
                               (play_animation_button.pos[0] - play_animation_button.image.get_width() * 5,
                                filmstrip_list[0].rect.midbottom[1] + (image.get_height() / 2)),
                               description=("Enable or disable the current frame",
                                            "Disabled frame will be cleared when change animation",
                                            "and will not be saved."))

help_button = SwitchButton(("Help:ON", "Help:OFF"), image,
                           (play_animation_button.pos[0] - play_animation_button.image.get_width() * 8.5,
                            filmstrip_list[0].rect.midbottom[1] + (image.get_height() / 2)),
                           description=("Enable or disable help popup.",
                                        "The bold line in the showroom indicate animation base point.",
                                        "Arrow keys to control showroom camera pos",
                                        "Control for parts selection:", "Left Click on part = Part selection",
                                        "Shift + Left Click = Add selection", "CTRL + Left Click = Remove selection",
                                        "- (minus) or = (equal) = Previous or next frame",
                                        "[ or ] = Previous or next animation",
                                        "Control with selected parts: ", "W,A,S,D = Move", "Mouse Right = Place",
                                        "Hold mouse wheel or Q,E = Rotate",
                                        "R,T = Angle and pos rotate based on center of all selected parts",
                                        "DEL = Clear part",
                                        "Page Up/Down or Numpad +/- = Change layer",
                                        "Some keyboard input like arrow key can be pressed along with Shift key to "
                                        "change value by 10",
                                        "The property list on the left is for whole animation, "
                                        "the right is for specific frame"))

undo_button = Button("Undo", image, (play_animation_button.pos[0] - play_animation_button.image.get_width() * 6,
                                     filmstrip_list[0].rect.midbottom[1] + (image.get_height() / 2)),
                     description=("Undo to previous edit (CTRL + Z)",
                                  "The undo also go back for other frame in the same animation."))
redo_button = Button("Redo", image, (play_animation_button.pos[0] - play_animation_button.image.get_width() * 7,
                                     filmstrip_list[0].rect.midbottom[1] + (image.get_height() / 2)),
                     description=("Redo edit (CTRL + Y)", "Redo to last undo edit."))

reset_button = Button("Reset", image, (screen_size[0] / 1.35, p_body_helper.rect.midtop[1] - (image.get_height() / 2)),
                      description=("Reset part edit", "Reset angle and flip."))

flip_hori_button = Button("Flip H", image, (reset_button.pos[0] + reset_button.image.get_width(),
                                            p_body_helper.rect.midtop[1] - (image.get_height() / 2)),
                          description=("Horizontal Flip part", "Flip the selected part horizontally."))
flip_mirror_button = Button("Flip M", image, (reset_button.pos[0] + reset_button.image.get_width() * 2,
                                              p_body_helper.rect.midtop[1] - (image.get_height() / 2)),
                            description=(
                                "Mirror Flip part", "Flip the selected part horizontally, angle, and position."))

zoom_d_button = Button("D Zoom", image, (reset_button.pos[0] + (reset_button.image.get_width() * 3),
                                         p_body_helper.rect.midtop[1] - (image.get_height() / 2)),
                       description=(
                           "Change scale selected parts and adjust position based on current distance from base point.",
                           "The distance changed is based on different from the current scale."
                           "converted to int value."))
zoom_dplus_button = Button("D Zoom+", image, (reset_button.pos[0] + (reset_button.image.get_width() * 4),
                                              p_body_helper.rect.midtop[1] - (image.get_height() / 2)),
                           description=(
                               "Add to scale value of selected parts and adjust position based on current distance from base point.",
                               "The distance changed is based on different from the current scale.",
                               "The input value get added to current selected parts' scale.",
                               "Not work well if previous scale value has decimal."))
# flip_vert_button = Button("Flip V", image, (reset_button.pos[0] + (reset_button.image.get_width() * 2),
#                                             p_body_helper.rect.midtop[1] - (image.get_height() / 2)),
#                           description=("Vertical Flip part", "Flip the selected part vertically."))
damage_button = Button("Do DMG", image, (reset_button.pos[0] + (reset_button.image.get_width() * 4),
                                         p_body_helper.rect.midtop[1] - (image.get_height() * 1.5)),
                       description=(
                           "Part do damage", "Add indication that the selected parts deal damage in this frame."))
part_copy_button = Button("Copy P", image, (screen_size[0] / 1.35,
                                            p_body_helper.rect.midtop[1] - (image.get_height() * 1.5)),
                          description=("Copy parts (ALT + C)", "Copy the selected part only from this frame."))
part_paste_button = Button("Paste P", image, (part_copy_button.rect.topright[0] + image.get_width() / 2,
                                              p_body_helper.rect.midtop[1] - (image.get_height() * 1.5)),
                           description=("Paste parts (ALT + V)", "Pasted the copied part only for this frame."))
part_stat_copy_button = Button("Copy PS", image, (part_copy_button.rect.topright[0] + image.get_width() * 1.5,
                                                  p_body_helper.rect.midtop[1] - (image.get_height() * 1.5)),
                               description=("Copy parts 'stat", "Copy the stat of selected part."))
part_stat_paste_button = Button("Paste PS", image, (part_copy_button.rect.topright[0] + image.get_width() * 2.5,
                                                    p_body_helper.rect.midtop[1] - (image.get_height() * 1.5)),
                                description=("Paste parts' stat", "Pasted the copied stats on same type of parts."))
p_all_button = Button("P All", image, (screen_size[0] / 1.35,
                                       p_body_helper.rect.midtop[1] - (image.get_height() * 2.5)),
                      description=("Select all current person parts",))
all_button = Button("All", image, (p_all_button.rect.topright[0] + image.get_width() / 2,
                                   p_body_helper.rect.midtop[1] - (image.get_height() * 2.5)),
                    description=("Select all parts",))
grid_button = SwitchButton(("Grid:ON", "Grid:OFF"), image,
                           (screen_size[0] / 1.35,
                            p_body_helper.rect.midtop[1] - (image.get_height() * 3.5)),
                           description=("Show editor grid", "Display or hide animation editor grid."))

showroom_colour_button = Button("Box RGB", image, (screen_size[0] / 1.35,
                                                   p_body_helper.rect.midtop[1] - (image.get_height() * 4.5)),
                                description=("Change showroom background colour",))
export_full_button = Button("To m PNG", image, (part_copy_button.rect.topright[0] + image.get_width() * 2.5,
                                                p_body_helper.rect.midtop[1] - (image.get_height() * 2.5)),
                            description=("Export animation to Full image png",
                                         "Export the current animation to png image files with size that cover all sprite parts."))
export_button = Button("To PNG", image, (part_copy_button.rect.topright[0] + image.get_width() * 1.5,
                                         p_body_helper.rect.midtop[1] - (image.get_height() * 2.5)),
                       description=(
                           "Export animation to PNG", "Export the current animation to several png image files."))

race_part_button = Button("", image, (reset_button.image.get_width() / 1.8,
                                      p_body_helper.rect.midtop[1] - (image.get_height() / 2)),
                          description=("Select part type",
                                       "Select char for body part, weapon type for weapon part,",
                                       "and effect type for effect part"))
p_selector = NameBox((250, image.get_height()), (reset_button.image.get_width() * 1.8,
                                                 p_body_helper.rect.midtop[1] - (image.get_height() * 5.5)),
                     description=("Select person to display in edit helper",
                                  "Parts from different person can still be selected in editor preview."))

camera_pos_show_button = NameBox((250, image.get_height()), (reset_button.image.get_width() * 1.8,
                                                             p_body_helper.rect.midtop[1] - (image.get_height() * 4.5)),
                                 description=("Camera POS",))
camera_pos_show_button.change_name(str(showroom_camera_pos))

sprite_mode_selector = NameBox((250, image.get_height()), (reset_button.image.get_width() * 1.8,
                                                           p_body_helper.rect.midtop[1] - (image.get_height() * 3.5)),
                               description=(
                                   "Select preview sprite mode", "Only for preview and not saved in animation file."))

sound_selector = NameBox((250, image.get_height()), (screen_size[0] - (reset_button.image.get_width() * 1.8),
                                                     p_body_helper.rect.midtop[1] - (image.get_height() * 5.5)),
                         description=("Add/remove sound effect to frame",
                                      "Sound will be played during in animation preview in this tool."))

sound_distance_selector = NameBox((250, image.get_height()),
                                  (screen_size[0] - (reset_button.image.get_width() * 1.8),
                                   p_body_helper.rect.midtop[1] - (image.get_height() * 4.5)),
                                  description=("Change sound effect distance if exist",
                                               "Will have no effect if there is not sound selected."))

# lock_button = SwitchButton(["Lock:OFF","Lock:ON"], image, (reset_button.pos[0] + reset_button.image.get_width() * 2,
#                                            p_body_helper.rect.midtop[1] - (image.get_height() / 1.5)))

input_ui = InputUI(load_image(data_dir, screen_scale, "input_ui.png", ("ui", "mainmenu_ui")),
                   (screen_size[0] / 2, screen_size[1] / 2))  # user text input ui box popup

image_list = load_base_button(data_dir, screen_scale)

input_ok_button = MenuButton(image_list, pos=(input_ui.rect.midleft[0] + image_list[0].get_width(),
                                              input_ui.rect.midleft[1] + image_list[0].get_height()),
                             key_name="confirm_button", layer=31)
input_cancel_button = MenuButton(image_list,
                                 pos=(input_ui.rect.midright[0] - image_list[0].get_width(),
                                      input_ui.rect.midright[1] + image_list[0].get_height()),
                                 key_name="cancel_button", layer=31)
input_button = (input_ok_button, input_cancel_button)
input_box = InputBox(input_ui.rect.center, input_ui.image.get_width())  # user text input box

input_ui_popup = (input_ui, input_box, input_ok_button, input_cancel_button)

confirm_ui = InputUI(load_image(data_dir, screen_scale, "input_ui.png", ("ui", "mainmenu_ui")),
                     (screen_size[0] / 2, screen_size[1] / 2))  # user confirm input ui box popup
confirm_ui_popup = (confirm_ui, input_ok_button, input_cancel_button)

colour_ui = InputUI(load_image(current_data_dir, screen_scale, "colour.png", "animation_maker_ui"),
                    (screen_size[0] / 2, screen_size[1] / 2))  # user text input ui box popup
colour_wheel = ColourWheel(load_image(main_data_dir, screen_scale, "rgb.png",
                                      subfolder=("animation", "sprite")),
                           (colour_ui.pos[0], colour_ui.pos[1] / 1.5))
colour_input_box = InputBox((colour_ui.rect.center[0], colour_ui.rect.center[1] * 1.2),
                            input_ui.image.get_width())  # user text input box

colour_ok_button = MenuButton(image_list, pos=(colour_ui.rect.midleft[0] + image_list[0].get_width(),
                                               colour_ui.rect.midleft[1] + (image_list[0].get_height() * 2)),
                              key_name="confirm_button", layer=31)
colour_cancel_button = MenuButton(image_list, pos=(colour_ui.rect.midright[0] - image_list[0].get_width(),
                                                   colour_ui.rect.midright[1] + (image_list[0].get_height() * 2)),
                                  key_name="cancel_button", layer=31)
colour_ui_popup = (colour_ui, colour_wheel, colour_input_box, colour_ok_button, colour_cancel_button)

box_img = load_image(current_data_dir, screen_scale, "property_box.png", "animation_maker_ui")
big_box_img = load_image(current_data_dir, screen_scale, "biglistbox.png", "animation_maker_ui")

ListBox.containers = popup_list_box
popup_list_box = ListBox((0, 0), big_box_img, 20)  # popup box need to be in higher layer
UIScroll(popup_list_box, popup_list_box.rect.topright)  # create scroll for popup list box
anim_prop_list_box = ListBox((0, filmstrip_list[0].rect.midbottom[1] +
                              (reset_button.image.get_height() * 1.5)), box_img, 8)
anim_prop_list_box.namelist = anim_property_list + ["Custom"]
frame_prop_list_box = ListBox((screen_size[0] - box_img.get_width(), filmstrip_list[0].rect.midbottom[1] +
                               (reset_button.image.get_height() * 1.5)), box_img, 8)
frame_prop_list_box.namelist = [frame_property_list + ["Custom"] for _ in range(max_frame)]
UIScroll(anim_prop_list_box, anim_prop_list_box.rect.topright)  # create scroll for animation prop box
UIScroll(frame_prop_list_box, frame_prop_list_box.rect.topright)  # create scroll for frame prop box
current_anim_row = 0
current_frame_row = 0
frame_property_select = [[] for _ in range(max_frame)]
anim_property_select = []
anim_prop_list_box.scroll.change_image(new_row=0, row_size=len(anim_prop_list_box.namelist))
frame_prop_list_box.scroll.change_image(new_row=0, row_size=len(frame_prop_list_box.namelist[current_frame]))
ui.add(anim_prop_list_box, frame_prop_list_box, anim_prop_list_box.scroll, frame_prop_list_box.scroll)

animation_selector = NameBox((600, image.get_height()), (screen_size[0] / 2, 0))
part_selector = NameBox((300, image.get_height()), (reset_button.image.get_width() * 3.5,
                                                    reset_button.rect.midtop[1]))

shift_press = False
anim = Animation(500, True)
model = Model()
model.animation_list = []
copy_list = []  # list of copied animation frames
all_copy_part = {}
all_copy_animation = {}
all_copy_name = {}
activate_list = [False] * max_frame

sound_selector.change_name("None")
sound_distance_selector.change_name("")
model.read_animation(animation_name)
animation_selector.change_name(animation_name)
if animation_name is not None:
    reload_animation(anim, model)
else:
    model.animation_list = [None] * max_frame
    model.edit_part(None, "new")
p_selector.change_name("p1")
sprite_mode_selector.change_name("Normal")
model.add_history()
animation_filter = [""]

while True:
    dt = clock.get_time() / 1000
    ui_dt = dt
    mouse_pos = pygame.mouse.get_pos()  # current mouse pos based on screen
    mouse_left_up = False  # left click
    mouse_left_down = False  # hold left click
    mouse_right_up = False  # right click
    mouse_right_down = False  # hold right click
    double_mouse_right = False  # double right click
    mouse_scroll_down = False
    mouse_scroll_up = False
    mouse_wheel_up = False  # mouse wheel click
    mouse_wheel_down = False  # hold mouse wheel click
    copy_press = False
    paste_press = False
    part_copy_press = False
    part_paste_press = False
    undo_press = False
    redo_press = False
    del_press = False
    shift_press = False
    ctrl_press = False
    alt_press = False
    popup_click = False
    input_esc = False
    popup_list = []

    key_press = pygame.key.get_pressed()

    if edit_delay:
        edit_delay -= dt
        if edit_delay < 0:
            edit_delay = 0

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()
            quit()

        elif event.type == pygame.MOUSEBUTTONUP:
            if event.button == 1:  # left click
                mouse_left_up = True
            if event.button == 2:  # click on mouse wheel
                mouse_wheel_up = True
            elif event.button == 3:  # Right Click
                mouse_right_up = True
                if mouse_timer == 0:
                    mouse_timer = 0.001  # Start timer after first mouse click
                elif mouse_timer < 0.3:  # if click again within 0.3 second for it to be considered double click
                    double_mouse_right = True  # double right click
                    mouse_timer = 0
            elif event.button == 4 or event.button == 5:
                if event.button == 4:  # Mouse scroll up
                    mouse_scroll_up = True
                else:  # Mouse scroll down
                    mouse_scroll_down = True

        elif event.type == pygame.KEYDOWN:
            if text_input_popup[0] == "text_input":
                if input_box in ui:
                    input_box.player_input(event, key_press)
                elif colour_input_box in ui:
                    colour_input_box.player_input(event, key_press)
                text_delay = 0.15

            elif event.key == pygame.K_ESCAPE:
                input_esc = True

    if text_input_popup[0] == "text_input" and text_delay == 0 and key_press[input_box.hold_key]:
        if input_box in ui:
            input_box.player_input(None, key_press)
        elif colour_input_box in ui:
            colour_input_box.player_input(None, key_press)
        text_delay = 0.1

    if pygame.mouse.get_pressed()[0]:  # Hold left click
        mouse_left_down = True
    elif pygame.mouse.get_pressed()[1]:  # Hold wheel click
        mouse_wheel_down = True
    elif pygame.mouse.get_pressed()[2]:  # Hold left click
        mouse_right_down = True

    ui.remove(text_popup)

    if text_delay > 0:
        text_delay += ui_dt
        if text_delay >= 0.3:
            text_delay = 0

    if input_ui not in ui and colour_ui not in ui:
        if key_press is not None and keypress_delay < 0.1:
            if key_press[pygame.K_LSHIFT] or key_press[pygame.K_RSHIFT]:
                shift_press = True
            if key_press[pygame.K_LCTRL] or key_press[pygame.K_RCTRL]:
                ctrl_press = True
                if key_press[pygame.K_c]:  # copy frame
                    copy_press = True
                elif key_press[pygame.K_v]:  # paste frame
                    paste_press = True
                elif key_press[pygame.K_z]:  # undo change
                    keypress_delay = 0.2
                    undo_press = True
                elif key_press[pygame.K_y]:  # redo change
                    keypress_delay = 0.2
                    redo_press = True
            elif key_press[pygame.K_LALT] or key_press[pygame.K_RALT]:
                alt_press = True
                if key_press[pygame.K_c]:  # copy part
                    part_copy_press = True
                elif key_press[pygame.K_v]:  # paste part
                    part_paste_press = True
            elif key_press[pygame.K_UP]:
                keypress_delay = 0.1
                if shift_press:
                    showroom_camera_pos[1] -= 10
                else:
                    showroom_camera_pos[1] -= 1
                recal_camera_pos(model)
                camera_pos_show_button.change_name(str(showroom_camera_pos))
                model.edit_part(mouse_pos, "")
            elif key_press[pygame.K_DOWN]:
                keypress_delay = 0.1
                if shift_press:
                    showroom_camera_pos[1] += 10
                else:
                    showroom_camera_pos[1] += 1
                recal_camera_pos(model)
                camera_pos_show_button.change_name(str(showroom_camera_pos))
                model.edit_part(mouse_pos, "")
            elif key_press[pygame.K_LEFT]:
                keypress_delay = 0.1
                if shift_press:
                    showroom_camera_pos[0] -= 10
                else:
                    showroom_camera_pos[0] -= 1
                recal_camera_pos(model)
                camera_pos_show_button.change_name(str(showroom_camera_pos))
                model.edit_part(mouse_pos, "")
            elif key_press[pygame.K_RIGHT]:
                keypress_delay = 0.1
                if shift_press:
                    showroom_camera_pos[0] += 10
                else:
                    showroom_camera_pos[0] += 1
                recal_camera_pos(model)
                camera_pos_show_button.change_name(str(showroom_camera_pos))
                model.edit_part(mouse_pos, "")
            elif key_press[pygame.K_w]:
                model.edit_part(mouse_pos, "move_up", specific_frame=current_frame)
            elif key_press[pygame.K_s]:
                model.edit_part(mouse_pos, "move_down", specific_frame=current_frame)
            elif key_press[pygame.K_a]:
                model.edit_part(mouse_pos, "move_left", specific_frame=current_frame)
            elif key_press[pygame.K_d]:
                model.edit_part(mouse_pos, "move_right", specific_frame=current_frame)
            elif key_press[pygame.K_q]:
                model.edit_part(mouse_pos, "tilt_1", specific_frame=current_frame)
            elif key_press[pygame.K_e]:
                model.edit_part(mouse_pos, "tilt_2", specific_frame=current_frame)
            elif key_press[pygame.K_r]:
                model.edit_part(mouse_pos, "full_rotate_1", specific_frame=current_frame)
            elif key_press[pygame.K_t]:
                model.edit_part(mouse_pos, "full_rotate_2", specific_frame=current_frame)
            elif key_press[pygame.K_DELETE]:
                keypress_delay = 0.1
                if model.part_selected:
                    model.edit_part(mouse_pos, "delete", specific_frame=current_frame)
            elif key_press[pygame.K_PAGEUP] or key_press[pygame.K_KP_PLUS]:
                keypress_delay = 0.1
                if model.part_selected:
                    model.edit_part(mouse_pos, "layer_up", specific_frame=current_frame)
            elif key_press[pygame.K_PAGEDOWN] or key_press[pygame.K_KP_MINUS]:
                keypress_delay = 0.1
                if model.part_selected:
                    model.edit_part(mouse_pos, "layer_down", specific_frame=current_frame)
            elif key_press[pygame.K_LEFTBRACKET] or key_press[pygame.K_RIGHTBRACKET]:
                if keypress_delay == 0:
                    keypress_delay = 0.1
                    animation_change = 1
                    if key_press[pygame.K_LEFTBRACKET]:
                        animation_change = -1
                    animation_list = list(current_pool[animation_race].keys())
                    if animation_filter[0] != "":
                        for key_filter in animation_filter:
                            if len(key_filter) > 0:
                                if key_filter[:2] == "--":  # exclude
                                    animation_list = [item for item in animation_list if key_filter[2:] not in item]
                                else:
                                    animation_list = [item for item in animation_list if key_filter in item]
                    try:
                        new_animation = animation_list[animation_list.index(animation_name) + animation_change]
                        change_animation(new_animation)
                    except (IndexError, ValueError):
                        if len(animation_list) > 0:
                            new_animation = animation_list[0]
                            change_animation(new_animation)
            elif key_press[pygame.K_MINUS] or key_press[pygame.K_EQUALS]:
                if keypress_delay == 0:
                    keypress_delay = 0.1
                    if key_press[pygame.K_MINUS]:
                        current_frame -= 1
                        if current_frame < 0:
                            current_frame = max_frame - 1
                    elif key_press[pygame.K_EQUALS]:
                        current_frame += 1
                        if current_frame > max_frame - 1:
                            current_frame = 0
                    change_frame_process()

            if mouse_scroll_up or mouse_scroll_down:
                if popup_list_box in ui and (
                        popup_list_box.rect.collidepoint(mouse_pos) or popup_list_box.scroll.rect.collidepoint(
                    mouse_pos)):
                    current_popup_row = list_scroll(mouse_scroll_up, mouse_scroll_down,
                                                    popup_list_box, current_popup_row, popup_list_box.namelist,
                                                    popup_namegroup, ui, screen_scale, layer=21)
                elif anim_prop_list_box.rect.collidepoint(mouse_pos) or anim_prop_list_box.scroll.rect.collidepoint(
                        mouse_pos):
                    current_anim_row = list_scroll(mouse_scroll_up, mouse_scroll_down,
                                                   anim_prop_list_box, current_anim_row, anim_prop_list_box.namelist,
                                                   anim_prop_namegroup, ui, screen_scale, old_list=anim_property_select)
                elif frame_prop_list_box.rect.collidepoint(mouse_pos) or frame_prop_list_box.scroll.rect.collidepoint(
                        mouse_pos):
                    current_frame_row = list_scroll(mouse_scroll_up, mouse_scroll_down,
                                                    frame_prop_list_box, current_frame_row,
                                                    frame_prop_list_box.namelist[current_frame], frame_prop_namegroup,
                                                    ui, screen_scale, old_list=frame_property_select[current_frame])
                elif model.part_selected != [] and showroom.rect.collidepoint(mouse_pos):
                    if mouse_scroll_up:  # Mouse scroll up
                        if ctrl_press:  # width scale only
                            model.edit_part(mouse_pos, "width_scale_up", specific_frame=current_frame)
                        elif alt_press:  # height scale only
                            model.edit_part(mouse_pos, "height_scale_up", specific_frame=current_frame)
                        else:
                            model.edit_part(mouse_pos, "full_scale_up", specific_frame=current_frame)
                    elif mouse_scroll_down:  # Mouse scroll down
                        if ctrl_press:  # width scale only
                            model.edit_part(mouse_pos, "width_scale_down", specific_frame=current_frame)
                        elif alt_press:  # height scale only
                            model.edit_part(mouse_pos, "height_scale_down", specific_frame=current_frame)
                        else:
                            model.edit_part(mouse_pos, "full_scale_down", specific_frame=current_frame)

        if mouse_timer != 0:  # player click mouse once before
            mouse_timer += ui_dt  # increase timer for mouse click using real time
            if mouse_timer >= 0.3:  # time pass 0.3 second no longer count as double click
                mouse_timer = 0

        if keypress_delay != 0:  # player press key once before
            keypress_delay += ui_dt
            if keypress_delay >= 0.3:
                keypress_delay = 0

        if mouse_left_up:
            if popup_list_box in ui:
                if popup_list_box.rect.collidepoint(mouse_pos):
                    popup_click = True
                    for index, name in enumerate(popup_namegroup):  # click on popup list
                        if name.rect.collidepoint(mouse_pos):
                            if popup_list_box.action == "part_select":
                                model.edit_part(mouse_pos, "part:" + name.name, specific_frame=current_frame,
                                                check_delay=False)
                            elif popup_list_box.action == "race_select":
                                model.edit_part(mouse_pos, "race:" + name.name, specific_frame=current_frame,
                                                check_delay=False)
                            elif "person" in popup_list_box.action:
                                p_body_helper.change_p_type(name.name, player_change=True)
                                effect_helper.change_p_type(name.name + "_effect", player_change=True)
                                p_selector.change_name(name.name)
                                sprite_mode_selector.change_name(model.sprite_mode[int(name.name[-1])])
                            elif "sound" in popup_list_box.action:
                                model.edit_part(mouse_pos, "sound_select:" + name.name, specific_frame=current_frame,
                                                check_delay=False)
                                sound_selector.change_name(name.name)
                            elif "_ver_select" in popup_list_box.action:
                                model.edit_part(mouse_pos, popup_list_box.action[0:3] + "_ver_select" + name.name,
                                                check_delay=False)
                                # sprite_ver_selector.change_name(name.name)
                            elif "_mode_select" in popup_list_box.action:
                                model.edit_part(mouse_pos, popup_list_box.action[0:3] + "_mode_select_" + name.name,
                                                check_delay=False)
                                sprite_mode_selector.change_name(name.name)

                            elif popup_list_box.action == "animation_chapter_select":
                                if animation_chapter != int(name.name):
                                    text_input_popup = ("confirm_input", "save_chapter_first", name.name)
                                    input_ui.change_instruction("Save Data First?")
                                    ui.add(input_ui_popup)
                            elif popup_list_box.action == "animation_race_select":
                                if name.name == "New Race":
                                    text_input_popup = ("text_input", "new_race")
                                    input_ui.change_instruction("Enter Race Name:")
                                    input_box.text_start("")
                                    ui.add(input_ui_popup)
                                elif animation_race != name.name:
                                    text_input_popup = ("confirm_input", "save_first", name.name)
                                    input_ui.change_instruction("Save Data First?")
                                    ui.add(input_ui_popup)
                            elif popup_list_box.action == "animation_select":
                                if animation_name != name.name:
                                    change_animation(name.name)
                            for this_name in popup_namegroup:  # remove name list
                                this_name.kill()
                                del this_name
                            ui.remove(popup_list_box, popup_list_box.scroll)
                            current_popup_row = 0  # reset row

                elif popup_list_box.scroll.rect.collidepoint(mouse_pos):  # scrolling on list
                    popup_click = True
                    new_row = popup_list_box.scroll.player_input(mouse_pos)
                    if new_row is not None:
                        current_popup_row = new_row
                        setup_list(NameList, current_popup_row, popup_list_box.namelist, popup_namegroup,
                                   popup_list_box, ui, screen_scale, layer=21)

                else:  # click other stuffs
                    for this_name in popup_namegroup:  # remove name list
                        this_name.kill()
                        del this_name
                    ui.remove(popup_list_box, popup_list_box.scroll)

            if not popup_click:  # button that can be clicked even when animation playing
                if play_animation_button.rect.collidepoint(mouse_pos):
                    if play_animation_button.current_option == 0:
                        play_animation_button.change_option(1)  # start playing animation
                        play_animation = True
                    else:
                        play_animation_button.change_option(0)  # stop animation
                        play_animation = False
                        model.edit_part(None, "change")

                elif grid_button.rect.collidepoint(mouse_pos):
                    if grid_button.current_option == 0:  # remove grid
                        grid_button.change_option(1)
                        showroom.grid = False
                    else:
                        grid_button.change_option(0)
                        showroom.grid = True

                elif help_button.rect.collidepoint(mouse_pos):
                    if help_button.current_option == 0:  # disable help
                        help_button.change_option(1)
                    else:
                        help_button.change_option(0)

                elif showroom_colour_button.rect.collidepoint(mouse_pos):
                    text_input_popup = ("text_input", "showroom_colour_")
                    ui.add(colour_ui_popup)

                elif anim_prop_list_box.scroll.rect.collidepoint(mouse_pos):  # scrolling on list
                    new_row = anim_prop_list_box.scroll.player_input(mouse_pos)
                    if new_row is not None:
                        current_anim_row = new_row
                        setup_list(NameList, current_anim_row, anim_prop_list_box.namelist, anim_prop_namegroup,
                                   anim_prop_list_box, ui, screen_scale, layer=9, old_list=anim_property_select)

                elif frame_prop_list_box.scroll.rect.collidepoint(mouse_pos):  # scrolling on list
                    new_row = frame_prop_list_box.scroll.player_input(mouse_pos)
                    if new_row is not None:
                        current_frame_row = new_row
                        setup_list(NameList, current_frame_row, frame_prop_list_box.namelist[current_frame],
                                   frame_prop_namegroup,
                                   frame_prop_list_box, ui, screen_scale, layer=9,
                                   old_list=frame_property_select[current_frame])

                elif anim_prop_list_box.rect.collidepoint(mouse_pos) or frame_prop_list_box.rect.collidepoint(
                        mouse_pos):
                    if activate_list[current_frame]:
                        namegroup = anim_prop_namegroup  # click on animation property list
                        list_box = anim_prop_list_box
                        select_list = anim_property_select
                        namelist = list_box.namelist
                        naming = "anim"
                        if frame_prop_list_box.rect.collidepoint(mouse_pos):  # click on frame property list
                            namegroup = frame_prop_namegroup
                            list_box = frame_prop_list_box
                            select_list = frame_property_select[current_frame]
                            namelist = list_box.namelist[current_frame]
                            naming = "frame"

                        for index, name in enumerate(namegroup):
                            if name.rect.collidepoint(mouse_pos):
                                if name.selected:  # unselect
                                    name.select()
                                    select_list.remove(name.name)
                                    specific_frame = None
                                    if naming == "frame":
                                        specific_frame = current_frame
                                    reload_animation(anim, model, specific_frame=specific_frame)
                                else:
                                    if name.name == "Custom":
                                        text_input_popup = ("text_input", "new_anim_prop")
                                        input_ui.change_instruction("Custom Property:")
                                        ui.add(input_ui_popup)
                                    elif name.name[-1] == "_" or name.name[
                                        -1].isdigit():  # property that need number value
                                        if not name.selected:
                                            if "colour" in name.name:
                                                text_input_popup = ("text_input", naming + "_prop_colour_" + name.name)
                                                ui.add(colour_ui_popup)
                                            else:
                                                text_input_popup = ("text_input", naming + "_prop_num_" + name.name)
                                                input_ui.change_instruction("Input Number Value:")
                                                ui.add(input_ui_popup)
                                    else:
                                        name.select()
                                        select_list.append(name.name)
                                        setup_list(NameList, current_frame_row, namelist, namegroup,
                                                   list_box, ui, screen_scale, layer=9, old_list=select_list)
                                        specific_frame = None
                                        if naming == "frame":
                                            specific_frame = current_frame
                                        reload_animation(anim, model, specific_frame=specific_frame)
                                property_to_pool_data(naming)

        if not play_animation:
            dt = 0
            if not popup_click:  # button that can't be clicked even when animation playing
                if mouse_left_up:
                    if clear_button.rect.collidepoint(mouse_pos):
                        model.edit_part(mouse_pos, "clear")

                    # elif reload_button.rect.collidepoint(mouse_pos):
                    #     pass

                    elif speed_button.rect.collidepoint(mouse_pos):
                        text_input_popup = ("text_input", "change_speed")
                        input_ui.change_instruction("Input Time Value:")
                        ui.add(input_ui_popup)

                    elif all_copy_button.rect.collidepoint(mouse_pos):
                        copy_list = []
                        for frame in model.frame_list:
                            frame_item = {}
                            for key, value in frame.items():
                                if type(value) is not list:
                                    frame_item[key] = value
                                else:
                                    frame_item[key] = value.copy()
                            copy_list.append(frame_item)

                    elif all_paste_button.rect.collidepoint(mouse_pos):
                        if copy_list:
                            model.add_history()
                            frame_property_select = [[] for _ in range(max_frame)]
                            anim_property_select = []
                            for frame_index, frame in enumerate(copy_list):
                                model.frame_list[frame_index] = {key: value.copy() if type(value) is list else value for
                                                                 key, value in frame.items()}
                            model.read_animation(animation_name, old=True)
                            reload_animation(anim, model)

                            model.edit_part(mouse_pos, "change")

                    elif all_frame_part_copy_button.rect.collidepoint(mouse_pos):
                        if model.part_selected:
                            for frame in range(len(model.frame_list)):
                                all_copy_part[frame] = {key: (value[:].copy() if type(value) is list else value) for
                                                        key, value in
                                                        model.bodypart_list[frame].items()}
                                all_copy_animation[frame] = {key: (value[:].copy() if value is not None else value) for
                                                             key, value in
                                                             model.animation_part_list[frame].items()}
                                all_copy_name[frame] = {key: (value[:].copy() if value is not None else value) for
                                                        key, value in
                                                        model.part_name_list[frame].items()}
                                # keep only selected one
                                all_copy_part[frame] = {item: all_copy_part[frame][item] for item in
                                                        all_copy_part[frame] if
                                                        item in model.mask_part_list and tuple(
                                                            model.mask_part_list.keys()).index(
                                                            item) in model.part_selected}
                                all_copy_animation[frame] = {item: all_copy_animation[frame][item] for index, item in
                                                             enumerate(all_copy_animation[frame].keys())
                                                             if
                                                             index in model.part_selected}
                                all_copy_name[frame] = {item: all_copy_name[frame][item] for index, item in
                                                        enumerate(all_copy_name[frame].keys()) if
                                                        index in model.part_selected}

                    elif all_frame_part_paste_button.rect.collidepoint(mouse_pos):
                        if all_copy_part:
                            model.edit_part(mouse_pos, "all frame selected part paste")

                    elif reverse_frame_button.rect.collidepoint(mouse_pos):
                        model.add_history()
                        model.frame_list = [item for item in model.frame_list if item and
                                            True in [True for key2, value2 in item.items() if len(value2) and
                                                     value2 and key2 != "animation_property"]]  # remove empty frame first
                        model.frame_list.reverse()
                        while len(model.frame_list) < max_frame:
                            model.frame_list.append({})
                        frame_property_select = [[] for _ in range(max_frame)]
                        model.read_animation(animation_name, old=True)
                        model.edit_part(mouse_pos, "change")
                        reload_animation(anim, model)
                        change_frame_process()

                        for strip_index, strip in enumerate(filmstrips):  # enable frame that not empty
                            for stuff in model.animation_part_list[strip_index].values():
                                if stuff:
                                    strip.activate = True
                                    activate_list[strip_index] = True
                                    strip.add_strip(change=False)
                                    break

                    elif add_frame_button.rect.collidepoint(mouse_pos):
                        model.add_history()
                        change_frame = len(model.bodypart_list) - 1
                        while change_frame > current_frame:
                            model.frame_list[change_frame] = {key: value.copy() if type(value) is list else value for
                                                              key, value
                                                              in model.frame_list[change_frame - 1].items()}
                            frame_property_select[change_frame] = frame_property_select[change_frame - 1].copy()
                            model.read_animation(animation_name, old=True)
                            change_frame -= 1
                        model.edit_part(mouse_pos, "clear")
                        model.edit_part(mouse_pos, "change")

                        for strip_index, strip in enumerate(filmstrips):  # enable frame that not empty
                            for stuff in model.animation_part_list[strip_index].values():
                                if stuff:
                                    strip.activate = True
                                    activate_list[strip_index] = True
                                    strip.add_strip(change=False)
                                    break

                    elif remove_frame_button.rect.collidepoint(mouse_pos):
                        model.add_history()
                        change_frame = current_frame
                        frame_property_select = [[] for _ in range(max_frame)]
                        while change_frame < len(model.bodypart_list) - 1:
                            model.frame_list[change_frame] = model.frame_list[change_frame + 1]
                            frame_property_select[change_frame] = frame_property_select[change_frame + 1].copy()
                            model.read_animation(animation_name, old=True)
                            change_frame += 1
                        model.edit_part(mouse_pos, "change")
                        reload_animation(anim, model)
                        change_frame_process()

                        for strip_index, strip in enumerate(filmstrips):  # enable frame that not empty
                            for stuff in model.animation_part_list[strip_index].values():
                                if stuff:
                                    strip.activate = True
                                    activate_list[strip_index] = True
                                    strip.add_strip(change=False)
                                    break

                    elif frame_copy_button.rect.collidepoint(mouse_pos):
                        copy_press = True

                    elif frame_paste_button.rect.collidepoint(mouse_pos):
                        paste_press = True

                    elif reset_camera_button.rect.collidepoint(mouse_pos):
                        showroom_camera_pos = [0, 0]
                        recal_camera_pos(model)
                        camera_pos_show_button.change_name(str(showroom_camera_pos))
                        model.edit_part(mouse_pos, "")

                    elif part_copy_button.rect.collidepoint(mouse_pos):
                        part_copy_press = True

                    elif part_paste_button.rect.collidepoint(mouse_pos):
                        part_paste_press = True

                    elif part_stat_copy_button.rect.collidepoint(mouse_pos):
                        if model.part_selected:
                            copy_part_stat = {key: (value[:].copy() if type(value) is list else value) for key, value in
                                              model.bodypart_list[current_frame].items()}
                            copy_animation_stat = {key: (value[:].copy() if value is not None else value) for key, value
                                                   in
                                                   model.animation_part_list[current_frame].items()}
                            copy_name_stat = {key: (value[:].copy() if value is not None else value) for key, value in
                                              model.part_name_list[current_frame].items()}

                            # keep only selected one
                            copy_part_stat = {item: copy_part_stat[item] for item in copy_part_stat if
                                              item in model.mask_part_list and tuple(model.mask_part_list.keys()).index(
                                                  item) in model.part_selected}
                            copy_animation_stat = {item: copy_animation_stat[item] for index, item in
                                                   enumerate(copy_animation_stat.keys()) if
                                                   index in model.part_selected}
                            copy_name_stat = {item: copy_name_stat[item] for index, item in
                                              enumerate(copy_name_stat.keys()) if index in model.part_selected}

                    elif part_stat_paste_button.rect.collidepoint(mouse_pos):
                        if copy_animation_stat is not None:
                            model.edit_part(mouse_pos, "paste part stat", specific_frame=current_frame)

                    elif p_all_button.rect.collidepoint(mouse_pos):
                        part_change = p_body_helper.ui_type + "_"
                        for part in model.mask_part_list:
                            if part_change in part:
                                if not ctrl_press:  # add parts
                                    model.click_part(mouse_pos, True, ctrl_press, part)
                                else:
                                    model.click_part(mouse_pos, False, ctrl_press, part)
                            elif part_change not in part and not shift_press and not ctrl_press:  # remove other parts
                                model.click_part(mouse_pos, False, True, part)
                        for helper in helper_list:
                            helper.select_part(None, False, False)  # reset first
                            for part in model.part_selected:
                                if tuple(model.mask_part_list.keys())[part] in helper.rect_part_list:
                                    helper.select_part(mouse_pos, True, False,
                                                       specific_part=tuple(model.mask_part_list.keys())[part])
                            helper.blit_part()

                    elif all_button.rect.collidepoint(mouse_pos):
                        for part in model.mask_part_list:
                            if not ctrl_press:  # add all parts
                                model.click_part(mouse_pos, True, ctrl_press, part)
                            else:
                                model.click_part(mouse_pos, False, ctrl_press, part)
                        for part in model.part_selected:
                            for helper in helper_list:
                                if tuple(model.mask_part_list.keys())[part] in helper.rect_part_list:
                                    helper.select_part(mouse_pos, True, False,
                                                       specific_part=list(model.mask_part_list.keys())[part])
                                    helper.blit_part()
                                    break

                    elif activate_button.rect.collidepoint(mouse_pos):
                        for strip_index, strip in enumerate(filmstrips):
                            if strip_index == current_frame:
                                if not strip.activate:
                                    strip.activate = True
                                    activate_list[strip_index] = True
                                    activate_button.change_option(0)
                                    strip.add_strip(change=False)
                                else:
                                    strip.activate = False
                                    activate_list[strip_index] = False
                                    activate_button.change_option(1)
                                    strip.add_strip(change=False)
                                anim_to_pool(animation_name, current_pool[animation_race], model, activate_list)
                                break

                    elif undo_button.rect.collidepoint(mouse_pos):
                        undo_press = True

                    elif redo_button.rect.collidepoint(mouse_pos):
                        redo_press = True

                    elif rename_button.rect.collidepoint(mouse_pos):
                        text_input_popup = ("text_input", "new_name")
                        input_ui.change_instruction("Rename Animation:")
                        input_box.text_start(animation_name)
                        ui.add(input_ui_popup)

                    elif duplicate_button.rect.collidepoint(mouse_pos):
                        text_input_popup = ("text_input", "duplicate_animation")
                        input_ui.change_instruction("Copy This Animation?")
                        last_char = str(1)
                        if animation_name + "(copy" + last_char + ")" in current_pool[animation_race]:  # copy exist
                            while animation_name + "(copy" + last_char + ")" in current_pool[animation_race]:
                                last_char = str(int(last_char) + 1)
                        elif "(copy" in animation_name and animation_name[-2].isdigit() and animation_name[-1] == ")":
                            last_char = str(int(animation_name[-2]) + 1)
                        input_box.text_start(animation_name + "(copy" + last_char + ")")

                        ui.add(input_ui_popup)

                    elif filter_button.rect.collidepoint(mouse_pos):
                        text_input_popup = ("text_input", "filter")
                        input_ui.change_instruction("Input text filters:")
                        input_filter = str(animation_filter)
                        for character in "'[]":
                            input_filter = input_filter.replace(character, "")
                        input_filter = input_filter.replace(", ", ",")
                        input_box.text_start(input_filter)
                        ui.add(input_ui_popup)

                    elif export_button.rect.collidepoint(mouse_pos):
                        text_input_popup = ("confirm_input", "export_animation")
                        input_ui.change_instruction("Export to PNGs?")
                        ui.add(input_ui_popup)

                    elif export_full_button.rect.collidepoint(mouse_pos):
                        text_input_popup = ("confirm_input", "export_full_animation")
                        input_ui.change_instruction("Export to a Full PNGs?")
                        ui.add(input_ui_popup)

                    elif flip_hori_button.rect.collidepoint(mouse_pos):
                        model.edit_part(mouse_pos, "flip1", specific_frame=current_frame)

                    elif flip_mirror_button.rect.collidepoint(mouse_pos):
                        model.edit_part(mouse_pos, "flip3", specific_frame=current_frame)

                    elif zoom_d_button.rect.collidepoint(mouse_pos):
                        text_input_popup = ("text_input", "change_d_zoom")
                        input_ui.change_instruction("Input new selected parts' zoom value")
                        ui.add(input_ui_popup)

                    elif zoom_dplus_button.rect.collidepoint(mouse_pos):
                        text_input_popup = ("text_input", "change_dplus_zoom")
                        input_ui.change_instruction("Input change to selected parts' zoom value")
                        ui.add(input_ui_popup)

                    # elif flip_vert_button.rect.collidepoint(mouse_pos):
                    #     model.edit_part(mouse_pos, "flip2", specific_frame=current_frame)

                    elif damage_button.rect.collidepoint(mouse_pos):
                        model.edit_part(mouse_pos, "DMG", specific_frame=current_frame)

                    elif reset_button.rect.collidepoint(mouse_pos):
                        model.edit_part(mouse_pos, "reset", specific_frame=current_frame)

                    elif part_selector.rect.collidepoint(mouse_pos):
                        if race_part_button.text != "":
                            current_part = list(model.animation_part_list[current_frame].keys())[
                                model.part_selected[-1]]
                            try:
                                if "special" in current_part:
                                    part_list = list(
                                        body_sprite_pool[race_part_button.text]["special"][
                                            character_mode_list[animation_race][
                                                model.sprite_mode[int(p_selector.text[1])]][
                                                "_".join(current_part.split("_")[:-1])]].keys())
                                elif "effect" in current_part:
                                    part_list = list(
                                        effect_sprite_pool[race_part_button.text].keys())
                                elif "weapon" in current_part:
                                    part_list = list(
                                        body_sprite_pool[race_part_button.text]["weapon"][
                                            character_mode_list[animation_race][
                                                model.sprite_mode[int(p_selector.text[1])]][current_part]].keys())
                                elif any(ext in current_part for ext in p_list):
                                    selected_part = current_part[3:]
                                    if selected_part[0:2] == "r_" or selected_part[0:2] == "l_":
                                        selected_part = selected_part[2:]
                                    part_list = list(
                                        body_sprite_pool[race_part_button.text][selected_part][
                                            character_mode_list[animation_race][
                                                model.sprite_mode[int(p_selector.text[1])]][current_part]].keys())

                            except KeyError:  # part not exist
                                print("not exist", current_part)
                                part_list = []
                            popup_list_open(popup_list_box, popup_namegroup, ui, "part_select",
                                            part_selector.rect.topleft, part_list, "bottom", screen_scale)

                    elif p_selector.rect.collidepoint(mouse_pos):
                        popup_list_open(popup_list_box, popup_namegroup, ui, "person_select",
                                        p_selector.rect.topleft, p_list, "bottom", screen_scale)

                    elif sprite_mode_selector.rect.collidepoint(mouse_pos):
                        part_list = character_mode_list[animation_race]
                        popup_list_open(popup_list_box, popup_namegroup, ui, p_body_helper.ui_type + "_mode_select",
                                        sprite_mode_selector.rect.topleft, part_list, "bottom", screen_scale)

                    elif sound_selector.rect.collidepoint(mouse_pos):
                        popup_list_open(popup_list_box, popup_namegroup, ui, "sound_select",
                                        (sound_selector.rect.topleft[0] - 400, sound_selector.rect.topleft[1]),
                                        ["None"] + list(sound_effect_pool.keys()), "bottom", screen_scale)

                    elif sound_distance_selector.rect.collidepoint(mouse_pos):
                        if sound_selector.text != "None":
                            text_input_popup = ("text_input", "change_sound_distance")
                            input_ui.change_instruction("Input sound distance value:")
                            ui.add(input_ui_popup)

                    elif race_part_button.rect.collidepoint(mouse_pos):
                        if model.part_selected:
                            current_part = tuple(model.mask_part_list.keys())[model.part_selected[-1]]
                            if "effect" in current_part:
                                part_list = list(effect_sprite_pool)
                            else:
                                part_list = list(body_sprite_pool.keys())
                            popup_list_open(popup_list_box, popup_namegroup, ui, "race_select",
                                            race_part_button.rect.topleft, part_list, "bottom", screen_scale)

                    elif animation_race_button.rect.collidepoint(mouse_pos):
                        current_popup_row = 0  # move current selected animation to top if not in filtered list
                        popup_list_open(popup_list_box, popup_namegroup, ui, "animation_race_select",
                                        (animation_race_button.rect.bottomleft[0],
                                         animation_race_button.rect.bottomleft[1]),
                                        ["New Race"] + [key for key in current_pool if key != "Template"],
                                        "top", screen_scale, current_row=current_popup_row)
                    elif animation_chapter_button.rect.collidepoint(mouse_pos):
                        current_popup_row = 0  # move current selected animation to top if not in filtered list
                        popup_list_open(popup_list_box, popup_namegroup, ui, "animation_chapter_select",
                                        (animation_chapter_button.rect.bottomleft[0],
                                         animation_chapter_button.rect.bottomleft[1]),
                                        chapter_list,
                                        "top", screen_scale, current_row=current_popup_row)

                    elif new_button.rect.collidepoint(mouse_pos):
                        text_input_popup = ("text_input", "new_animation")
                        input_ui.change_instruction("New Animation Name:")
                        ui.add(input_ui_popup)

                    elif save_button.rect.collidepoint(mouse_pos):
                        text_input_popup = ("confirm_input", "save_animation")
                        input_ui.change_instruction("Save Data?")
                        ui.add(input_ui_popup)

                    elif delete_button.rect.collidepoint(mouse_pos):
                        text_input_popup = ("confirm_input", "del_animation")
                        input_ui.change_instruction("Delete This Animation?")
                        ui.add(input_ui_popup)

                    elif size_button.rect.collidepoint(mouse_pos):
                        text_input_popup = ("text_input", "change_size")
                        input_ui.change_instruction("Input Size Number:")
                        ui.add(input_ui_popup)

                    elif animation_selector.rect.collidepoint(mouse_pos):
                        animation_list = list(current_pool[animation_race].keys())
                        if animation_filter[0] != "":
                            for key_filter in animation_filter:
                                if len(key_filter) > 0:
                                    if key_filter[:2] == "--":  # exclude
                                        animation_list = [item for item in animation_list if key_filter[2:] not in item]
                                    else:
                                        animation_list = [item for item in animation_list if key_filter in item]
                        current_popup_row = 0  # move current selected animation to top if not in filtered list
                        if animation_name in animation_list:
                            current_popup_row = animation_list.index(animation_name)
                        popup_list_open(popup_list_box, popup_namegroup, ui, "animation_select",
                                        (animation_selector.rect.bottomleft[0],
                                         animation_selector.rect.bottomleft[1]),
                                        animation_list, "top", screen_scale,
                                        current_row=current_popup_row)

                    else:  # click on other stuff
                        for strip_index, strip in enumerate(filmstrips):  # click on frame film list
                            if strip.rect.collidepoint(mouse_pos) and current_frame != strip_index:  # click new frame
                                current_frame = strip_index
                                change_frame_process()

                                if strip.activate:
                                    activate_button.change_option(0)
                                else:
                                    activate_button.change_option(1)
                                break

                        helper_click = False
                        for index, helper in enumerate(helper_list):  # click on helper
                            if helper.rect.collidepoint(mouse_pos):
                                helper_click = helper
                                break
                        if helper_click is not False:  # to avoid removing selected part when click other stuff
                            new_mouse_pos = pygame.Vector2(
                                (mouse_pos[0] - helper_click.rect.topleft[0]),
                                (mouse_pos[1] - helper_click.rect.topleft[1]))
                            this_part = helper_click.select_part(new_mouse_pos, shift_press, ctrl_press)
                            if not shift_press and not ctrl_press:  # remove selected part in other helpers
                                model.part_selected = []  # clear old list first
                                for index, helper in enumerate(helper_list):
                                    if helper != helper_click:
                                        helper.select_part(None, False, True)
                            elif this_part is not None and ctrl_press and tuple(model.mask_part_list.keys()).index(
                                    this_part) in model.part_selected:
                                model.part_selected.remove(
                                    tuple(model.mask_part_list.keys()).index(this_part))  # clear old list first
                            for index, helper in enumerate(helper_list):  # add selected part to model selected
                                if helper.part_selected:
                                    for part in helper.part_selected:
                                        model.click_part(new_mouse_pos, True, False, part)
                                helper.blit_part()

                if copy_press:
                    copy_part_frame = {key: (value[:].copy() if type(value) is list else value) for key, value in
                                       model.bodypart_list[current_frame].items()}
                    copy_animation_frame = {key: (value[:].copy() if value is not None else value) for key, value in
                                            model.animation_part_list[current_frame].items()}
                    copy_name_frame = {key: (value[:].copy() if value is not None else value) for key, value in
                                       model.part_name_list[current_frame].items()}

                elif paste_press:
                    if copy_animation_frame is not None:
                        model.add_history()
                        model.bodypart_list[current_frame] = {key: (value[:].copy() if type(value) is list else value)
                                                              for key, value in
                                                              copy_part_frame.items()}
                        model.animation_part_list[current_frame] = {
                            key: (value[:].copy() if value is not None else value) for key, value in
                            copy_animation_frame.items()}
                        model.part_name_list[current_frame] = {key: (value[:].copy() if value is not None else value)
                                                               for key, value in
                                                               copy_name_frame.items()}
                        model.edit_part(mouse_pos, "change")

                elif part_copy_press:
                    if model.part_selected:
                        copy_part = {key: (value[:].copy() if type(value) is list else value) for key, value in
                                     model.bodypart_list[current_frame].items()}
                        copy_animation = {key: (value[:].copy() if value is not None else value) for key, value in
                                          model.animation_part_list[current_frame].items()}
                        copy_name = {key: (value[:].copy() if value is not None else value) for key, value in
                                     model.part_name_list[current_frame].items()}

                        # keep only selected one
                        copy_part = {item: copy_part[item] for item in copy_part if
                                     item in model.mask_part_list and tuple(model.mask_part_list.keys()).index(
                                         item) in model.part_selected}
                        copy_animation = {item: copy_animation[item] for index, item in enumerate(copy_animation.keys())
                                          if
                                          index in model.part_selected}
                        copy_name = {item: copy_name[item] for index, item in enumerate(copy_name.keys()) if
                                     index in model.part_selected}

                elif part_paste_press:
                    if copy_part is not None:
                        model.edit_part(mouse_pos, "paste", specific_frame=current_frame)

                elif undo_press:
                    if model.current_history > 0:
                        model.current_history -= 1
                        model.edit_part(None, "undo")

                elif redo_press:
                    if len(model.animation_history) - 1 > model.current_history:
                        model.current_history += 1
                        model.edit_part(None, "redo")

                if showroom.rect.collidepoint(mouse_pos):  # mouse at showroom
                    if mouse_left_up:  # left click on showroom
                        new_mouse_pos = pygame.Vector2(
                            (mouse_pos[0] - showroom.rect.topleft[0]) * showroom_scale_mul[0],
                            (mouse_pos[1] - showroom.rect.topleft[1]) * showroom_scale_mul[1])
                        model.click_part(new_mouse_pos, shift_press, ctrl_press)
                        for index, helper in enumerate(helper_list):
                            helper.select_part(None, shift_press, ctrl_press)
                            if model.part_selected:
                                for part in model.part_selected:
                                    if tuple(model.mask_part_list.keys())[part] in helper.rect_part_list:
                                        helper.select_part(mouse_pos, True, False,
                                                           specific_part=tuple(model.mask_part_list.keys())[part])
                            helper.blit_part()
                    elif model.part_selected:
                        new_mouse_pos = pygame.Vector2(
                            (mouse_pos[0] - showroom.rect.topleft[0]) * showroom_scale_mul[0] * model.size,
                            (mouse_pos[1] - showroom.rect.topleft[1]) * showroom_scale_mul[1] * model.size)
                        if mouse_wheel_up or mouse_wheel_down:
                            model.edit_part(new_mouse_pos, "rotate", specific_frame=current_frame)
                        elif mouse_right_down:
                            if not keypress_delay:
                                model.edit_part(new_mouse_pos, "place", specific_frame=current_frame)
                                keypress_delay = 0.1
                        elif mouse_right_up:
                            model.edit_part(new_mouse_pos, "place", specific_frame=current_frame)

            if model.part_selected:
                part = model.part_selected[-1]
                if model.animation_part_list[current_frame] is not None and \
                        tuple(model.mask_part_list.keys())[part] in tuple(
                    model.animation_part_list[current_frame].keys()):
                    name_text = model.part_name_list[current_frame][tuple(model.mask_part_list.keys())[part]]
                    if name_text is None:
                        name_text = ["", ""]
                    race_part_button.change_text(name_text[0])
                    part_selector.change_name(name_text[1])
                else:
                    race_part_button.change_text("")
                    part_selector.change_name("")
            elif race_part_button.text:
                race_part_button.change_text("")
                part_selector.change_name("")
    else:  # input box function
        dt = 0
        if (input_ok_button in ui and input_ok_button.event) or (colour_ok_button in ui and colour_ok_button.event) or \
                key_press[pygame.K_RETURN] or key_press[pygame.K_KP_ENTER]:
            input_ok_button.event = False
            colour_ok_button.event = False

            if text_input_popup[1] == "new_animation":
                if input_box.text not in current_pool[animation_race]:  # no existing name already
                    animation_name = input_box.text
                    animation_selector.change_name(animation_name)
                    current_frame = 0
                    model.edit_part(mouse_pos, "new")
                    change_animation(animation_name)

            elif text_input_popup[1] == "new_race":
                if input_box.text not in current_pool:  # no existing name already
                    animation_race = input_box.text
                    current_pool[animation_race] = {key: value.copy() for key, value in
                                                    current_pool["Template"].items()}
                    for key in current_pool[animation_race]:
                        for index in range(len(current_pool[animation_race][key])):
                            current_pool[animation_race][key][index] = {
                                key2: value2.copy() if type(value2) is list else value2 for key2, value2 in
                                current_pool[animation_race][key][index].items()}
                    change_animation_race(animation_race)

            elif text_input_popup[1] == "save_animation":
                anim_save_pool(current_pool[animation_race], animation_chapter, animation_race, anim_column_header)

            elif text_input_popup[1] == "save_chapter_first":
                anim_save_pool(current_pool[animation_race], animation_chapter, animation_race, anim_column_header)
                change_animation_chapter(int(text_input_popup[2]))
                animation_chapter_button.change_text("CH: " + str(animation_chapter))

            elif text_input_popup[1] == "save_first":
                anim_save_pool(current_pool[animation_race], animation_chapter, animation_race, anim_column_header)
                change_animation_race(text_input_popup[2])

            elif text_input_popup[1] == "new_name":
                old_name = animation_name
                if input_box.text not in current_pool[animation_race]:  # no existing name already
                    animation_name = input_box.text
                    animation_selector.change_name(animation_name)
                    anim_to_pool(animation_name, current_pool[animation_race], model, activate_list, replace=old_name)

            elif text_input_popup[1] == "export_animation":
                for index, frame in enumerate(anim.frames):
                    if activate_list[index]:
                        pygame.image.save(frame, animation_name + "_" + str(index + 1) + ".png")

            elif text_input_popup[1] == "export_full_animation":
                min_x = float("infinity")
                max_x = -float("infinity")
                min_y = float("infinity")
                max_y = -float("infinity")
                for index, frame in enumerate(anim.frames):
                    if activate_list[index]:
                        pose_layer_list = model.make_layer_list(model.animation_part_list[index])
                        for layer in pose_layer_list:
                            part = model.animation_part_list[index][layer]
                            part_image = part[0]
                            if len(part) > 5:
                                if part[4]:  # flip
                                    part_image = pyflip(part_image, True, False)
                                if part[6] != 1 or part[7] != 1:  # scale
                                    part_image = smoothscale(part_image, (part_image.get_width() * part[6],
                                                                          part_image.get_height() * part[7]))
                                if part[3]:
                                    part_image = sprite_rotate(part_image, part[3])

                                width_check = part_image.get_width()
                                height_check = part_image.get_height()
                                if part[2][0] - width_check < min_x:
                                    min_x = part[2][0] - width_check
                                if part[2][0] + width_check > max_x:
                                    max_x = part[2][0] + width_check
                                if part[2][1] - height_check < min_y:
                                    min_y = part[2][1] - height_check  # most top y pos
                                if part[2][1] + height_check > max_y:
                                    max_y = part[2][1] + height_check  # lowest bottom y pos

                for index, frame in enumerate(anim.frames):
                    if activate_list[index]:
                        pose_layer_list = model.make_layer_list(model.animation_part_list[index])
                        image = pygame.Surface((abs(min_x) + abs(max_x), abs(min_y) + abs(max_y)),
                                               pygame.SRCALPHA)  # default size will scale down later
                        base_point = (image.get_width() / 2 - ((min_x + max_x) / 2), image.get_height() - max_y)
                        for layer in pose_layer_list:
                            part = model.animation_part_list[index][layer]
                            if part is not None and part[0] is not None:
                                part_rotated = part[0]
                                if part[4]:
                                    part_rotated = pyflip(part_rotated, True, False)
                                if part[6] != 1 or part[7] != 1:
                                    part_rotated = smoothscale(part_rotated, (part_rotated.get_width() * part[6],
                                                                              part_rotated.get_height() * part[7]))
                                if part[3]:
                                    part_rotated = sprite_rotate(part_rotated, part[3])  # rotate part sprite
                                new_target = (part[2][0] + base_point[0], part[2][1] + base_point[1])
                                rect = part_rotated.get_rect(center=new_target)
                                image.blit(part_rotated, rect)
                        # image = smoothscale(image, (image.get_width() / model.size, image.get_height() / model.size))
                        pygame.image.save(image, animation_name + "_" + str(index + 1) + ".png")

            elif text_input_popup[1] == "duplicate_animation":
                old_name = animation_name
                if input_box.text not in current_pool[animation_race]:  # no existing name already
                    animation_name = input_box.text
                    animation_selector.change_name(animation_name)
                    anim_to_pool(animation_name, current_pool[animation_race], model, activate_list, duplicate=old_name)
                    model.read_animation(animation_name)
                    model.clear_history()

            elif text_input_popup[1] == "del_animation":
                anim_del_pool(current_pool[animation_race], animation_name)
                if len(current_pool[animation_race]) == 0:  # no animation left, create empty one
                    animation_name = "empty"
                    animation_selector.change_name(animation_name)
                    current_frame = 0
                    model.edit_part(mouse_pos, "new")
                else:  # reset to the first animation
                    change_animation(tuple(current_pool[animation_race].keys())[0])

            elif text_input_popup[1] == "change_speed":
                if re.search("[a-zA-Z]", input_box.text) is None:
                    try:
                        new_speed = float(input_box.text)
                        speed_button.change_text("Time: " + input_box.text)
                        anim.speed_ms = new_speed
                    except ValueError:
                        pass

            elif text_input_popup[1] == "change_sound_distance":
                if input_box.text.isdigit():
                    new_distance = int(input_box.text)
                    sound_distance_selector.change_name(input_box.text)
                    model.frame_list[current_frame]["sound_effect"][1] = new_distance
                    model.frame_list[current_frame]["sound_effect"][2] = int(new_distance / 10000)

            elif text_input_popup[1] == "change_d_zoom":
                if re.search("[a-zA-Z]", input_box.text) is None:
                    model.edit_part(mouse_pos, "d_zoom:" + str(input_box.text), specific_frame=current_frame)

            elif text_input_popup[1] == "change_dplus_zoom":
                if re.search("[a-zA-Z]", input_box.text) is None:
                    model.edit_part(mouse_pos, "dplus_zoom:" + str(input_box.text), specific_frame=current_frame)

            elif text_input_popup[1] == "new_anim_prop":  # custom animation property
                if input_box.text not in anim_prop_list_box.namelist:
                    anim_prop_list_box.namelist.insert(-1, input_box.text)
                if input_box.text not in anim_property_select:
                    anim_property_select.append(input_box.text)
                setup_list(NameList, current_anim_row, anim_prop_list_box.namelist, anim_prop_namegroup,
                           anim_prop_list_box, ui, screen_scale, layer=9, old_list=anim_property_select)
                select_list = anim_property_select
                property_to_pool_data("anim")

            elif text_input_popup[1] == "new_frame_prop":  # custom frame property
                if input_box.text not in frame_prop_list_box.namelist:
                    frame_prop_list_box.namelist[current_frame].insert(-1, input_box.text)
                if input_box.text not in frame_property_select[current_frame]:
                    frame_property_select[current_frame].append(input_box.text)
                setup_list(NameList, current_frame_row, frame_prop_list_box.namelist[current_frame],
                           frame_prop_namegroup,
                           frame_prop_list_box, ui, screen_scale, layer=9,
                           old_list=frame_property_select[current_frame])
                select_list = frame_property_select[current_frame]
                property_to_pool_data("frame")

            elif "_prop_num" in text_input_popup[1] and (
                    input_box.text.isdigit() or (input_box.text.count(".") == 1 and
                                                 input_box.text[0] != "." and input_box.text[-1] != ".") and
                    re.search("[a-zA-Z]", input_box.text) is None):  # add property that need value
                namegroup = anim_prop_namegroup  # click on animation property list
                list_box = anim_prop_list_box
                namelist = list_box.namelist
                select_list = anim_property_select
                naming = "anim"
                if "frame" in text_input_popup[1]:  # click on frame property list
                    namegroup = frame_prop_namegroup
                    list_box = frame_prop_list_box
                    namelist = list_box.namelist[current_frame]
                    select_list = frame_property_select[current_frame]
                    naming = "frame"
                for name in namelist:
                    if name in (text_input_popup[1]):
                        index = namelist.index(name)
                        namelist[index] = name[0:name.rfind("_") + 1] + input_box.text
                        select_list.append(name[0:name.rfind("_") + 1] + input_box.text)
                        setup_list(NameList, current_frame_row, namelist, namegroup,
                                   list_box, ui, screen_scale, layer=9, old_list=select_list)
                        specific_frame = None
                        if naming == "frame":
                            specific_frame = current_frame
                        reload_animation(anim, model, specific_frame=specific_frame)
                        property_to_pool_data(naming)
                        break

            elif "showroom_colour_" in text_input_popup[1] and re.search("[a-zA-Z]", colour_input_box.text) is None and \
                    colour_input_box.text.count(",") >= 2:
                colour = colour_input_box.text.replace(" ", "")
                colour = colour.split(",")
                colour = [int(item) for item in colour]
                showroom.colour = colour

            elif "_prop_colour" in text_input_popup[1] and re.search("[a-zA-Z]", colour_input_box.text) is None and \
                    colour_input_box.text.count(",") >= 2:  # add colour related property
                namegroup = anim_prop_namegroup
                naming = "anim"
                list_box = anim_prop_list_box
                name_list = list_box.namelist
                select_list = anim_property_select
                if "frame" in text_input_popup[1]:  # click on frame property list
                    namegroup = frame_prop_namegroup
                    naming = "frame"
                    list_box = frame_prop_list_box
                    name_list = list_box.namelist[current_frame]
                    select_list = frame_property_select[current_frame]
                colour = colour_input_box.text.replace(" ", "")
                colour = colour.replace(",", ".")
                for name in name_list:
                    if name in (text_input_popup[1]):
                        if naming == "frame":
                            index = name_list.index(name)
                        elif naming == "anim":
                            index = name_list.index(name)

                        name_list[index] = name[0:name.rfind("_") + 1] + colour
                        select_list.append(name[0:name.rfind("_") + 1] + colour)
                        setup_list(NameList, current_frame_row, name_list, namegroup, list_box, ui, screen_scale,
                                   layer=9, old_list=select_list)
                        specific_frame = None
                        if naming == "frame":
                            specific_frame = current_frame
                        reload_animation(anim, model, specific_frame=specific_frame)
                        property_to_pool_data(naming)
                        break

            elif text_input_popup[1] == "change_size" and input_box.text and re.search("[a-zA-Z]",
                                                                                       input_box.text) is None:
                try:
                    model.size = float(input_box.text)
                    model.read_animation(animation_name, old=True)
                    reload_animation(anim, model)
                except ValueError:
                    pass

            elif text_input_popup[1] == "filter":
                animation_filter = input_box.text.split(",")

            elif text_input_popup[1] == "quit":
                pygame.time.wait(1000)
                pygame.quit()

            input_box.text_start("")
            text_input_popup = (None, None)
            ui.remove(*input_ui_popup, *colour_ui_popup)

        elif colour_wheel in ui and mouse_left_up and colour_wheel.rect.collidepoint(mouse_pos):
            colour = str(colour_wheel.get_colour())
            colour = colour[1:-1]  # remove bracket ()
            colour_input_box.text_start(colour[:colour.rfind(",")])  # keep only 3 first colour value not transparent

        elif (input_cancel_button in ui and input_cancel_button.event) or (
                colour_cancel_button in ui and colour_cancel_button.event) or input_esc:
            if text_input_popup[1] == "save_first":
                change_animation_race(text_input_popup[2])
            elif text_input_popup[1] == "save_chapter_first":
                change_animation_chapter(int(text_input_popup[2]))
                animation_chapter_button.change_text("CH: " + str(animation_chapter))
            input_cancel_button.event = False
            colour_cancel_button.event = False
            input_box.text_start("")
            text_input_popup = (None, None)
            ui.remove(*input_ui_popup, *confirm_ui_popup, *colour_ui_popup)

    ui.update()
    anim.play(showroom.image, (0, 0), activate_list)
    current_frame = anim.show_frame
    for strip_index, strip in enumerate(filmstrips):
        if strip_index == current_frame:
            strip.selected(True)
            break
    pen.fill((150, 150, 150))
    ui.draw(pen)

    pygame.display.update()
    clock.tick(60)

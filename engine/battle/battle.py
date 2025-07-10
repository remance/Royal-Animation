import sys
import time
from copy import deepcopy
from math import sin, cos, radians
from os import path
from random import choice, randint

import pygame
from pygame import Vector2, display, mouse, sprite, Surface, JOYDEVICEADDED, JOYDEVICEREMOVED, SRCALPHA
from pygame.locals import *
from pygame.mixer import Sound, Channel

from engine.camera.camera import Camera
from engine.character.character import Character
from engine.drama.drama import TextDrama
from engine.effect.effect import Effect
from engine.scene.scene import Scene
from engine.stageobject.stageobject import StageObject, RotateStageObject
from engine.uibattle.uibattle import FPSCount, BattleCursor, YesNo, CharacterSpeechBox, CharacterInteractPrompt, \
    ScreenFade
from engine.uimenu.uimenu import TextPopup
from engine.utils.common import clean_group_object
from engine.utils.data_loading import load_image, load_images, filename_convert_readable as fcv
from engine.utils.text_making import number_to_minus_or_plus
from engine.weather.weather import Weather

script_dir = path.split(path.abspath(__file__))[0] + "/"

decision_route = {"yes": "a", "no": "b"}
inf = float("inf")


def set_start_load(self, what):  # For output asset loading time in terminal
    globals()['load_timer'] = time.time()
    self.game.loading_screen("Loading " + what)  # change loading screen to display progress
    return "Loading {0}... ".format(what)


def set_done_load():
    duration = time.time() - globals()['load_timer']
    return " DONE ({0}s)\n".format(duration)


class Battle:
    from engine.game.activate_input_popup import activate_input_popup
    activate_input_popup = activate_input_popup

    from engine.battle.add_sound_effect_queue import add_sound_effect_queue
    add_sound_effect_queue = add_sound_effect_queue

    from engine.battle.check_event import check_event
    check_event = check_event

    from engine.battle.cal_shake_value import cal_shake_value
    cal_shake_value = cal_shake_value

    from engine.battle.camera_process import camera_process
    camera_process = camera_process

    from engine.battle.change_game_state import change_game_state
    change_game_state = change_game_state

    from engine.game.change_pause_update import change_pause_update
    change_pause_update = change_pause_update

    from engine.battle.common_process import common_process
    common_process = common_process

    from engine.battle.cutscene_player_input import cutscene_player_input
    cutscene_player_input = cutscene_player_input

    from engine.battle.drama_process import drama_process
    drama_process = drama_process

    from engine.battle.end_cutscene_event import end_cutscene_event
    end_cutscene_event = end_cutscene_event

    from engine.battle.escmenu_process import escmenu_process, back_to_battle_state
    back_to_battle_state = back_to_battle_state
    escmenu_process = escmenu_process

    from engine.battle.fix_camera import fix_camera
    fix_camera = fix_camera

    from engine.battle.load_battle_sprite_animation import load_battle_sprite_animation
    load_battle_sprite_animation = load_battle_sprite_animation

    from engine.battle.make_battle_ui import make_battle_ui
    make_battle_ui = make_battle_ui

    from engine.battle.make_esc_menu import make_esc_menu
    make_esc_menu = make_esc_menu

    from engine.battle.play_sound_effect import play_sound_effect
    play_sound_effect = play_sound_effect

    from engine.battle.spawn_character import spawn_character
    spawn_character = spawn_character

    from engine.battle.spawn_weather_matter import spawn_weather_matter
    spawn_weather_matter = spawn_weather_matter

    from engine.battle.state_battle_process import state_battle_process
    state_battle_process = state_battle_process
    state_process = state_battle_process

    from engine.battle.state_court_process import state_court_process
    state_court_process = state_court_process

    from engine.battle.state_map_process import state_map_process
    state_map_process = state_map_process

    from engine.battle.state_menu_process import state_menu_process
    state_menu_process = state_menu_process

    from engine.battle.shake_camera import shake_camera
    shake_camera = shake_camera

    from engine.battle.event_process import event_process
    event_process = event_process

    from engine.lorebook.lorebook import lorebook_process
    lorebook_process = lorebook_process

    battle = None
    camera = None
    ui_updater = None
    ui_drawer = None
    screen = None
    camera_size = None
    camera_max = None
    start_camera_mode = "Follow"

    base_fall_gravity = 900

    process_list = {"battle": state_battle_process, "menu": state_menu_process, "map": state_map_process,
                    "court": state_court_process}

    def __init__(self, game):
        self.game = game
        Battle.battle = self

        # TODO LIST for full chapter 1
        # add skill/moveset unlockable for enemy (charisma)
        # add enemy trap with delay and cycle
        # add one more playable char
        # add online/lan multiplayer?
        #  mission select, side mission, feast system
        # add ranking record system
        # add pvp mode, follower recruit unlock with all save story progress
        # add sound type to skill/move for collide and damage sound check
        # find way to increase speech text size
        # add no hit for stoppable frame in action property
        # finish main menu

        self.clock = pygame.time.Clock()  # Game clock to keep track of realtime pass

        self.config = game.config
        self.master_volume = game.master_volume
        self.music_volume = game.music_volume
        self.effect_volume = game.effect_volume
        self.voice_volume = game.voice_volume
        self.play_music_volume = game.play_music_volume
        self.play_effect_volume = game.play_effect_volume
        self.play_voice_volume = game.play_voice_volume
        self.joystick_bind_name = game.joystick_bind_name
        self.player_key_control = {player: self.config["USER"]["control player " + str(player)] for player in
                                   game.player_list}
        self.player_key_bind = {player: self.game.player_key_bind_list[player][self.player_key_control[player]] for
                                player in game.player_list}
        self.player_key_bind_name = {player: {value: key for key, value in self.player_key_bind[player].items()} for
                                     player in game.player_list}
        self.player_key_press = {player: {key: False for key in self.player_key_bind[player]} for player in
                                 game.player_list}
        self.player_key_hold = {player: {key: False for key in self.player_key_bind[player]} for player in
                                game.player_list}
        self.player_joystick = self.game.player_joystick
        self.joystick_player = self.game.joystick_player
        self.screen_rect = game.screen_rect
        self.screen_width = self.screen_rect.width
        self.screen_height = self.screen_rect.height
        self.corner_screen_width = game.corner_screen_width
        self.corner_screen_height = game.corner_screen_height

        Battle.camera_size = (self.screen_width, self.screen_height)
        Battle.camera_max = (self.screen_width - 1, self.screen_height - 1)
        self.camera_center_x = self.camera_size[0] / 2
        self.camera_center_y = self.camera_size[1] / 2

        self.main_dir = game.main_dir
        self.data_dir = game.data_dir
        self.screen_scale = game.screen_scale
        self.battle_cameras = game.battle_cameras
        Battle.ui_updater = game.battle_ui_updater
        Battle.ui_drawer = game.battle_ui_drawer

        self.character_updater = game.character_updater
        self.all_chars = game.all_chars
        self.speech_boxes = game.speech_boxes
        self.stage_objects = game.stage_objects
        self.effect_updater = game.effect_updater
        self.realtime_ui_updater = game.realtime_ui_updater

        self.cursor = game.cursor
        self.joysticks = game.joysticks
        self.joystick_name = game.joystick_name

        self.button_ui = game.button_ui

        # Text popup
        self.text_popup = TextPopup()
        self.scene_translation_text_popup = TextPopup()  # popup box for text that translate background script

        self.input_box = game.input_box
        self.input_ui = game.input_ui
        self.input_ok_button = game.input_ok_button
        self.input_cancel_button = game.input_cancel_button
        self.input_ui_popup = game.input_ui_popup
        self.confirm_ui_popup = game.confirm_ui_popup
        self.all_input_ui_popup = game.all_input_ui_popup

        self.weather_matters = game.weather_matters
        self.weather_effect = game.weather_effect

        # self.lorebook = game.lorebook
        # self.lore_name_list = game.lore_name_list
        # self.filter_tag_list = game.filter_tag_list
        # self.lore_buttons = game.lore_buttons
        # self.subsection_name = game.subsection_name
        # self.tag_filter_name = game.tag_filter_name

        # self.lorebook_stuff = game.lorebook_stuff

        self.music_pool = game.music_pool
        self.sound_effect_pool = game.sound_effect_pool
        self.ambient_pool = game.ambient_pool
        self.weather_ambient_pool = game.weather_ambient_pool
        self.sound_effect_queue = {}
        self.stage_music_pool = {}  # pool for music already converted to pygame Sound

        self.weather_screen_adjust = self.screen_width / self.screen_height  # for weather sprite spawn position
        self.right_corner = self.screen_width - (5 * self.screen_scale[0])
        self.bottom_corner = self.screen_height - (5 * self.screen_scale[1])

        self.character_data = self.game.character_data
        self.battle_map_data = self.game.battle_map_data
        self.weather_data = self.battle_map_data.weather_data
        self.weather_matter_images = self.battle_map_data.weather_matter_images
        self.weather_list = self.battle_map_data.weather_list
        self.char_sprite_chapter = self.game.char_sprite_chapter
        self.character_animation_data = self.game.character_animation_data
        self.body_sprite_pool = self.game.body_sprite_pool
        self.default_body_sprite_pool = self.game.default_body_sprite_pool
        self.default_effect_animation_pool = self.game.default_effect_animation_pool
        self.part_sprite_adjust = self.game.part_sprite_adjust
        self.effect_animation_pool = self.game.effect_animation_pool
        self.language = self.game.language
        self.localisation = self.game.localisation
        self.save_data = game.save_data
        self.main_story_profile = self.game.save_data.save_profile
        self.main_player = 1
        self.game_speed = 1
        self.play_time = 0

        self.player_objects = {}
        self.players_control_input = {1: None, 2: None, 3: None, 4: None}
        self.game_state = "battle"
        self.esc_menu_mode = "menu"

        self.chapter = None
        self.mission = None
        self.stage = None

        self.best_depth = display.mode_ok(self.screen_rect.size, self.game.window_style,
                                          32)  # Set the display mode
        Battle.screen = display.set_mode(self.screen_rect.size, self.game.window_style,
                                         self.best_depth)  # set up self screen

        # Assign battle variable to some classes
        Character.sound_effect_pool = self.sound_effect_pool
        Effect.sound_effect_pool = self.sound_effect_pool

        # Create battle ui
        cursor_images = load_images(self.data_dir, subfolder=("ui", "cursor_battle"))  # no need to scale cursor
        self.main_player_battle_cursor = BattleCursor(cursor_images, self.player_key_control[1])
        self.current_cursor = self.main_player_battle_cursor

        self.fps_count = FPSCount(self)  # FPS number counter
        if self.game.show_fps:
            self.realtime_ui_updater.add(self.fps_count)

        battle_ui_images = self.game.battle_ui_images
        CharacterSpeechBox.images = battle_ui_images

        self.screen_fade = ScreenFade()
        self.speech_prompt = CharacterInteractPrompt(battle_ui_images["button_weak"])
        # self.court_book = CourtBook(load_images(self.data_dir, screen_scale=self.screen_scale,
        #                                         subfolder=("ui", "court_ui"), key_file_name_readable=True))
        # self.city_map = CityMap(load_images(self.data_dir, screen_scale=self.screen_scale,
        #                                     subfolder=("ui", "map_select_ui")))

        battle_ui_dict = self.make_battle_ui(battle_ui_images)

        self.decision_select = YesNo(battle_ui_images)

        self.player_portraits = battle_ui_dict["player_portraits"]
        self.player_wheel_uis = battle_ui_dict["player_wheel_uis"]

        self.current_weather = Weather(1, 0, 0, None)

        TextDrama.images = load_images(self.data_dir, screen_scale=self.screen_scale,
                                       subfolder=("ui", "popup_ui", "drama_text"))
        self.drama_text = TextDrama(self)  # message at the top of screen that show up for important event

        # Battle ESC menu
        esc_menu_dict = self.make_esc_menu()

        self.battle_menu_button = esc_menu_dict["battle_menu_button"]
        self.esc_option_menu_button = esc_menu_dict["esc_option_menu_button"]
        self.esc_slider_menu = esc_menu_dict["esc_slider_menu"]
        self.esc_value_boxes = esc_menu_dict["esc_value_boxes"]
        self.esc_option_text = esc_menu_dict["volume_texts"]
        self.dialogue_box = esc_menu_dict["dialogue_box"]
        self.esc_dialogue_button = esc_menu_dict["esc_dialogue_button"]

        # Create the game camera
        self.camera_mode = "Follow"  # mode of game camera, follow player character or free observation
        self.camera_pos = Vector2(500, 500)  # camera pos on scene
        self.camera_left = (self.camera_pos[0] - self.camera_center_x)
        self.base_camera_begin = (self.camera_pos[0] - self.camera_center_x) / self.screen_scale[0]
        self.base_camera_end = (self.camera_pos[0] + self.camera_center_x) / self.screen_scale[0]

        self.shown_camera_pos = self.camera_pos  # pos of camera shown to player, in case of screen shaking or other effects

        self.clock_time = 0
        self.true_dt = 0
        self.dt = 0  # Realtime used for time calculation
        self.ui_dt = 0  # Realtime used for ui timer
        self.screen_shake_value = 0  # count for how long to shake camera

        self.ui_timer = 0  # This is timer for ui update function, use realtime
        self.drama_timer = 0  # This is timer for combat related function, use self time (realtime * game_speed)
        self.weather_spawn_timer = 0

        Battle.camera = Camera(self.screen, self.camera_size)

        self.base_cursor_pos = [0, 0]  # mouse pos on the map based on camera position

        self.show_cursor_timer = 0

        # music player
        self.current_music = None
        self.music_left = Channel(0)
        self.music_left.set_volume(self.play_music_volume, 0)
        self.music_right = Channel(1)
        self.music_right.set_volume(0, self.play_music_volume)
        self.current_ambient = None
        self.ambient = Channel(2)
        self.ambient.set_volume(self.play_effect_volume)
        self.weather_ambient = Channel(3)
        self.weather_ambient.set_volume(self.play_effect_volume)

        # Battle map object
        Scene.image = Surface.subsurface(self.camera.image, (0, 0, self.camera.image.get_width(),
                                                             self.camera.image.get_height()))
        Scene.battle = self
        self.scenes = {}

        self.empty_scene_image = Surface((self.screen_width, self.screen_height), SRCALPHA)

        self.base_stage_start = 0
        self.stage_start = 0
        self.base_stage_end = 0
        self.stage_end = 0
        self.start_cutscene = []
        self.reach_scene_event_list = {}  # cutscene that play when camera reach scene
        self.player_interact_event_list = {}
        self.stage_end_list = {}
        self.end_delay = 0  # delay until scene end and continue to next one
        self.cutscene_in_progress = False
        self.cutscene_finish_camera_delay = 0  # delay before camera can move again after cutscene
        self.stage_end_choice = False
        self.stage_scene_lock = {}
        self.cutscene_playing = None
        self.current_scene = 1

    def prepare_new_stage(self, chapter, mission, stage):
        for message in self.inner_prepare_new_stage(chapter, mission, stage):
            self.game.error_log.write("Start Stage:" + str(chapter) + "." + str(mission) + "." + str(stage))
            print(message, end="")

    def inner_prepare_new_stage(self, chapter, mission, stage):
        """Setup stuff when start new scene"""
        self.chapter = chapter
        self.mission = mission
        self.stage = stage

        # Stop all sound
        for sound_ch in range(1000):
            if Channel(sound_ch).get_busy():
                Channel(sound_ch).stop()
        self.current_music = None
        self.current_ambient = None

        print("Start loading", self.chapter, self.mission, self.stage)
        self.game.loading_lore_text = self.localisation.grab_text(
            ("load", randint(0, len(self.localisation.text[self.language]["load"]) - 1), "Text"))

        yield set_start_load(self, "scene setup")
        self.current_weather.__init__(1, 0, 0, self.weather_data)

        stage_data = self.game.preset_map_data[chapter][mission][stage]
        stage_object_data = stage_data["data"]
        stage_event_data = deepcopy(stage_data["event"])
        loaded_item = []
        self.stage_scene_lock = {}
        self.stage_end_choice = False
        self.cutscene_playing = None
        self.base_stage_end = 0  # for object pos
        self.base_stage_start = 0  # for camera pos
        self.stage_start = self.camera_center_x
        self.stage_end = -self.camera_center_x
        self.decision_select.selected = None
        self.end_delay = 0
        self.start_cutscene = []
        self.reach_scene_event_list = {}
        self.player_interact_event_list = {}
        self.stage_end_list = {}
        self.stage_music_pool = {}
        self.speech_prompt.clear()

        self.game.animation_data.load_stage_object_data(chapter)  # this will load data if chapter is different
        for value in stage_object_data:
            if "scene" in value["Type"]:  # assign scene data
                scene = int(value["Type"].split(":")[-1])
                if value["Type"] not in self.scenes:
                    self.scenes[scene] = Scene()
                    self.battle_cameras[scene] = sprite.LayeredUpdates()
                if value["Object"] not in loaded_item:  # load image
                    if "scene" in value["Type"]:  # load background scene
                        image = self.empty_scene_image
                        if path.exists(
                                path.join(self.data_dir, "map", "scene", fcv(value["Object"], revert=True) + ".png")):
                            image = load_image(self.data_dir, self.screen_scale,
                                               fcv(value["Object"], revert=True) + ".png",
                                               ("map", "scene"))
                        self.scenes[scene].images[value["Object"]] = image
                        loaded_item.append(value["Object"])
                self.scenes[scene].data[value["POS"]] = value["Object"]
            elif "endchoice" in value["Type"]:
                self.stage_end_choice = True
            elif "object" in value["Type"]:
                angle = 0
                flip = 0
                animation_speed = 0.1
                width_scale = 1
                height_scale = 1
                # use whatever the last camera if not defined
                scene_camera = [item for item in self.battle_cameras.values()][-1]
                if "scene" in value["Property"]:
                    scene_camera = self.battle_cameras[value["Property"]["scene"]]
                if "angle" in value["Property"]:
                    angle = value["Property"]["angle"]
                if "flip" in value["Property"]:
                    flip = value["Property"]["flip"]
                if "animation_speed" in value["Property"]:
                    animation_speed = value["Property"]["animation_speed"]
                if "width_scale" in value["Property"]:
                    width_scale = value["Property"]["width_scale"]
                if "height_scale" in value["Property"]:
                    height_scale = value["Property"]["height_scale"]
                if "rotate" in value["Type"]:
                    rotate_speed = 10
                    rotate_left = True
                    if "rotate_speed" in value["Property"]:
                        rotate_speed = value["Property"]["rotate_speed"]
                    if "rotate_left" in value["Property"]:
                        rotate_left = value["Property"]["rotate_left"]

                    RotateStageObject(scene_camera, value["Object"], value["POS"], game_id=value["ID"],
                                      angle=angle, flip=flip, animation_speed=animation_speed, width_scale=width_scale,
                                      height_scale=height_scale, rotate_speed=rotate_speed,
                                      rotate_left=rotate_left)
                else:
                    StageObject(scene_camera, value["Object"], value["POS"], game_id=value["ID"], angle=angle,
                                flip=flip, animation_speed=animation_speed, width_scale=width_scale,
                                height_scale=height_scale)

        if stage_event_data:  # add scene if event has scene change event
            parent_event_run_check = True
            for value in stage_data["event_data"]:
                event_run_check = True
                if value["ID"]:
                    parent_event_run_check = True
                    if ("once" in value["Trigger"] and
                            value["ID"] + self.chapter + self.mission + self.stage in
                            self.main_story_profile["story event"]):  # parent event
                        parent_event_run_check = False
                if ("story choice" in value["Property"] and (
                        value["Property"]["story choice"] != value["Property"]["story choice"].split("_")[0] + "_" +
                        self.main_story_profile["story choice"][value["Property"]["story choice"].split("_")[0]])):
                    event_run_check = False
                if value["Type"] == "bgchange" and event_run_check and parent_event_run_check:
                    image = self.empty_scene_image

                    images = self.scenes[value["Property"]["scene"]].images

                    if value["Object"] not in images:
                        if path.exists(
                                path.join(self.data_dir, "map", "scene", fcv(value["Object"], revert=True) + ".png")):
                            image = load_image(self.data_dir, self.screen_scale,
                                               fcv(value["Object"], revert=True) + ".png",
                                               ("map", "scene"))  # no scaling yet
                        images[value["Object"]] = image

        base_stage_end = 0
        stage_end = -self.camera_center_x
        stage_bg_data = {}
        for stage in self.scenes.values():
            for key in stage.data:
                if key != "event":
                    stage_bg_data[key] = None
        for key in stage_bg_data:
            stage_end += self.screen_width
            self.stage_end_list[key] = stage_end
        if not self.base_stage_end:  # no scene end from lock, use last scene end value
            self.base_stage_end = base_stage_end
            self.stage_end = stage_end
        yield set_done_load()

        yield set_start_load(self, "animation setup")
        character_list = [this_char["ID"] for this_char in stage_data["character"]]

        if stage_event_data:  # add character if event has character create event
            for value in stage_data["event_data"]:
                if value["Type"] == "create" and value["Object"] not in character_list:
                    character_list.append(value["Object"])

        character_list = tuple([char_id for char_id in set(character_list)])

        for key in tuple(self.body_sprite_pool.keys()):
            if key not in character_list:  # remove unused animation data
                self.body_sprite_pool.pop(key)

        self.game.animation_data.load_data(chapter, character_list)  # this will load data if chapter is different
        self.load_battle_sprite_animation(character_list)
        # WheelUI.item_sprite_pool = self.default_body_sprite_pool[int(self.chapter)]["Item"]["special"]
        yield set_done_load()

        yield set_start_load(self, "common setup")
        self.camera_mode = self.start_camera_mode

        stage_character = [item for item in stage_data["character"]]

        self.spawn_character(stage_character)

        # for player in self.player_objects:
        #     self.realtime_ui_updater.add(self.player_portraits[player])
        #     self.player_portraits[player].add_char_portrait(self.player_objects[player])
        #     if self.scene == "training":
        #         self.realtime_ui_updater.add(self.player_trainings[player])

        if stage_event_data:
            self.stage_music_pool = {key: Sound(self.music_pool[key]) for key in stage_event_data["music"] if
                                     key.lower() not in ("none", "resume", "pause")}
            for trigger, value in stage_event_data.items():
                if ("story choice" not in value or
                        (value["story choice"] == value["story choice"].split("_")[0] + "_" +
                         self.main_story_profile["story choice"][value["story choice"].split("_")[0]])):
                    # event with once condition will not be played again if already play once for the save profile
                    # also check parent event that depend on story choice
                    if "char" in trigger:  # trigger depend on character
                        for key, value2 in value.items():
                            for this_char in self.all_chars:
                                if this_char.game_id == key:
                                    if "in_camera" in trigger:  # reach camera event
                                        this_char.reach_camera_event = value2
                                    break
                    elif "start" in trigger:
                        for key, value2 in value.items():
                            for key3, value3 in value2.items():
                                if value3[0]["Type"]:  # check only parent event type data
                                    self.start_cutscene = value3
                    elif "interact" in trigger:
                        for key, value2 in value.items():
                            char_found = None
                            for char in self.all_chars:
                                if char.game_id == key:
                                    char_found = char
                                    break
                            for key3, value3 in value2.items():
                                if "/Any/" in value3[0]["ID"] or "/" + self.main_player_object.char_id + "/" in \
                                        value3[0][
                                            "ID"]:
                                    # only add event involving the character of first player
                                    if value3[0]["Type"] == "char":
                                        # must always have char id as second item in trigger
                                        if char_found:
                                            if char_found not in self.player_interact_event_list:
                                                self.player_interact_event_list[char_found] = []
                                            self.player_interact_event_list[char_found].append(value3)
                                    elif value3[0]["Type"] == "pos":  # interact with specific pos
                                        if key not in self.player_interact_event_list:
                                            self.player_interact_event_list[key] = []
                                        self.player_interact_event_list[key].append(value3)
                    elif "camera" in trigger:  # trigger depend on camera reaching something
                        if "reach_scene" in trigger:
                            for key, value2 in value.items():
                                for key3, value3 in value2.items():
                                    if key not in self.reach_scene_event_list:
                                        self.reach_scene_event_list[key] = {}
                                    if value3[0]["Type"] == "cutscene":  # check only parent event type data
                                        if "cutscene" not in self.reach_scene_event_list[key]:
                                            self.reach_scene_event_list[key]["cutscene"] = []
                                        self.reach_scene_event_list[key]["cutscene"].append(value3)
                                    elif value3[0]["Type"] == "weather":
                                        weather_strength = 0
                                        wind_direction = randint(0, 359)
                                        if "strength" in value3[0]["Property"]:
                                            weather_strength = value3[0]["Property"]["strength"]
                                        if "wind direction" in value3[0]["Property"]:
                                            wind_direction = value3[0]["Property"]["wind direction"]
                                        self.reach_scene_event_list[key]["weather"] = (
                                            value3[0]["Object"], wind_direction, weather_strength)
                                    elif value3[0]["Type"] == "music":
                                        if value3[0]["Object"] != "stop":
                                            self.reach_scene_event_list[key]["music"] = str(value3[0]["Object"])
                                        else:
                                            self.reach_scene_event_list[key]["music"] = None
                                    elif value3[0]["Type"] == "sound":
                                        if "sound" not in self.reach_scene_event_list[key]:
                                            self.reach_scene_event_list[key]["sound"] = []
                                        # sound effect must have sound distance and shake value in property
                                        self.reach_scene_event_list[key]["sound"].append(
                                            (choice(self.sound_effect_pool[str(value3[0]["Object"])]),
                                             value3[0]["Property"]["sound distance"],
                                             value3[0]["Property"]["shake value"]))

        for scene in self.scenes.values():
            scene.setup()
        yield set_done_load()

    def run_game(self):
        # Create Starting Values
        self.input_popup = None  # no popup asking for user text input state
        self.drama_text.queue = []  # reset drama text popup queue

        # if self.main_story_profile["interface event queue"]["inform"]:
        #     for item in self.main_story_profile["interface event queue"]["inform"].copy():
        #         self.drama_text.queue.append(item)
        #         self.main_story_profile["interface event queue"]["inform"].remove(item)

        self.camera_mode = self.start_camera_mode

        self.camera_pos = Vector2(500, self.camera_center_y)
        self.fix_camera()

        self.shown_camera_pos = self.camera_pos

        self.screen_shake_value = 0
        self.cutscene_in_progress = 0
        self.cutscene_finish_camera_delay = 0
        self.follower_talk_timer = 0
        self.ui_timer = 0
        self.drama_timer = 0
        self.dt = 0
        self.ui_dt = 0
        self.weather_spawn_timer = 0
        self.show_cursor_timer = 0
        self.main_player_battle_cursor.shown = True
        self.play_time = 0
        self.stage_gold = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
        self.stage_score = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}

        self.base_cursor_pos = [0, 0]  # mouse pos on the map based on camera position
        mouse.set_pos(Vector2(self.camera_pos[0], 140 * self.screen_scale[1]))  # set cursor to midtop screen

        self.player_key_control = {player: self.config["USER"]["control player " + str(player)] for player in
                                   self.game.player_list}
        self.player_control_keyboard = {player: True for player in self.player_key_control if
                                        self.player_key_control[player] == "keyboard"}
        self.player_key_bind = {player: self.game.player_key_bind_list[player][self.player_key_control[player]] for
                                player in self.game.player_list}
        self.player_key_bind_name = {player: {value: key for key, value in self.player_key_bind[player].items()} for
                                     player in self.game.player_list}
        self.player_key_press = {player: {key: False for key in self.player_key_bind[player]} for player in
                                 self.game.player_list}
        self.player_key_hold = {player: {key: False for key in self.player_key_bind[player]} for player in
                                self.game.player_list}
        self.player_joystick = self.game.player_joystick
        self.joystick_player = self.game.joystick_player

        self.screen.fill((0, 0, 0))
        self.realtime_ui_updater.add(self.main_player_battle_cursor)
        self.remove_ui_updater(self.cursor)

        if self.start_cutscene:
            # play start cutscene
            self.cutscene_playing = deepcopy(self.start_cutscene)
            self.start_cutscene = []

        frame = 0
        while True:  # battle running
            frame += 1

            if frame % 30 == 0 and hasattr(self.game, "profiler"):  # Remove for stable release, along with dev key
                self.game.profiler.refresh()
                frame = 0

            key_state = pygame.key.get_pressed()
            esc_press = False
            self.cursor.scroll_down = False
            self.cursor.scroll_up = False

            self.player_key_press = {key: dict.fromkeys(self.player_key_press[key], False) for key in
                                     self.player_key_press}
            self.player_key_hold = {key: dict.fromkeys(self.player_key_hold[key], False) for key in
                                    self.player_key_hold}

            self.clock_time = self.clock.get_time()
            self.true_dt = self.clock_time / 1000  # dt before game_speed
            self.play_time += self.true_dt

            for player in self.player_objects:  # only check for active player
                if self.player_key_control[player] == "keyboard":
                    for key in self.player_key_press[player]:  # check for key holding
                        if type(self.player_key_bind[player][key]) == int and \
                                key_state[self.player_key_bind[player][key]]:
                            self.player_key_hold[player][key] = True
                else:
                    player_key_bind_name = self.player_key_bind_name[player]
                    # joystick = self.player_joystick[player]  # TODO rework this later, change id to object
                    for joystick_id, joystick in self.joysticks.items():  # TODO find way so no need to loop this
                        if self.player_joystick[player] == joystick_id:
                            for i in range(joystick.get_numbuttons()):
                                if joystick.get_button(i) and i in player_key_bind_name:
                                    self.player_key_hold[player][player_key_bind_name[i]] = True

                            for i in range(joystick.get_numhats()):
                                if joystick.get_hat(i)[0] > 0.1 or joystick.get_hat(i)[0] < -0.1:
                                    hat_name = "hat" + number_to_minus_or_plus(joystick.get_hat(i)[0]) + str(0)
                                    if hat_name in self.player_key_bind_name:
                                        self.player_key_hold[player][player_key_bind_name[hat_name]] = True
                                if joystick.get_hat(i)[1] > 0.1 or joystick.get_hat(i)[1] < -0.1:
                                    hat_name = "hat" + number_to_minus_or_plus(joystick.get_hat(i)[1]) + str(1)
                                    if hat_name in self.player_key_bind_name:
                                        self.player_key_hold[player][player_key_bind_name[hat_name]] = True

                            for i in range(joystick.get_numaxes()):
                                if joystick.get_axis(i) > 0.5 or joystick.get_axis(i) < -0.5:
                                    if i in (2, 3) and player == 1:  # right axis only for cursor (player 1 only)
                                        vec = Vector2(joystick.get_axis(2), joystick.get_axis(3))
                                        radius, angle = vec.as_polar()
                                        adjusted_angle = (angle + 90) % 360
                                        new_pos = Vector2(self.current_cursor.pos[0] +
                                                          (self.clock_time * sin(radians(adjusted_angle))),
                                                          self.current_cursor.pos[1] -
                                                          (self.clock_time * cos(radians(adjusted_angle))))
                                        if new_pos[0] < 0:
                                            new_pos[0] = 0
                                        elif new_pos[0] > self.corner_screen_width:
                                            new_pos[0] = self.corner_screen_width
                                        if new_pos[1] < 0:
                                            new_pos[1] = 0
                                        elif new_pos[1] > self.corner_screen_height:
                                            new_pos[1] = self.corner_screen_height
                                        mouse.set_pos(new_pos)
                                    else:
                                        axis_name = "axis" + number_to_minus_or_plus(joystick.get_axis(i)) + str(i)
                                        if axis_name in player_key_bind_name:
                                            # axis pressing require different way to check than other buttons
                                            if (joystick.get_axis(i) > 0.9 or joystick.get_axis(i) < -0.9) and \
                                                    player_key_bind_name[axis_name] in self.player_objects[
                                                player].player_key_hold_timer:
                                                self.player_key_hold[player][player_key_bind_name[axis_name]] = True
                                            else:
                                                self.player_key_hold[player][player_key_bind_name[axis_name]] = True
                                                self.player_key_press[player][player_key_bind_name[axis_name]] = True
                            break

            self.base_cursor_pos = Vector2(
                (self.main_player_battle_cursor.pos[0] - self.camera_center_x + self.camera_pos[0]),
                (self.main_player_battle_cursor.pos[1] - self.camera_center_y + self.camera_pos[
                    1]))  # mouse pos on the map based on camera position

            for event in pygame.event.get():  # get event that happen
                if event.type == pygame.MOUSEBUTTONUP:
                    if event.button == 4:  # Mouse scroll down
                        self.cursor.scroll_up = True
                    elif event.button == 5:  # Mouse scroll up
                        self.cursor.scroll_down = True

                elif event.type == QUIT:  # quit game
                    pygame.quit()
                    sys.exit()

                elif event.type == pygame.JOYBUTTONUP:
                    joystick = event.instance_id
                    if joystick in self.joystick_player:
                        player = self.joystick_player[joystick]
                        if self.player_key_control[player] == "joystick" and \
                                event.button in self.player_key_bind_name[player]:  # check for key press
                            self.player_key_press[player][self.player_key_bind_name[player][event.button]] = True

                elif event.type == pygame.KEYDOWN:
                    event_key_press = event.key
                    if event_key_press == K_ESCAPE:  # accept esc button always
                        esc_press = True
                    for player in self.player_control_keyboard:
                        if event_key_press in self.player_key_bind_name[player]:  # check for key press
                            self.player_key_press[player][self.player_key_bind_name[player][event_key_press]] = True

                    # FOR DEVELOPMENT
                    if event.key == K_F1:
                        self.drama_text.queue.append(("Hello and welcome to showcase video", "Cannon Shot Medium"))
                    elif event.key == K_F7:  # clear profiler
                        if hasattr(self.game, "profiler"):
                            self.game.profiler.clear()
                    elif event.key == K_F8:  # show/hide profiler
                        if not hasattr(self.game, "profiler"):
                            self.game.setup_profiler()
                        self.game.profiler.switch_show_hide()

                elif event.type == JOYDEVICEADDED:
                    # Player add new joystick by plug in
                    joy = pygame.joystick.Joystick(event.device_index)
                    self.joysticks[joy.get_instance_id()] = joy
                    joy_name = joy.get_name()
                    for name in self.joystick_bind_name:
                        if name in joy_name:  # find common name
                            self.joystick_name[joy.get_instance_id()] = name
                    if joy.get_instance_id() not in self.joystick_name:
                        self.joystick_name[joy.get_instance_id()] = "Other"

                    for player in self.player_key_control:  # check for player with joystick control but no assigned yet
                        if self.player_key_control[player] == "joystick" and player not in self.player_joystick:
                            # assign new joystick to player with joystick control setting
                            self.player_joystick[player] = joy.get_instance_id()
                            self.joystick_player[joy.get_instance_id()] = player
                            break  # only one player get assigned

                elif event.type == JOYDEVICEREMOVED:
                    # Player unplug joystick
                    del self.joysticks[event.instance_id]
                    del self.joystick_name[event.instance_id]
                    for key, value in self.player_joystick.copy().items():
                        if value == event.instance_id:
                            self.player_joystick.pop(key)
                            self.joystick_player.pop(value)
                            break

            if self.player_key_press[self.main_player]["Menu/Cancel"]:
                # open/close menu
                esc_press = True

            self.ui_updater.update()  # update ui before more specific update

            return_state = self.state_process(esc_press)  # run code based on current state
            if return_state is not None:
                return return_state

            display.update()  # update game display, draw everything
            self.clock.tick(1000)  # clock update even if self pause

    def add_ui_updater(self, *args):
        self.ui_updater.add(*args)
        self.ui_drawer.add(*args)

    def remove_ui_updater(self, *args):
        self.ui_updater.remove(*args)
        self.ui_drawer.remove(*args)

    def exit_battle(self):
        # remove menu and ui
        self.remove_ui_updater(self.battle_menu_button.values(), self.esc_slider_menu.values(),
                               self.esc_value_boxes.values(), self.esc_option_text.values(),
                               self.scene_translation_text_popup)

        for key in self.player_objects:
            self.player_portraits[key].reset_value()
        self.realtime_ui_updater.remove(self.player_portraits.values(), self.player_wheel_uis.values(),
                                        self.decision_select)

        # stop all sounds
        for sound_ch in range(1000):
            if Channel(sound_ch).get_busy():
                Channel(sound_ch).stop()
        self.current_music = None
        self.current_ambient = None
        self.stage_music_pool = {}

        # remove all reference from battle object
        self.player_objects = {}
        self.scenes = {}

        self.speech_prompt.clear()  # clear speech prompt from updater to avoid being deleted

        clean_group_object((self.all_chars, self.effect_updater, self.weather_matters))

        self.sound_effect_queue = {}

        self.drama_timer = 0  # reset drama text popup
        self.realtime_ui_updater.remove(self.drama_text)
        self.remove_ui_updater(self.drama_text)

from math import radians
from random import uniform
from types import MethodType

import pygame
from pygame import sprite, Vector2
from pygame.sprite import Sprite
from pygame.mask import from_surface
from pygame.transform import flip, smoothscale, rotate

from engine.character.ai_move import ai_move_dict
from engine.uibattle.uibattle import CharacterIndicator

rotation_list = (90, -90)
rotation_name = ("l_side", "r_side")
rotation_dict = {key: rotation_name[index] for index, key in enumerate(rotation_list)}

infinity = float("inf")


class Character(Sprite):
    battle = None
    character_data = None
    sound_effect_pool = None

    image = pygame.Surface((0, 0))  # start with empty surface

    from engine.utils.common import clean_object
    clean_object = clean_object

    from engine.utils.rotation import set_rotate
    set_rotate = set_rotate

    from engine.character.character_event_process import character_event_process
    character_event_process = character_event_process

    from engine.character.check_new_animation import check_new_animation
    check_new_animation = check_new_animation

    from engine.character.check_prepare_action import check_prepare_action
    check_prepare_action = check_prepare_action

    from engine.character.enter_stage import enter_stage
    enter_stage = enter_stage

    from engine.character.move_logic import move_logic
    move_logic = move_logic

    from engine.character.pick_animation import pick_animation
    pick_animation = pick_animation

    from engine.character.pick_cutscene_animation import pick_cutscene_animation
    pick_cutscene_animation = pick_cutscene_animation

    from engine.character.play_animation import play_animation
    play_animation = play_animation

    from engine.character.play_cutscene_animation import play_cutscene_animation
    play_cutscene = play_cutscene_animation

    from engine.character.player_input import player_input
    player_input = player_input

    from engine.character.player_input_wheel_ui_mode import player_input_wheel_ui_mode
    player_input_wheel_ui_mode = player_input_wheel_ui_mode

    from engine.character.rotate_logic import rotate_logic
    rotate_logic = rotate_logic

    from engine.character.start_animation_body_part import start_animation_body_part
    start_animation_body_part = start_animation_body_part

    walk_command_action = {"name": "Walk", "movable": True, "walk": True, "not_reset_special_state": True}
    run_command_action = {"name": "Run", "movable": True, "run": True, "not_reset_special_state": True}
    halt_command_action = {"name": "Halt", "movable": True, "walk": True, "halt": True, "not_reset_special_state": True}
    dash_command_action = {"name": "Dash", "uncontrollable": True, "movable": True, "forced move": True, "no dmg": True,
                           "hold": True, "dash": True, "not_reset_special_state": True}

    # static variable
    default_animation_play_time = 0.1
    base_ground_pos = 2000

    def __init__(self, battle_camera, game_id, layer_id, stat, player_control=False):
        """
        Character object represent a character that may or may not fight in battle
        """
        Sprite.__init__(self, self.containers)
        self.screen_scale = self.battle.screen_scale
        self.battle_camera = battle_camera
        self.game_id = game_id  # object ID for reference
        self.layer_id = layer_id  # ID for sprite layer calculation
        self.base_layer = 0
        self.name = stat["Name"]
        self.show_name = self.battle.localisation.grab_text(("character", stat["ID"] + self.battle.chapter, "Name"))
        if "(" in self.show_name and "," in self.show_name:
            self.show_name = self.battle.localisation.grab_text(("character", stat["ID"], "Name"))
        self.player_control = player_control  # character controlled by player
        self.indicator = None
        self.cutscene_event = None
        self.followers = []
        self.speech = None
        self.ai_lock = False

        self.current_action = {}  # action being performed
        self.command_action = {}  # next action to be performed
        self.animation_pool = {}  # list of animation sprite this character can play with its action
        self.current_animation = {}  # list of animation frames playing
        self.current_animation_direction = {}
        self.frame_timer = 0
        self.show_frame = 0  # current animation frame
        self.current_animation_name = None
        self.max_show_frame = 0
        self.stoppable_frame = False
        self.replace_idle_animation = None
        self.interrupt_animation = False
        self.freeze_timer = 0
        self.hold_timer = 0  # how long animation holding so far
        self.release_timer = 0  # time when hold release
        self.timer = uniform(0, 0.1)
        self.mode_timer = 0

        self.live = True
        self.invisible = False
        self.invincible = False
        self.fly = False
        self.reach_camera_event = {}

        self.position = "Stand"
        self.mode = "Normal"
        self.just_change_mode = False
        self.mode_list = stat["Mode"]

        # Variable related to sprite
        self.body_size = int(stat["Size"] / 10)
        if self.body_size < 1:
            self.body_size = 1
        self.sprite_size = stat["Size"] * 10 * self.screen_scale[
            1]  # use for pseudo sprite size of character for positioning of effect
        self.sprite_height = (100 + stat["Size"]) * self.screen_scale[1]
        self.arrive_condition = stat["Arrive Condition"]

        self.city_walk_speed = 500  # movement speed in city, not affected by anything
        self.ground_pos = self.base_ground_pos
        self.y_momentum = 0
        self.x_momentum = 0

        self.base_animation_play_time = self.default_animation_play_time
        self.animation_play_time = self.base_animation_play_time
        self.final_animation_play_time = self.animation_play_time

        self.fall_gravity = self.battle.base_fall_gravity
        self.angle = -90
        if "Angle" in stat:
            self.angle = stat["Angle"]
        self.new_angle = self.angle
        self.radians_angle = radians(360 - self.angle)  # radians for apply angle to position
        self.run_direction = 0  # direction check to prevent character able to run in opposite direction right away
        self.sprite_direction = rotation_dict[min(rotation_list,
                                                  key=lambda x: abs(
                                                      x - self.angle))]  # find closest in list of rotation for sprite direction

        self.char_id = str(stat["ID"])
        # self.char_id_event = self.char_id + "_"  # for faster event check instead of having to + "_" every time
        self.sprite_ver = self.battle.char_sprite_chapter[self.char_id]
        self.command_pos = Vector2(0, 0)

        if "Scene" in stat:  # data with scene positioning
            self.base_pos = Vector2(stat["POS"][0] + (3840 * (stat["Scene"] - 1)),
                                    stat["POS"][1])  # true position of character in battle
        else:  # character with no scene position data such as summon
            self.base_pos = Vector2(stat["POS"])  # true position of character in battle

        self.last_pos = None  # may be used by AI or specific character update check for position change
        self.pos = Vector2((self.base_pos[0] * self.screen_scale[0],
                            self.base_pos[1] * self.screen_scale[1]))
        self.cutscene_target_pos = None

        self.body_parts = {}

        for p in ("p1", "p2", "p3", "p4"):
            self.body_parts |= {p + "_head": None, p + "_neck": None, p + "_body": None,
                                p + "_r_arm_up": None, p + "_r_arm_low": None, p + "_r_hand": None,
                                p + "_l_arm_up": None, p + "_l_arm_low": None, p + "_l_hand": None,
                                p + "_r_leg_up": None, p + "_r_leg_low": None, p + "_r_foot": None,
                                p + "_l_leg_up": None, p + "_l_leg_low": None, p + "_l_foot": None,
                                p + "_main_weapon": None, p + "_sub_weapon": None,
                                p + "_special_1": None, p + "_special_2": None, p + "_special_3": None,
                                p + "_special_4": None, p + "_special_5": None, p + "_special_6": None,
                                p + "_special_7": None, p + "_special_8": None, p + "_special_9": None,
                                p + "_special_10": None}

        self.retreat_stage_end = self.battle.base_stage_end + self.sprite_size
        self.retreat_stage_start = -self.sprite_size

    def update(self, dt):
        self.ai_update(dt)

        if self.angle != self.new_angle:  # Rotate Function
            self.rotate_logic()
        self.move_logic(dt)  # Move function
        done = self.play_animation(dt, False)
        self.check_new_animation(done)

    @staticmethod
    def inactive_update(*args):
        pass

    def cutscene_update(self, dt):
        """Update for cutscene"""
        if self.cutscene_target_pos and self.cutscene_target_pos != self.base_pos:
            speed = 350
            if "speed" in self.current_action:
                speed = self.current_action["speed"]
            # move to target pos based on data if any
            move = self.cutscene_target_pos - self.base_pos
            require_move_length = move.length()  # convert length
            move.normalize_ip()
            move *= speed * dt

            if move.length() <= require_move_length:  # move normally according to move speed
                self.base_pos += move
            else:  # move length pass the base_target destination
                self.base_pos = Vector2(self.cutscene_target_pos)  # just change base position to base target

            self.pos = Vector2((self.base_pos[0] * self.screen_scale[0],
                                self.base_pos[1] * self.screen_scale[1]))

            for part in self.body_parts.values():
                part.re_rect()

        if self.live:  # only play animation for alive char
            hold_check = False
            if ("hold" in self.current_animation_direction[self.show_frame]["property"] and
                    "hold" in self.current_action):
                hold_check = True
            done = self.play_cutscene_animation(dt, hold_check)
            if (self.cutscene_event and "interact" not in self.current_action and
                    "select" not in self.current_action and "wait" not in self.current_action):
                # remove cutscene with no wait, select, or interact property
                if self.cutscene_event in self.battle.cutscene_playing:
                    self.battle.cutscene_playing.remove(self.cutscene_event)
                self.cutscene_event = None
            if (not self.cutscene_event and done and not self.cutscene_target_pos) or \
                    (self.cutscene_target_pos and self.cutscene_target_pos == self.base_pos) or \
                    (self.cutscene_event and not self.cutscene_target_pos and
                     ((done or hold_check) and not self.cutscene_target_pos and "interact" not in self.current_action and
                      "select" not in self.current_action and "wait" in self.current_action and not self.speech)):
                if self.cutscene_event in self.battle.cutscene_playing:
                    self.battle.cutscene_playing.remove(self.cutscene_event)
                self.cutscene_event = None

                if self.cutscene_target_pos and self.cutscene_target_pos == self.base_pos:
                    self.cutscene_target_pos = None

                if "next action" not in self.current_action:
                    if done:
                        if "die" in self.current_action:  # die animation
                            self.current_action = {}
                            self.show_frame = self.max_show_frame
                            self.max_show_frame = 0  # reset max_show_frame to 0 to prevent restarting animation
                            self.start_animation_body_part()  # revert previous show_frame 0 animation start
                            return

                    if "repeat after" not in self.current_action:
                        self.pick_cutscene_animation({})
                    else:  # event indicate repeat animation after event end
                        self.current_action["repeat"] = True
                        if not self.live:
                            self.current_action["die"] = True
                else:
                    self.current_action = self.current_action["next action"]
                    self.pick_cutscene_animation(self.current_action)

    def ai_update(self, dt):
        pass


class PlayerCharacter(Character):

    def __init__(self, battle_camera, game_id, layer_id, stat):
        Character.__init__(self, battle_camera, game_id, layer_id, stat, player_control=True)
        self.update = MethodType(Character.update, self)
        self.player_input = self.player_input

        self.command_key_input = []
        self.command_key_hold = None
        self.last_command_key_input = None
        self.input_mode = None

        self.indicator = CharacterIndicator(self)
        self.player_command_key_input = []
        self.player_key_input_timer = []
        self.player_key_hold_timer = {}

        self.enter_stage(self.battle.character_animation_data)


class AICharacter(Character):
    def __init__(self, battle_camera, game_id, layer_id, stat, specific_behaviour=None):
        Character.__init__(self, battle_camera, game_id, layer_id, stat)
        self.update = MethodType(Character.update, self)
        ai_behaviour = "idle_city_ai"
        if specific_behaviour:
            ai_behaviour = specific_behaviour

        self.ai_move = ai_move_dict["default"]
        if ai_behaviour in ai_move_dict:
            self.ai_move = ai_move_dict[ai_behaviour]

        self.city_walk_speed = 100

        self.ai_lock = True  # lock AI from activity when start battle, and it positions outside of scene lock
        self.event_ai_lock = False  # lock AI until event unlock it only

        if "Ground Y POS" in stat and stat["Ground Y POS"]:  # replace ground pos based on data in scene
            self.ground_pos = stat["Ground Y POS"]

        char_property = {}
        if "Property" in stat:
            char_property = {key: value for key, value in stat["Property"].items()}
        if "Stage Property" in stat:
            char_property |= stat["Stage Property"]
        for stuff in char_property:  # set attribute from property
            if stuff == "target":
                if type(char_property["target"]) is int:  # target is AI
                    target = char_property["target"]
                else:  # target is player
                    target = char_property["target"][-1]

                for this_char in self.battle.all_chars:
                    if target == this_char.game_id:  # find target char object
                        self.target = this_char
                        break
            elif stuff == "idle":  # replace idle animation
                self.replace_idle_animation = char_property["idle"]
            else:
                self.__setattr__(stuff, char_property[stuff])

        self.ai_timer = 0  # for whatever timer require for AI action
        self.ai_movement_timer = 0  # timer to move for AI
        self.ai_attack_timer = 0  # timer to attack for AI
        self.end_ai_movement_timer = uniform(2, 6)

        self.enter_stage(self.battle.character_animation_data)

    def ai_update(self, dt):
        if self.ai_timer:
            self.ai_timer += dt
        if self.ai_movement_timer:
            self.ai_movement_timer -= dt
            if self.ai_movement_timer < 0:
                self.ai_movement_timer = 0
        self.ai_move(self)


class BodyPart(Sprite):
    battle = None
    body_sprite_pool = None
    empty_surface = pygame.Surface((0, 0))

    def __init__(self, owner, part, can_hurt=True):
        self.screen_scale = self.battle.screen_scale
        self.owner = owner
        self.battle_camera = owner.battle_camera
        self.sprite_ver = self.owner.sprite_ver
        self.owner_layer = 0
        self.angle = self.owner.angle
        self._layer = 10
        Sprite.__init__(self, self.containers)
        self.image_update_contains = []  # object that need updating when base_image get updated
        self.part = part
        self.part_name = self.part[3:]
        if self.part_name[0:2] == "l_" or self.part_name[0:2] == "r_":
            self.part_name = self.part_name[2:]
        elif "weapon" in self.part_name:
            self.part_name = "weapon"
        if "special" in self.part:
            self.part = "_".join(self.part.split("_")[:-1])
        self.stuck_effect = []  # effect that stuck on this body part
        self.can_hurt = can_hurt
        self.object_type = "body"
        self.mode = "Normal"
        self.base_image = self.empty_surface
        self.image = self.empty_surface
        self.data = ()  # index 1=part name, 2and3=pos xy, 4=angle, 5=flip, 6=layer , 7=width scale, 8=height scale, 9=deal damage or not
        self.rect = self.image.get_rect(topleft=(0, 0))
        # self.mask = from_surface(self.image)

        # Variables not really used or changed but required for same functions as Effect
        self.duration = 0
        self.stick_reach = False  # not used for body parts but require for checking
        self.stick_timer = 0  # not used but require for checking

    @staticmethod
    def adjust_image(image, data):
        # index 1=part name, 2and3=pos xy, 4=angle, 5=flip, 7=scale
        if data[5]:
            image = flip(image, True, False)
        if data[7] != 1 or data[8] != 1:
            image = smoothscale(image, (image.get_width() * data[7], image.get_height() * data[8]))
        if data[4]:
            image = rotate(image, data[4])
        return image

    def get_part(self, data):
        self.angle = self.owner.angle
        self.mode = self.owner.mode_list[self.owner.mode][self.part]

        if self.data != data or self.owner.just_change_mode:
            self.data = data
            sprite_type = self.data[0]
            sprite_name = self.data[1]
            if self.image_update_contains:  # update any object after getting base image
                # part with update must always have 0 flip 0 angle and 1 scale in animation data to work will apply rotate later
                self.base_image = \
                    self.body_sprite_pool[self.sprite_ver][sprite_type]["special"][self.data[1]][self.mode][0][1][0]
                for item in self.image_update_contains:
                    item.update()
            else:
                # index 1=part name, 2and3=pos xy, 4=angle, 5=flip, 7=width scale 8 = height scale
                if "special" in self.part_name:
                    if sprite_name == "Template" and "change_sprite" in self.owner.current_action:
                        # template sprite that need replace
                        sprite_type = self.owner.current_action["change_sprite"]
                        if sprite_type == "Item" and "item" in self.owner.current_action:  # change to item using
                            self.image = \
                                self.body_sprite_pool[self.sprite_ver][sprite_type]["special"][self.mode][
                                    self.owner.current_action["item"]]
                            self.image = self.adjust_image(self.image, self.data)
                    else:
                        self.image = \
                            self.body_sprite_pool[self.sprite_ver][sprite_type]["special"][sprite_name][self.mode][
                                self.data[5]][self.data[7]][self.data[8]][self.data[4]]
                else:
                    self.image = self.body_sprite_pool[self.sprite_ver][sprite_type][self.part_name][
                        sprite_name][self.mode][self.data[5]][self.data[7]][self.data[8]][self.data[4]]

            self.re_rect()
            if self in self.battle_camera:
                self.battle_camera.change_layer(self, self.owner_layer - data[6])

    def re_rect(self):
        if self.data:
            if self not in self.battle_camera:  # was remove because no data previously
                if not self.owner.invisible:
                    self.battle_camera.add(self)
            elif self.owner.invisible:  # remove part from camera for invisible character
                self.battle_camera.remove(self)
            self.rect = self.image.get_rect(center=((self.owner.pos[0] + (self.data[2] * self.screen_scale[0])),
                                                    (self.owner.pos[1] + (self.data[3] * self.screen_scale[1]))))
            # self.mask = from_surface(self.image)
        else:
            if self in self.battle_camera:
                self.battle_camera.remove(self)

    def update(self, dt):
        pass

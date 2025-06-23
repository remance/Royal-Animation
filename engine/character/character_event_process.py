from random import uniform
from types import MethodType

from pygame import Vector2

from engine.uibattle.uibattle import CharacterSpeechBox

infinity = float("inf")


def character_event_process(self, event, event_property):
    from engine.character.character import Character

    if event["Type"] == "hide":
        self.battle_camera.remove(self.body_parts.values())
        if self.indicator:  # also hide indicator
            self.battle_camera.remove(self.indicator)
        self.cutscene_update = MethodType(Character.inactive_update, self)
        self.battle.cutscene_playing.remove(event)
    elif event["Type"] == "show":
        if self.indicator:
            self.battle_camera.add(self.indicator)
        self.cutscene_update = MethodType(Character.cutscene_update, self)
        self.battle.cutscene_playing.remove(event)
    elif event["Type"] == "idle":  # replace idle animation, note that it replace even after cutscene finish
        self.replace_idle_animation = event["Animation"]
        self.battle.cutscene_playing.remove(event)
    elif event["Type"] == "remove":
        self.die(delete=True)
        self.battle.cutscene_playing.remove(event)
    elif event["Type"] == "unlock":  # unlock AI via event
        self.ai_lock = False
        self.event_ai_lock = False
        self.battle.cutscene_playing.remove(event)
        for team in self.battle.all_team_enemy:
            if team != self.team and self not in self.battle.all_team_enemy[team]:
                self.battle.all_team_enemy[team].add(self)
    elif event["Type"] == "lock":  # lock AI via event
        self.event_ai_lock = True
        self.ai_lock = True
        self.battle.cutscene_playing.remove(event)
    elif not self.cutscene_event:
        # replace previous event when there is new one to play next

        self.cutscene_event = event
        if "POS" in event_property:  # move to position
            if type(event_property["POS"]) is str:
                target_scene = self.battle.current_scene
                if "reach_" in event_property["POS"]:
                    target_scene = self.battle.reach_scene

                if "start" in event_property["POS"]:
                    positioning = self.layer_id
                    if self.layer_id > 4:
                        positioning = uniform(1, 4)
                    ground_pos = self.ground_pos
                    if self.fly:  # flying character can just move with current y pos
                        ground_pos = self.base_pos[1]
                    self.cutscene_target_pos = Vector2(
                        (3840 * target_scene) + (100 * positioning), ground_pos)
                elif "middle" in event_property["POS"]:
                    ground_pos = self.ground_pos
                    if self.fly:  # flying character can just move with current y pos
                        ground_pos = self.base_pos[1]
                    self.cutscene_target_pos = Vector2(
                        (3840 * target_scene) - (self.battle.camera_center_x * 1.5),
                        ground_pos)
                elif "center" in event_property["POS"]:
                    # true center, regardless of flying
                    self.cutscene_target_pos = Vector2(
                        (3840 * target_scene) - (self.battle.camera_center_x * 1.5),
                        self.battle.camera_center_y)
            else:
                self.cutscene_target_pos = Vector2(
                    event_property["POS"][0],
                    event_property["POS"][1])
        elif "target" in event_property:
            for character2 in self.battle.all_chars:
                if character2.game_id == event_property["target"]:  # go to target pos
                    self.cutscene_target_pos = character2.base_pos
                    break
        if "direction" in event_property:
            if event_property["direction"] == "target":
                # facing target must have cutscene_target_pos
                if self.cutscene_target_pos[0] >= self.base_pos[0]:
                    self.new_direction = "Right"
                else:
                    self.new_direction = "Left"
            else:
                self.new_direction = event_property["direction"].capitalize()
            self.rotate_logic()
        animation = event["Animation"]
        action_dict = event_property
        if animation:
            action_dict = {"name": event["Animation"]} | event_property
        if action_dict and action_dict != self.current_action:  # start new action
            self.pick_cutscene_animation(action_dict)
        if event["Text ID"]:
            start_speech(self, event, event_property)


def start_speech(self, event, event_property):
    specific_timer = None
    player_input_indicator = None
    voice = False
    if "voice" in event_property:
        voice = event_property["voice"]
    body_part = "p1_head"
    if "body part" in event_property:
        body_part = event_property["body part"]
    font_size = 60
    if "font size" in event_property:
        font_size = event_property["font size"]
    max_text_width = 800
    if "max text width" in event_property:
        max_text_width = event_property["max text width"]
    if "interact" in event_property:
        specific_timer = infinity
        player_input_indicator = True
    elif "timer" in event_property:
        specific_timer = event_property["timer"]
    elif "select" in event_property:
        # selecting event, also infinite timer but not add player input indication
        specific_timer = infinity

    if "direction" in event_property:
        if self.sprite_direction != event_property["direction"]:  # change speech angle
            self.new_direction = event_property["direction"].capitalize()
            self.rotate_logic()

    self.speech = CharacterSpeechBox(self, self.battle.localisation.grab_text(("event", event["Text ID"], "Text")),
                                     specific_timer=specific_timer,
                                     player_input_indicator=player_input_indicator,
                                     cutscene_event=event, add_log=event["Text ID"], voice=voice, body_part=body_part,
                                     font_size=font_size, max_text_width=max_text_width)

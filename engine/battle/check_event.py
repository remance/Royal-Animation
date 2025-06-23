from copy import deepcopy

from pygame.mixer import Sound


def check_event(self):
    for player_index, player_object in self.player_objects.items():
        player_object.player_input(player_index, self.dt)

    if self.reach_scene_event_list:
        # check for event with camera reaching
        if self.scenes.reach_scene in self.reach_scene_event_list:
            if "weather" in self.reach_scene_event_list[self.scenes.reach_scene]:
                # change weather
                self.current_weather.__init__(
                    self.reach_scene_event_list[self.scenes.reach_scene]["weather"][0],
                    self.reach_scene_event_list[self.scenes.reach_scene]["weather"][1],
                    self.reach_scene_event_list[self.scenes.reach_scene]["weather"][2],
                    self.weather_data)
                self.reach_scene_event_list[self.scenes.reach_scene].pop("weather")
            if "music" in self.reach_scene_event_list[self.scenes.reach_scene]:  # change music
                self.current_music = None
                if self.reach_scene_event_list[self.scenes.reach_scene]["music"] != "none":
                    self.current_music = self.stage_music_pool[
                        self.reach_scene_event_list[self.scenes.reach_scene]["music"]]
                if self.current_music:
                    self.music_left.play(self.current_music, loops=-1, fade_ms=100)
                    self.music_right.play(self.current_music, loops=-1, fade_ms=100)
                    self.music_left.set_volume(self.play_music_volume, 0)
                    self.music_right.set_volume(0, self.play_music_volume)
                else:  # stop music
                    self.music_left.stop()
                    self.music_right.stop()
                self.reach_scene_event_list[self.scenes.reach_scene].pop("music")
            if "ambient" in self.reach_scene_event_list[self.scenes.reach_scene]:  # change ambient
                self.current_ambient = None
                if self.reach_scene_event_list[self.scenes.reach_scene]["ambient"] != "none":
                    self.current_ambient = Sound(self.ambient_pool[
                                                     self.reach_scene_event_list[self.scenes.reach_scene][
                                                         "ambient"]])
                if self.current_ambient:
                    self.ambient.play(self.current_ambient, loops=-1, fade_ms=100)
                    self.ambient.set_volume(self.play_effect_volume)
                else:  # stop ambient
                    self.ambient.stop()
                self.reach_scene_event_list[self.scenes.reach_scene].pop("ambient")
            if "sound" in self.reach_scene_event_list[self.scenes.reach_scene]:  # play sound
                for sound_effect in self.reach_scene_event_list[self.scenes.reach_scene]["sound"]:
                    self.add_sound_effect_queue(sound_effect[0],
                                                self.camera_pos, sound_effect[1], sound_effect[2])
                self.reach_scene_event_list[self.scenes.reach_scene].pop("sound")
            if "cutscene" in self.reach_scene_event_list[self.scenes.reach_scene]:  # cutscene
                self.cutscene_finish_camera_delay = 1
                for parent_event in self.reach_scene_event_list[self.scenes.reach_scene]["cutscene"]:
                    # play one parent at a time
                    self.cutscene_playing = parent_event
                    if "replayable" not in parent_event[0]["Property"]:
                        self.reach_scene_event_list[self.scenes.reach_scene].pop("cutscene")
            if not self.reach_scene_event_list[self.scenes.reach_scene]:  # no more event left
                self.reach_scene_event_list.pop(self.scenes.reach_scene)

    if self.player_interact_event_list:  # event that require player interaction (talk)
        event_list = sorted({key[0]: self.main_player_object.base_pos.distance_to(key[1]) for key in
                             [(item2, item2) if type(item2) is tuple else (item2, item2.base_pos) for
                              item2 in
                              self.player_interact_event_list]}.items(), key=lambda item3: item3[1])
        for item in event_list:
            target_pos = item[0]
            if type(item[0]) is not tuple:
                target_pos = (item[0].base_pos[0], item[0].base_pos[1] - (item[0].sprite_size * 4.5))
            distance = self.main_player_object.base_pos[0] - target_pos[0]
            direction_check = "Right"
            if distance < 0:  # target at left side
                direction_check = "Left"
            if 50 <= abs(distance) <= 250 and self.main_player_object.sprite_direction == direction_check:
                # use player with the lowest number as interactor
                self.speech_prompt.add_to_screen(self.main_player_object, item[0], target_pos)
                if self.player_key_press[self.main_player]["Weak"]:  # player interact, start event
                    self.speech_prompt.clear()  # remove prompt

                    if type(item[0]) is not tuple:
                        if (item[0].base_pos[0] - self.main_player_object.base_pos[0] < 0 and
                            item[0].sprite_direction != "Right") or \
                                (item[0].base_pos[0] - self.main_player_object.base_pos[0] >= 0 and
                                 item[0].sprite_direction != "Left"):  # target change direction to face player
                            item[0].new_direction *= -1
                            item[0].rotate_logic()

                    if "replayable" not in self.player_interact_event_list[item[0]][0][0]["Property"]:
                        self.cutscene_playing = self.player_interact_event_list[item[0]][0]
                        self.player_interact_event_list[item[0]].remove(self.cutscene_playing)
                        if not self.player_interact_event_list[item[0]]:
                            self.player_interact_event_list.pop(item[0])
                    else:  # event can be replayed while in this mission, use copy to prevent delete
                        self.cutscene_playing = deepcopy(self.player_interact_event_list[item[0]][0])
                break  # found event npc
            elif distance > 250:  # no event npc nearby
                break

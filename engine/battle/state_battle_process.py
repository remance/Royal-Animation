from types import MethodType

from pygame.mixer import Channel

from engine.character.character import Character


def state_battle_process(self, esc_press):
    # print(" ")
    if esc_press:  # pause game and open menu
        for sound_ch in range(1000):
            if Channel(sound_ch).get_busy():  # pause all sound playing
                Channel(sound_ch).pause()

        self.change_game_state("menu")  # open menu
        self.scene_translation_text_popup.popup(
            (self.screen_rect.midleft[0], self.screen_height * 0.88),
            self.game.localisation.grab_text(
                ("scene", self.chapter, self.mission, self.stage, str(self.current_scene), "Text")),
            width_text_wrapper=self.screen_width)
        self.add_ui_updater(self.cursor, self.battle_menu_button.values(),
                            self.scene_translation_text_popup)  # add menu and its buttons to drawer
        self.realtime_ui_updater.remove(self.main_player_battle_cursor)
    elif not self.cutscene_playing:
        if self.player_key_press[self.main_player]["Inventory Menu"]:
            # open court book
            self.court_book.add_portraits(self.main_story_profile["interface event queue"]["courtbook"])
            self.add_ui_updater(self.cursor, self.court_book)
            self.change_game_state("court")
        elif self.player_key_press[self.main_player]["Special"]:
            # open city map
            self.add_ui_updater(self.cursor, self.city_map)
            self.change_game_state("map")

    self.camera_process()

    # Update game time
    self.dt = self.true_dt * self.game_speed  # apply dt with game_speed for calculation
    if self.dt > 0.1:  # one frame update should not be longer than 0.1 second for calculation
        self.dt = 0.1  # make it so stutter and lag does not cause overtime issue

    if self.cutscene_finish_camera_delay and not self.cutscene_playing:
        self.cutscene_finish_camera_delay -= self.dt
        if self.cutscene_finish_camera_delay < 0:
            self.cutscene_finish_camera_delay = 0

    self.ui_timer += self.dt  # ui update by real time instead of self time to reduce workload
    self.ui_dt = self.dt  # get ui timer before apply

    if self.main_player_battle_cursor.pos_change:  # display cursor when have movement
        self.show_cursor_timer = 0.1
        self.main_player_battle_cursor.shown = True

    if self.show_cursor_timer:
        self.show_cursor_timer += self.dt
        if self.show_cursor_timer > 3:
            self.show_cursor_timer = 0
            self.main_player_battle_cursor.shown = False
            self.main_player_battle_cursor.rect.topleft = (-100, -100)

    # Weather system
    if self.current_weather.spawn_rate:
        self.weather_spawn_timer += self.dt
        if self.weather_spawn_timer >= self.current_weather.spawn_rate:
            self.weather_spawn_timer = 0
            self.spawn_weather_matter()

    # Screen shaking
    self.shown_camera_pos = self.camera_pos.copy()  # reset camera pos first
    if self.screen_shake_value:
        decrease = 1000
        if self.screen_shake_value > decrease:
            decrease = self.screen_shake_value
        self.screen_shake_value -= (self.dt * decrease)
        self.shake_camera()
        if self.screen_shake_value < 0:
            self.screen_shake_value = 0

    current_frame = self.camera_pos[0] / self.screen_width
    if current_frame == 0.5:  # at center of first scene
        self.current_scene = 1
        self.spawn_check_scene = 1
        self.reach_scene = 1
    elif abs(current_frame - int(current_frame)) >= 0.5:  # at right half of scene
        self.current_scene = int(current_frame) + 1
        self.spawn_check_scene = self.current_scene
        self.reach_scene = self.current_scene + 1
    else:
        self.current_scene = int(current_frame)  # at left half of scene
        self.spawn_check_scene = self.current_scene + 1
        self.reach_scene = self.current_scene
    self.camera_scale = (self.camera_pos[0] - (self.screen_width * self.current_scene)) / self.screen_width

    self.camera_y_shift = self.camera_center_y - self.shown_camera_pos[1]

    if abs(self.camera_scale - int(self.camera_scale)) != 0.5:  # two frames shown in one screen
        if self.camera_scale > 0.5:
            self.camera_scale = (self.camera_scale, 1 - self.camera_scale)
        elif self.camera_scale > -0.5:
            self.camera_scale = (0.5 + self.camera_scale, -self.camera_scale + 0.5)
        else:
            self.camera_scale = (-self.camera_scale, self.camera_scale)
    else:
        self.camera_scale = 0

    # Battle related updater
    if not self.cutscene_playing:
        self.character_updater.update(self.dt)
        self.effect_updater.update(self.dt)
    else:
        self.character_updater.cutscene_update(self.dt)
        self.effect_updater.cutscene_update(self.dt)

    self.realtime_ui_updater.update()  # update UI

    self.common_process()

    # if self.ui_timer >= 0.1:
    #     for key, value in self.player_objects.items():
    #         self.player_portraits[key].value_input(value)
    #
    #     self.ui_drawer.draw(self.screen)  # draw the UI
    #     self.ui_timer -= 0.1
    if not self.cutscene_playing:  # no current cutscene check for event
        self.check_event()
    else:  # currently in cutscene mode
        end_battle_specific_mission = self.event_process()
        if end_battle_specific_mission is not None:  # event cause the end of mission, go to the output mission next
            return end_battle_specific_mission

        if not self.cutscene_playing:  # finish with current parent cutscene
            for char in self.character_updater:
                char.cutscene_update = MethodType(Character.cutscene_update, char)

    # camera update
    for key, stage in self.scenes.items():
        stage.update(self.camera_left, self.camera_y_shift)
        self.camera.update(self.shown_camera_pos, self.battle_cameras[key])
    self.camera.update(self.shown_camera_pos, self.battle_cameras["ui"])
    self.camera.out_update(self.realtime_ui_updater)  # update ui last

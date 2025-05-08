from engine.utils.data_loading import filename_convert_readable as fcv


def state_map_process(self, esc_press):
    self.camera.out_update(self.realtime_ui_updater)
    self.ui_drawer.draw(self.screen)  # draw the UI

    self.common_process()

    if self.city_map.selected_map:  # player select new map
        selected_map = self.city_map.selected_map
        self.city_map.selected_map = None
        self.remove_ui_updater(self.cursor, self.city_map)
        self.change_game_state("battle")
        return fcv(selected_map)
    elif self.player_key_press[self.main_player]["Special"] or esc_press:
        self.remove_ui_updater(self.cursor, self.city_map)
        self.change_game_state("battle")

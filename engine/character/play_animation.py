def play_animation(self, dt, hold_check):
    """
    Play character animation
    :param self: Character object
    :param dt: Time
    :param hold_check: Check if holding animation frame or not
    :return: Boolean of animation finish playing or not
    """
    if not hold_check:  # not holding current frame
        self.frame_timer += dt
        if self.frame_timer >= self.final_animation_play_time:  # start next frame or end animation
            self.frame_timer = 0
            self.stoppable_frame = False

            if "reverse" not in self.current_action:
                if self.show_frame != self.max_show_frame:  # continue next frame
                    self.show_frame += 1
                else:  # reach end frame
                    self.show_frame = 0
                    if "repeat" not in self.current_action:  # not loop
                        return True
            else:
                if self.show_frame:  # continue next frame
                    self.show_frame -= 1
                else:  # reach end frame
                    if "repeat" not in self.current_action:  # not loop
                        return True

            if self.current_animation_direction[self.show_frame]["sound_effect"]:  # play sound from animation
                sound = self.current_animation_direction[self.show_frame]["sound_effect"]
                self.battle.add_sound_effect_queue(self.sound_effect_pool[sound[0]][0],
                                                   self.pos, sound[1], sound[2])

            self.start_animation_body_part()
            self.final_animation_play_time = self.animation_play_time

            if "play_time_mod" in self.current_animation_direction[self.show_frame]:
                self.final_animation_play_time *= self.current_animation_direction[self.show_frame]["play_time_mod"]
    elif self.just_change_mode:
        if hold_check:  # only do this when hold to change sprite mode
            self.start_animation_body_part()
        self.just_change_mode = False
    return False

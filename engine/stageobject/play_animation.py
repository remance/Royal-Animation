def play_animation(self, speed, dt, hold_check=False):
    """
    Play damage sprite animation
    :param self: Object of the animation sprite
    :param speed: Play speed
    :param dt: Time
    :param hold_check: Check if holding animation frame or not
    :return: Boolean of animation finish playing and just start
    """
    done = False
    just_start = False  # check if new frame just start playing this call
    if not hold_check:  # not holding current frame
        self.frame_timer += dt
        if self.frame_timer >= speed:
            self.frame_timer = 0
            just_start = True
            if self.show_frame < len(self.current_animation) - 1:  # continue next frame
                self.show_frame += 1
                self.base_image = self.current_animation[self.show_frame]
            else:  # reach end frame
                if self.repeat_animation:
                    self.show_frame = 0
                    self.base_image = self.current_animation[self.show_frame]
                else:
                    done = True
        self.adjust_sprite()
        # self.rect already reset in adjust_sprite()
    return done, just_start

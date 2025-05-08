from random import uniform


def shake_camera(self):
    self.shown_camera_pos = [self.shown_camera_pos[0] + uniform(-1, 1) * self.screen_shake_value,
                             self.shown_camera_pos[1] + uniform(-1, 1) * self.screen_shake_value]

    if self.shown_camera_pos[0] > self.stage_end:  # camera cannot go further than max x
        self.shown_camera_pos[0] = self.stage_end
    elif self.shown_camera_pos[0] < self.camera_center_x:  # camera does not move beyond left corner scene
        self.shown_camera_pos[0] = self.camera_center_x

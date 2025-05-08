from pygame.sprite import Sprite


class Scene(Sprite):
    image = None
    battle = None

    def __init__(self):
        from engine.game.game import Game
        self.main_dir = Game.main_dir
        self.data_dir = Game.data_dir
        self.screen_scale = Game.screen_scale
        self.screen_size = Game.screen_size
        self.screen_width = self.screen_size[0]
        self.screen_height = self.screen_size[1]
        self.half_screen = self.screen_width / 2
        self._layer = 0
        Sprite.__init__(self)
        self.data = {}
        self.images = {}
        self.shown_camera_pos = None

        self.alpha = 0
        self.fade_speed = 1
        self.fade_start = False
        self.fade_in = False
        self.fade_out = False
        self.fade_delay = 0

    def update(self, camera_scale, current_scene, shown_camera_pos, camera_y_shift):
        if camera_scale:  # two frames shown in one screen
            if current_scene in self.data:
                frame_one = self.images[self.data[current_scene]]
                rect = frame_one.get_rect(topright=(self.screen_width - (self.screen_width * camera_scale[0]),
                                                    camera_y_shift))
                self.image.blit(frame_one, rect)

            if current_scene + 1 in self.data:
                frame_two = self.images[self.data[current_scene + 1]]
                rect = frame_two.get_rect(topleft=(self.screen_width * camera_scale[1], camera_y_shift))
                self.image.blit(frame_two, rect)
        else:
            if current_scene in self.data:
                frame_image = self.images[self.data[current_scene]]
                rect = frame_image.get_rect(midtop=(frame_image.get_width() / 2, camera_y_shift))
                self.image.blit(frame_image, rect)

        if self.fade_start:
            if self.fade_in:  # keep fading in
                self.alpha += self.battle.dt * self.fade_speed
                if self.alpha >= 255:
                    self.alpha = 255
                    self.fade_in = False
                self.image.fill((0, 0, 0, self.alpha))
            elif self.fade_out:
                self.alpha -= self.battle.dt * self.fade_speed
                if self.alpha <= 0:
                    self.alpha = 0
                    self.fade_out = False
                self.image.fill((0, 0, 0, self.alpha))

            if self.fade_delay:
                self.fade_delay -= self.battle.dt
                if self.fade_delay < 0:
                    self.fade_delay = 0
            if not self.fade_delay:
                self.fade_start = False

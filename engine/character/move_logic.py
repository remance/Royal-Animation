from pygame import Vector2

infinity = float("inf")


def move_logic(self, dt):
    """Calculate and move character position according to speed"""
    if "movable" in self.current_action:
        # animation allow movement or in air which always allow movement
        if "walk" in self.current_action:
            if self.combat_state != "City":
                self.move_speed = self.walk_speed
            else:
                self.move_speed = self.city_walk_speed
        elif "run" in self.current_action:
            self.move_speed = self.run_speed
        else:
            self.move_speed = 1000 + abs(self.x_momentum * 2)

        if self.x_momentum:
            if self.x_momentum > 0:  # going right
                self.x_momentum -= dt * self.move_speed
                if self.x_momentum < 0.1:
                    self.x_momentum = 0
            else:  # going left
                self.x_momentum += dt * self.move_speed
                if self.x_momentum > 0.1:
                    self.x_momentum = 0

        if self.y_momentum > 0:  # climbing through air
            self.y_momentum -= dt * 800
            self.move_speed += self.y_momentum
            if self.y_momentum <= 0:  # reach highest y momentum now fall down
                self.y_momentum = -self.fall_gravity
        elif self.y_momentum < 0 and self.base_pos[1] == self.ground_pos:  # reach ground, reset y momentum
            self.y_momentum = 0

        if self.x_momentum or self.y_momentum:  # has movement
            new_pos = self.base_pos + Vector2(self.x_momentum, -self.y_momentum)
            move = new_pos - self.base_pos
            if move.length():
                move.normalize_ip()
                move *= self.move_speed * dt
                self.base_pos += move
                if "forced move" not in self.current_action:  # die, knockdown does not change direction
                    if self.x_momentum > 0:
                        self.new_direction = "Right"
                    elif self.x_momentum < 0:
                        self.new_direction = "Left"

                if self.base_pos[1] < -1000:
                    self.base_pos[1] = -1000
                    self.y_momentum = -self.fall_gravity

                if self.player_control:  # player character cannot go pass camera
                    if self.battle.base_camera_begin > self.base_pos[0]:
                        self.base_pos[0] = self.battle.base_camera_begin
                        self.x_momentum = 0
                    elif self.base_pos[0] > self.battle.base_camera_end:
                        self.base_pos[0] = self.battle.base_camera_end
                        self.x_momentum = 0
                else:  # AI character cannot go pass scene border unless broken
                    if self.battle.base_stage_start > self.base_pos[0]:
                        self.base_pos[0] = self.battle.base_stage_start
                        self.x_momentum = 0
                    elif self.base_pos[0] > self.battle.base_stage_end:
                        self.base_pos[0] = self.battle.base_stage_end
                        self.x_momentum = 0

                self.pos = Vector2((self.base_pos[0] * self.screen_scale[0],
                                    self.base_pos[1] * self.screen_scale[1]))

                for part in self.body_parts.values():
                    part.re_rect()

        elif "fly" not in self.current_action:
            # reach target, interrupt moving animation
            self.interrupt_animation = True  # in moving animation, interrupt it

    elif self.current_action:  # not movable animation, reset speed
        if "movable" in self.current_action:  # in moving animation, interrupt it
            self.interrupt_animation = True

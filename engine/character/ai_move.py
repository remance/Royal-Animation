from random import choice, uniform

from pygame import Vector2

follow_distance = 100
stay_formation_distance = 1


def stationary_ai(self):
    pass


def cinematic_ai(self):
    pass


def observer_ai(self):
    """Keep facing target"""
    if self.target.base_pos[0] >= self.base_pos[0]:
        self.new_direction = "Right"
    else:
        self.new_direction = "Left"


def common_ai(self):
    if not self.current_action and not self.command_action and not self.ai_movement_timer:
        # if not self.nearest_enemy or self.nearest_enemy[1] > self.max_attack_range:
        # walk randomly when not attack or inside scene lock
        self.ai_movement_timer = uniform(0.1, 3)
        self.x_momentum = uniform(0.1, 1.5) * self.walk_speed * choice((-1, 1))
        if (self.x_momentum < 0 and abs(self.base_pos[0] - self.battle.base_stage_start) < 50) or \
                (self.x_momentum > 0 and abs(self.base_pos[0] - self.battle.base_stage_end) < 50):
            # too close to corner move other way to avoid stuck
            self.x_momentum *= -1
        self.command_action = self.walk_command_action | {"x_momentum": True}


def move_city_ai(self):
    if not self.current_action and not self.command_action and not self.ai_movement_timer:
        # if not self.nearest_enemy or self.nearest_enemy[1] > self.max_attack_range:
        # walk randomly when not attack or inside scene lock
        self.ai_movement_timer = uniform(0.1, 5)
        self.x_momentum = uniform(0.1, 10) * self.city_walk_speed * choice((-1, 1))
        if (self.x_momentum < 0 and abs(self.base_pos[0] - self.battle.base_stage_start) < 50) or \
                (self.x_momentum > 0 and abs(self.base_pos[0] - self.battle.base_stage_end) < 50):
            # too close to corner move other way to avoid stuck
            self.x_momentum *= -1
        self.command_action = self.walk_command_action | {"x_momentum": True}


ai_move_dict = {"default": stationary_ai, "boss_cheer": observer_ai,
                "move_city_ai": move_city_ai}

from random import uniform


def enter_stage(self, animation_data_pool):
    """run once when scene start or character just get created"""
    from engine.character.character import BodyPart

    # Grab only animation sprite that the character can use
    self.animation_data_pool = animation_data_pool[self.char_id]
    self.animation_pool = animation_data_pool[self.char_id]
    exist_part = []  # list to remove unused body parts from loop entirely
    for animation in self.animation_pool.values():
        for frame in animation["Right"]:
            for part, data in frame.items():
                if data and part not in exist_part:
                    exist_part.append(part)

    self.body_parts = {key: value for key, value in self.body_parts.items() if key in exist_part}
    self.body_parts = {
        key: BodyPart(self, key) if not any(ext in key for ext in ("weapon", )) else BodyPart(self, key)
        for key, value in self.body_parts.items()}

    # adjust layer
    if self.player_control:  # player character get priority in sprite showing
        self.base_layer = int(self.layer_id * self.body_size * 1000000000)
        self.dead_layer = self.base_layer / 100000000
    else:
        if self.invincible:  # invincible character has lower layer priority
            self.base_layer = int(self.layer_id * self.body_size * 1000)
            self.dead_layer = self.base_layer
        else:
            self.base_layer = int(self.layer_id * self.body_size * 1000000)
            self.dead_layer = self.base_layer / 10000
    for part in self.body_parts.values():
        part.owner_layer = self.base_layer
        part.dead_layer = self.dead_layer

    self.pick_animation()

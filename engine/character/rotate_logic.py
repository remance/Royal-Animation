def rotate_logic(self):
    if self.sprite_direction != self.new_direction:
        self.sprite_direction = self.new_direction  # character can rotate at once
        self.current_animation_direction = self.current_animation[self.sprite_direction]

        for part in self.body_parts.values():
            part.re_rect()

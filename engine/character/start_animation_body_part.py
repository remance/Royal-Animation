def start_animation_body_part(self):
    from engine.effect.effect import Effect
    for key, part_data in self.current_animation_direction[self.show_frame].items():
        if part_data:
            if "effect_" in key:
                Effect(self.battle_camera, self, part_data, part_data[6], moveset=self.current_moveset)
            else:
                if key in self.body_parts:
                    # only change part if data not same as previous one
                    self.body_parts[key].get_part(part_data)
        elif key in self.body_parts:  # only reset for body part, not effect part
            self.body_parts[key].data = ()
            self.body_parts[key].re_rect()
            self.body_parts[key].already_hit = []

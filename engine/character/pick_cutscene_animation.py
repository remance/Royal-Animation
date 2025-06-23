def pick_cutscene_animation(self, action):
    """Pick animation to play for cutscene, simpler than normal pick_animation"""
    # reset various animation variable and position
    self.stoppable_frame = False
    self.hit_enemy = False
    self.interrupt_animation = False
    self.show_frame = 0
    self.frame_timer = 0
    self.release_timer = 0
    self.x_momentum = 0
    self.y_momentum = 0
    self.current_moveset = None
    self.continue_moveset = None
    self.move_speed = 0
    self.freeze_timer = 0

    self.command_action = {}
    self.current_action = action
    if "name" in self.current_action:  # pick animation with cutscene animation data
        animation_name = self.current_action["name"]
        if "replace_idle" in self.current_action:  # replace idle animation
            self.replace_idle_animation = self.current_action["name"]

    else:  # idle animation
        if not self.replace_idle_animation:
            animation_name = "Idle"
        else:
            animation_name = self.replace_idle_animation

    if animation_name in self.animation_pool:
        self.current_animation = self.animation_pool[animation_name]
    else:  # animation not found, use default
        print("cutscene_animation_not_found", self.name, animation_name, self.current_action)
        animation_name = "Default"
        self.current_animation = self.animation_pool["Default"]

    self.current_animation_direction = self.current_animation[self.sprite_direction]
    self.current_animation_data = self.animation_data_pool[animation_name]

    max_frame = len(self.current_animation_direction) - 1
    if "reverse" not in self.current_action:
        self.max_show_frame = max_frame
    else:
        self.max_show_frame = 0
        self.show_frame = max_frame
    self.max_show_frame = max_frame

    if "start_frame" in self.current_action:
        self.show_frame = int(self.cutscene_event["Property"]["start_frame"])
        if self.show_frame < 0:
            self.show_frame += len(self.current_animation_direction)
            if self.show_frame < 0:
                self.show_frame = 0

    self.current_animation_name = animation_name

    self.start_animation_body_part()
    self.final_animation_play_time = self.default_animation_play_time  # use default play speed
    if "play_time_mod" in self.current_animation_direction[self.show_frame]:
        self.final_animation_play_time *= self.current_animation_direction[self.show_frame]["play_time_mod"]

    if self.current_animation_direction[self.show_frame]["sound_effect"]:  # play sound from animation
        sound = self.current_animation_direction[self.show_frame]["sound_effect"]
        self.battle.add_sound_effect_queue(self.sound_effect_pool[sound[0]][0],
                                           self.pos, sound[1], sound[2])

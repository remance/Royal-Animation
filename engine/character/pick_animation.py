from engine.uibattle.uibattle import DamageNumber


def pick_animation(self):
    if "name" in self.current_action:  # pick animation with current action
        if "moveset" in self.current_action:
            animation_name = None
            if self.current_moveset:  # has moveset to perform
                animation_name = self.current_moveset["Move"]

                if "no prepare" not in self.current_action:  # check if action has prepare animation to perform
                    self.current_action = self.check_prepare_action(
                        self.current_moveset)  # check for prepare animation first
                if "sub action" not in self.current_action:  # main action now, not prepare or after action
                    resource_cost = self.current_moveset["Resource Cost"]
                    if self.current_moveset["Resource Cost"] > 0:
                        # only apply cost modifier for move that reduce resource
                        resource_cost = self.current_moveset["Resource Cost"] * self.resource_cost_modifier
                    if (self.resource >= resource_cost or (self.health_as_resource and
                                                           (self.health > resource_cost or self.is_summon))) and \
                            self.current_moveset["Move"] not in self.attack_cooldown:
                        self.current_action = self.current_action | self.current_moveset["Property"]  # add property

                        if self.resource >= resource_cost:
                            self.resource -= resource_cost
                            if self.resource < 0:
                                self.resource = 0
                            elif self.resource > self.base_resource:
                                self.resource = self.base_resource
                        else:  # use health, no need require check since condition above should do it already
                            self.health -= resource_cost

                        if self.current_moveset["Cooldown"]:
                            self.attack_cooldown[self.current_moveset["Move"]] = self.current_moveset["Cooldown"]

                    else:  # no resource to do the move, reset to idle
                        if self.current_moveset["Move"] in self.attack_cooldown:  # add cooldown value to screen
                            DamageNumber(str(round(self.attack_cooldown[self.current_moveset["Move"]], 1)),
                                         (self.pos[0], self.pos[1] - (self.sprite_height * 2)), False, self.team,
                                         move=False)
                        self.current_moveset = None
                        self.continue_moveset = None
                        animation_name = "Idle"

                else:  # prepare animation simply play without action related stuff
                    animation_name = self.current_action[
                        "name"]

            if not animation_name:  # None animation_name from no moveset found, use idle
                self.current_moveset = None
                self.continue_moveset = None
                self.current_action = {}
                animation_name = "Idle"
                self.current_animation = self.animation_pool[animation_name]

        else:  # animation that is not related to action moveset
            self.current_moveset = None
            self.continue_moveset = None
            animation_name = self.current_action["name"]

        if "replace_idle" in self.current_action:  # replace idle animation
            self.replace_idle_animation = self.current_action["name"]

    else:  # idle animation
        self.current_moveset = None
        self.continue_moveset = None

        if not self.replace_idle_animation:
            animation_name = "Idle"
        else:
            animation_name = self.replace_idle_animation

    if animation_name in self.animation_pool:
        self.current_animation = self.animation_pool[animation_name]
    else:  # animation not found, use default  # TODO remove in stable?
        print("notfound", self.name, animation_name, self.current_action, self.command_action, self.live)
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

    self.start_animation_body_part()
    self.final_animation_play_time = self.animation_play_time  # get new play speed
    if "play_time_mod" in self.current_animation_direction[self.show_frame]:
        self.final_animation_play_time *= self.current_animation_direction[self.show_frame]["play_time_mod"]
    if "animation_play_time_mod" in self.current_action:
        self.final_animation_play_time *= self.current_action["animation_play_time_mod"]

    if self.current_animation_direction[self.show_frame]["sound_effect"]:  # play sound from animation
        sound = self.current_animation_direction[self.show_frame]["sound_effect"]
        self.battle.add_sound_effect_queue(self.sound_effect_pool[sound[0]][0],
                                           self.pos, sound[1], sound[2])

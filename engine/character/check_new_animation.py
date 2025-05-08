from random import randint, uniform

from pygame import Vector2

from engine.effect.effect import Effect
from engine.uibattle.uibattle import DamageNumber


def check_new_animation(self, done):

    # Pick new action and animation, either when animation finish or get interrupt,
    # low level action got replace with more important one, finish playing, skill animation and its effect end
    if (self.interrupt_animation and "uninterruptible" not in self.current_action) or \
            (((not self.current_action or "low level" in self.current_action) and
              self.command_action) or done):
        # finish current action
        if done:
            if self.current_moveset:
                if self.current_moveset["Status"]:  # moveset apply status effect
                    for effect in self.current_moveset["Status"]:
                        self.apply_status(self, effect)
                        for ally in self.near_ally:
                            if ally[1] <= self.current_moveset["Range"]:  # apply status based on range
                                ally[0].apply_status(self, effect)
                            else:
                                break

        # Reset action check
        if "next action" in self.current_action and (not self.interrupt_animation or not self.command_action) and \
                (not self.current_moveset or "no auto next" not in self.current_moveset["Property"]):
            # play next action from current first instead of command if not finish by interruption
            self.current_action = self.current_action["next action"]
        elif ("remove momentum when done" not in self.current_action and
              (("x_momentum" in self.current_action and self.x_momentum) or
               ("y_momentum" in self.current_action and self.y_momentum))) and not self.interrupt_animation:
            # action that require movement to run out first before continue to next action
            pass  # pass not getting new action

        elif "run" in self.current_action and not self.command_action:  # stop running, halt
            self.current_action = self.halt_command_action
            if self.angle == -90:
                self.x_momentum = self.walk_speed
            else:
                self.x_momentum = -self.walk_speed
        elif "halt" in self.current_action:  # already halting
            self.x_momentum = 0
            self.current_action = self.command_action  # continue next action when animation finish
            self.command_action = {}
        else:
            self.current_action = self.command_action  # continue next action when animation finish
            self.command_action = {}

        # reset animation playing related value
        self.stoppable_frame = False
        self.interrupt_animation = False

        self.show_frame = 0
        self.frame_timer = 0
        self.move_speed = 0

        self.pick_animation()

        # new action property
        if "freeze" in self.current_action:
            self.freeze_timer = self.current_action["freeze"]

        if "x_momentum" in self.current_action and not isinstance(self.current_action["x_momentum"], bool):
            # action with specific x_momentum from data like attack action that move player, not for AI move
            if self.angle != 90:
                self.x_momentum = self.current_action["x_momentum"]
            else:
                self.x_momentum = -self.current_action["x_momentum"]
        if "y_momentum" in self.current_action and not isinstance(self.current_action["y_momentum"], bool):
            self.y_momentum = self.current_action["y_momentum"]

from math import log2

from pygame.sprite import spritecollide, collide_mask
from pygame.transform import smoothscale, flip


def hit_collide_check(self, check_damage_effect=True):
    """
    Check for collision with enemy effect and body parts
    @param self: Effect object
    @param check_damage_effect: Check for damage effect collision before body parts, also check for bodypart that deal damage
    @return: Boolean whether the object is killed from collision
    """
    hit_list = spritecollide(self, self.owner.enemy_part_list, False,
                             collided=collide_mask)  # check body part collision
    if hit_list:
        for enemy_part in hit_list:
            enemy = enemy_part.owner
            if enemy_part.can_hurt and enemy.live and enemy not in self.already_hit and \
                    ("no dmg" not in enemy.current_action or not enemy.player_control):  # collide body part
                collide_pos = collide_mask(self, enemy_part)
                if collide_pos:  # in case collide change
                    self.owner.hit_enemy = True
                    self.hit_register(enemy, enemy_part, collide_pos)
                    self.already_hit.append(enemy)

                    if not self.penetrate and not self.owner.attack_penetrate and not self.stick_reach:
                        self.reach_target()
                        return True
    if self.stick_timer and not self.stuck_part:  # bounce off after reach if not stuck on enemy part
        sprite_bounce(self)


def sprite_bounce(self):
    if self.angle > 0:
        self.x_momentum = 100
    else:
        self.x_momentum = -100
    self.y_momentum = 100
    self.current_animation = self.animation_pool["Base"]  # change image to base
    self.base_image = self.current_animation[self.show_frame]
    self.adjust_sprite()
    self.battle.all_damage_effects.remove(self)

import cProfile
from datetime import datetime
from math import cos, sin, radians
from random import choice

from pygame import Vector2, Surface, SRCALPHA, Color, Rect, draw, mouse
from pygame.font import Font
from pygame.transform import smoothscale, rotate, flip

from engine.uimenu.uimenu import UIMenu
from engine.utils.text_making import number_to_minus_or_plus, text_render_with_bg, text_render_with_texture, \
    minimise_number_text, make_long_text

team_colour = {0: Color("grey"), 1: Color("black"), 2: Color("red"), 3: Color("blue"), 4: Color("darkgoldenrod1"),
               5: Color("purple"), 6: Color("orange"),
               "health": Color("seagreen4"), "resource": Color("slateblue1"), "revive": Color("purple")}

chapter_font_name = {"simple": "simple_talk_font", "1": "ch1_talk_font", "2": "ch2_talk_font", "3": "ch3_talk_font",
                     "4": "ch4_talk_font", "5": "ch5_talk_font", "6": "ch6_talk_font"}


class UIBattle(UIMenu):
    def __init__(self, player_cursor_interact=True, has_containers=False):
        """
        Parent class for all battle menu user interface
        """
        from engine.battle.battle import Battle
        UIMenu.__init__(self, player_cursor_interact=player_cursor_interact, has_containers=has_containers)
        self.updater = Battle.ui_updater  # change updater to use battle ui updater instead of main menu one
        self.battle = Battle.battle
        self.screen = Battle.screen
        self.camera_size = Battle.camera_size
        self.camera_max = Battle.camera_max


class ButtonUI(UIBattle):
    def __init__(self, image, layer=11):
        self._layer = layer
        UIBattle.__init__(self)
        self.pos = (0, 0)
        self.image = image
        self.rect = self.image.get_rect(center=self.pos)
        self.mouse_over = False

    def change_pos(self, pos):
        self.pos = pos
        self.rect = self.image.get_rect(center=self.pos)


class BattleCursor(UIBattle):
    def __init__(self, images, player_input):
        """Game battle cursor"""
        self._layer = 100  # as high as possible, always blit last
        UIBattle.__init__(self)
        self.pos_change = False

        self.images = images
        self.image = images["normal"]
        self.pos = Vector2(self.screen_size[0] / 2, self.screen_size[1] / 29)
        self.old_mouse_pos = (0, 0)
        self.rect = self.image.get_rect(topleft=self.pos)
        self.player_input = player_input
        self.shown = True

    def change_input(self, player_input):
        self.player_input = player_input

    def change_image(self, image_name):
        """Change cursor image to whatever input name"""
        self.image = self.images[image_name]
        self.rect = self.image.get_rect(topleft=self.pos)

    def update(self):
        """Update cursor position based on joystick or mouse input"""
        new_pos = mouse.get_pos()
        self.pos_change = False
        if self.old_mouse_pos != new_pos:
            self.old_mouse_pos = new_pos
            self.pos = Vector2(self.old_mouse_pos)  # get pos from mouse first
            self.pos_change = True

        if self.player_input == "joystick":  # joystick control
            for joystick in self.battle.joysticks.values():
                for i in range(joystick.get_numaxes()):
                    if joystick.get_axis(i) > 0.1 or joystick.get_axis(i) < -0.1:
                        axis_name = number_to_minus_or_plus(joystick.get_axis(i))
                        if i == 2:
                            if axis_name == "+":
                                self.pos[0] += 5
                            else:
                                self.pos[0] -= 5
                        if i == 3:
                            if axis_name == "+":
                                self.pos[1] += 5
                            else:
                                self.pos[1] -= 5
                        self.pos_change = True

        if self.pos[0] > self.camera_max[0]:
            self.pos[0] = self.camera_max[0]
        elif self.pos[0] < 0:
            self.pos[0] = 0
        if self.pos[1] > self.camera_max[1]:
            self.pos[1] = self.camera_max[1]
        if self.pos[1] < 0:
            self.pos[1] = 0

        if self.shown:
            self.rect.topleft = self.pos


class ScreenFade(UIBattle):
    def __init__(self):
        self._layer = 99
        UIBattle.__init__(self)
        self.font = Font(self.ui_font["manuscript_font"], int(100 * self.screen_scale[1]))
        self.use_font_texture = "gold"
        self.text = None
        self.rect = self.battle.screen.get_rect()
        self.max_text_width = int(self.screen_size[0] * 0.8)
        self.image = Surface(self.rect.size, SRCALPHA)
        self.alpha = 0
        self.text_alpha = 0
        self.text_delay = 0
        self.fade_speed = 1
        self.text_surface = None
        self.text_rect = None
        self.text_fade_in = False
        self.fade_in_done = False
        self.fade_out = False
        self.done = False

    def reset(self, text=None, font_texture=None, font_size=70, instant_fade=False,
              text_fade_in=False, text_delay=0, fade_speed=1, fade_out=False):
        """
        Reset value for new fading
        @param text: new text
        @param font_texture: font texture name
        @param font_size: font size
        @param instant_fade: no fading animation
        @param text_fade_in: text also need to do fade in animation to appear
        @param text_delay: timer for delay showing text after fade in finish
        @param fade_speed: speed of screen fading
        @param fade_out: also fade out after finish
        """
        self.use_font_texture = font_texture
        self.text_alpha = 255
        self.text_fade_in = True
        if not text_fade_in:
            self.text_fade_in = False
            self.text_alpha = 0
        self.text_delay = text_delay
        if not font_texture:
            self.use_font_texture = "gold"
        if not instant_fade:
            self.alpha = 1  # fade in
        else:  # start with fade almost complete
            self.alpha = 254
        self.fade_speed = 1000 * fade_speed
        self.image = Surface(self.rect.size, SRCALPHA)
        self.image.fill((20, 20, 20))
        self.text = text
        self.text_surface = None
        self.text_rect = None
        self.fade_in_done = False
        self.fade_out = fade_out
        self.done = False
        if self.text:
            font_size = int(font_size * self.screen_scale[1])
            self.font = Font(self.ui_font["manuscript_font"], font_size)
            image_height = int((self.font.render(self.text, True, (0, 0, 0)).get_width()) / self.max_text_width)
            if not image_height:  # only one line
                self.text_surface = text_render_with_texture(self.text, self.font,
                                                             self.font_texture[self.use_font_texture])
            else:
                # Find new image height, using code from make_long_text
                x, y = (font_size, font_size)
                words = [word.split(" ") for word in
                         str(text).splitlines()]  # 2D array where each row is a list of words
                space = self.font.size(" ")[0]  # the width of a space
                for line in words:
                    for word in line:
                        word_surface = self.font.render(word, True, (0, 0, 0))
                        word_width, word_height = word_surface.get_size()
                        if x + word_width >= self.max_text_width:
                            x = font_size  # reset x
                            y += word_height  # start on new row.
                        x += word_width + space
                    x = font_size  # reset x
                    y += word_height  # start on new row
                self.text_surface = Surface((self.max_text_width, y), SRCALPHA)
                self.text_surface.fill((0, 0, 0, 0))
                make_long_text(self.text_surface, text, (font_size, font_size), self.font,
                               with_texture=(self.font_texture[self.use_font_texture], None),
                               specific_width=self.max_text_width, alignment="center")

            self.text_rect = self.text_surface.get_rect(center=self.image.get_rect().center)
            if not text_fade_in:
                self.image.blit(self.text_surface, self.text_rect)
        self.image.set_alpha(self.alpha)

    def update(self):
        if not self.fade_in_done:  # keep fading
            self.alpha += self.battle.true_dt * self.fade_speed
            if self.alpha >= 255:
                self.alpha = 255
                self.fade_in_done = True
            self.image.set_alpha(self.alpha)
        elif self.text_fade_in and self.text:  # add text when finish fading if any
            if not self.text_delay:
                self.image.blit(self.text_surface, self.text_rect)
                if self.text_alpha:
                    self.text_alpha -= self.battle.true_dt
                    if self.text_alpha < 0:
                        self.text_alpha = 0
        else:
            if self.text_delay:
                self.text_delay -= self.battle.true_dt
                if self.text_delay < 0:
                    self.text_delay = 0
            if not self.text_delay:
                if self.fade_out:
                    self.alpha -= self.battle.true_dt * self.fade_speed
                    if self.alpha <= 0:
                        self.alpha = 0
                        self.done = True
                    self.image.set_alpha(self.alpha)
                else:
                    self.done = True


class PlayerPortrait(UIBattle):
    def __init__(self, health_bar_image, resource_bar_image, guard_bar_image, player, pos):
        self._layer = 9
        UIBattle.__init__(self, player_cursor_interact=False)
        self.player = player
        self.image = Surface((320 * self.screen_scale[0], 120 * self.screen_scale[1]), SRCALPHA)
        self.rect = self.image.get_rect(midleft=pos)

        self.font = Font(self.ui_font["main_button"], int(18 * self.screen_scale[1]))

        self.health_bar_image = health_bar_image
        self.base_health_bar_image = health_bar_image.copy()
        self.health_bar_rect = self.health_bar_image.get_rect(topleft=(120 * self.screen_scale[0],
                                                                       20 * self.screen_scale[1]))
        self.health_text_rect = self.health_bar_image.get_rect(center=(self.health_bar_image.get_width() / 2,
                                                                       self.health_bar_image.get_height() / 2))

        self.resource_bar_image = resource_bar_image
        self.base_resource_bar_image = resource_bar_image.copy()
        self.resource_bar_rect = self.resource_bar_image.get_rect(topleft=(120 * self.screen_scale[0],
                                                                           50 * self.screen_scale[1]))
        self.resource_text_rect = self.resource_bar_image.get_rect(center=(self.health_bar_image.get_width() / 2,
                                                                           self.health_bar_image.get_height() / 2))

        self.guard_bar_image = guard_bar_image
        self.base_guard_bar_image = guard_bar_image.copy()
        self.guard_bar_rect = self.guard_bar_image.get_rect(topleft=(120 * self.screen_scale[0],
                                                                     80 * self.screen_scale[1]))
        self.guard_text_rect = self.guard_bar_image.get_rect(center=(self.health_bar_image.get_width() / 2,
                                                                     self.health_bar_image.get_height() / 2))

        self.bar_size = self.base_health_bar_image.get_size()
        self.last_health_value = None
        self.last_resource_value = None
        self.last_guard_value = None
        self.last_resurrect_value = None

        self.base_image = self.image.copy()

    def add_char_portrait(self, who):
        self.image = self.base_image.copy()
        if who.char_id + self.battle.chapter in self.battle.character_data.character_portraits:
            portrait = self.battle.character_data.character_portraits[who.char_id + self.battle.chapter]
        else:
            portrait = self.battle.character_data.character_portraits[who.char_id]
        portrait_rect = portrait.get_rect(topleft=(0, 0))
        self.image.blit(portrait, portrait_rect)
        self.reset_value()

    def reset_value(self):
        self.last_health_value = None
        self.last_resource_value = None
        self.last_guard_value = None
        self.last_resurrect_value = None

    def value_input(self, who):
        if self.last_health_value != who.health:
            self.last_health_value = who.health
            self.health_bar_image = self.base_health_bar_image.copy()
            percent = 1 - (who.health / who.base_health)
            bar = Surface((self.bar_size[0] * percent, self.bar_size[1]))
            bar.fill((0, 0, 0))
            self.health_bar_image.blit(bar, (self.bar_size[0] - bar.get_width(), 0))
            value_text = self.font.render(str(int(self.last_health_value)) + " / " + str(who.base_health), True,
                                          (220, 220, 220))
            self.health_bar_image.blit(value_text, self.health_text_rect)
            self.image.blit(self.health_bar_image, self.health_bar_rect)

        if self.last_resource_value != who.resource:
            self.last_resource_value = who.resource
            self.resource_bar_image = self.base_resource_bar_image.copy()
            percent = 1 - (who.resource / who.base_resource)
            bar = Surface((self.bar_size[0] * percent, self.bar_size[1]))
            bar.fill((0, 0, 0))
            self.resource_bar_image.blit(bar, (self.bar_size[0] - bar.get_width(), 0))
            value_text = self.font.render(str(int(self.last_resource_value)) + " / " + str(who.base_resource), True,
                                          (220, 220, 220))
            self.resource_bar_image.blit(value_text, self.resource_text_rect)
            self.image.blit(self.resource_bar_image, self.resource_bar_rect)

        if self.last_guard_value != who.guard:
            self.last_guard_value = who.guard
            self.guard_bar_image = self.base_guard_bar_image.copy()
            percent = 1 - (who.guard / who.max_guard)
            bar = Surface((self.bar_size[0] * percent, self.bar_size[1]))
            bar.fill((0, 0, 0))
            self.guard_bar_image.blit(bar, (self.bar_size[0] - bar.get_width(), 0))
            value_text = self.font.render(str(int(self.last_guard_value)) + " / " + str(who.max_guard), True,
                                          (220, 220, 220))
            self.guard_bar_image.blit(value_text, self.guard_text_rect)
            self.image.blit(self.guard_bar_image, self.guard_bar_rect)


class FPSCount(UIBattle):
    def __init__(self, parent):
        self._layer = 12
        UIBattle.__init__(self, player_cursor_interact=False)
        self.image = Surface((160 * self.screen_scale[0], 80 * self.screen_scale[1]), SRCALPHA)
        self.base_image = self.image.copy()
        self.font = Font(self.ui_font["main_button"], int(60 * self.screen_scale[1]))
        self.clock = parent.clock
        fps_text = self.font.render("60", True, (255, 60, 60))
        self.text_rect = fps_text.get_rect(center=(self.image.get_width() / 2, self.image.get_height() / 2))
        self.rect = self.image.get_rect(topleft=self.screen_rect.topleft)

    def update(self):
        """Update current fps"""
        self.image = self.base_image.copy()
        fps = str(int(self.clock.get_fps()))
        fps_text = self.font.render(fps, True, (255, 60, 60))
        self.image.blit(fps_text, self.text_rect)


class YesNo(UIBattle):
    def __init__(self, images):
        UIBattle.__init__(self)
        self._layer = 5
        self.yes_image = images["yes"]
        self.no_image = images["no"]

        self.yes_zoom_animation_timer = 0
        self.no_zoom_animation_timer = 0

        self.image = Surface((self.yes_image.get_width() * 2.5, self.yes_image.get_height() * 1.5), SRCALPHA)
        self.base_image = self.image.copy()

        self.pos = Vector2(self.screen_size[0] / 2, 400 * self.screen_scale[1])
        yes_image_rect = self.yes_image.get_rect(midleft=(0, self.image.get_height() / 2))
        no_image_rect = self.no_image.get_rect(midright=(self.image.get_width(), self.image.get_height() / 2))
        self.image.blit(self.yes_image, yes_image_rect)
        self.image.blit(self.no_image, no_image_rect)
        self.base_image2 = self.image.copy()
        self.selected = None

        self.rect = self.image.get_rect(center=self.pos)

    def update(self):
        yes_image_rect = self.yes_image.get_rect(midleft=(0, self.image.get_height() / 2))
        no_image_rect = self.no_image.get_rect(midright=(self.image.get_width(),
                                                         self.image.get_height() / 2))
        cursor_pos = (self.battle.main_player_battle_cursor.pos[0] - self.rect.topleft[0],
                      self.battle.main_player_battle_cursor.pos[1] - self.rect.topleft[1])
        if yes_image_rect.collidepoint(cursor_pos):
            self.image = self.base_image.copy()
            self.no_zoom_animation_timer = 0
            if not self.yes_zoom_animation_timer:
                self.yes_zoom_animation_timer = 0.01
                yes_zoom_animation_timer = 1.01
            else:
                self.yes_zoom_animation_timer += self.battle.dt / 5
                yes_zoom_animation_timer = 1 + self.yes_zoom_animation_timer
                if self.yes_zoom_animation_timer > 0.2:
                    yes_zoom_animation_timer = 1.2 - (self.yes_zoom_animation_timer - 0.2)
                    if self.yes_zoom_animation_timer > 0.4:
                        self.yes_zoom_animation_timer = 0

            yes_image = smoothscale(self.yes_image, (self.yes_image.get_width() * yes_zoom_animation_timer,
                                                     self.yes_image.get_height() * yes_zoom_animation_timer))
            yes_image_rect = yes_image.get_rect(midleft=(0, self.image.get_height() / 2))
            self.image.blit(yes_image, yes_image_rect)
            self.image.blit(self.no_image, no_image_rect)

        elif no_image_rect.collidepoint(cursor_pos):
            self.image = self.base_image.copy()
            self.yes_zoom_animation_timer = 0
            if not self.no_zoom_animation_timer:
                self.no_zoom_animation_timer = 0.01
                no_zoom_animation_timer = 1.01
            else:
                self.no_zoom_animation_timer += self.battle.dt / 5
                no_zoom_animation_timer = 1 + self.no_zoom_animation_timer
                if self.no_zoom_animation_timer > 0.2:
                    no_zoom_animation_timer = 1.2 - (self.no_zoom_animation_timer - 0.2)
                    if self.no_zoom_animation_timer > 0.4:
                        self.no_zoom_animation_timer = 0

            no_image = smoothscale(self.no_image, (self.no_image.get_width() * no_zoom_animation_timer,
                                                   self.no_image.get_height() * no_zoom_animation_timer))
            no_image_rect = no_image.get_rect(midright=(self.image.get_width(), self.image.get_height() / 2))
            self.image.blit(no_image, no_image_rect)
            self.image.blit(self.yes_image, yes_image_rect)

        elif self.no_zoom_animation_timer or self.yes_zoom_animation_timer:
            self.no_zoom_animation_timer = 0
            self.yes_zoom_animation_timer = 0
            self.image = self.base_image2.copy()

        if self.battle.player_key_press[self.battle.main_player]["Weak"]:
            if yes_image_rect.collidepoint(cursor_pos):
                self.selected = "yes"
            elif no_image_rect.collidepoint(cursor_pos):
                self.selected = "no"
                pass


class CharacterIndicator(UIBattle):
    def __init__(self, character):
        self._layer = 9999999999999999998
        UIBattle.__init__(self, has_containers=True)
        self.font = Font(self.ui_font["main_button"], 42)
        self.character = character
        self.height_adjust = character.sprite_height * 3.5
        if character.player_control:  # player indicator
            text = character.game_id

            self.image = text_render_with_bg(text,
                                             Font(self.ui_font["manuscript_font"], int(42 * self.screen_scale[1])),
                                             gf_colour=team_colour[self.character.team], o_colour=Color("white"))
        else:  # follower indicator
            text = "F" + str(character.leader.game_id)

            self.image = text_render_with_bg(text,
                                             Font(self.ui_font["manuscript_font"], int(32 * self.screen_scale[1])),
                                             gf_colour=team_colour[self.character.team], o_colour=Color("white"))

        self.base_pos = None
        self.pos = self.character.pos
        self.rect = self.image.get_rect(midbottom=self.pos)

    def update(self, dt):
        if self.base_pos != self.character.base_pos:
            self.base_pos = self.character.base_pos.copy()
            self.pos = (self.character.pos[0], (self.character.pos[1] - self.height_adjust))
            self.rect.midbottom = self.pos


class UIScroll(UIBattle):
    def __init__(self, ui, pos):
        """
        Scroll for any applicable ui
        :param ui: Any ui object, the ui must has max_row_show attribute, layer, and image surface
        :param pos: Starting pos
        :param layer: Surface layer value
        """
        self.ui = ui
        self._layer = self.ui.layer + 2  # always 2 layer higher than the ui and its item
        UIBattle.__init__(self)

        self.ui.scroll = self
        self.height_ui = self.ui.image.get_height()
        self.max_row_show = self.ui.max_row_show
        self.pos = pos
        self.image = Surface((10, self.height_ui))
        self.image.fill((255, 255, 255))
        self.base_image = self.image.copy()
        self.button_colour = (100, 100, 100)
        draw.rect(self.image, self.button_colour, (0, 0, self.image.get_width(), self.height_ui))
        self.rect = self.image.get_rect(topright=self.pos)
        self.current_row = 0
        self.row_size = 0

    def create_new_image(self):
        percent_row = 0
        max_row = 100
        self.image = self.base_image.copy()
        if self.row_size:
            percent_row = self.current_row * 100 / self.row_size
            max_row = (self.current_row + self.max_row_show) * 100 / self.row_size
        max_row = max_row - percent_row
        draw.rect(self.image, self.button_colour,
                  (0, int(self.height_ui * percent_row / 100), self.image.get_width(),
                   int(self.height_ui * max_row / 100)))

    def change_image(self, new_row=None, row_size=None):
        """New row is input of scrolling by user to new row, row_size is changing based on adding more log or clear"""
        if row_size is not None:
            self.row_size = row_size
        if new_row is not None:  # accept from both wheeling scroll and drag scroll bar
            self.current_row = new_row
        self.create_new_image()

    def player_input(self, mouse_pos, mouse_scroll_up=False, mouse_scroll_down=False):
        """Player input update via click or scrolling"""
        if mouse_pos and self.rect.collidepoint(mouse_pos):
            mouse_value = (mouse_pos[1] - self.pos[
                1]) * 100 / self.height_ui  # find what percentage of mouse_pos at the scroll bar (0 = top, 100 = bottom)
            if mouse_value > 100:
                mouse_value = 100
            if mouse_value < 0:
                mouse_value = 0
            new_row = int(self.row_size * mouse_value / 100)
            if self.row_size > self.max_row_show and new_row > self.row_size - self.max_row_show:
                new_row = self.row_size - self.max_row_show
            if self.row_size > self.max_row_show:  # only change scroll position in list longer than max length
                self.change_image(new_row)
            return self.current_row


class CharacterBaseInterface(UIBattle):
    def __init__(self, pos, image):
        UIBattle.__init__(self, player_cursor_interact=False)
        self.pos = pos
        self.image = image
        self.rect = self.image.get_rect(center=self.pos)


class CourtBook(UIBattle):
    def __init__(self, images):
        UIBattle.__init__(self)
        self._layer = 11
        self.images = images
        self.image = self.images["Base"]

        self.event = {}
        self.event_timer = 0

        self.empty_portrait = Surface((100 * self.screen_scale[0], 100 * self.screen_scale[1]), SRCALPHA)
        self.portrait_rect = {"King": self.empty_portrait.get_rect(
            center=(835 * self.screen_scale[0], 110 * self.screen_scale[1])),
            "Queen": self.empty_portrait.get_rect(
                center=(1085 * self.screen_scale[0], 110 * self.screen_scale[1])),
            "Regent": self.empty_portrait.get_rect(
                center=(1600 * self.screen_scale[0], 110 * self.screen_scale[1])),
            "Grand Marshal": self.empty_portrait.get_rect(
                center=(195 * self.screen_scale[0], 326 * self.screen_scale[1])),
            "Faith Keeper": self.empty_portrait.get_rect(
                center=(450 * self.screen_scale[0], 326 * self.screen_scale[1])),
            "Lord Steward": self.empty_portrait.get_rect(
                center=(705 * self.screen_scale[0], 326 * self.screen_scale[1])),
            "Lord Chancellor": self.empty_portrait.get_rect(
                center=(960 * self.screen_scale[0], 326 * self.screen_scale[1])),
            "Prime Minister": self.empty_portrait.get_rect(
                center=(1215 * self.screen_scale[0], 326 * self.screen_scale[1])),
            "Lord Chamberlain": self.empty_portrait.get_rect(
                center=(1470 * self.screen_scale[0], 326 * self.screen_scale[1])),
            "Confidant": self.empty_portrait.get_rect(
                center=(1725 * self.screen_scale[0], 326 * self.screen_scale[1])),
            "Royal Champion": self.empty_portrait.get_rect(
                center=(195 * self.screen_scale[0], 530 * self.screen_scale[1])),
            "Chief Scholar": self.empty_portrait.get_rect(
                center=(450 * self.screen_scale[0], 530 * self.screen_scale[1])),
            "Chief Architect": self.empty_portrait.get_rect(
                center=(705 * self.screen_scale[0], 530 * self.screen_scale[1])),
            "Lord Judge": self.empty_portrait.get_rect(
                center=(960 * self.screen_scale[0], 530 * self.screen_scale[1])),
            "Secret Keeper": self.empty_portrait.get_rect(
                center=(1215 * self.screen_scale[0], 530 * self.screen_scale[1])),
            "Vice Chamberlain": self.empty_portrait.get_rect(
                center=(1470 * self.screen_scale[0], 530 * self.screen_scale[1])),
            "Seneschal": self.empty_portrait.get_rect(
                center=(1725 * self.screen_scale[0], 530 * self.screen_scale[1])),
            "King Of Arms": self.empty_portrait.get_rect(
                center=(195 * self.screen_scale[0], 758 * self.screen_scale[1])),
            "Vice Marshal": self.empty_portrait.get_rect(
                center=(450 * self.screen_scale[0], 758 * self.screen_scale[1])),
            "Court Mage": self.empty_portrait.get_rect(
                center=(705 * self.screen_scale[0], 758 * self.screen_scale[1])),
            "Chief Justiciar": self.empty_portrait.get_rect(
                center=(960 * self.screen_scale[0], 758 * self.screen_scale[1])),
            "Chief Verderer": self.empty_portrait.get_rect(
                center=(1215 * self.screen_scale[0], 758 * self.screen_scale[1])),
            "Master Of Ceremony": self.empty_portrait.get_rect(
                center=(1470 * self.screen_scale[0], 758 * self.screen_scale[1])),
            "Health Keeper": self.empty_portrait.get_rect(
                center=(1725 * self.screen_scale[0], 758 * self.screen_scale[1])),
            "Provost Marshal": self.empty_portrait.get_rect(
                center=(195 * self.screen_scale[0], 950 * self.screen_scale[1])),
            "Hound Keeper": self.empty_portrait.get_rect(
                center=(450 * self.screen_scale[0], 950 * self.screen_scale[1])),
            "Master Of Ride": self.empty_portrait.get_rect(
                center=(705 * self.screen_scale[0], 950 * self.screen_scale[1])),
            "Flower Keeper": self.empty_portrait.get_rect(
                center=(960 * self.screen_scale[0], 950 * self.screen_scale[1])),
            "Master Of Hunt": self.empty_portrait.get_rect(
                center=(1215 * self.screen_scale[0], 950 * self.screen_scale[1])),
            "Court Jester": self.empty_portrait.get_rect(
                center=(1470 * self.screen_scale[0], 950 * self.screen_scale[1])),
            "Court Herald": self.empty_portrait.get_rect(
                center=(1725 * self.screen_scale[0], 950 * self.screen_scale[1]))}

        self.circle_rect = {key: self.images[key].get_rect(
            center=(value.centerx, value.centery + (10 * self.screen_scale[1]))) for
            key, value in self.portrait_rect.items()}

        self.base_image = self.image.copy()  # empty first image
        self.base_image2 = self.image.copy()  # image after added all portraits except one with event

        self.rect = self.image.get_rect(topleft=(0, 0))

    def check_character_localisation(self, who, item):
        if who:
            if who + self.battle.chapter in self.battle.character_data.character_portraits:
                return self.grab_text(("character", who + self.battle.chapter, item))
            elif who in self.battle.character_data.character_portraits:
                return self.grab_text(("character", who, item))
            elif who + str(self.battle.main_story_profile["character"][
                               "Sprite Ver"]) in self.battle.character_data.character_portraits:
                return self.grab_text(
                    ("character", who + str(self.battle.main_story_profile["character"]["Sprite Ver"]), item))
        return "Empty"

    def check_portrait(self, who):
        """Find portrait with appropriate version in data"""
        if who:
            if who + self.battle.chapter in self.battle.character_data.character_portraits:
                return self.battle.character_data.character_portraits[who + self.battle.chapter]
            elif who in self.battle.character_data.character_portraits:
                return self.battle.character_data.character_portraits[who]
            elif who + str(self.battle.main_story_profile["character"][
                               "Sprite Ver"]) in self.battle.character_data.character_portraits:
                return self.battle.character_data.character_portraits[
                    who + self.battle.main_story_profile["character"]["sprite ver"]]
        return self.empty_portrait

    def add_portraits(self, event):
        self.image = self.base_image.copy()
        self.event = event
        for portrait, rect in self.portrait_rect.items():
            if portrait not in event:
                self.blit_portrait(portrait,
                                   self.check_portrait(self.battle.main_story_profile["save state"]["court"][portrait]),
                                   rect)
            self.image.blit(self.images[portrait], self.circle_rect[portrait])
        self.base_image2 = self.image.copy()

    def blit_portrait(self, portrait_key, image, rect):
        if portrait_key in ("Queen", "Regent", "Lord Chancellor", "Prime Minister", "Confidant", "Chief Architect",
                            "Lord Judge", "Vice Chamberlain", "Vice Marshall", "Chief Verderer", "Health Keeper",
                            "Master of Ride", "Court Herald"):  # flip portrait to face left for some titles
            image = flip(image, True, False)
        self.image.blit(image, rect)

    def update(self):
        self.battle.remove_ui_updater(self.battle.text_popup)
        if self.event:
            playing_event = tuple(self.event.keys())[0]
            self.image = self.base_image2.copy()
            if not self.event_timer:
                self.battle.drama_text.queue.append((self.grab_text(("ui", playing_event)) + " " +
                                                     self.grab_text(("ui", "New Holder:")) +
                                                     self.check_character_localisation(self.event[playing_event],
                                                                                       "Name"),
                                                     "Parchment_write"))
                self.event_timer = 1
            else:
                self.event_timer -= self.battle.dt
            self.image.blit(self.images[playing_event], self.circle_rect[playing_event])
            if self.battle.main_story_profile["save state"]["court"][playing_event]:  # fade out old portrait
                old_image = self.check_portrait(
                    self.battle.main_story_profile["save state"]["court"][playing_event]).copy()
                old_image.set_alpha(255 * self.event_timer)
                self.blit_portrait(playing_event, old_image, self.portrait_rect[playing_event])
            old_image = self.check_portrait(self.event[playing_event]).copy()  # fade in new one
            old_image.set_alpha(255 * (1 - self.event_timer))
            self.blit_portrait(playing_event, old_image, self.portrait_rect[playing_event])
            self.image.blit(self.images[playing_event], self.circle_rect[playing_event])
            if self.event_timer <= 0:  # event end
                self.event_timer = 0
                self.battle.main_story_profile["save state"]["court"][playing_event] = self.event[playing_event]
                self.event.pop(playing_event)
                self.base_image2 = self.image.copy()
        else:
            cursor_pos = (self.battle.cursor.pos[0] - self.rect.topleft[0],
                          self.battle.cursor.pos[1] - self.rect.topleft[1])
            for image, rect in self.portrait_rect.items():
                if rect.collidepoint(cursor_pos):
                    self.battle.add_ui_updater(self.battle.text_popup)
                    char_name = self.battle.main_story_profile["save state"]["court"][image]
                    self.battle.text_popup.popup((0, 0),
                                                 (self.grab_text(("ui", image)),
                                                  self.grab_text(("ui", "Role:")) +
                                                  self.grab_text(("ui", image + "'s Role")),
                                                  self.grab_text(("ui", "Holder:")) +
                                                  self.check_character_localisation(char_name, "Name"),
                                                  self.check_character_localisation(char_name, "Description")),
                                                 shown_id=image, width_text_wrapper=800 * self.game.screen_scale[0])
                    break


class CityMap(UIBattle):
    def __init__(self, images):
        UIBattle.__init__(self)
        self._layer = 11
        self.selected_animation_timer = []
        self.images = images
        self.image = self.images["map"]
        self.base_image = self.image.copy()

        self.selected = None

        self.rect = self.image.get_rect(topleft=(0, 0))

        self.stage_select_rect = {"herbalist": self.images["herbalist"].get_rect(
            center=(252 * self.screen_scale[0], 691 * self.screen_scale[1])),
            "training": self.images["training"].get_rect(
                center=(330 * self.screen_scale[0], 285 * self.screen_scale[1])),
            "barrack": self.images["barrack"].get_rect(
                center=(428 * self.screen_scale[0], 394 * self.screen_scale[1])),
            "blacksmith": self.images["blacksmith"].get_rect(
                center=(438 * self.screen_scale[0], 579 * self.screen_scale[1])),
            "cathedral": self.images["cathedral"].get_rect(
                center=(711 * self.screen_scale[0], 645 * self.screen_scale[1])),
            "plaza": self.images["plaza"].get_rect(
                center=(884 * self.screen_scale[0], 704 * self.screen_scale[1])),
            "tavern": self.images["tavern"].get_rect(
                center=(970 * self.screen_scale[0], 801 * self.screen_scale[1])),
            "garden": self.images["garden"].get_rect(
                center=(1022 * self.screen_scale[0], 497 * self.screen_scale[1])),
            "artificer": self.images["artificer"].get_rect(
                center=(1339 * self.screen_scale[0], 382 * self.screen_scale[1])),
            "market": self.images["market"].get_rect(
                center=(1377 * self.screen_scale[0], 629 * self.screen_scale[1])),
            "scriptorium": self.images["scriptorium"].get_rect(
                center=(1617 * self.screen_scale[0], 436 * self.screen_scale[1])),
            "throne": self.images["throne"].get_rect(
                center=(1015 * self.screen_scale[0], 109 * self.screen_scale[1])),
            "library": self.images["library"].get_rect(
                center=(730 * self.screen_scale[0], 202 * self.screen_scale[1])),
            "hall": self.images["hall"].get_rect(
                center=(1021 * self.screen_scale[0], 199 * self.screen_scale[1])),
            "council": self.images["council"].get_rect(
                center=(1298 * self.screen_scale[0], 198 * self.screen_scale[1]))
        }

        for image, rect in self.stage_select_rect.items():
            self.base_image.blit(self.images[image], rect)
        self.image = self.base_image.copy()
        self.selected_map = None

    def update(self):
        cursor_pos = (self.battle.cursor.pos[0] - self.rect.topleft[0],
                      self.battle.cursor.pos[1] - self.rect.topleft[1])
        found_select = False
        self.selected_map = None
        for image, rect in self.stage_select_rect.items():
            if rect.collidepoint(cursor_pos):
                found_select = True
                self.image = self.base_image.copy()
                if self.selected_animation_timer:  # already has previous hovering
                    if self.selected_animation_timer[0] != image:  # different hovering
                        self.selected_animation_timer = [image, 0]
                else:
                    self.selected_animation_timer = [image, 0]
                self.selected_animation_timer[1] += self.battle.dt / 5
                zoom_animation_timer = 1 + self.selected_animation_timer[1]
                if self.selected_animation_timer[1] > 0.2:
                    zoom_animation_timer = 1.2 - (self.selected_animation_timer[1] - 0.2)
                    if self.selected_animation_timer[1] > 0.4:
                        self.selected_animation_timer[1] = 0

                new_image = smoothscale(self.images[image],
                                        (self.images[image].get_width() * zoom_animation_timer,
                                         self.images[image].get_height() * zoom_animation_timer))
                self.image.blit(new_image, new_image.get_rect(center=rect.center))

                if self.battle.player_key_press[self.battle.main_player][
                    "Weak"] or self.battle.cursor.is_select_just_up:
                    self.selected_map = image
                break

        if not found_select:
            self.selected_animation_timer = []
            self.image = self.base_image


class CharacterInteractPrompt(UIBattle):
    def __init__(self, image):
        """Weak button prompt that indicate player can talk to target"""
        self._layer = 9999999999999999999998
        UIBattle.__init__(self, player_cursor_interact=False)
        self.character = None
        self.target = None
        self.target_pos = None
        self.button_image = image
        font = Font(self.ui_font["manuscript_font"], int(40 * self.screen_scale[1]))
        text_surface = text_render_with_bg("Talk", font)
        self.image = Surface((150 * self.screen_scale[0], 55 * self.screen_scale[1]), SRCALPHA)
        text_rect = text_surface.get_rect(midright=self.image.get_rect().midright)
        self.image.blit(text_surface, text_rect)
        self.image.blit(image, image.get_rect(midleft=self.image.get_rect().midleft))

        self.rect = self.image.get_rect(center=(0, 0))

    def add_to_screen(self, character, target, target_pos):
        self.character = character
        self.target_pos = target_pos
        self.target = target
        font = Font(self.ui_font[chapter_font_name[self.battle.chapter]], int(40 * self.screen_scale[1]))
        text_surface = text_render_with_bg(target.show_name, font)
        self.image = Surface((text_surface.get_width() + self.button_image.get_width() +
                              (10 * self.screen_scale[0]), 55 * self.screen_scale[1]), SRCALPHA)
        text_rect = text_surface.get_rect(midright=self.image.get_rect().midright)
        self.image.blit(text_surface, text_rect)
        self.image.blit(self.button_image, self.button_image.get_rect(midleft=self.image.get_rect().midleft))

        self.rect = self.image.get_rect(midbottom=(self.target_pos[0] * self.screen_scale[0],
                                                   self.target_pos[1] * self.screen_scale[1]))
        if self not in self.battle.battle_cameras["ui"]:
            self.battle.battle_cameras["ui"].add(self)
            self.battle.effect_updater.add(self)

    def update(self, *args):
        if self.target_pos and not 100 < abs(self.character.base_pos[0] - self.target_pos[0]) < 250:
            # check if player move too far from current target prompt
            self.clear()

    def clear(self):
        self.character = None
        self.target = None
        self.target_pos = None
        if self in self.battle.battle_cameras["ui"]:
            self.battle.battle_cameras["ui"].remove(self)
            self.battle.effect_updater.remove(self)


class CharacterSpeechBox(UIBattle):
    images = {}
    simple_font = False

    def __init__(self, character, text, specific_timer=None, player_input_indicator=False, cutscene_event=None,
                 add_log=None, voice=False, body_part="p1_head", font_size=60, max_text_width=800):
        """Speech box that appear from character head"""
        self._layer = 9999999999999999998
        UIBattle.__init__(self, player_cursor_interact=False, has_containers=True)
        font = self.battle.chapter
        if self.simple_font:
            font = "simple"

        self.font_size = int(font_size * self.screen_scale[1])
        self.font = Font(self.ui_font[chapter_font_name[font]], self.font_size)
        max_text_width *= self.screen_scale[0]

        # Find text height, using code from make_long_text
        start_pos = (0, self.font_size / 2)
        true_max_width = start_pos[0]
        x, y = start_pos[0], start_pos[1]
        words = [word.split(" ") for word in
                 str(text).splitlines()]  # 2D array where each row is a list of words
        space = self.font.size(" ")[0]  # the width of a space
        exceed_max_width = False
        for line in words:
            for word in line:
                word_surface = self.font.render(word, True, (0, 0, 0))
                word_width, word_height = word_surface.get_size()
                if x + word_width >= max_text_width:
                    exceed_max_width = True
                    x = self.font_size  # reset x
                    y += word_height  # start on new row.
                if not exceed_max_width:
                    true_max_width += word_width + space
                x += word_width + space
            x = self.font_size  # reset x
            y += word_height  # start on new row

        self.text_surface = Surface((true_max_width, y), SRCALPHA)

        self.text_surface.fill((224, 224, 224))
        make_long_text(self.text_surface, text, start_pos, self.font)

        start_top = self.images["speech_start_top"]
        start_mid = smoothscale(self.images["speech_start_mid"], (self.images["speech_start_mid"].get_width(),
                                                                  self.text_surface.get_height()))
        start_bottom = self.images["speech_start_bottom"]

        end_top = self.images["speech_end_top"]
        end_mid = smoothscale(self.images["speech_end_mid"], (self.images["speech_end_mid"].get_width(),
                                                              self.text_surface.get_height()))
        end_bottom = self.images["speech_end_bottom"]

        body_top = smoothscale(self.images["speech_body_top"], (self.text_surface.get_width(),
                                                                self.images["speech_body_top"].get_height()))
        body_bottom = smoothscale(self.images["speech_body_bottom"], (self.text_surface.get_width(),
                                                                self.images["speech_body_bottom"].get_height()))

        self.base_image = Surface((self.text_surface.get_width() + start_top.get_width() + end_top.get_width(),
                                   self.text_surface.get_height() + start_top.get_height() + start_bottom.get_height()),
                                  SRCALPHA)

        start_top_rect = start_top.get_rect(topleft=(0, 0))
        self.base_image.blit(start_top, start_top_rect)

        start_bottom_rect = start_bottom.get_rect(bottomleft=(0, self.base_image.get_height()))
        self.base_image.blit(start_bottom, start_bottom_rect)

        start_mid_rect = start_mid.get_rect(topleft=(0, start_top_rect.height))
        self.base_image.blit(start_mid, start_mid_rect)

        end_top_rect = end_top.get_rect(topright=(self.base_image.get_width(), 0))
        self.base_image.blit(end_top, end_top_rect)

        end_bottom_rect = end_bottom.get_rect(bottomright=(self.base_image.get_width(), self.base_image.get_height()))
        self.base_image.blit(end_bottom, end_bottom_rect)

        end_mid_rect = end_mid.get_rect(topright=(self.base_image.get_width(), end_top_rect.height))
        self.base_image.blit(end_mid, end_mid_rect)

        body_top_rect = body_top.get_rect(topleft=(start_top_rect.width, 0))
        self.base_image.blit(body_top, body_top_rect)

        body_bottom_rect = body_bottom.get_rect(bottomleft=(start_bottom_rect.width, self.base_image.get_height()))
        self.base_image.blit(body_bottom, body_bottom_rect)

        self.right_image = self.base_image.copy()
        self.left_image = flip(self.base_image, 1, 0)

        text_rect = self.text_surface.get_rect(topleft=start_mid_rect.topright)
        self.right_image.blit(self.text_surface, text_rect)

        text_rect = self.text_surface.get_rect(topright=(self.base_image.get_width() - start_mid_rect.topright[0],
                                                             start_mid_rect.topright[1]))
        self.left_image.blit(self.text_surface, text_rect)

        if player_input_indicator:  # add player weak button indicate for closing speech in cutscene
            rect = self.images["button_weak"].get_rect(topleft=(0, text_rect.height * 1.2))
            self.left_image.blit(self.images["button_weak"], rect)

            rect = self.images["button_weak"].get_rect(topright=(self.base_image.get_width(),
                                                                 text_rect.height * 1.2))
            self.right_image.blit(self.images["button_weak"], rect)

        self.character = character
        self.character.speech = self
        self.player_input_indicator = player_input_indicator
        self.cutscene_event = cutscene_event
        self.head_part = self.character.body_parts[body_part]  # assuming character always has p1 head
        self.base_pos = self.character.base_pos.copy()
        self.finish_unfolding = False
        self.current_length = start_top.get_width()

        self.max_length = self.base_image.get_width()  # max length of the body, not counting the end corner

        self.base_image = self.right_image
        self.image = self.base_image.subsurface((0, 0, self.current_length, self.base_image.get_height()))
        self.rect = self.image.get_rect(midleft=self.head_part.rect.center)

        if voice:
            self.battle.add_sound_effect_queue(choice(self.battle.sound_effect_pool[voice[0]]),
                                               self.battle.camera_pos, voice[1],
                                               voice[2], volume="voice")
        elif voice is False:  # None will play no sound
            self.battle.add_sound_effect_queue(choice(self.battle.sound_effect_pool["Parchment_write"]),
                                               self.battle.camera_pos, 1000,
                                               0, volume="voice")

        if specific_timer:
            self.timer = specific_timer
        else:
            self.timer = 3
            if len(text) > 20:
                self.timer += int(len(text) / 20)
        if add_log:
            self.battle.main_story_profile["dialogue log"].append(("(" + datetime.now().strftime("%d/%m/%Y %H:%M:%S") + ")" +
                                            " ch." + self.battle.chapter + "." + self.battle.mission + "." +
                                            self.battle.stage + " " + self.character.show_name + ": ", add_log))
            if len(self.battle.main_story_profile["dialogue log"]) > 500:
                self.battle.main_story_profile["dialogue log"] = self.battle.main_story_profile["dialogue log"][1:]
        self.update(0)

    def update(self, dt):
        """Play unfold animation and blit text at the end"""
        direction_left = False
        if self.character.sprite_direction == "Left":  # left direction facing
            if self.head_part.rect.midleft[0] - (
                    self.battle.shown_camera_pos[0] - self.battle.camera.camera_w_center) < self.base_image.get_width():
                self.base_image = self.right_image
                self.rect = self.image.get_rect(bottomleft=self.head_part.rect.midright)
            else:
                # text will exceed screen, go other way
                direction_left = True
                self.base_image = self.left_image
                self.rect = self.image.get_rect(bottomright=self.head_part.rect.midleft)

        else:  # right direction facing
            if (self.battle.shown_camera_pos[0] + self.battle.camera.camera_w_center) - \
                    self.head_part.rect.midright[0] < self.base_image.get_width():
                # text will exceed screen, go other way
                direction_left = True
                self.base_image = self.left_image
                self.rect = self.image.get_rect(bottomright=self.head_part.rect.midleft)
            else:
                self.base_image = self.right_image
                self.rect = self.image.get_rect(bottomleft=self.head_part.rect.midright)

        if self.rect.midtop[1] < 0:  # exceed top scene
            self.rect = self.image.get_rect(midtop=(self.rect.midtop[0], 0))

        if self.current_length < self.max_length:  # keep unfolding if not yet reach max length
            self.current_length += self.max_length * dt
            if self.current_length > self.max_length:
                self.current_length = self.max_length
            if direction_left:
                self.image = self.base_image.subsurface((self.max_length - self.current_length, 0,
                                                         self.current_length, self.image.get_height()))
            else:
                self.image = self.base_image.subsurface((0, 0, self.current_length, self.image.get_height()))

        else:  # finish animation, count down timer
            self.timer -= dt
            if self.timer <= 0:
                self.character.speech = None
                self.kill()
                return

        if not self.character.live:  # kill speech if character die
            self.character.speech = None
            self.kill()
            return


class DamageNumber(UIBattle):
    def __init__(self, value, pos, critical, team, move=True):
        self._layer = 9999999999999999999
        UIBattle.__init__(self, has_containers=True)
        self.move = move

        if critical:
            self.image = text_render_with_bg(str(value),
                                             Font(self.ui_font["manuscript_font2"], int(76 * self.screen_scale[1])),
                                             gf_colour=team_colour[team])
        else:
            self.image = text_render_with_bg(str(value),
                                             Font(self.ui_font["manuscript_font"], int(46 * self.screen_scale[1])),
                                             gf_colour=team_colour[team])
        self.rect = self.image.get_rect(midbottom=pos)
        self.timer = 0.5

    def update(self, dt):
        self.timer -= dt
        if self.move:
            self.rect.center = (self.rect.center[0], self.rect.center[1] - (dt * 200))
        if self.timer <= 0:
            self.kill()


class WheelUI(UIBattle):
    command_list = {"Down": "Attack", "Left": "Free", "Up": "Follow", "Right": "Stay"}  # same as in PlayerCharacter
    item_sprite_pool = None
    choice_list_key = {"Down": 1, "Left": 2, "Up": 3, "Right": 4}
    choice_key = tuple(choice_list_key.keys())

    def __init__(self, images, player, pos):
        """Wheel choice ui to select item"""
        self._layer = 11
        UIBattle.__init__(self)
        self.small_font = Font(self.ui_font["main_button"], int(16 * self.screen_scale[1]))
        self.font = Font(self.ui_font["main_button"], int(20 * self.screen_scale[1]))
        self.pos = pos
        self.choice_list = ()
        self.selected = "Up"
        self.player = player

        self.wheel_button_image = images["wheel"]
        self.wheel_selected_button_image = images["wheel_selected"]
        self.wheel_text_image = images["wheel_text"]

        self.base_image2 = Surface((self.wheel_button_image.get_width() * 5,
                                    self.wheel_button_image.get_height() * 4), SRCALPHA)  # empty image
        self.rect = self.base_image2.get_rect(midtop=self.pos)

        image_center = (self.base_image2.get_width() / 2, self.base_image2.get_height() / 2)
        self.wheel_image_with_stuff = []
        self.wheel_selected_image_with_stuff = []
        self.wheel_rect = []
        angle_space = 360 / 4
        angle = 0
        for wheel_button in range(4):
            base_target = Vector2(image_center[0] - (image_center[0] / 2 *
                                                     sin(radians(angle))),
                                  image_center[1] + (image_center[1] / 1.6 *
                                                     cos(radians(angle))))
            angle += angle_space

            self.wheel_image_with_stuff.append(self.wheel_button_image.copy())
            self.wheel_selected_image_with_stuff.append(self.wheel_selected_button_image.copy())
            self.wheel_rect.append(self.wheel_button_image.get_rect(center=base_target))
            self.base_image2.blit(self.wheel_image_with_stuff[wheel_button], self.wheel_rect[wheel_button])
        self.image = self.base_image2.copy()

    def selection(self, key_input):
        self.selected = key_input
        for index, rect in enumerate(self.wheel_rect):
            if self.selected == self.choice_key[index]:
                self.image.blit(self.wheel_selected_image_with_stuff[index], rect)
            else:
                self.image.blit(self.wheel_image_with_stuff[index], rect)
            if self.choice_list[index]:
                text_image = self.wheel_text_image.copy()  # blit text again to avoid wheel overlap old text
                if self.choice_list[index] in self.command_list.values():  # command
                    text_surface = self.small_font.render(self.grab_text(("ui", self.choice_list[index])),
                                                          True,
                                                          (20, 20, 20))
                else:
                    text_surface = text_render_with_bg(
                        str(self.battle.player_objects[self.player].item_usage[self.choice_list[index]]),
                        self.font)  # add item number
                    self.wheel_image_with_stuff[index].blit(text_surface,
                                                            text_surface.get_rect(topright=rect.topright))
                    self.wheel_selected_image_with_stuff[index].blit(text_surface,
                                                                     text_surface.get_rect(topright=rect.topright))

                    text_surface = self.small_font.render(self.grab_text(("item", self.choice_list[index],
                                                                          "Name")), True, (20, 20, 20))

                text_image.blit(text_surface, text_surface.get_rect(center=(text_image.get_width() / 2,
                                                                            text_image.get_height() / 2)))

                self.image.blit(text_image, text_image.get_rect(center=self.wheel_rect[index].midbottom))

    def change_text_icon(self, blit_list, item_wheel=False):
        """Add icon or text to the wheel choice"""
        self.image = self.base_image2.copy()
        self.choice_list = blit_list
        for index, value in enumerate(blit_list):
            self.wheel_image_with_stuff[index] = self.wheel_button_image.copy()
            self.wheel_selected_image_with_stuff[index] = self.wheel_selected_button_image.copy()
            if value:  # Wheel choice with icon at center
                surface = self.item_sprite_pool[self.battle.chapter]["Normal"][value]
                rect = surface.get_rect(center=(self.wheel_image_with_stuff[index].get_width() / 2,
                                                self.wheel_image_with_stuff[index].get_height() / 2))

                self.wheel_image_with_stuff[index].blit(surface, rect)
                self.wheel_selected_image_with_stuff[index].blit(surface, rect)

                if item_wheel:
                    text_surface = text_render_with_bg(str(self.battle.player_objects[self.player].item_usage[value]),
                                                       self.font)  # add item number
                    self.wheel_image_with_stuff[index].blit(text_surface,
                                                            text_surface.get_rect(topright=rect.topright))
                    self.wheel_selected_image_with_stuff[index].blit(text_surface,
                                                                     text_surface.get_rect(topright=rect.topright))

                    text_surface = self.small_font.render(self.grab_text(("item", value, "Name")), True,
                                                          (20, 20, 20))
                else:
                    text_surface = self.small_font.render(self.grab_text(("ui", value)), True,
                                                          (20, 20, 20))

                if self.selected == self.choice_key[index]:
                    self.image.blit(self.wheel_selected_image_with_stuff[index], self.wheel_rect[index])
                else:
                    self.image.blit(self.wheel_image_with_stuff[index], self.wheel_rect[index])
                text_image = self.wheel_text_image.copy()
                text_image.blit(text_surface, text_surface.get_rect(center=(text_image.get_width() / 2,
                                                                            text_image.get_height() / 2)))

                self.image.blit(text_image, text_image.get_rect(center=self.wheel_rect[index].midbottom))


class Profiler(cProfile.Profile, UIBattle):

    def __init__(self):
        UIBattle.__init__(self, player_cursor_interact=False)
        self.size = (1200, 600)
        self.image = Surface(self.size)
        self.rect = Rect((0, 0, *self.size))
        self.font = Font(self.ui_font["main_button"], 16)
        self._layer = 12
        self.visible = False
        self.empty_image = Surface((0, 0))

    def refresh(self):
        import io
        from pstats import Stats

        # There should be a way to hide/show something using the sprite api but
        # I didn't get it to work so I did this solution instead

        if self.visible:
            self.image = Surface(self.size)
            s_io = io.StringIO()
            stats = Stats(self, stream=s_io)
            stats.sort_stats('tottime').print_stats(20)
            info_str = s_io.getvalue()
            self.enable()  # profiler must be re-enabled after get stats
            self.image.fill(0x112233)
            self.image.blit(self.font.render("press F7 to clear times", True, Color("white")), (0, 0))
            for e, line in enumerate(info_str.split("\n"), 1):
                self.image.blit(self.font.render(line, True, Color("white")), (0, e * 20))
        else:
            self.image = self.empty_image

    def switch_show_hide(self):
        self.visible = not self.visible
        self.refresh()

import webbrowser

browser = webbrowser.get()


def menu_main(self, esc_press):
    if self.start_game_button.event:  # preset map list menu
        self.start_battle("1", "1", "Teaparty")

    # elif self.lore_button.event:  # battle
    #     self.start_battle("1", "1", "Miqdoll")

    elif self.option_button.event:  # change main menu to option menu
        self.menu_state = "option"
        self.remove_ui_updater(self.mainmenu_button)

        self.add_ui_updater(self.option_menu_button, self.option_menu_sliders.values(), self.value_boxes.values(),
                            self.option_text_list)

    elif self.quit_button.event or esc_press:  # open quit game confirmation input
        self.activate_input_popup(("confirm_input", "quit"), "Quit Game?", self.confirm_ui_popup)

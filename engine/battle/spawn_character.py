from engine.character.character import AICharacter


def spawn_character(self, char_list):
    for data in char_list:
        # if type(data["Object ID"]) is not str:
        if "story choice" in data["Stage Property"]:
            mission_choice_appear = data["Stage Property"]["story choice"].split("_")[0]
        if ("no player pick" not in data["Stage Property"] or \
            data["ID"] not in [player.char_id for player in self.player_objects.values()]) and \
                ("story choice" not in data["Stage Property"] or
                 data["Stage Property"]["story choice"] ==
                 mission_choice_appear + "_" + self.main_story_profile["story choice"][mission_choice_appear]):
            # check if no_player_pick and player with same character exist
            specific_behaviour = None
            if "specific behaviour" in data["Stage Property"]:
                specific_behaviour = data["Stage Property"]["specific behaviour"]
            layer = data["Object ID"]
            if "set layer" in data["Stage Property"]:
                layer = data["Stage Property"]["set layer"]
            AICharacter(self.battle_cameras[data["Camera"]], data["Object ID"], layer,
                        data | self.character_data.character_list[data["ID"]] |
                        {"Sprite Ver": self.chapter}, specific_behaviour=specific_behaviour)

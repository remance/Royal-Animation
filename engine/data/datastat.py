import csv
import os

from engine.utils.data_loading import stat_convert, filename_convert_readable as fcv


class GameData:
    def __init__(self):
        from engine.game.game import Game
        self.main_dir = Game.main_dir
        self.data_dir = Game.data_dir
        self.font_dir = Game.font_dir
        self.localisation = Game.localisation
        self.screen_scale = Game.screen_scale


class CharacterData(GameData):
    def __init__(self):
        """
        For keeping all data related to character.
        """
        GameData.__init__(self)

        # Character stat dict
        default_mode = {}
        with open(os.path.join(self.data_dir, "animation", "template.csv"),
                  encoding="utf-8", mode="r") as edit_file:
            rd = tuple(csv.reader(edit_file, quoting=csv.QUOTE_ALL))
            for index, stuff in enumerate(rd[0]):
                if "special" in stuff:  # remove number after special
                    rd[0][index] = "_".join(rd[0][index].split("_")[:-1])
            default_mode["Normal"] = {stuff: "Normal" for
                                      index, stuff in enumerate(rd[0]) if stuff[0] == "p"}

        self.character_list = {}
        with open(os.path.join(self.data_dir, "character", "character.csv"),
                  encoding="utf-8", mode="r") as edit_file:
            rd = tuple(csv.reader(edit_file, quoting=csv.QUOTE_ALL))
            header = rd[0]
            for row_index, row in enumerate(rd[1:]):
                dict_column = ("Property",)
                dict_column = [index for index, item in enumerate(header) if item in dict_column]
                for n, i in enumerate(row):
                    row = stat_convert(row, n, i, dict_column=dict_column)

                self.character_list[row[0]] = {header[i]: row[i] for i, _ in enumerate(row)}
                # Add character mode data
                self.character_list[row[0]]["Mode"] = {"Normal": default_mode["Normal"]}
                if os.path.exists(
                        os.path.join(self.data_dir, "character", "character", fcv(row[0], revert=True) + ".csv")):
                    with open(os.path.join(self.data_dir, "character", "character", fcv(row[0], revert=True) + ".csv"),
                              encoding="utf-8", mode="r") as edit_file2:
                        rd2 = tuple(csv.reader(edit_file2, quoting=csv.QUOTE_ALL))
                        header2 = rd2[0]
                        for row_index2, row2 in enumerate(rd2[1:]):
                            self.character_list[row[0]]["Mode"][row2[0]] = {header2[index + 1]: stuff for
                                                                            index, stuff in enumerate(row2[1:])}
            edit_file.close()

        # self.character_portraits = load_images(self.data_dir, screen_scale=self.screen_scale,
        #                                        subfolder=("character", "portrait"),
        #                                        key_file_name_readable=True)

        # Effect that exist as its own sprite in battle
        self.effect_list = {}
        with open(os.path.join(self.data_dir, "character", "effect.csv"),
                  encoding="utf-8", mode="r") as edit_file:
            rd = tuple(csv.reader(edit_file, quoting=csv.QUOTE_ALL))
            header = rd[0]
            tuple_column = ("Status Conflict", "Status", "Enemy Status",
                            "Special Effect")  # value in tuple only
            tuple_column = [index for index, item in enumerate(header) if item in tuple_column]
            dict_column = ("Property",)
            dict_column = [index for index, item in enumerate(header) if item in dict_column]
            for index, row in enumerate(rd[1:]):
                for n, i in enumerate(row):
                    row = stat_convert(row, n, i, tuple_column=tuple_column, dict_column=dict_column)
                self.effect_list[row[0]] = {header[index + 1]: stuff for index, stuff in enumerate(row[1:])}
        edit_file.close()

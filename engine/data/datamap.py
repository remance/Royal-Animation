import copy
import csv
import os
from pathlib import Path

from engine.data.datastat import GameData
from engine.utils.data_loading import stat_convert, load_images, filename_convert_readable as fcv


class BattleMapData(GameData):
    def __init__(self):
        """
        For keeping all data related to battle map.
        """
        GameData.__init__(self)

        self.weather_data = {}
        with open(os.path.join(self.data_dir, "map", "weather", "weather.csv"),
                  encoding="utf-8", mode="r") as edit_file:
            rd = tuple(csv.reader(edit_file, quoting=csv.QUOTE_ALL))
            header = rd[0]
            tuple_column = ("Spell",)
            tuple_column = [index for index, item in enumerate(header) if item in tuple_column]
            dict_column = ("Property",)
            dict_column = [index for index, item in enumerate(header) if item in dict_column]
            for index, row in enumerate(rd[1:]):
                for n, i in enumerate(row):
                    row = stat_convert(row, n, i, tuple_column=tuple_column, dict_column=dict_column)
                self.weather_data[row[0]] = {header[index + 1]: stuff for index, stuff in enumerate(row[1:])}
        edit_file.close()

        weather_list = [item["Name"] for item in self.weather_data.values()]
        strength_list = ("Light ", "Normal ", "Strong ")
        self.weather_list = []
        for item in weather_list:  # list of weather with different strength
            for strength in strength_list:
                self.weather_list.append(strength + item)
        self.weather_list = tuple(self.weather_list)
        edit_file.close()

        self.weather_matter_images = {}
        for this_weather in weather_list:  # Load weather matter sprite image
            try:
                images = load_images(self.data_dir, screen_scale=self.screen_scale,
                                     subfolder=("map", "weather", "matter", fcv(this_weather, revert=True)))
                self.weather_matter_images[this_weather] = tuple(images.values())
            except FileNotFoundError:
                self.weather_matter_images[this_weather] = ()

        read_folder = Path(os.path.join(self.data_dir, "map", "preset"))
        sub1_directories = [x for x in read_folder.iterdir() if x.is_dir()]

        self.preset_map_folder = []  # folder for reading later
        self.preset_map_data = {}

        for file_chapter in sub1_directories:
            read_folder = Path(os.path.join(self.data_dir, "map", "preset", file_chapter))
            chapter_file_name = os.sep.join(os.path.normpath(file_chapter).split(os.sep)[-1:])
            sub2_directories = [x for x in read_folder.iterdir() if x.is_dir()]

            self.preset_map_data[chapter_file_name] = {}
            for file_map in sub2_directories:
                map_file_name = os.sep.join(os.path.normpath(file_map).split(os.sep)[-1:])
                self.preset_map_folder.append(map_file_name)
                self.preset_map_data[chapter_file_name][map_file_name] = {}

                read_folder = Path(os.path.join(self.data_dir, "map", "preset", file_chapter, file_map))
                sub3_directories = [x for x in read_folder.iterdir() if x.is_dir()]
                for file_stage in sub3_directories:
                    stage_file_name = fcv(os.sep.join(os.path.normpath(file_stage).split(os.sep)[-1:]))
                    self.preset_map_data[chapter_file_name][map_file_name][stage_file_name] = {}
                    if stage_file_name != "0":  # city scene use different reading
                        original_event_data, event_data = self.load_map_event_data(chapter_file_name, map_file_name,
                                                                                   stage_file_name.lower())
                        self.preset_map_data[chapter_file_name][map_file_name][stage_file_name] = \
                            {"data": self.load_map_object_data(chapter_file_name, map_file_name,
                                                               stage_file_name.lower()),
                             "character": self.load_map_unit_data(chapter_file_name, map_file_name,
                                                                  stage_file_name.lower()),
                             "event_data": original_event_data,
                             "event": event_data}

    def load_map_event_data(self, campaign_id, map_id, stage_id, scene_id=""):
        with open(os.path.join(self.data_dir, "map", "preset", campaign_id, map_id, stage_id, scene_id,
                               "event.csv"), encoding="utf-8", mode="r") as unit_file:
            rd = list(csv.reader(unit_file, quoting=csv.QUOTE_ALL))
            header = rd[0]
            str_column = ("Type",)
            str_column = [index for index, item in enumerate(header) if item in str_column]
            tuple_column = ("Trigger",)
            tuple_column = [index for index, item in enumerate(header) if item in tuple_column]
            dict_column = ("Property",)
            dict_column = [index for index, item in enumerate(header) if item in dict_column]
            for data_index, data in enumerate(rd[1:]):  # skip header
                for n, i in enumerate(data):
                    data = stat_convert(data, n, i, tuple_column=tuple_column, dict_column=dict_column,
                                        str_column=str_column)
                rd[data_index + 1] = {header[index]: stuff for index, stuff in enumerate(data)}
            event_data = rd[1:]
            # keep event data in trigger structure for easier check
            original_event_data = copy.deepcopy(event_data)
            if event_data:
                final_event_data = {"music": []}
                for item in event_data:
                    if item["ID"]:  # item with no parent ID mean it is child of previous found parent
                        next_level = final_event_data
                        for trigger in item["Trigger"]:
                            if trigger not in next_level:
                                next_level[trigger] = {}
                            next_level = next_level[trigger]
                        parent_id = item["ID"]
                        if parent_id not in next_level:
                            next_level[parent_id] = []
                    if item["Type"] == "music":  # add music to list for loading
                        final_event_data["music"].append(str(item["Object"]))
                    next_level[parent_id].append(item)
                unit_file.close()
                return original_event_data, final_event_data

            unit_file.close()
            return original_event_data, event_data

    def load_map_object_data(self, campaign_id, map_id, stage_id, scene_id=""):
        try:
            with open(os.path.join(self.data_dir, "map", "preset", campaign_id, map_id, stage_id, scene_id,
                                   "object_pos.csv"), encoding="utf-8", mode="r") as unit_file:
                rd = list(csv.reader(unit_file, quoting=csv.QUOTE_ALL))
                header = rd[0]
                dict_column = ("Property",)
                dict_column = [index for index, item in enumerate(header) if item in dict_column]
                for data_index, data in enumerate(rd[1:]):  # skip header
                    for n, i in enumerate(data):
                        data = stat_convert(data, n, i, dict_column=dict_column)
                    rd[data_index + 1] = {header[index]: stuff for index, stuff in enumerate(data)}
                char_data = rd[1:]
            unit_file.close()
            return char_data
        except FileNotFoundError as b:
            print("file not found", b)
            return {}

    def load_map_unit_data(self, campaign_id, map_id, stage_id, scene_id=""):
        try:
            with open(os.path.join(self.data_dir, "map", "preset", campaign_id, map_id, stage_id, scene_id,
                                   "character_pos.csv"), encoding="utf-8", mode="r") as unit_file:
                rd = list(csv.reader(unit_file, quoting=csv.QUOTE_ALL))
                header = rd[0]
                int_column = ("Team",)  # value int only
                list_column = ("POS",)  # value in list only
                float_column = ("Start Health", "Start Stamina")  # value in float
                dict_column = ("Stage Property",)
                int_column = [index for index, item in enumerate(header) if item in int_column]
                list_column = [index for index, item in enumerate(header) if item in list_column]
                float_column = [index for index, item in enumerate(header) if item in float_column]
                dict_column = [index for index, item in enumerate(header) if item in dict_column]

                for data_index, data in enumerate(rd[1:]):  # skip header
                    for n, i in enumerate(data):
                        data = stat_convert(data, n, i, list_column=list_column, int_column=int_column,
                                            float_column=float_column, dict_column=dict_column)
                    rd[data_index + 1] = {header[index]: stuff for index, stuff in enumerate(data)}
                char_data = rd[1:]
            unit_file.close()
            return char_data
        except FileNotFoundError as b:
            print("file not found", b)
            return {}

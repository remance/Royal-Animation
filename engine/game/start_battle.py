import gc
from datetime import datetime
from os.path import join as path_join
from random import choices

from pygame.mixer import music

gear_reward_quantity_list = (1, 2, 3, 4, 5)
gear_reward_quantity_score = (50, 30, 20, 7, 3)
gear_type_list = ("weapon 1", "weapon 2", "head", "chest", "arm", "leg", "accessory")


def start_battle(self, chapter, mission, stage):
    # self.error_log.write("\n Map: " + str(self.map_selected) + "\n")
    self.loading_screen("start")

    music.stop()
    # for _ in range(100):
    #     new_custom_equip = tuple(self.generate_custom_equipment((gear_type_list)[random.randint(0, 6)], "Standard").items())
    #     self.save_data.save_profile["character"][1]["storage"][new_custom_equip] = 1
    self.battle.prepare_new_stage(chapter, mission, stage)
    next_battle = self.battle.run_game()  # run next scene
    self.battle.exit_battle()  # run exit battle for previous one

    # music.play()
    gc.collect()  # collect no longer used object in previous battle from memory

    # Finish battle, check for next one
    self.battle.change_game_state("battle")  # reset battle game state when end

    save_profile = self.save_data.save_profile

    if next_battle is True and str(int(stage) + 1) not in self.preset_map_data[chapter][mission]:  # need to use is True
        # finish all scene in the mission, update save data of the game first before individual save
        if int(save_profile["game"]["chapter"]) < int(chapter):
            save_profile["game"]["chapter"] = chapter
            save_profile["game"]["mission"] = mission
        elif mission.isdigit() and int(save_profile["game"]["mission"]) < int(mission):
            save_profile["game"]["mission"] = mission

    self.save_data.make_save_file(path_join(self.main_dir, "save", "game.dat"),
                                  save_profile)

    self.battle.decision_select.selected = None  # reset decision here instead of in battle method
    if next_battle is True:  # finish scene, continue to next one
        if str(int(stage) + 1) in self.preset_map_data[chapter][mission]:  # has next scene
            self.start_battle(chapter, mission, str(int(stage) + 1))
        else:
            self.start_battle(self.battle.main_story_profile["chapter"],
                              self.battle.main_story_profile["mission"], "0")

    elif next_battle is not False:  # start specific mission need to contain number
        self.start_battle(chapter, next_battle, "1")

    # for when memory leak checking
    # logging.warning(mem_top())
    # print(len(vars(self)))
    # print(len(gc.get_objects()))
    # self.error_log.write(str(new_gc_collect).encode('unicode_escape').decode('unicode_escape'))

    # print(vars(self))
    # from engine.character.character import Character
    # type_count = {}
    # for item in gc.get_objects():
    #     if type(item) not in type_count:
    #         type_count[type(item)] = 1
    #     else:
    #         type_count[type(item)] += 1
    # type_count = sorted({key: value for key, value in type_count.items()}.items(), key=lambda item: item[1],
    #                     reverse=True)
    # print(type_count)
    # print(item.current_animation)
    #     print(vars(item))
    # asdasd
    # except NameError:
    #     asdasdasd
    # except:
    #     pass
    # print(gc.get_referrers(self.unit_animation_pool))

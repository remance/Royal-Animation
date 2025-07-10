from engine.utils.data_loading import prepare_animation_sprite


def load_battle_sprite_animation(self, character_list):
    for char_id in character_list:
        for part_type in self.part_sprite_adjust[char_id]:
            for part_name in self.part_sprite_adjust[char_id][part_type]:
                for key in self.part_sprite_adjust[char_id][part_type][part_name]:
                    if part_type == "effect":
                        animation_pool = self.effect_animation_pool
                        sprite_chapter = int(self.chapter)
                        default_pool = self.default_effect_animation_pool
                    else:
                        if self.char_sprite_chapter[char_id] not in self.body_sprite_pool:
                            self.body_sprite_pool[self.char_sprite_chapter[char_id]] = {}
                        if part_type not in self.body_sprite_pool[self.char_sprite_chapter[char_id]]:
                            self.body_sprite_pool[self.char_sprite_chapter[char_id]][part_type] = {}
                        animation_pool = self.body_sprite_pool[self.char_sprite_chapter[char_id]][part_type]
                        if part_name not in animation_pool:
                            animation_pool[part_name] = {}
                        if key not in animation_pool[part_name]:
                            animation_pool[part_name][key] = {}
                        animation_pool = animation_pool[part_name][key]
                        default_pool = self.default_body_sprite_pool
                        sprite_chapter = self.char_sprite_chapter[char_id]
                    prepare_animation_sprite(self.screen_scale, animation_pool, sprite_chapter, part_type, part_name,
                                             key,
                                             default_pool, self.part_sprite_adjust[char_id])

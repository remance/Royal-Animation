def check_prepare_action(self, value):
    """Assuming attack/special button related is always last button"""
    action = self.current_action

    if value["After Animation"]:
        action = action | {"next action": value["After Animation"] | {"no prepare": True, "sub action": True}}

    if value["Prepare Animation"]:  # has animation to do first before performing main animation
        return value["Prepare Animation"] | \
            {"sub action": True,
             "next action": value["Property"] | action | self.current_moveset["Property"] | {"no prepare": True}}
    return action  # not add property here, will be added later

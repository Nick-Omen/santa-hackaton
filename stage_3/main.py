import json
import math
import os
import random
import sys
from datetime import datetime

import requests
from PIL import Image, ImageDraw
import numpy as np

MAP_ID = "dd6ed651-8ed6-4aeb-bcbc-d8a51c8383cc"
TOKEN = "85972f67-7f9f-4f30-a319-119b91b3dca8"


def get_map():
    res = requests.get(f"https://datsanta.dats.team/json/map/{MAP_ID}.json", headers={"X-API-Key": TOKEN})
    return res.json()


def send_route(moves, stack_of_bags):
    res = requests.post(
        "https://datsanta.dats.team/api/round",
        data=json.dumps({
            "mapID": MAP_ID,
            "moves": moves,
            "stackOfBags": stack_of_bags,
        }),
        headers={"X-API-Key": TOKEN, "Content-Type": "application/json"},
    )
    file_name = datetime.now().strftime("%Y-%m-%d|%H:%M:%S")
    res_data = res.json()
    with open(f"./responses/{file_name}.json", "w+") as f:
        json.dump({"req": {
            "mapID": MAP_ID,
            "moves": moves,
            "stackOfBags": stack_of_bags,
        }, "res": res_data}, f, sort_keys=False, indent=2)
    return res_data


def save_initial_map():
    map_data = get_map()
    with open("./map.json", "w+") as f:
        def sort_children(current_child):
            return -math.dist((current_child["x"], current_child["y"]), (0, 0))

        map_data["children"] = sorted(map_data["children"], key=sort_children)
        gifts = map_data["gifts"]
        gifts_by_cat = {}
        for gift in gifts:
            if gift["type"] not in gifts_by_cat:
                gifts_by_cat[gift["type"]] = []
            gifts_by_cat[gift["type"]].append(gift)
        for key in gifts_by_cat:
            gifts_by_cat[key].sort(key=lambda x: x["price"])
        map_data["gifts"] = gifts_by_cat
        json.dump(map_data, f)


def read_initial_map():
    save_initial_map()
    return read_map("./map.json")


def read_map(file_path):
    with open(file_path, "r+") as f:
        return json.load(f)


def check_round_status(round_id):
    res = requests.get(
        f"https://datsanta.dats.team/api/round/{round_id}",
        headers={"X-API-Key": TOKEN},
    )
    with open(f"./responses/{round_id}.json", "w+") as f:
        json.dump(res.json(), f)
    return res.json()


def clear_cache():
    dirs = os.listdir("./map_states/")
    for file in dirs:
        if file.endswith(".gitkeep"):
            continue
        os.remove(f"./map_states/{file}")
    if os.path.exists("./map.json"):
        os.remove("./map.json")


def draw_map():
    image = Image.new("RGBA", (10000, 10000), color=(0, 0, 0, 0))
    draw = ImageDraw.Draw(image)

    initial_map = read_initial_map()
    draw.regular_polygon(
        (10, 10, 20),
        n_sides=4,
        fill=(0, 255, 0, 255),
    )

    for move in initial_map["children"]:
        draw.regular_polygon(
            (move["x"], move["y"], 10),
            n_sides=4,
            fill=(255, 0, 0, 255),
        )

    for area in initial_map["snowAreas"]:
        draw.regular_polygon(
            (area["x"], area["y"], area["r"]),
            n_sides=360,
            fill=(255, 255, 255, 30),
            outline=(255, 255, 255, 255),
        )
    image.save("./map.png")

# Обучающие игры [educational_games]
# Музыкальные игры [music_games]
# Игрушки в ванную [bath_toys]
# Велосипед [bike]
# Краски [paints]
# Шкатулка [casket]
# Футбольный мяч [soccer_ball]
# Игрушечная кухня [toy_kitchen]


PRESENT_CATEGORIES = {
    "male": {
        (0, 2): ["music_games", "bath_toys"],
        (2, 5): ["educational_games", "paints"],
        (5, 7): ["soccer_ball", "paints", "bike"],
        (7, 11): ["bike", "soccer_ball"],
    },
    "female": {
        (0, 2): ["music_games", "bath_toys"],
        (2, 5): ["educational_games", "paints"],
        (5, 7): ["toy_kitchen", "paints", "casket"],
        (7, 11): ["bike", "toy_kitchen", "casket"],
    }
}


# PRESENT_CATEGORIES = { # v1
#     "male": {
#         (0, 3): ["bath_toys", "educational_games"],
#         (3, 5): ["educational_games", "music_games"],
#         (5, 7): ["soccer_ball"],
#         (7, 11): ["bike"],
#     },
#     "female": {
#         (0, 3): ["bath_toys", "educational_games"],
#         (3, 5): ["educational_games", "music_games"],
#         (5, 7): ["paints", "casket"],
#         (7, 11): ["toy_kitchen", "casket"],
#     }
# }


def read_last_map_state():
    dirs = os.listdir("./map_states/")
    last_state = 0

    if not dirs:
        return read_initial_map(), last_state

    for file in dirs:
        try:
            state = int(file.split(".")[0])
            if state > last_state:
                last_state = state
        except ValueError:
            pass
    return read_map(f"./map_states/{last_state}.json"), last_state


def select_present(child, presents):
    cat = PRESENT_CATEGORIES[child["gender"]]

    for age_range, categories in cat.items():
        if age_range[0] <= child["age"] < age_range[1]:
            category = random.choice(categories)
            return presents[category].pop(round(len(presents[category]) // 3.8))


def calculate_route_iter(children, pool, pointer):
    max_weight = 0
    max_vol = 0
    route = []
    gifts = []

    if pointer >= 1000:
        return route, gifts

    child = children[pointer]
    present = pool[f"{child['x']}_{child['y']}"]

    while max_weight + present["weight"] <= 200 and max_vol + present["volume"] <= 100:
        max_weight += present["weight"]
        max_vol += present["volume"]
        route.append({"x": child["x"], "y": child["y"]})
        pointer += 1
        try:
            child = children[pointer]
            present = pool[f"{child['x']}_{child['y']}"]
        except IndexError:
            break

    max_x = max([r["x"] for r in route])
    coord = list(filter(lambda x: x["x"] == max_x, route))

    route = sorted(route, key=lambda c: math.dist((c["x"], c["y"]), (coord[0]["x"], coord[0]["y"])))

    for r in route:
        gifts.append(pool[f"{r['x']}_{r['y']}"]["id"])

    route.append({"x": 0, "y": 0})

    return route, gifts, pointer


def save_map_images(stack_of_moves, restricted_zones):
    image = Image.new("RGBA", (2500, 2500), color=(0, 0, 0, 0))
    draw = ImageDraw.Draw(image)

    for area in restricted_zones:
        draw.regular_polygon(
            (area["x"] // 4, area["y"] // 4, area["r"] // 4),
            n_sides=360,
            fill=(255, 255, 255, 100),
            outline=(255, 255, 255, 255),
        )

    for moves in stack_of_moves:
        for move in moves:
            if move["x"] == 0 and move["y"] == 0:
                continue
            draw.regular_polygon(
                (move["x"] // 4, move["y"] // 4, 4),
                n_sides=4,
                fill=(255, 0, 0, 255),
            )

    color = (255, 255, 255, 255)
    last_n = 0

    for n, moves in enumerate(stack_of_moves):
        new_image = image.copy()
        new_draw = ImageDraw.Draw(new_image)
        for i in range(len(moves) - 1, 0, -1):
            new_draw.line((
                moves[i]["x"] // 4,
                moves[i]["y"] // 4,
                moves[i-1]["x"] // 4,
                moves[i-1]["y"] // 4,
            ), fill=color)
            draw.regular_polygon(
                (moves[i]["x"] // 4, moves[i]["y"] // 4, 4),
                n_sides=4,
                fill=(0, 255, 0, 255),
            )
        draw.regular_polygon(
            (moves[0]["x"] // 4, moves[0]["y"] // 4, 4),
            n_sides=4,
            fill=(0, 255, 0, 255),
        )
        new_image.save(f"./images/map-{n}.png")
        last_n = n

    image.save(f"./images/map-{last_n}.png")


def main():
    clear_cache()
    map_data = read_initial_map()
    selected_presents = {}
    for child in map_data["children"]:
        selected_presents[f"{child['x']}_{child['y']}"] = select_present(child, map_data["gifts"])

    total_gifts_price = sum([selected_presents[key]["price"] for key in selected_presents])

    print(f"Total gifts price: {total_gifts_price}")
    if 49000 < total_gifts_price > 50000:
        return

    total_moves = 0
    total_presents = 0

    stack_of_bags = []
    moves = []

    count_steps = 0

    child_pointer = 0
    while child_pointer < 1000:
        route_moves, bag, child_pointer = calculate_route_iter(map_data["children"], selected_presents, child_pointer)
        total_moves += len(route_moves)
        total_presents += len(bag)
        count_steps += 1
        moves.append(route_moves)
        stack_of_bags.append(bag)

    stack_of_bags.reverse()
    print("total_moves:", total_moves)
    print("total_presents:", total_presents)
    print("count_steps:", count_steps, len(stack_of_bags))
    print(sum([len(move) for move in moves]))
    print(sum([len(bag) for bag in stack_of_bags]))

    # save_map_images(moves, map_data["snowAreas"])
    req_moves = []
    for move in moves:
        req_moves += move

    res = send_route(req_moves, stack_of_bags)
    print(res)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "check":
        check_round_status(sys.argv[2])
    else:
        main()

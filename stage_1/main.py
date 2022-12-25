import json
import os
import random
import sys
from datetime import datetime

import requests
from PIL import Image, ImageDraw
from shapely import Point, LineString

MAP_ID = "faf7ef78-41b3-4a36-8423-688a61929c08"
TOKEN = "85972f67-7f9f-4f30-a319-119b91b3dca8"


def get_map():
    res = requests.get(f"https://datsanta.dats.team/json/map/{MAP_ID}.json", headers={"X-API-Key": TOKEN})
    return res.json()


def save_initial_map():
    map_data = get_map()
    with open("./map.json", "w+") as f:
        map_data["gifts"] = sorted(map_data["gifts"], key=lambda v: v["volume"] + v["weight"])
        map_data["children"] = sorted(map_data["children"], key=lambda v: (v["y"] + v["x"]))
        json.dump(map_data, f)


def read_initial_map():
    if not os.path.exists("./map.json"):
        save_initial_map()
    return read_map("./map.json")


def read_map(file_path):
    with open(file_path, "r+") as f:
        return json.load(f)


def send_route(data):
    res = requests.post(
        "https://datsanta.dats.team/api/round",
        data=json.dumps(data),
        headers={"X-API-Key": TOKEN, "Content-Type": "application/json"},
    )
    file_name = datetime.now().strftime("%Y-%m-%d|%H:%M:%S")
    res_data = res.json()
    with open(f"./responses/{file_name}.json", "w+") as f:
        json.dump({"req": data, "res": res_data}, f)
    return res_data


def check_round_status(round_id):
    res = requests.get(
        f"https://datsanta.dats.team/api/round/{round_id}",
        headers={"X-API-Key": TOKEN},
    )
    with open(f"./responses/{round_id}.json", "w+") as f:
        json.dump(res.json(), f)
    return res.json()


def collect_bags(map_data):
    taken_gifts = []
    total_weight = 0
    total_volume = 0

    if len(map_data["gifts"]) == 0:
        return []

    """
    Starts with last items from array, because they are the biggest.
    """
    current_item = map_data["gifts"][len(map_data["gifts"]) - 1]
    while total_weight + current_item["weight"] <= 200 and total_volume + current_item["volume"] <= 100:
        item = map_data["gifts"].pop()
        taken_gifts.append(item)
        total_volume += item["volume"]
        total_weight += item["weight"]
        if len(map_data["gifts"]) == 0:
            return taken_gifts
        current_item = map_data["gifts"][len(map_data["gifts"]) - 1]

    if len(map_data["gifts"]) == 0:
        return taken_gifts

    current_item = map_data["gifts"][0]
    while total_weight + current_item["weight"] <= 200 and total_volume + current_item["volume"] <= 100:
        item = map_data["gifts"].pop(0)
        taken_gifts.append(item)
        total_volume += item["volume"]
        total_weight += item["weight"]
        if len(map_data["gifts"]) == 0:
            return taken_gifts
        current_item = map_data["gifts"][0]

    return taken_gifts


def get_children(map_data, count):
    children = []
    for _ in range(count):
        children.append(map_data["children"].pop(0))
    return sorted(children, key=lambda v: (v["x"], -v["y"]))


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


def save_map_state(state, map_data):
    assert len(map_data["gifts"]) == len(map_data["children"]), map_data
    with open(f"./map_states/{state}.json", "w+") as f:
        json.dump(map_data, f)


def clear_cache():
    dirs = os.listdir("./map_states/")
    for file in dirs:
        if file.endswith(".gitkeep"):
            continue
        os.remove(f"./map_states/{file}")
    if os.path.exists("./map.json"):
        os.remove("./map.json")


def get_iteration_state(restricted_zones):
    map_data, state = read_last_map_state()
    bags = collect_bags(map_data)
    children = get_children(map_data, len(bags))
    children.append({"x": 0, "y": 0})

    save_map_state(state + 1, map_data)
    return list(reversed(bags)), children


def get_restricted_zones():
    map_data = read_initial_map()
    restricted_zones = []
    for area in map_data["snowAreas"]:
        restricted_zones.append(area)
    return restricted_zones


def save_map_images(stack_of_moves, restricted_zones):
    image = Image.new("RGBA", (10000, 10000), color=(0, 0, 0, 0))
    draw = ImageDraw.Draw(image)

    for area in restricted_zones:
        draw.regular_polygon(
            (area["x"], area["y"], area["r"]),
            n_sides=360,
            fill=(255, 255, 255, 100),
            outline=(255, 255, 255, 255),
        )

    for moves in stack_of_moves:
        for move in moves:
            if move["x"] == 0 and move["y"] == 0:
                continue
            draw.regular_polygon(
                (move["x"], move["y"], 10),
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
                moves[i]["x"],
                moves[i]["y"],
                moves[i-1]["x"],
                moves[i-1]["y"],
            ), fill=color)
            draw.regular_polygon(
                (moves[i]["x"], moves[i]["y"], 10),
                n_sides=4,
                fill=(0, 255, 0, 255),
            )
        draw.regular_polygon(
            (moves[0]["x"], moves[0]["y"], 10),
            n_sides=4,
            fill=(0, 255, 0, 255),
        )
        new_image.save(f"./images/map-{n}.png")
        last_n = n

    image.save(f"./images/map-{last_n}.png")


def main(with_output=False):
    clear_cache()
    stacks_of_bags = []
    stack_of_moves = []

    restricted_zones = get_restricted_zones()
    bags, iter_moves = get_iteration_state(restricted_zones)

    while len(bags) > 0 and len(iter_moves) > 0:
        stacks_of_bags.insert(0, [bag["id"] for bag in bags])
        stack_of_moves.append(iter_moves)

        bags, iter_moves = get_iteration_state(restricted_zones)

    if with_output:
        save_map_images(stack_of_moves, restricted_zones)

    total_moves = []
    for moves in stack_of_moves:
        total_moves += moves

    res = send_route({
        "mapID": MAP_ID,
        "stackOfBags": stacks_of_bags,
        "moves": total_moves,
    })

    if res["success"] is True:
        print(f"Success: {res['roundId']}")
    else:
        print(f"Failed: {res}")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "check":
        check_round_status(sys.argv[2])
    else:
        is_output = False
        try:
            is_output = sys.argv[1] == "output"
        except IndexError:
            pass
        finally:
            main(with_output=is_output)

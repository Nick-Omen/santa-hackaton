import json
import os
import sys
from shapely.geometry import LineString, Point
from datetime import datetime

import requests

MAP_ID = "faf7ef78-41b3-4a36-8423-688a61929c08"
TOKEN = "85972f67-7f9f-4f30-a319-119b91b3dca8"


def get_map():
    res = requests.get(f"https://datsanta.dats.team/json/map/{MAP_ID}.json", headers={"X-API-Key": TOKEN})
    return res.json()


def save_initial_map():
    map_data = get_map()
    with open("./map.json", "w+") as f:
        map_data["gifts"] = sorted(map_data["gifts"], key=lambda v: v["volume"] + v["weight"])
        map_data["children"] = sorted(map_data["children"], key=lambda v: (v["y"], v["x"]))
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
    while total_weight + current_item["weight"] < 200 and total_volume + current_item["volume"] < 100:
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
        os.remove(f"./map_states/{file}")
    os.remove(f"./map.json")


def avoid_intersection(restricted_zones, line, step, current_position, steps):
    print('====================================================')
    print("current_position: ", current_position)
    print("next_step: ", step)
    intersected_zones = []
    for zone, point in restricted_zones:
        if zone.intersects(line):
            intersected_zones.append((zone, point))

    for zone, point in intersected_zones:
        intersection = zone.intersection(line)
        print("intersection: ", point)
        print(intersection.coords)

    """
    Кароч тут надо как-то обойти ебучую зону пересечения вьюги
    """

    print('====================================================')


def new_moves_without_intersections(restricted_zones, steps):
    new_steps = []
    current_coords = {"x": 0, "y": 0}

    for step in steps:
        line = LineString([
            Point(current_coords["x"], current_coords["y"]),
            Point(step["x"], step["y"]),
        ])
        if any((line.intersects(zone) for zone, point in restricted_zones)):
            avoid_intersection(restricted_zones, line, step, current_coords, steps)
        else:
            new_steps.append(step)
        current_coords = step
    return new_steps


def get_iteration_state(restricted_zones):
    map_data, state = read_last_map_state()
    bags = collect_bags(map_data)
    children = get_children(map_data, len(bags))
    children.append({"x": 0, "y": 0})
    moves = new_moves_without_intersections(restricted_zones, children)

    save_map_state(state + 1, map_data)
    return bags, moves


def get_restricted_zones():
    map_data = read_initial_map()
    restricted_zones = []
    for area in map_data["snowAreas"]:
        restricted_zones.append((Point(area["x"], area["y"]).buffer(area["r"]), area))
    return restricted_zones


def main():
    clear_cache()
    stacks_of_bags = []
    stack_of_moves = []

    restricted_zones = get_restricted_zones()
    bags, iter_moves = get_iteration_state(restricted_zones)

    while len(bags) > 0 and len(iter_moves) > 0:
        stacks_of_bags.append([bag["id"] for bag in bags])
        stack_of_moves.append(iter_moves)

        bags, iter_moves = get_iteration_state(restricted_zones)

    total_moves = []
    for moves in stack_of_moves:
        total_moves += moves

    print("len(total_moves)", len(total_moves))

    return

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
        main()

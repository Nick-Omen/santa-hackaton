import json
import os
import random
import sys
from datetime import datetime

import requests


MAP_ID = "a8e01288-28f8-45ee-9db4-f74fc4ff02c8"
TOKEN = "85972f67-7f9f-4f30-a319-119b91b3dca8"


def get_map():
    res = requests.get(f"https://datsanta.dats.team/json/map/{MAP_ID}.json", headers={"X-API-Key": TOKEN})
    return res.json()


def send_gifts(data, categories):
    res = requests.post(
        "https://datsanta.dats.team/api/round2",
        data=json.dumps({
            "mapID": MAP_ID,
            "presentingGifts": data,
        }),
        headers={"X-API-Key": TOKEN, "Content-Type": "application/json"},
    )
    file_name = datetime.now().strftime("%Y-%m-%d|%H:%M:%S")
    res_data = res.json()
    with open(f"./responses/{file_name}.json", "w+") as f:
        json.dump({"req": data, "res": res_data, "cats": categories}, f, sort_keys=False, indent=2)
    return res_data


def save_initial_map():
    map_data = get_map()
    with open("./map.json", "w+") as f:
        json.dump(map_data, f)


def read_initial_map():
    if not os.path.exists("./map.json"):
        save_initial_map()
    return read_map("./map.json")


def read_map(file_path):
    with open(file_path, "r+") as f:
        return json.load(f)


def check_round_status(round_id):
    res = requests.get(
        f"https://datsanta.dats.team/api/round2/{round_id}",
        headers={"X-API-Key": TOKEN},
    )
    with open(f"./responses/{round_id}.json", "w+") as f:
        json.dump(res.json(), f)
    return res.json()


def clear_cache():
    if os.path.exists("./map.json"):
        os.remove("./map.json")


def get_children():
    random.shuffle(read_initial_map()["children"])
    return read_initial_map()["children"]


def get_presents_by_category():
    categorized_presents = {}
    for present in sorted(read_initial_map()["gifts"], key=lambda x: x["price"]):
        if present["type"] not in categorized_presents:
            categorized_presents[present["type"]] = []
        categorized_presents[present["type"]].append(present)
    return categorized_presents

# Конструкторы [constructors]
# Куклы [dolls]
# Радиоуправляемые игрушки [radio_controlled_toys]
# Игрушечный транспорт [toy_vehicles]
# Настольные игры [board_games]
# Подвижные игры [outdoor_games]
# Игровая площадка [playground]
# Мягкие игрушки [soft_toys]
# Компьютерные игры [computer_games]
# Сладости [sweets]
# Книги [books]
# Домашнее животное [pet]
# Одежда (сумочки, заколки, платья, рюкзаки) [clothes]


CATEGORIES = {
    "male": {
        0: "clothes",
        1: "soft_toys",
        2: "sweets",
        3: "playground",
        4: "constructors",
        5: "pet",
        6: "toy_vehicles",
        7: "outdoor_games",
        8: "board_games",
        9: "radio_controlled_toys",
        10: "computer_games",
    },
    "female": {
        0: "clothes",
        1: "soft_toys",
        2: "sweets",
        3: "playground",
        4: "clothes",
        5: "pet",
        6: "dolls",
        7: "outdoor_games",
        8: "board_games",
        9: "books",
        10: "computer_games",
    }
}

AVERAGE_BUDGET = {
    "total": 0,
    "avg": 100,
}

TOTAL_CHILDREN = {i: 0 for i in range(0, 11)}

TOTAL_CHILDREN["male"] = {i: 0 for i in range(0, 11)}
TOTAL_CHILDREN["female"] = {i: 0 for i in range(0, 11)}


def select_present(child, presents):
    cat = CATEGORIES[child["gender"]][child["age"]]

    if child["age"] < 2:
        return presents[cat].pop(0)

    if child["age"] < 3:
        return presents[cat].pop(round(len(presents[cat]) // 2))


    return presents[cat].pop()
            # if child["age"] < 2:
            #     return presents[categories[0]].pop()
            # if child["age"] < 5:
            #     return presents[categories[0]].pop(len(presents[categories[0]]) // 3)
            # if child["age"] < 8:
            #     return presents[categories[0]].pop(len(presents[categories[0]]) // 2)
            # return presents[categories[0]].pop()


def get_gift_for_child(child, presents):
    present = select_present(child, presents)
    AVERAGE_BUDGET["total"] += present["price"]
    TOTAL_CHILDREN[child["age"]] += 1
    TOTAL_CHILDREN[child["gender"]][child["age"]] += present["price"]
    return {
        "giftID": present["id"],
        "childID": child["id"],
    }


def main():
    clear_cache()
    presents = get_presents_by_category()

    presenting_gifts = []

    for child in get_children():
        presenting_gifts.append(get_gift_for_child(child, presents))

    print(f"Total budget: {AVERAGE_BUDGET['total']}")
    print(f"Average budget: {AVERAGE_BUDGET['total'] / len(get_children())}")
    print(TOTAL_CHILDREN)

    if 99000 <= AVERAGE_BUDGET["total"] <= 100000:
        res = send_gifts(presenting_gifts, CATEGORIES)
        print(res)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "check":
        check_round_status(sys.argv[2])
    else:
        main()

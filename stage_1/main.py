import json
from dataclasses import dataclass
from pprint import pprint

import requests

MAP_ID = "faf7ef78-41b3-4a36-8423-688a61929c08"
TOKEN = "85972f67-7f9f-4f30-a319-119b91b3dca8"


class Bag:
    id: int
    volume: int
    weight: int


class Move:
    id: int
    volume: int
    weight: int


@dataclass
class RouteData:
    mapID: str
    stackOfBags: list[Bag]
    moves: list[Move]


def get_map():
    res = requests.get(f"https://datsanta.dats.team/json/map/{MAP_ID}.json", headers={"X-API-Key": TOKEN})
    return res.json()


def save_map():
    map_data = get_map()
    with open("./map.json", "w+") as f:
        json.dump(map_data, f, indent=4)


def create_router(data: RouteData):
    res = requests.post(
        "https://datsanta.dats.team/api/round",
        json.dumps(data.__dict__),
        headers={"X-API-Key": TOKEN},
    )
    print(res.json())


if __name__ == "__main__":
    save_map()

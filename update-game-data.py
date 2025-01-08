#!/usr/bin/env python3

import httpx
import json
import natsort
import re
import sys
import typing


def main():
    client = httpx.Client(http2=True, timeout=60, follow_redirects=True)
    print('Loading item list from TeamCraft...', file=sys.stderr)
    item_list: dict[str, dict[str, str]] = client.get('https://raw.githubusercontent.com/ffxiv-teamcraft/ffxiv-teamcraft/master/libs/data/src/lib/json/items.json').raise_for_status().json()
    print('Processing item mappings...', file=sys.stderr)
    mappings = dict[str, set[int]]()
    is_number = re.compile('[0-9]+$')
    for item_id, names in dict[str, dict[str, str]].items(item_list):
        if not is_number.match(item_id):
            raise ValueError(f'Invalid item ID: {item_id}')
        for name in dict[str, str].values(names):
            if len(name) == 0:
                continue
            if name in mappings:
                mappings[name].add(int(item_id))
            else:
                mappings[name] = {int(item_id)}
    print('Storing item mappings to item-mappings.json...', file=sys.stderr)
    with open('item-mappings.json', 'w', encoding='utf-8') as f:
        f.write('{')
        for i, (name, ids) in enumerate(natsort.natsorted(mappings.items())):
            f.write('\n  ' if i == 0 else ',\n  ')
            json.dump(name, f, ensure_ascii=False)
            f.write(': ')
            json.dump(sorted(ids), f)
        f.write('\n}\n')
    print('Loading market list from Universalis...', file=sys.stderr)
    dc_list: list[dict[str, str | list[int]]] = client.get('https://universalis.app/api/v2/data-centers').raise_for_status().json()
    world_list: list[dict[str, int | str]] = client.get('https://universalis.app/api/v2/worlds').raise_for_status().json()
    markets = dict[str, str]()
    for i in dc_list:
        markets[typing.cast(str, i['name'])] = 'dc'
        markets[typing.cast(str, i['region'])] = 'region'
    for i in world_list:
        markets[typing.cast(str, i['name'])] = 'world'
    print('Storing market list to market-list.json...', file=sys.stderr)
    with open('market-list.json', 'w', encoding='utf-8') as f:
        json.dump(markets, f, ensure_ascii=False, indent=2, sort_keys=True)
        f.write('\n')


if __name__ == '__main__':
    main()

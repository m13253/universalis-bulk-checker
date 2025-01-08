#!/usr/bin/env python3

import csv
import enum
import httpx
import itertools
import json
import sys
import typing
import urllib.parse


class Item:

    def __init__(self, item_id: int, name: str, hq: bool, want_quantity: int, market: str) -> None:
        self.item_id = item_id
        self.name = name
        self.hq = hq
        self.want_quantity = want_quantity
        self.market = market
        self.result_available = False
        self.actual_quantity: int | None = None
        self.price_each: float | None = None
        self.sells_per_day: float | None = None

    @property
    def name_with_hq(self) -> str:
        return self.name + '[HQ]' if self.hq else self.name

    @property
    def universalis_url(self) -> str:
        return 'https://universalis.app/market/' + str(self.item_id)


class RequestType(enum.Enum):
    Sell = 0
    BuyNQ = 1
    BuyHQ = 2

    def __lt__(self, other: 'RequestType') -> bool:
        return self.value < other.value


class RequestQueue:

    def __init__(self, market_types: dict[str, str]) -> None:
        self.market_types = market_types
        self.queue = dict[tuple[str, RequestType], list[Item]]()

    def add(self, item: Item) -> None:
        key = (item.market, (RequestType.BuyHQ if item.hq else RequestType.BuyNQ) if item.want_quantity > 0 else RequestType.Sell)
        if key in self.queue:
            self.queue[key].append(item)
        else:
            self.queue[key] = [item]

    def resolve(self, progress_callback: typing.Callable[[int], None]) -> None:
        client = httpx.Client(http2=True, timeout=60, follow_redirects=True)
        count = 0
        progress_callback(count)
        for key in sorted(self.queue.keys()):
            (market, request_type), items = key, self.queue[key]
            market = urllib.parse.quote(market, '')
            item_handles = dict[int, list[Item]]()
            for i in items:
                if i.item_id in item_handles:
                    item_handles[i.item_id].append(i)
                else:
                    item_handles[i.item_id] = [i]
            item_ids = sorted(item_handles.keys())
            for item_ids_group in itertools.batched(item_ids, 100):
                item_ids_joined = urllib.parse.quote(','.join(map(str, item_ids_group)), '')
                prices = dict[str, list[dict[str, int | dict[str, dict[str, dict[str, int | float]]]]]]
                listing: dict[str, list[dict[str, int]] | float]
                listings: dict[str, dict[str, dict[str, list[dict[str, int]] | float]]]
                match request_type:
                    case RequestType.Sell:
                        prices = client.get(f'https://universalis.app/api/v2/aggregated/{market}/{item_ids_joined}').raise_for_status().json()
                        for price in prices['results']:
                            for item in item_handles[price['itemId']]:
                                self._write_selling_price(item, price)
                                count += 1
                    case RequestType.BuyNQ:
                        if len(item_ids_group) == 1:
                            listing = client.get(f'https://universalis.app/api/v2/{market}/{item_ids_joined}?fields=listings.quantity,listings.total,listings.tax,nqSaleVelocity').raise_for_status().json()
                            for item in item_handles[item_ids_group[0]]:
                                self._write_buying_price(item, listing)
                                count += 1
                        else:
                            listings = client.get(f'https://universalis.app/api/v2/{market}/{item_ids_joined}?fields=items.listings.quantity,items.listings.total,items.listings.tax,items.nqSaleVelocity').raise_for_status().json()
                            for item_id, listing in listings['items'].items():
                                for item in item_handles[int(item_id)]:
                                    self._write_buying_price(item, listing)
                                    count += 1
                    case RequestType.BuyHQ:
                        if len(item_ids_group) == 1:
                            listing = client.get(f'https://universalis.app/api/v2/{market}/{item_ids_joined}?hq=1&fields=listings.quantity,listings.total,listings.tax,hqSaleVelocity').raise_for_status().json()
                            for item in item_handles[item_ids_group[0]]:
                                self._write_buying_price(item, listing)
                                count += 1
                        else:
                            listings = client.get(f'https://universalis.app/api/v2/{market}/{item_ids_joined}?hq=1&fields=items.listings.quantity,items.listings.total,items.listings.tax,items.hqSaleVelocity').raise_for_status().json()
                            for item_id, listing in listings['items'].items():
                                for item in item_handles[int(item_id)]:
                                    self._write_buying_price(item, listing)
                                    count += 1
                progress_callback(count)

    @staticmethod
    def _write_buying_price(item: Item, listing: dict[str, list[dict[str, int]] | float] | None) -> None:
        item.result_available = True
        if listing is None:
            return
        actual_quantity, total_price = 0, 0
        for i in typing.cast(list[dict[str, int]], listing['listings']):
            if actual_quantity >= item.want_quantity:
                break
            actual_quantity += i['quantity']
            total_price += i['total'] + i['tax']
        if actual_quantity != 0:
            item.actual_quantity = actual_quantity
            item.price_each = (total_price * 20) / (actual_quantity * 21)  # Remove 5% tax
        item.sells_per_day = typing.cast(float, listing.get('hqSaleVelocity') if item.hq else listing.get('nqSaleVelocity'))

    def _write_selling_price(self, item: Item, price: dict[str, int | dict[str, dict[str, dict[str, int | float]]]]) -> None:
        item.result_available = True
        item.actual_quantity = item.want_quantity
        quality = 'hq' if item.hq else 'nq'
        try:
            item.price_each = -typing.cast(dict[str, dict[str, dict[str, dict[str, int]]]], price)[quality]['minListing'][self.market_types[item.market]]['price']
        except KeyError:
            pass
        try:
            item.sells_per_day = typing.cast(dict[str, dict[str, dict[str, dict[str, int]]]], price)[quality]['dailySaleVelocity'][self.market_types[item.market]]['quantity']
        except KeyError:
            pass


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print(f'Usage: {argv[0]} input.csv', file=sys.stderr)
        return 1
    try:
        with open('item-mappings.json', 'r', encoding='utf-8-sig') as f:
            mappings: dict[str, list[int]] = json.load(f)
    except FileNotFoundError:
        print('Error: Cannot load item-mappings.json, run update-game-data.py first.', file=sys.stderr)
        return 1
    try:
        with open('market-list.json', 'r', encoding='utf-8-sig') as f:
            market_types: dict[str, str] = json.load(f)
            market_canonicalize = {str.casefold(i): i for i in market_types.keys()}
    except FileNotFoundError:
        print('Error: Cannot load market-list.json, run update-game-data.py first.', file=sys.stderr)
        return 1

    items = list[Item]()
    queue = RequestQueue(market_types)

    for filename in argv[1:]:
        with open(filename, 'r', encoding='utf-8-sig') as f:
            csv_reader = csv.reader(f)
            for line_num, line in enumerate(csv_reader):
                name, quantity_str, market = (line + ['', '', ''])[:3]
                if len(name) == 0:
                    continue
                if name.endswith('[HQ]'):
                    hq = True
                    name = name[:-4]
                elif name.endswith('\ue03c'):
                    hq = True
                    name = name[:-1]
                else:
                    hq = False
                if name not in mappings:
                    print(f'Line {line_num + 1}: Unknown item {name}. Item names are case sensitive', file=sys.stderr)
                    return 1
                try:
                    quantity = int(quantity_str)
                except ValueError:
                    print(f'Line {line_num + 1}: The item quantity {quantity_str} is not an integer', file=sys.stderr)
                    return 1
                try:
                    market = market_canonicalize[market.casefold()]
                except KeyError:
                    print(f'Line {line_num + 1}: Market name {market} is neither a world name, a DC name, nor a region name', file=sys.stderr)
                    return 1
                for item_id in mappings[name]:
                    item = Item(item_id, name, hq, quantity, market)
                    items.append(item)
                    queue.add(item)

    queue.resolve(lambda count: print(f'Loading prices [{count}/{len(items)}]...', file=sys.stderr))

    if not sys.stdout.isatty:
        sys.stdout.write('\ufeff')
    csv_writer = csv.writer(sys.stdout)
    csv_writer.writerow(['Item', 'Want Quantity', 'Market', 'Price Each (w/o tax)', 'Actual Quantity', 'Sells per Day', 'Universalis URL'])
    for item in items:
        csv_writer.writerow([item.name_with_hq, item.want_quantity, item.market, '' if item.price_each is None else f'{item.price_each:.2f}', '' if item.actual_quantity is None else item.actual_quantity, '' if item.sells_per_day is None else f'{item.sells_per_day:.2f}', item.universalis_url])
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))

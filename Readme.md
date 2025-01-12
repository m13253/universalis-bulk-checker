# Universalis-bulk-checker

Check prices from Universalis for bulk material purchases

---

As an FFXIV player living in a datacenter crowded with raiders, (Yes, I mean Mana.) you start to consider making gil by gathering / crafting raid consumables. You know that one culinarian can only feed 11 full parties, so prices of consumables are always supply-driven in Mana.

But you start to get puzzled: Should I use HQ materials to shorten crafting time, or NQ materials to cut cost? Should I use the CP Potion to increase HQ rate, or the Spiritbond Potion to earn some extra gil?

Although you use Teamcraft Profit Calculator to find the world-hop prices for materials, but the “lowest price” shown is not suitable for mass-production: After the cheapest is bought out, the lowest price will become different. You want a software that can estimate your gil spending for mass purchases.

You want a tool that can act fast: If on a reset day, the consumables are sold out so fast, causing the HQ materials to raise price, you can switch to NQ materials immediately in your next craft batch.

That’s why Universalis-bulk-checker is invented. You provide a list of materials (with their corresponding quantities) to purchase and sell. It gives you a list of prices so you can insert into a worksheet to figure out today’s ideal synthesis plan.

## Usage

1. Prepare a Python environment.

   Universalis-bulk-checker is developed using Python 3.13. While lower versions may work, it’s recommended to use at least 3.13 to avoid troubles.

   Use `pip3 install -U -r requirements.txt` to install the dependency libraries.

2. Update the game data (each time a new patch releases).

   Use `python3 ./update-game-data.py` to fetch the latest market and item data.

   The results will be stored in `item-mappings.json` and `market-list.json` files.

   You only need to do this once after each patch release.

3. Prepare your input CSV.

   Here is an example:
   ```csv
   トラルコーンオイル,198,Mana
   トラルコーンオイル[HQ],198,Mana
   ムケッカ[HQ],-297,Titan
   ```

   You must spell the item names and `[HQ]` marks exactly, with correct capitalization (EN/DE/FR) or Kana forms (JP). You can use your favorite spreadsheet software to prepare such CSV file, but remember to save in UTF-8 encoding.

   This example means you want to query the price for buying 198× トラルコーンオイル (NQ or HQ), and 198× トラルコーンオイル[HQ] from the lowest offerings in Mana markets, and selling 297× ムケッカ[HQ] at the lowest price of Titan.

   Please check [`example-input-Moqueca.csv`](example-input-Moqueca.csv) for a fully working demo.

4. Run the program.

   ```bash
   python3 ./check-prices.py example-input-Moqueca.csv > price-report.csv
   ```

   The algorithm works like this: In your specified market, the program considers buying from the listing one by one, until you have enough quantity. It does not consider buying in an optimal order to reduce overpurchase, (which is a bin pack problem,) because overpurchase is not an issue if mass-producing.

   If your quantity is negative, the program assumes you are selling, and will simply query the lowest price of the specified market. For selling mode only, Universalis may provide a slightly outdated price from its cache to save their server resources.

   Any tax is used in the calculation but removed prior to output. This way, rounding errors introduced in the tax calculation can be minimized to at most once.

5. Collect the price report.

   Open `price-report.csv` with your favorite spreadsheet software. (MS Excel, Apple Numbers, Google Sheets, LibreOffice Calc, etc.)

   In addition to the prices, the “Actual Quantity” column indicates how many items you will be overpurchasing (by subtracting “Want Quantity”). The “Sells per Day” column shows an estimate using data from past 4 days (sell mode) or 7 days (purchase mode).

6. Finish your worksheet.

   You will have to do this step yourself. Luckily, the provided [`example-worksheet-Moqueca.ods`](example-worksheet-Moqueca.ods) can be used as a starting point.

   Copy the contents of `price-report.csv` to the top part of `example-worksheet-Moqueca.ods`, so the bottom part will automatically update.

   To customize the bottom part, you will need to measure how fast you can gather / craft each item with your current gear. You might need to use [Raphael FFXIV Crafting Solver](https://www.raphael-xiv.com) to find your best meal and potion for crafting.

7. Profit!

   Pick your desired gathering / crafting plan and start to make gil!

8. Extend your business!

   What if you are tired of crafting Moqueca and want to try other [meals](https://ffxiv.consolegameswiki.com/wiki/Meals) and [potions](https://ffxiv.consolegameswiki.com/wiki/Medicines)? Or if your datacenter isn’t populated with raiders so you want to craft housing items instead?

   Use your imagination and wish you fortune and luck!

## Notice

This program is written with minimal error checks. Therefore, if you misspell an item name, I don’t know what error it will spit out.

If you get an error, check your input CSV carefully, then submit a bug report. I will try to help but no guarantees.

## License

This software is released under the MIT license.

If you can code, please take my code and make it better! For example, give it a graphical interface or turn it into a Web app so no installation is required — as long as you follow the copyright requirements listed in the [LICENSE](LICENSE) file.

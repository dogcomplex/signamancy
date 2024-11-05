
import json
from collections import defaultdict
import random
import argparse

# Brief synopsis of the game rules
game_rules = """
This is a crafting-based game where players start with a basic inventory and can use various recipes to create new items. 
The goal is to earn enough money to pay increasing rent each week.

- Each recipe transforms specific inventory items into other items.
- Some recipes are probability-based, while others consume all of an item (denoted by 'X').
- Special mechanic: When a 🌞 is produced, it can be immediately applied to any and all recipes requiring a 🌞 in a single batch.

Players save their game state to a file, which includes the current inventory and all build recipes. They can then upload this file in subsequent sessions to continue their game.
"""

def parse_all_recipes(file_name='recipes.csv'):
    parsed_recipes = {}
    with open(file_name, 'r', encoding='utf-8') as file:
        for line in file:
            if ',' in line:
                recipe_id, input_output = line.strip().split(',')
                if '=>' in input_output:
                    inputs, outputs = input_output.split('=>')
                    input_items, output_items = parse_recipe_parts(inputs, outputs)
                    parsed_recipes[recipe_id] = {'inputs': input_items, 'outputs': output_items}
    return parsed_recipes

def parse_recipe_parts(inputs, outputs):
    inputs = inputs.strip().split(' ')
    outputs = outputs.strip().split(' ')

    input_items = defaultdict(int)
    output_items = defaultdict(list)

    try:
        for item in inputs:
            if 'X' in item:
                item = item.replace('X', '')
                input_items[item] = 'X'
            elif item[-1].isdigit():
                quantity = int(''.join(filter(str.isdigit, item)))
                item = item.rstrip('0123456789.')
                if item in input_items:
                    input_items[item] += quantity
                else:
                    input_items[item] = quantity
            else:
                if item in input_items:
                    input_items[item] += 1
                else:
                    input_items[item] = 0

        for item in outputs:
            if '%' in item:
                item, probability = item.split('%')
                if probability == '':
                    probability = 1/len([item for item in outputs if '%' in item])
                else:
                    probability = float(probability) / 100
                output_items[item] = ('prob', probability)
            elif '-' in item:
                #format stringnum-num
                left, range_max = item.split('-')
                range_min = float(''.join(filter(str.isdigit, left)))
                # rstrip float:
                item = left.rstrip('0123456789.')
                output_items[item] = ('range', range_min, range_max)
            else:
                if item[-1].isdigit():
                    quantity = float(''.join(filter(str.isdigit, item)))
                    item = item.rstrip('0123456789.')
                else:
                    quantity = 1
                output_items[item] = ('fixed', quantity)
    except Exception as e:
        print("Error parsing recipe.")
        print(f"Inputs: {inputs} | Outputs: {outputs} | Error: {e}")
        return None, None

    return input_items, output_items

def is_recipe_valid(inventory, input_items):
    for item, quantity in input_items.items():
        if quantity != 'X' and (item not in inventory or inventory[item] < quantity):
            return False
    return True

def apply_recipe(inventory, input_items, output_items):
    for item, quantity in input_items.items():
        if quantity == 'X' or item not in inventory:
            inventory[item] = 0
        else:
            inventory[item] -= quantity

    for item, quantity in output_items.items():
        if item not in inventory:
            inventory[item] = 0
        if quantity[0] == 'prob':
            if random.random() <= quantity[1]:
                inventory[item] += 1
        elif quantity[0] == 'range':
            inventory[item] += random.randint(quantity[1], quantity[2])
        elif quantity[0] == 'fixed':
            inventory[item] += quantity[1]

    return inventory

def filter_sun_based_recipes(parsed_recipes):
    sun_based_recipes = []
    for recipe_id, recipe in parsed_recipes.items():
        if '🌞' in recipe['inputs']:
            sun_based_recipes.append(recipe_id)
    return sun_based_recipes

def apply_sun_recipes_once(inventory, parsed_recipes):
    for recipe_id in filter_sun_based_recipes(parsed_recipes):
        input_items = parsed_recipes[recipe_id]['inputs']
        output_items = parsed_recipes[recipe_id]['outputs']
        if is_recipe_valid(inventory, input_items):
            inventory = apply_recipe(inventory, input_items, output_items)
    return inventory

def get_high_value_item_recipes(all_recipes):
    # High-value items identified from the recipe list
    high_value_items = ['🍯', '🥃🥕', '🥃🦈', '🔥🦈', '🥃🤍', '🔲🥇']  # Add more as needed
    return [recipe for recipe in all_recipes if any(item in recipe for item in high_value_items)]

def get_tool_upgrade_recipes(all_recipes):
    # Tool upgrades
    tool_upgrades = ['🪓🥉', '⛏🥈', '♠🥇', '🚿🥈', '🎣🥈']  # Add more as needed
    return [recipe for recipe in all_recipes if any(upgrade in recipe for upgrade in tool_upgrades)]

def get_potential_sale_value(item):
    # Define sale values for items - this should be comprehensive and based on the game's economy
    sale_values = {
        '🍯': 30, '🥃🥕': 40, '🥃🦈': 100, '🔥🦈': 150, # and so on for other items
    }
    return sale_values.get(item, 0)

def assess_recipe_value(recipe, inventory):
    # Calculate the potential value of a recipe based on output items and sale values
    _, _, output_items = parse_recipe_advanced(recipe)
    total_value = 0
    for item, possibilities in output_items.items():
        for possibility in possibilities:
            if possibility[0] == 'fixed':
                total_value += get_potential_sale_value(item) * possibility[1]
            # Add more logic for 'prob' and 'range' if needed
    return total_value

def get_dynamic_high_value_item_recipes(all_recipes, inventory):
    # Rank recipes by their potential value
    recipe_values = [(recipe, assess_recipe_value(recipe, inventory)) for recipe in all_recipes]
    # Sort recipes by their value in descending order
    high_value_recipes = sorted(recipe_values, key=lambda x: x[1], reverse=True)
    return [recipe for recipe, value in high_value_recipes if value > 0]

def get_dynamic_tool_upgrade_recipes(all_recipes, inventory):
    # Example tool upgrade logic - this could be refined based on the game's mechanics
    tool_upgrades = ['🪓', '⛏', '♠', '🚿', '🎣']
    return [recipe for recipe in all_recipes if any(upgrade in recipe for upgrade in tool_upgrades and is_recipe_valid(inventory, recipe))]

def strategic_choose_next(inventory, parsed_recipes, sun_queue):
    # Strategy for choosing the next recipe
    # Prioritize tool upgrades
    tool_upgrade_recipes = [recipe_id for recipe_id, recipe in parsed_recipes.items() if 'upgrade' in recipe_id]
    for recipe_id in tool_upgrade_recipes:
        if is_recipe_valid(inventory, parsed_recipes[recipe_id]['inputs']):
            return recipe_id

    # Prioritize high-value items
    high_value_item_recipes = [recipe_id for recipe_id, recipe in parsed_recipes.items() if 'high_value' in recipe_id]
    for recipe_id in high_value_item_recipes:
        if is_recipe_valid(inventory, parsed_recipes[recipe_id]['inputs']):
            return recipe_id

    # Fallback to any valid recipe
    for recipe_id in parsed_recipes:
        if is_recipe_valid(inventory, parsed_recipes[recipe_id]['inputs']):
            return recipe_id

    return "No valid recipe found"

def choose_recipe(recipe_id, inventory, parsed_recipes, sun_queue):
    if recipe_id not in parsed_recipes:
        return "Recipe not found."

    input_items = parsed_recipes[recipe_id]['inputs']
    output_items = parsed_recipes[recipe_id]['outputs']

    if '🌞' in input_items:
        sun_queue.append(recipe_id)
        return "Recipe added to the sun queue."

    if is_recipe_valid(inventory, input_items):
        inventory = apply_recipe(inventory, input_items, output_items)
        if '🌞' in output_items:
            inventory = apply_sun_recipes_once(inventory, parsed_recipes)
            return "Recipe applied successfully. 🌞 produced and applied."
        return "Recipe applied successfully."
    else:
        return "Recipe is not valid with the current inventory."

def apply_sun_queue(inventory, sun_queue, parsed_recipes):
    while sun_queue:
        recipe_id = sun_queue.pop(0)
        input_items = parsed_recipes[recipe_id]['inputs']
        output_items = parsed_recipes[recipe_id]['outputs']
        if is_recipe_valid(inventory, input_items):
            inventory = apply_recipe(inventory, input_items, output_items)
    return inventory

def load_recipes_from_file(file_name='recipes.csv'):
    with open(file_name, 'r', encoding='utf-8') as file:
        return [line.strip() for line in file]

def save_game_state_to_file(game_state, file_name='game_state.json'):
    with open(file_name, 'w', encoding='utf-8') as file:
        json.dump(game_state, file, indent=4)

def load_game_state_from_file(file_name='game_state.json'):
    try:
        with open(file_name, 'r', encoding='utf-8') as file:
            return json.load(file)
    except FileNotFoundError:
        print("No game state file found. Starting a new game.")
        return {"inventory": defaultdict(int, {'💫': 1}), "sun_queue": [], "recipes": load_recipes_from_file()}

def pretty_print_inventory(inventory):
    print("Current Inventory:")
    for item, quantity in inventory.items():
        print(f"{item}: {quantity}")

def pretty_print_recipes(recipes):
    print("Available Recipes:")
    for recipe in recipes:
        print("{recipe}:\n {inputs} => {outputs}".format(
            recipe=recipe,
            inputs=[f"{item}{quantity}" for item, quantity in recipes[recipe]['inputs'].items()],
            outputs=[f"{item}{quantity}" for item, quantity in recipes[recipe]['outputs'].items()]
        ))

def main():
    parser = argparse.ArgumentParser(description='Command-line tool for crafting game')
    parser.add_argument('command', help='The command to execute (choose_recipe, reset, print_inventory, list_recipes)')
    parser.add_argument('recipe_id', nargs='?', help='ID of the recipe to choose', default=None)
    args = parser.parse_args()

    game_state = load_game_state_from_file()
    inventory = game_state.get('inventory', defaultdict(int, {'💫': 1}))
    sun_queue = game_state.get('sun_queue', [])
    parsed_recipes = parse_all_recipes()

    if args.command == 'choose_recipe':
        choice = args.recipe_id if args.recipe_id else ''
        result = choose_recipe(choice, inventory, parsed_recipes, sun_queue)
        print(result)
    elif args.command == 'reset':
        inventory = defaultdict(int, {'💫': 1})
        sun_queue = []
        parsed_recipes = parse_all_recipes()  # Reload recipes on reset
        print("Game reset.")
    elif args.command == 'print_inventory':
        pretty_print_inventory(inventory)
    elif args.command == 'list_recipes':
        pretty_print_recipes(parsed_recipes)
    elif args.command == 'print_sun_queue':
        print(sun_queue)
    elif args.command == 'help':
        print(game_rules)
    else:
        print("Invalid command.")

    save_game_state_to_file({"inventory": inventory, "sun_queue": sun_queue, "recipes": parsed_recipes})

if __name__ == '__main__':
    main()
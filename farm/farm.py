import csv
import re
import random
import torch
from torch import sparse
import time

# Initialize CUDA if available
# torch.set_default_tensor_type(torch.FloatTensor)
try:
  torch.cuda.init()
except:
  print("CUDA not available")
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

def parse_quantity(quantity_str):
    if quantity_str == '':
        return 1
    elif quantity_str == 'X':
        return 'ALL'
    elif quantity_str.startswith('%'):
        return ('PROB', float(quantity_str[1:])/100)
    elif '-' in quantity_str:
        start, end = map(float, quantity_str.split('-'))
        return ('RANGE', (start, end))
    else:
        return float(quantity_str)

def process_recipe_file(file_path):
    ingredient_dict = {}
    recipes = {}
    latest_index = 0

    with open(file_path, newline='', encoding='utf-8') as csvfile:
        reader = csv.reader(csvfile)
        for row in reader:
            try:
                recipe_name, formula = row
                input_ingredients, output_ingredients = formula.split('=>')
                input_ingredients = input_ingredients.strip().split()
                output_ingredients = output_ingredients.strip().split()

                input_ingredients_dict = {}
                output_ingredients_dict = {}

                for ing in input_ingredients:
                    # split into the leading id and the quantity
                    # quantity is either a number, 'X' (all), a range (e.g. 1-2), or a probability (e.g. %50)
                    #print('REGEX', re.findall(r'(.*?)([\dX\-\%\.]*$)', ing), ing, input_ingredients)
                    ingredient_id, quantity = re.findall(r'(.*?)([\dX\-\%\.]*$)', ing)[0]
                    ingredient_id = ingredient_id.strip()
                    if ingredient_id not in ingredient_dict:
                        ingredient_dict[ingredient_id] = latest_index
                        latest_index += 1
                    input_ingredients_dict[ingredient_id] = parse_quantity(quantity)

                for ing in output_ingredients:
                    ingredient_id, quantity = re.findall(r'(.*?)([\dX\-\%\.]*$)', ing)[0]
                    ingredient_id = ingredient_id.strip()
                    if ingredient_id not in ingredient_dict:
                        ingredient_dict[ingredient_id] = latest_index
                        latest_index += 1
                    output_ingredients_dict[ingredient_id] = parse_quantity(quantity)

                recipes[recipe_name] = {'requires': input_ingredients_dict, 'produces': output_ingredients_dict}
            except ValueError:
                if row != []:
                    print(f"Skipping invalid row: {row}")

    return ingredient_dict, recipes


def encode_inventory(ingredients):
    tensor = torch.zeros(num_ingredients, device=device)
    for ing, qty in ingredients.items():
        tensor[ingredient_dict[ing]] = qty
    return tensor

def encode_recipe(requires, produces):
    min_in = torch.zeros(num_ingredients, device=device)
    max_in = torch.zeros(num_ingredients, device=device)
    min_out = torch.zeros(num_ingredients, device=device)
    max_out = torch.zeros(num_ingredients, device=device)
    requires_all_in = torch.zeros(num_ingredients, device=device)
    chances_out = torch.zeros(num_ingredients, device=device)

    for ing, qty in requires.items():
        if qty == 'ALL':
            requires_all_in[ingredient_dict[ing]] = 1
        elif isinstance(qty, tuple) and qty[0] == 'RANGE':
            min_in[ingredient_dict[ing]], max_in[ingredient_dict[ing]] = qty[1]
        else:
            min_in[ingredient_dict[ing]] = max_in[ingredient_dict[ing]] = qty

    for ing, qty in produces.items():
        if isinstance(qty, tuple) and qty[0] == 'PROB':
            chances_out[ingredient_dict[ing]] = qty[1]
        elif isinstance(qty, tuple) and qty[0] == 'RANGE':
            min_out[ingredient_dict[ing]], max_out[ingredient_dict[ing]] = qty[1]
        else:
            min_out[ingredient_dict[ing]] = max_out[ingredient_dict[ing]] = qty

    return min_in, max_in, min_out, max_out, requires_all_in, chances_out

def process_batch_recipes(inventories_in, recipe_in):
    # inventories_in is batch_size x num_ingredients
    # recipe_in is 6 x num_ingredients
    batch_size = inventories_in.shape[0]
    num_ingredients = inventories_in.shape[1]

    # Unpack batch recipe info (assuming these are now sparse 3D tensors)
    min_in, max_in, min_out, max_out, requires_all_in, chances_out = recipe_in
    # each of these is 1 x num_ingredients

    # Replicate chances_out for each recipe in the batch
    # TODO replace these with batch of different recipes
    chances_out_batch = chances_out.repeat(batch_size, 1)
    requires_all_batch = requires_all_in.repeat(batch_size, 1)
    # Generate random values for required ingredients where ranges exist
    random_in = torch.rand(batch_size, num_ingredients, device=device)
    random_out = torch.rand(batch_size, num_ingredients, device=device)

    # Generate random values for required ingredients where ranges exist
    # range_in should be batch_size x num_ingredients
    range_in = min_in + (max_in - min_in) * random_in
    #print('RANGE IN:  ', len(range_in), '\n', range_in)
    # final_in should be batch_size x num_ingredients
    # set it to equal inventory if requires_all_in is 1, otherwise set it to range_in, for each inventory in the batch
    final_in = torch.where(requires_all_batch == 1, inventories_in, range_in)

    #print('Final req: ', final_in)

    # Check if each recipe in the batch can be processed
    success = torch.all((inventories_in >= final_in) | (requires_all_in.to_dense() == 1), dim=1)

    # FILTER STEP HERE?

    # Generate random value between min_out and max_out for each recipe ingredient in each batch
    range_out = min_out + (max_out - min_out) * random_out
    #print('RANGE OUT:  ', len(range_out), '\n', range_out)

    # Parallelized handling of 'chances_out' probabilities
    # selected IF random value is between the cumulative probability and the next cumulative probability
    cum_prob = torch.cumsum(chances_out_batch.to_dense(), dim=1)
    #print('CUMULATIVE PROB:  ', len(cum_prob), '\n', cum_prob)
    random_vals = torch.rand(batch_size, 1)
    #print('RANDOM VALUES:  ', len(random_vals), '\n', random_vals)
    comparisons = (cum_prob > random_vals).int()
    #print('COMPARISONS:  ', len(comparisons), '\n', comparisons)
    lucky_choice = torch.argmax(comparisons, dim=1)
    #print('LUCKY CHOICE:  ', len(lucky_choice), '\n', lucky_choice)
    lucky_out = torch.zeros(batch_size, num_ingredients, device=device)
    # set the selected ingredient to 1 if selected != 0 index (not found)
    lucky_out[torch.arange(batch_size), lucky_choice] = 1
    # mask out the first column (argmax defaults index 0 if nothing is found)
    # NOTE this will create a bug if the first ingredient is the one selected legitimately
    # solve this by making ingredient index 0 a dummy ingredient never/rarely used for this purpose
    lucky_out[:, 0] = 0
    #print('LUCKY OUT:  ', len(lucky_out), '\n', lucky_out)

    # Make changes:
    inventories_out = inventories_in.clone()
    inventories_out[success] += (range_out + lucky_out - final_in)[success]
    print('SUCCESS: ', len(success), '\n', success)

    return inventories_out, success


#MAIN:
if __name__ == '__main__':

  # Create a mock ingredient dictionary (assuming a small set for testing)
  ingredient_dict, recipes = process_recipe_file('recipes_py.csv')
  mock_ingredients = {"flour": 0, "sugar": 1, "eggs": 2, "milk": 3, "butter": 4, "cake": 5, "carrots": 6, "carrot_cake": 7}
  mock_recipes = {
    "cake": {
        'requires': {'flour': 'ALL', 'sugar': 1, 'eggs': ('RANGE', (1, 2)), 'milk': 1, 'butter': 1}, 
        'produces': {'cake': ('RANGE', (1, 2))}
    },
    "carrot_cake": {
        'requires': {'flour': 'ALL', 'sugar': ('RANGE', (1, 2)), 'eggs': ('RANGE', (1, 2)), 'milk': 1, 'butter': 1, 'carrots': ('RANGE', (0, 2))}, 
        'produces': {'cake': ('PROB', 0.3), 'carrot_cake': ('PROB', 0.3), 'carrots': ('RANGE', (1, 2))}
    }
  }
  num_ingredients = len(ingredient_dict)

  print('INGREDIENTS_PARSED: \n', ingredient_dict)
  #print('RECIPES_PARSED: \n', recipes)

  # Mock batch inventory tensor
  #mock_recipe = encode_recipe(mock_recipes['carrot_cake']['requires'], mock_recipes['carrot_cake']['produces'])
  inventories_in = torch.rand((1000000, num_ingredients), device=device) * 10  # Random quantities
  #mock_recipe_in = torch.stack([mock_recipe[0], mock_recipe[1], mock_recipe[2], mock_recipe[3], mock_recipe[4], mock_recipe[5]], dim=0)

  encoded_recipes = {}
  for recipe_name, recipe in recipes.items():
    encoded_recipes[recipe_name] = encode_recipe(recipe['requires'], recipe['produces'])

  test_recipe_index = 0
  test_recipe_key = list(encoded_recipes.keys())[test_recipe_index]
  test_recipe = list(encoded_recipes.values())[test_recipe_index]
  
  start_time = time.time()

  print('INVENTORIES: \n', inventories_in)
  print('RECIPE: (in_min, in_max, out_min, out_max, in_all, out_rand):  \n', test_recipe_key, test_recipe)

   

  # Process the batch of recipes
  inventories_out, success = process_batch_recipes(inventories_in, test_recipe)

  end_time = time.time()

  # 100M inventories takes like a minute on CPU
  print(f"Processing time: {end_time - start_time} seconds")
  print('PROCESSED INVENTORIES: \n', inventories_out)


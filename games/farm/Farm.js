/* eslint-disable */
import React, { useId } from 'react';
// import logo from './logo.svg';
// import './App.css';
import recipesCsv from './recipes.csv'
import * as d3 from 'd3'



function uniqBy(a, key) {
    var seen = {};
    return a.filter(function(item) {
        var k = key(item);
        return seen.hasOwnProperty(k) ? false : (seen[k] = true);
    })
}

function filterZeros(o) {
    return Object.keys(o).filter((k) => o[k] > 0).reduce((r, k) => (r[k] = o[k], r), {});
}


// MAIN
const inventory = {
    '💫': 1 // Start
}
const recipes = {
    ID_Start: '💫 => 💫'
}
const emoji_indexed_recipes = {
    '💫': {inputs: [], outputs: []}
}
const recipe_history = []
const growing_inventory = {}
const root_node = 'ID_Start'
const target_end = 'ID_Rent1'
const target_reward = 2000
const failure_penalty = 1000
const iterations = 10000
let success = false

let all_nodes = {}
let duplicate_nodes = 0

/*
Roll Sell options once per day
    - for each sell recipe, roll
Roll Buy options once per day + 1-10 quantity

special case for 🌞
    - for each recipe that has all other things, add 1 🌞 per day
    - means we gotta keep a tally... unless time is weird this way and actually does it automatically...
special rule for %.01
special rule for % 
special rule for X
special case for payday and feat day 2 and 7


PROBLEMS:
buy/sell doesn't quite work with fresh rerolls.  needs cached per day? (i.e. solved by making 🛒 like 🌞)
everything else can be rerolled on click
feats increasing shop stock don't add (can only hard replace) - means we have no + mechanism
- duplicate feats shouldnt be possible

*/

/*
parse_ingredients: takes a recipe string and returns the parsed (and randomly-rolled) ingredients list
Inputs: recipe (string), inventory (string => float)
*/
const parse_ingredients = (ingredients, inventory) => {
    let roll = Math.random() * 100
    const changes = {}
    const ingredients2 = ingredients.trim().split(' ')
    const ingredients_with_chance = ingredients2.filter((ingredient) => ingredient.includes('%')).length
    ingredients2.forEach((ingredient) => {
        let [in2, chance] = ingredient.trim().split('%')
        // cast chance to decimal
        if (ingredient.trim().indexOf('%') === -1)
            chance = 100
        else
            chance = chance ? parseFloat(chance) : 100.0/ingredients_with_chance
        
        let quantity = 1
        let emoji
        //const emojiRegex = new RegExp(/[\u{1f300}-\u{1f5ff}\u{1f900}-\u{1f9ff}\u{1f600}-\u{1f64f}\u{1f680}-\u{1f6ff}\u{2600}-\u{26ff}\u{2700}-\u{27bf}\u{1f1e6}-\u{1f1ff}\u{1f191}-\u{1f251}\u{1f004}\u{1f0cf}\u{1f170}-\u{1f171}\u{1f17e}-\u{1f17f}\u{1f18e}\u{3030}\u{2b50}\u{2b55}\u{2934}-\u{2935}\u{2b05}-\u{2b07}\u{2b1b}-\u{2b1c}\u{3297}\u{3299}\u{303d}\u{00a9}\u{00ae}\u{2122}\u{23f3}\u{24c2}\u{23e9}-\u{23ef}\u{25b6}\u{23f8}-\u{23fa}]/ug)
        const regex =  /^((\u00a9|\u00ae|[\u2000-\u3300]|\ud83c[\ud000-\udfff]|\ud83d[\ud000-\udfff]|\ud83e[\ud000-\udfff]|⛰️|🙆‍♂️|0️⃣|1️⃣|2️⃣|3️⃣|4️⃣|5️⃣|6️⃣|7️⃣|8️⃣|9️⃣|🔟)+)([\.\dX\-\σ]*)$/
        // console.log(in2, emoji, quantity, chance, roll, in2.match(regex))
        if (!regex.test(in2)) {
            console.log(ingredients, in2, emoji, quantity, chance, roll, in2.match(regex))
            throw 'Parse error'
        }
        const match = in2.match(regex).filter((x) => x.trim())
        emoji = match[1]
        if (match[3] === 'X') // X = ALL AVAILABLE
            quantity = inventory[emoji] || 0
        else if (match[3] && (match[3].indexOf('-') > -1 || match[3].indexOf('σ') > -1)) { // MIN-MAX
            let min, max, mean, sd, stats;
            if (match[3] && match[3].split('-').length === 3) {  // MIN-MEANσSD-MAX
                [min, stats, max] = match[3].split('-');               
                [mean, sd] = stats.split('σ').map((x) => parseFloat(x.trim()));
            } else if (match[3] && match[3].split('-').length === 2) { // MIN-MAX
                [min, max] = match[3].split('-')
                mean = (parseFloat(min) + parseFloat(max)) / 2
            } else { // MEANσSD
                [mean, sd] = stats.split('σ').map((x) => parseFloat(x.trim()))
            }
            min = min || 0
            
            // console.log(parseFloat(min), parseFloat(max), match[3], match[3].split('-'))

            // GENERATE RANDOMLY
            if (max === undefined && sd !== undefined)
                quantity = Math.max(min, d3.randomNormal(mean, sd)())
            else if (max !== undefined && sd !== undefined)
                quantity = Math.min(Math.max(min, d3.randomNormal(mean, sd)()), max)
            else if (max === undefined && sd === undefined) {
                console.log(in2, emoji, quantity, chance, roll, in2.match(regex))
                throw 'Parse error'
            } else
                quantity = Math.floor(Math.random() * (parseFloat(max) - parseFloat(min) + 1)) + parseFloat(min)

        } else if (match[3]) // NORMAL RAW QUANTITY
            quantity = parseFloat(match[3])
        // ELSE QUANTITY = 1
         
        if (!emoji) {
            console.log(in2, emoji, quantity, chance, roll, in2.match(regex))
            throw 'Parse error'
        }
        if (inventory[emoji] === undefined)
            inventory[emoji] = 0
        if (chance === 100 || roll < chance && roll > 0)
            changes[emoji] = quantity
        else
            changes[emoji] = 0
        if (chance < 100)
            roll -= chance
                
    })
    return changes
}



/*
parse_recipe: takes a recipe string and returns an object with inputs and outputs
Inputs: recipe (string), inventory (string => float)
*/
const parse_recipe = (recipe, inventory) => {
    const [inputs, outputs] = recipe.trim().split('=>')
    const parsed = {
        inputs: parse_ingredients(inputs, inventory),
        outputs: parse_ingredients(outputs, inventory)
    }
    return parsed
}

/*
has_ingredients: takes a recipe object and returns true if the inventory has all the ingredients
Inputs: ingredients (string => float), inventory (string => float)
*/
const has_ingredients = (ingredients, inventory) => {
    for (const ingredient in ingredients) {
        if (ingredient !== '🌞' && inventory[ingredient] < ingredients[ingredient])
            return false
    }
    return true
}

/*
parse_recipes: takes a csv string and returns an object with all the recipes
Inputs: csv (string), recipes (string => string), emoji_indexed_recipes [string => [{recipe}]], inventory (string => float)
*/


const parse_recipes = async (csv, recipes, emoji_indexed_recipes, inventory) => {
    await d3.csv(csv, undefined, (row) => {
        if (row.ID === '') // skip empty lines
            return
        const result = parse_recipe(row.Recipe, inventory)
        recipes[row.ID] = row.Recipe.trim()
        //if (row.ID === 'ID_Shop_Stock')
        //    console.log(row, result)
        Object.keys(result.inputs).forEach((ingredient) => {
            if (!emoji_indexed_recipes[ingredient])
                emoji_indexed_recipes[ingredient] = {inputs:[], outputs:[]}
            emoji_indexed_recipes[ingredient].inputs.push({
                ID: row.ID,
                Recipe: row.Recipe.trim(),
            })
        })
        Object.keys(result.outputs).forEach((ingredient) => {
            if (!emoji_indexed_recipes[ingredient])
                emoji_indexed_recipes[ingredient] = {inputs:[], outputs:[]}
            emoji_indexed_recipes[ingredient].outputs.push({
                ID: row.ID,
                Recipe: row.Recipe.trim(),
            })
        })
    });
}


/*
transact_recipe: takes a recipe object and returns true if the inventory has all the ingredients
Inputs: id (string), recipe (string), inventory (string => float), growing_inventory {string => float}, recipe_history [string => {parsed_recipe}]
*/
const transact_recipe = (id, recipe, inventory, growing_inventory, recipe_history) => {
    const result = parse_recipe(recipe, inventory)
    // console.log(result, has_ingredients(result.inputs, inventory))
    if (!has_ingredients(result.inputs, inventory))
        return false
    if (recipe_history)
        recipe_history.push({ ID: id, Recipe: recipe, Parsed: result })

    const grow_recipe = (Object.keys(result.inputs).filter((ingredient) => ingredient === '🌞').length > 0)
    for (const ingredient in result.inputs) {
        // sun recipes need time to grow
        if (grow_recipe) {
            Object.keys(result.outputs).forEach((ingredient) => {
                if (!growing_inventory[ingredient])
                    growing_inventory[ingredient] = 0
                growing_inventory[ingredient] += result.outputs[ingredient]
            })
        }
        if (ingredient !== '🌞')
            inventory[ingredient] -= result.inputs[ingredient]
    }
    if (Object.keys(result.outputs).filter((ingredient) => ingredient === '🌞').length > 0) // generated sun!
        grow_recipes(growing_inventory, inventory)
    
    if (!grow_recipe)
        for (const ingredient in result.outputs)
            inventory[ingredient] += result.outputs[ingredient]
    
    return true
}

/*
grow_recipes: takes a recipe object and returns true if the inventory has all the ingredients
Inputs: growing_inventory {string => float}, inventory (string => float)
*/
const grow_recipes = (growing_inventory, inventory) => {
    if (Object.keys(growing_inventory).length === 0)
        return false
    Object.keys(growing_inventory).forEach((ingredient) => {
        inventory[ingredient] += growing_inventory[ingredient]
    })
    growing_inventory = {}
    return true
}

const initialize = async (recipes, emoji_indexed_recipes, inventory) => {
    await parse_recipes(recipesCsv, recipes, emoji_indexed_recipes, inventory)
}

const naive_loop = async () => {    
    // INIT
    await initialize()

    console.log(Object.keys(inventory).length, inventory)
    console.log(Object.keys(recipes).length, recipes)
    console.log(Object.keys(emoji_indexed_recipes).length, emoji_indexed_recipes)
    console.log(recipe_history.length, recipe_history)

    let changes = true
    let choices = []
    let count = 0
    const max = 100
    while(changes) {
        changes = false
        choices = {}
        Object.keys(inventory).forEach((ingredient) => {
            if (inventory[ingredient] > 0 && emoji_indexed_recipes[ingredient]) {
                emoji_indexed_recipes[ingredient].inputs.forEach((recipe) => {
                    if (has_ingredients(parse_recipe(recipe.Recipe, inventory).inputs, inventory))
                        choices[recipe.ID] = recipe.Recipe // NOTE: will eventually fail if inputs are %
                })
            }
        })
        const num_choices = Object.keys(choices).length
        if (num_choices > 0) {
            // console.log(choices)
            const choice = Object.keys(choices)[Math.floor(Math.random() * num_choices)]
            changes = transact_recipe(choice, choices[choice], inventory, growing_inventory, recipe_history)
        }
        // console.log(Object.keys(inventory).length, inventory)
        if (count++ > max)
            break
    }
    
    console.log(recipes)
    console.log(inventory)
    console.log(recipe_history)
    console.log(growing_inventory)
}

class State {
    constructor(inventory, growing_inventory, target_recipe) {
        this.inventory = inventory
        this.growing_inventory = growing_inventory
    }

    uid() {
        let uid = Object.keys(this.inventory)
        .filter((ingredient) => this.inventory[ingredient] !== undefined && this.inventory[ingredient] > 0)
        .map((ingredient) => ingredient + this.state.inventory[ingredient] + ' ')
        uid += ' growing: '
        uid += Object.keys(this.growing_inventory)
        .filter((ingredient) => this.growing_inventory[ingredient] !== undefined && this.growing_inventory[ingredient] > 0)
        .map((ingredient) => ingredient + this.growing_inventory[ingredient] + ' ')
        return uid
    }

    serialize() {
        return JSON.stringify([filterZeros(this.inventory), filterZeros(this.growing_inventory)])
    }

    static deserialize(serialized) {
        const [inventory, growing_inventory] = JSON.parse(serialized)
        return new State(inventory, growing_inventory)
    }
}

// MONTE CARLO TREE SEARCH
class Node {
    /*
    Each Node is the current Inventory + Growing Recipes
    Each Edge(Child) is a Recipe
    */
    constructor(state, parent = undefined) {
        this.state = {
            target_recipe: state.target_recipe ? state.target_recipe : undefined,
            inventory: state.inventory ? state.inventory : Object.assign({}, inventory),
            growing_inventory: state.growing_inventory ? state.growing_inventory : Object.assign({}, growing_inventory),
            recipe_history: state.recipe_history ? state.recipe_history : recipe_history.slice()
        };
        this.depth = parent === undefined ? 0 : parent.depth + 1;
        this.parent = parent;
        this.children = []
        this.visits = 0;
        this.rewards = 0;
        this.expanded = false;
        this.terminal = false;
    }

    uid(hash = true) {
        let uid  
        uid = this.expanded ? '' : 'X '
        uid += this.state.target_recipe.ID + ' ' + this.state.target_recipe.Recipe + ': '
        uid += Object.keys(this.state.inventory)
        .filter((ingredient) => this.state.inventory[ingredient] !== undefined && this.state.inventory[ingredient] > 0)
        .map((ingredient) => ingredient + this.state.inventory[ingredient] + ' ')
        uid += ' growing: '
        uid += Object.keys(this.state.growing_inventory)
        .filter((ingredient) => this.state.growing_inventory[ingredient] !== undefined && this.state.growing_inventory[ingredient] > 0)
        .map((ingredient) => ingredient + this.state.growing_inventory[ingredient] + ' ')

        // hash the uid
        if (hash) {
            uid = uid.split('').reduce((a,b)=>{a=((a<<5)-a)+b.charCodeAt(0);return a&a},0)
        }
        return uid
    }

    // DEPRECATED
    serialize() {
        const puid = this.parent ? this.parent.uid() : undefined
        let serialized = JSON.stringify([puid, this.depth, this.visits, this.rewards, this.expanded, this.terminal, this.children.map((child) => child.uid()),
            this.state.target_recipe,
            filterZeros(this.state.inventory),
            filterZeros(this.state.growing_inventory),
            this.state.recipe_history
        ])
        // console.log(serialized)
        return serialized
    }

    // DEPRECATED
    deserialize(serialized) {
        let [parent_uid, depth, visits, rewards, expanded, terminal, children, target_recipe, inventory, growing_inventory, recipe_history] = JSON.parse(serialized)
        this.depth = depth
        this.visits = visits
        this.rewards = rewards
        this.expanded = expanded
        this.terminal = terminal
        this.parent = parent_uid // UID
        this.children = children // UIDS
        this.state.target_recipe = target_recipe
        this.state.inventory = inventory
        this.state.growing_inventory = growing_inventory
        this.state.recipe_history = recipe_history
        return parent_uid
    }
  
    update(reward) {
      this.visits++;
      this.rewards += reward;
    }

    isTerminal() {
        // check if the state of the node is a terminal state
        // this will depend on the game you are implementing

        if (this.isWin())
            this.terminal = true
        if (this.expanded && this.children.length === 0)
            this.terminal = true
        return this.terminal
    }

    isWin() {
        if (this.state.inventory['✅2️⃣'] > 0)
            return true
        return false
    }
  
    // MONTE CARLO TREE SEARCH
    get UCB1() {
      if (this.visits === 0) return 0 // Number.MAX_SAFE_INTEGER;
      return (
        this.rewards / this.visits +
        Math.sqrt(2 * Math.log(this.parent.visits) / this.visits)
      );
    }

    select(best_fit = false) {
        // select the child node with the highest UCB1 value, tiebreaking randomly
        const sorted = this.children.sort((a, b) => {
            if (!best_fit && a.visits === 0 && b.visits !== 0) return -1 // TODO this -1 doesn't seem right uhhh
            if (!best_fit && a.visits !== 0 && b.visits === 0) return 1

            if (a.visits === 0 && b.visits === 0) return 0
            if (a.UCB1 > b.UCB1) return -1;
            if (a.UCB1 < b.UCB1) return 1;
            return 0;
        });
        // if (!best_fit)
        //   return this.children[Math.floor(Math.random() * this.children.length)]
        
        
        return this.children[0]
    }

    
    simulate() {
        // simulate the game from the current state and return the resulting reward
        
        /*
        const num_choices = this.children.length
        if (this.children.length > 0) {
            // console.log(choices)
            const choice = Object.keys(choices)[Math.floor(Math.random() * this.children.length)]
            changes = transact_recipe(choice, choices[choice], this.state.inventory, this.state.growing_inventory)
        }
        */
        const prev_gold = this.parent ? this.parent.state.inventory['💰'] || 0 : 0
        const old_uid = this.uid() // before simulator is rerun

        
        if (this.parent) {
            this.state.inventory = Object.assign({}, this.parent.state.inventory)
            this.state.growing_inventory = Object.assign({}, this.parent.state.growing_inventory)
            this.state.recipe_history = this.parent.state.recipe_history ? this.parent.state.recipe_history.slice() : []
        } else {
            this.state.inventory = Object.assign({}, inventory)
            this.state.growing_inventory = Object.assign({}, growing_inventory)
            this.state.recipe_history = []
        }

        const prev_inventory = Object.assign({}, this.state.inventory)
        const success = transact_recipe(this.state.target_recipe.ID, this.state.target_recipe.Recipe, this.state.inventory, this.state.growing_inventory, this.state.recipe_history)
        if (!success) {
            console.log(this.state.target_recipe, this.state, prev_gold, this, pretty_print_inventory(prev_inventory))
            throw 'Weird, that should have worked'
        } 
                
        const new_gold = this.state.inventory['💰'] || 0
        const gold_change = new_gold - prev_gold
        //if (gold_change !== 0)
        //    console.log(prev_gold, new_gold, gold_change, this.state.target_recipe.ID, this.state.target_recipe.Recipe)
        
        return gold_change // + Math.log(this.depth) // TODO NOOOOOO fucking idea why rewards are getting flipped negative
    }


    expand() {
        // expand the node by adding a new child representing a new state in the game
        // this will depend on the game you are implementing
        // you may need to generate all possible child nodes and add them to the children array


        this.children = []

        // GET EDGES
        const valid_child_recipes =
            Object.keys(this.state.inventory)
            .filter((ingredient) => this.state.inventory[ingredient] > 0  && emoji_indexed_recipes[ingredient] !== undefined)
            .map((ingredient) => emoji_indexed_recipes[ingredient].inputs)
            .map((recipes_list) => recipes_list.filter((recipe) => has_ingredients(parse_recipe(recipe.Recipe, this.state.inventory).inputs, this.state.inventory)))
            .filter((recipes_list) => recipes_list.length > 0)
        const unique_valid_child_recipes = uniqBy(valid_child_recipes.flat(), (item) => item.ID)
        // console.log(this.state, valid_child_recipes, unique_valid_child_recipes)

        if (this.children.length === 0) {
            unique_valid_child_recipes.forEach((recipe) => {
                // console.log(ingredient, emoji_indexed_recipes[ingredient].inputs)
                
                //if (recipe.ID === 'ID_Shop_Stock')
                    //console.log(2222, recipe.ID, recipe)
                const child = new Node({
                    target_recipe: recipe
                }, this)

                this.children.push(child)
            })
        } else {
            throw 'No longer possible?'
            unique_valid_child_recipes.forEach((recipe) => {
                const child = this.children.find((child) => child.state.target_recipe.ID === recipe.ID)
                if (!child) {
                    const new_child = new Node({
                        target_recipe: recipe,
                        inventory: Object.assign({}, this.state.inventory), 
                        growing_inventory: Object.assign({}, this.state.growing_inventory),
                        recipe_history:  this.state.recipe_history ? this.state.recipe_history.slice() : [],
                    }, this)
                    this.children.push(new_child)
                } else {
                    // console.log('DUPLICATE CHILD NDOE: ', child, recipe)
                }
            })
        }

        if (this.children.length !== unique_valid_child_recipes.length) {
            console.log(this, valid_child_recipes, unique_valid_child_recipes)
            throw 'Weird, we should have the same number of children as unique recipes'
        }
        // console.log(this, valid_child_recipes, unique_valid_child_recipes)
        this.expanded = true
        return this
    }

    backpropagate(reward) {
        // update the node's statistics with the given reward
        this.update(reward);
        // propagate the update to the parent node
        if (this.parent) {
            this.parent.backpropagate(reward);
        }
    }

    save() {
        const uid = this.uid()
        if (all_nodes[uid]) {
            if (this.parent)
                this.parent.children = this.parent.children.filter((child) => child.uid() !== uid).concat(all_nodes[uid])
            return all_nodes[uid]
        } else
            all_nodes[uid] = this
        // this.children.forEach((child) => child.save())
        return this
    }
}

function MCTS(root, iterations) {
    for (let i = 0; i < iterations; i++) {
        let node = root;

        while(true) {
            let reward = node.simulate()
            node = node.save()
            const expanded = node.expanded
            node = node.expand()
            if (node.isTerminal()) {
                if (node.isWin()) {
                    reward = node.state.inventory['💰'] ? node.state.inventory['💰'] + target_reward : target_reward // bonus for reaching the target
                    node.backpropagate(reward);
                    success = true
                    console.log('WE FUCKIN DID IT REDDIT')
                } else {
                    if (node.children.length === 0)
                        reward = node.state.inventory['💰'] ? node.state.inventory['💰'] - failure_penalty : -failure_penalty
                    node.backpropagate(reward);
                    if (node.state.inventory['⏹'] > 0) {
                        console.log('DEAD END', node)
                        throw 'There should be moves left'
                    }
                    console.log('DEAD END', node)
                }
                break
            } else
                node.backpropagate(reward)

            if (!expanded)
                break
            
            const selected = node.select()
            selected.parent = node
            selected.depth = node.depth + 1
            node = selected
        }

        // console.log(Object.keys(all_nodes).length, node)
        // pretty_print_inventory(node.state.inventory, node.state.growing_inventory)
    }
    // print:
    print_best_path(root)

    // root.save()
    // console.log('ALL NODES: ', Object.keys(all_nodes).length, duplicate_nodes, all_nodes)

    return root;
}

const print_best_path =  (root) => {
    let node = root
    while(node.expanded && node.children.length > 0) {
        node = node.select(true) // best fit
        const choices = []
        node.children.forEach((choice) => choices.push({ depth: choice.depth, visits: choice.visits, rewards: choice.rewards, recipe: choice.state.target_recipe }))
        console.log('BEST PATH: ', node.depth, node.visits, node.rewards, node.UCB1, node.state.inventory['💰'], node, node.state.target_recipe, node.state.recipe_history, node.state.inventory, node.state.growing_inventory, choices)

        pretty_print_inventory(node.state.inventory, node.state.growing_inventory)
    }
}
  

const serialize_nodes = (nodes) => {
    const serialized_nodes = {}
    Object.keys(nodes).forEach((key) => {
        const node = nodes[key]
        serialized_nodes[key] = node.serialize()
    })
    return serialized_nodes
}

const deserialize_nodes = (serialized_nodes) => {
    const nodes = {}
    Object.keys(serialized_nodes).forEach((key) => {
        const serialized_node = serialized_nodes[key]
        const node = new Node()
        node.deserialize(serialized_node)
        nodes[key] = node
        if (!node.parent) {
            root = node
        }
    })
    Object.keys(nodes).forEach((key) => {
        const node = nodes[key]
        if (node.parent)
            node.parent = nodes[node.parent]
        node.children = node.children.map((child) => nodes[child])
    })
    return nodes
}



let last_saved_file_code = 0
let paused = false

const save_to_file = (data, filename) => {
    const blob = new Blob([data], {type: 'application/json'})
    const a = document.createElement('a')
    a.href = URL.createObjectURL(blob)
    a.download = filename
    a.click()
}


const start_MCTS = async () => {
    await initialize(recipes, emoji_indexed_recipes, inventory)

    console.log(Object.keys(inventory).length, inventory)
    console.log(Object.keys(recipes).length, recipes)
    console.log(Object.keys(emoji_indexed_recipes).length, emoji_indexed_recipes)
    console.log(recipe_history.length, recipe_history)

    // create pretty list of links
    const links = document.createElement('div')
    links.style = 'display: flex; flex-direction: column; align-items: center; justify-content: center; width: 100%; height: 100%;'
    document.body.appendChild(links)


    // create NEW link
    const new_link = document.createElement('a')
    new_link.href = '#'
    new_link.innerText = 'NEW'
    links.appendChild(new_link)
    new_link.onclick = async () => {
        console.log('NEW')
        paused = false
        all_nodes = {}
        const root = new Node({
            target_recipe: {
                ID: 'ID_Start',
                Recipe: recipes['ID_Start']
            },
            inventory: Object.assign({}, inventory),
            growing_inventory: Object.assign({}, inventory),
            recipe_history: recipe_history.slice(),
        })
        const loop = async () => {
            if (paused) {
                console.log('PAUSE RECOGNIZED')
                return
            }
            MCTS(root, iterations)
            const data = JSON.stringify(serialize_nodes(all_nodes))
            console.log(Object.keys(all_nodes).length, data.length)
            // save_to_file(data, 'mcts_'+ ++last_saved_file_code +'.json')
            console.log('Ready')
            if (success) {
                console.log('SUCCESS')
                return
            }
            setTimeout(loop, 0)
        }
        loop()
        
    }

    // create SAVE link
    const save_link = document.createElement('a')
    save_link.href = '#'
    save_link.innerText = 'SAVE'
    links.appendChild(save_link)
    save_link.onclick = async () => {
        const serialized = JSON.stringify(serialize_nodes(all_nodes))
        save_to_file(serialized, 'mcts_'+ ++last_saved_file_code +'.json')
    }

    // create LOAD link
    const load_link = document.createElement('a')
    load_link.href = '#'
    load_link.innerText = 'LOAD'
    links.appendChild(load_link)
    load_link.onclick = async () => {
        const file = document.createElement('input')
        file.type = 'file'
        file.onchange = async (e) => {
            const file = e.target.files[0]
            const text = await file.text()
            const serialized_nodes = JSON.parse(text)
            all_nodes = deserialize_nodes(serialized_nodes)
            console.log('LOADED', Object.keys(all_nodes).length)
        }
        file.click()
    }

    // create START link
    const start_link = document.createElement('a')
    start_link.href = '#'
    start_link.innerText = 'START'
    links.appendChild(start_link)
    start_link.onclick = async () => {
        paused = false
        const root = Object.keys(all_nodes).filter(key => all_nodes[key].parent === undefined)[0]
        const loop = async () => {
            if (paused) {
                console.log('PAUSE RECOGNIZED')
                return
            }
            MCTS(root, iterations)
            const data = JSON.stringify(serialize_nodes(all_nodes))
            console.log(Object.keys(all_nodes).length, duplicate_nodes, data.length)
            save_to_file(data, 'mcts_'+ ++last_saved_file_code +'.json')
            console.log('Ready')
            if (success) {
                console.log('SUCCESS')
                return
            }
            setTimeout(loop, 0)
        }
        loop()
    }

    // create PAUSE link
    const pause_link = document.createElement('a')
    pause_link.href = '#'
    pause_link.innerText = 'PAUSE'
    links.appendChild(pause_link)
    pause_link.onclick = () => {
        paused = true
        console.log('PAUSED')
    }

    // create board on page
    const board = document.createElement('div')
    board.style = 'display: flex; flex-direction: column; align-items: center; justify-content: center; width: 100%; height: 100%;'
    board.id = 'board'
    document.body.appendChild(board)
}

const pretty_print_inventory = (inventory, growing_inventory = {}) => {
    const pretty_inventory = {}
    const pretty_growing = {}
    let board = '⏹' + (inventory['⏹'] || '') + ': '
    
    const board_items = [
        '🟩', '🟨', '🟧', '🟦', '🌳', '🗻', '⛰', '☘', '🍀', '🕳', '🟤',
        '🐝', '🥅', '🍺⚙', '🔥⚙', '🥫⚙', '🧀⚙', '🧵⚙', '🧂⚙', '➕', '🌱⚙', '🚿⚙', '🤖', '🚧', // '⏹',
        '🐄', '🐔', '🐑', '🐖'
    ]
    Object.keys(inventory).forEach((key) => {
        // if string matches start of another string
        const match = board_items.find((item) => key.startsWith(item) && !key.includes('💳'))
        if (match)
            pretty_inventory[key] = inventory[key]
    })
    Object.keys(pretty_inventory).forEach((key) => {
        if (pretty_inventory[key] > 0)
            board += key + (pretty_inventory[key] || '') + '  '
    })

    board += '\n🌞' + (inventory['🌞'] || '') + ': '

    Object.keys(growing_inventory).forEach((key) => {
        const match = board_items.find((item) => key.startsWith(item) && !key.includes('💳'))
        if (match)
            pretty_growing[key] = inventory[key]
    })
    Object.keys(pretty_growing).forEach((key) => {
        if (pretty_growing[key] > 0)
            board += key + (pretty_growing[key] || '') + '  '
    })

    board += '\n🛒' + (inventory['💳'] || '') + ': '

    const shop = {}
    Object.keys(inventory).forEach((key) => {
        if (key.includes('💳'))
            shop[key] = inventory[key]
    })
    Object.keys(shop).forEach((key) => {
        if (shop[key] > 0)
            board += key + (shop[key] || '') + '  '
    })

    board += '\n💧' + (inventory['💧'] || '') + ': '
    const tools = {}
    const tool_items = [
        '🔰', '♠', '🪓', '⛏', '🚿', '🎣', '🔨'
    ]
    Object.keys(inventory).forEach((key) => {
        const match = tool_items.find((item) => key.startsWith(item))
        if (match)
            tools[key] = inventory[key]
    })
    Object.keys(tools).forEach((key) => {
        if (tools[key] > 0)
            board += key + (tools[key] || '') + '  '
    })


    board += '\n💰' + (inventory['💰'] || '') + ': '
    const backpack = {}
    const excludes = ['⏹', '🌞', '💧', '🛒', '💰']
    Object.keys(inventory).forEach((key) => {
        const is_board_item = board_items.find((item) => key.startsWith(item))
        const is_tool = tool_items.find((item) => key.startsWith(item))
        if (!is_board_item && !is_tool && !key in excludes && !key.includes('💳'))
            backpack[key] = inventory[key]
    })
    Object.keys(backpack).forEach((key) => {
        if (backpack[key] > 0)
            board += key + (backpack[key] || '') + '  '
    })
    

    // update board on page
    const board_element = document.getElementById('board')
    board_element.innerText = board

    console.log(board)
}






// MAIN LOOP
//naive_loop()

// MCTS
start_MCTS()

export default inventory
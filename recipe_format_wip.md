

# Please format the following bulk list of projects into a more functional build-recipe-style format.
# Consider the following examples for a guide on how to do this conversion.  You will be breaking down the list of info into separate recipes, particularly distinguishing between build and operation aspects.
# Be thoughtful about the nature of what is being represented.  Where it makes sense to change standard formatting, interject with a #Note please do so to explain your choices.
# Be very careful to preserve the original units and quantities.  All the original data must be included in the new recipes format.  Leave a #Note if that's ever violated or if you're unsure how to reformat.

# Output the TODO list in the new recipes format as per the examples.  Use # Original:, # Build:, # Operation: sections exactly as shown in the examples.  Process every line from the TODO list of notes as a separate recipe set.

# Hints: usually operations costs are measured in energy or money per year.  These are not always correctly labelled in the original data and so need to be reasoned out.  Sometime electricity/money/etc may be a build cost or even a production output.  Infer based on the nature of the data notes.
# Numbers are standardized to powers of either 1 or 3 (1, 3, 10, 30, 100, 300, etc.)
# Always round pessimistically (up for requirements/waste, down for efficiency)
# Units should include time components when representing rates (e.g. kg/day, ton/yr)
# Compound terms use underscores (e.g., Human_Survival)
# Each resource/property has a consistent emoji identifier
# Use real-world data but round to standardized numbers
# Account for all inputs and outputs where possible (conservation of mass/energy) within reasonable approximations

# FORMATTING RULES:

# => denotes a transformation, which removes the resources on the left and produces the resources on the right
#    conditional logic is expressed using the same resources on both sides (necessary for the transformation but not affected by it)
# :> denotes properties contained within a symbol.  Generally this is shorthand for full labels.  
#    e.g. 🥇Gold :> ⚖️30_ton/m3 💰100m 🪨1_ton  is mostly equivalent to just prefixing each property: 🥇⚖️30_ton/m3 🥇💰100m 🥇🪨1_ton.  All of these are just definitional properties of the 🥇Gold symbol.
#    note: :> are just properties it contains, not the full definition.  i.e. there may be other properties/contents
# <=> is just shorthand for two equations using => in both directions.  Equivalence.
# order doesn't matter aside from the left => right side differences

# ======= OUTPUT FORMAT:

# Original: 
# 🚢Kariba Lock              🗿100k tons     ⚙️30k tons    📏100 m       💰100m        🚢100m tons/yr 
# Build:
🗿100k_tons  ⚙️30k_tons  📏100_m  💰100m  => 🚢Kariba_Lock
# Operation:
🚢Kariba_Lock => 🚢Kariba_Lock  🚢100m_tons/yr

# ======= RECIPES:

# Original: 
# 🚢Kariba Lock              🗿100k tons     ⚙️30k tons    📏100 m       💰100m        🚢100m tons/yr 
# Build:
🗿100k_tons  ⚙️30k_tons  📏100_m  💰100m  => 🚢Kariba_Lock
# Operation:
🚢Kariba_Lock => 🚢Kariba_Lock  🚢100m_tons/yr

# Original: 
# 🚢Cahora Bassa Lock        🗿100k tons     ⚙️30k tons    📏100 m       💰100m        🚢100m tons/yr 
# Build:
🗿100k_tons  ⚙️30k_tons  📏100_m  💰100m  => 🚢Cahora_Bassa_Lock
# Operation:
🚢Cahora_Bassa_Lock => 🚢Cahora_Bassa_Lock  🚢100m_tons/yr

# Original: 
# 🎡Bucket Wheel Excavator   ⛏️100m tons/yr  ⚙️3k tons     ⚡️3 MW        💰30m
# Build:
⚙️3k_tons  💰30m  => 🎡Bucket_Wheel_Excavator
# Operation:
🎡Bucket_Wheel_Excavator  ⚡️3_MW/yr  => 🎡Bucket_Wheel_Excavator  ⛏️100m_tons/yr

# Original:
# 🏭Plasma Processor         🗿100k tons/yr  📏10 m        ⚡️100 KW      💰300k
# Build:
📏10_m  💰300k  => 🏭Plasma_Processor
# Operation:
🏭Plasma_Processor  ⚡️100_KW/yr  => 🏭Plasma_Processor  🗿100k_tons/yr

# Original:
# 🏭Plasma Refinery          🗿10m tons/yr   📐1k m2       ⚡️10 MW       💰30m
# Build:
📐1k_m2  💰30m  => 🚇Plasma_Tunneler
# Operation:
🚇Plasma_Tunneler  ⚡️10_MW/yr  => 🚇Plasma_Tunneler  ⛏️100m_tons/yr

# Original:
# 🚇Plasma Tunneler          ⛏️100m tons/yr  📏1 km/yr     ⚡️1 GW        ⭕10 m 
# Build:
⭕10_m  => 🚇Plasma_Tunneler
# Operation:
🚇Plasma_Tunneler ⚡️1_GW/yr   => 🚇Plasma_Tunneler  ⛏️100m_tons/yr 📏1_km/yr

# Original:
# 🚇Plasma MicroTunneler     ⛏️1m tons/yr    📏1 km/yr     ⚡️100 MW      ⭕1 m 
# Build:
⭕1_m  => 🚇Plasma_MicroTunneler
# Operation:
🚇Plasma_MicroTunneler  ⚡️100_MW/yr   => 🚇Plasma_MicroTunneler  ⛏️1m_tons/yr 📏1_km/yr

# Original:
# 🌞Solar Farm PV            ⚡️1 GW          📐10m m2      💰1b
# Build:
💰1b 📐10m_m2 => 🌞Solar_Farm_PV_GW
# Operation:
🌞Solar_Farm_PV_GW  => 🌞Solar_Farm_PV_GW  ⚡️1_GW/yr

# Original:
# 🌞Solar Farm PV            ⚡️1 MW          📐10k m2      💰1m
# Build:
💰1m 📐10k_m2 => 🌞Solar_Farm_PV_MW
# Operation:
🌞Solar_Farm_PV_MW  => 🌞Solar_Farm_PV_MW  ⚡️1_MW/yr

# Original:
# 🥔Cylinder Farm            👤10k pop       🥔10k ton/yr  📐1 km2       💧3m  ton/yr  
# Build:
📐1_km2 => 🥔Cylinder_Farm
# Operation:
🥔Cylinder_Farm 💧3_m_ton/yr  => 🥔Cylinder_Farm 🥔10k_ton/yr
👤10k_pop/yr  🥔10k_ton/yr => 👤10k_pop/yr
# Note: Separate recipe for food consumption by population

# Original:
# 🥔Dacha Farm               👤1 pop         🥔1 ton/yr    📐100 m2      💧300 ton/yr 
# Build:
📐100_m2 => 🥔Dacha_Farm
# Operation:
🥔Dacha_Farm 💧300_ton/yr  => 🥔Dacha_Farm 🥔1_ton/yr
👤1_pop/yr  🥔1_ton/yr => 👤1_pop/yr

# Original:
# 🥔Taro Farm                👤1 pop         🥔1 ton/yr    📐100 m2      💧300 ton/yr
# Build:
📐100_m2 => 🥔Taro_Farm
# Operation:
🥔Taro_Farm 💧300_ton/yr  => 🥔Taro_Farm 🥔1_ton/yr
👤1_pop/yr  🥔1_ton/yr => 👤1_pop/yr

# Original:
# 🌿Greenhouse Biomes        👤10m pop       🥔10m tons    📐1m m2       🪞1m m2       🪵1m ton
# Build:
📐1m_m2  🪞1m_m2  🪵1m_ton => 🌿Greenhouse_Biomes
# Operation:
🌿Greenhouse_Biomes  => 🌿Greenhouse_Biomes  🥔10m_tons/yr
👤10m_pop/yr  🥔10m_tons/yr => 👤10m_pop/yr

# Original:
# 🌿Biomes Backup            🌿300k          🥔300k ton/yr 📐300m m2     💧300m ton/yr 🎓300k pop/yr
# Build:
📐300m_m2 🌿300k => 🌿Biomes_Backup
# Operation:
🌿Biomes_Backup  💧300m_ton/yr  =>  🌿Biomes_Backup  🥔300k_ton/yr
🎓300k_pop/yr  🥔300k_ton/yr => 🎓300k_pop/yr
# lol why are these scholars

# Original:
# 🫘Coffee Farm              ☕3k ton/yr     📐1m m2
# Build:
📐1m_m2 => ☕Coffee_Farm
# Operation:
☕Coffee_Farm => ☕Coffee_Farm ☕3k_ton/yr

# Original:
# 🛍ZimShop                  🎓300 pop/yr    📐1k m2
# Build:
📐1k_m2 => 🛍ZimShop
# Operation:
🛍ZimShop => 🛍ZimShop 🎓300_pop/yr

# Original:
# 🛍ZimShops                 🎓1m pop/yr     📐3m m2
# Build:
📐3m_m2 => 🛍ZimShops
# Operation:
🛍ZimShops => 🛍ZimShops 🎓1m_pop/yr

# Original:
# 🏟️Kariba Barge             👤10k pop       ⚙️10k tons    📐30k m2      ⚡️1 MW       💰30m
# Build:
📐30k_m2  💰30m  ⚙️10k_tons  => 🏟Kariba_Barge
# Operation:
🏟Kariba_Barge ⚡️1_MW/yr  => 🏟Kariba_Barge 👤10k_pop/yr

# Original:
# 🏟️Kariba Floating Stadium  👤100k pop      🏟️10
# Build:
🏟️10 => 🏟Kariba_Floating_Stadium
# Operation:
🏟Kariba_Floating_Stadium => 🏟Kariba_Floating_Stadium 👤100k_pop/yr

# Original:
# 🖥️Operations Center        📱1m            📐10k m2      💰10m         🧠100
# Build:
📐10k_m2  💰10m  => 🖥Operations_Center
# Operation:
🖥Operations_Center 🧠100/yr => 🖥Operations_Center 📱1m/yr

# Original:
# 📲Electronics Fab          📱1m/yr         📐300 m2      📲30m         💰3m         
# Build:
📐300_m2  💰3m  => 📲Electronics_Fab
# Operation:
📲Electronics_Fab 📲30_m/yr => 📲Electronics_Fab 📱1m/yr

# Original:
# 📱Census Device            📱1m            📐10k m       💰100m
# Build:
📐10k_m  💰100m  => 📱Census_Device
# Operation:
📱Census_Device => 📱Census_Device 📱1m/yr

# Original:
# 📱Electronics Shops        📱1m/yr         📐1k m2       💰1m          💵300m
# Build:
📐1k_m2  💰1m  => 📱Electronics_Shops
# Operation:
📱Electronics_Shops 💵300m/yr => 📱Electronics_Shops 📱1m/yr

# Original:
# 🇿🇼Zimbazi Seaport          🗿300k tons     ⚙️100k tons   📏1k km       ⛏️10b ton     🎡100     💰3b        
# Build:
🗿300k_tons  ⚙️100k_tons  📏1k_km  ⛏️10b_ton  🎡100  💰3b  => 🎡100 🇿🇼Zimbazi_Seaport
# Operation:
🇿🇼Zimbazi_Seaport => 🇿🇼Zimbazi_Seaport


# Original:
# 📡Space Center             🚀10k LEO/yr   📦100 tons/yr  ⛽️300k ton     ⚙️1m tons/yr 🛰️10k/yr  💨300k ton 📲100k 💰300m/yr
# Build:
💰300m  📲100k  => 📡Space_Center
# Operation:
📡Space_Center  ⛽️300k_ton/yr  ⚙️1m_tons/yr  💰300m/yr  => 📡Space_Center 🚀10k_LEO/yr  📦100_tons/yr  💨300k_ton/yr
📦100_tons/yr => 🛰️10k/yr  📦100_tons/yr

# Original:
# 🚀LEO Rocket               🏎️10k m/s              ⛽️30 ton       ⚙️100 ton    🛰️1       💨30 ton   📲10   💰30k
# Build:
💰30k  📲10  ⚙️100_ton => 🚀LEO_Rocket
# Operation:
🚀LEO_Rocket ⛽️30_ton  => 🚀LEO_Rocket 🏎️10k_m/s  📦10_kg  💨30_ton
📦10_kg => 🛰️1  📦10_kg
# Note: limited reuse

# Original:
# 🛰️Satellite Payload        🛰️10 kg        📲100          🔋10 wh        🌞10w        💫3k/yr   
# Build:
💰3k 📲100  => 🛰️Satellite_Payload
# Properties:
🛰️Satellite_Payload :> 🛰️10_kg  💫3k/yr
# Operation:
🛰️Satellite_Payload  🌞10w => 🛰️Satellite_Payload  🔋10_wh
# Note: watts per hour?

# Original:
# ⛽️Rocket Fuel              ⛽️1 ton        💰1k
# Build:
💰1k  => ⛽️Rocket_Fuel_1_ton

# Original:
# ⛏️Limestone Quarry         🐚100m tons/yr  📐10m m2      🎡1
# Build:
📐10m_m2  🎡1  => ⛏️Limestone_Quarry
# Operation:
⛏️Limestone_Quarry => ⛏️Limestone_Quarry 🐚100m_tons/yr

# Original:
# 🔥Cement Calcinators       🗿10m ton/yr    📐10k m2      ⚡️1GW         💰100k        🐚1m ton/yr
# Build:
📐10k_m2  💰100k  => 🔥Cement_Calcinators
# Operation:
🔥Cement_Calcinators  ⚡️1_GW/yr  🐚1m_ton/yr  => 🔥Cement_Calcinators  🗿10m_ton/yr

# Original:
# 🌞Cement Solar Farm PV     🥉3k tons       📐10m m2      ⚡️1GW         💰1b  
# Build:
📐10m_m2  🥉3k_tons  💰1b  => 🌞Cement_Solar_Farm_PV
# Operation:
🌞Cement_Solar_Farm_PV => 🌞Cement_Solar_Farm_PV ⚡️1_GW/yr

# Original:
# 🌊Kariba Hydroelectric Dam 🗿3m tons       📏100 m       ⚡️1 GW
# Build:
🗿3m_tons  📏100_m  => 🌊Kariba_Hydroelectric_Dam
# Operation:
🌊Kariba_Hydroelectric_Dam => 🌊Kariba_Hydroelectric_Dam ⚡️1_GW/yr

# Original:
# ⚙️Kariba Steel Refinery    ⚙️1m tons/yr    📐3m m2       ⚡️1 GW
# Build:
📐3m_m2  => ⚙️Kariba_Steel_Refinery
# Operation:
⚙️Kariba_Steel_Refinery ⚡️1_GW/yr => ⚙️Kariba_Steel_Refinery ⚙️1m_tons/yr

# Original:
# 🏭Iron Refinery - Gas      ⚙️1m tons/yr    📐1m m2       ⚡️300 MW
# Build:
📐1m_m2  => 🏭Iron_Refinery_Gas
# Operation:
🏭Iron_Refinery_Gas ⚡️300_MW/yr => 🏭Iron_Refinery_Gas ⚙️1m_tons/yr

# Original:
# 🏭Iron Refinery - Hydrogen ⚙️1m tons/yr    📐1m m2       ⚡️1 GW
# Build:
📐1m_m2  => 🏭Iron_Refinery_Hydrogen
# Operation:
🏭Iron_Refinery_Hydrogen ⚡️1_GW/yr => 🏭Iron_Refinery_Hydrogen ⚙️1m_tons/yr

# Original:
# 🏭Iron Refinery - Blast    ⚙️1m tons/yr    📐1m m2       ⚡️1 GW
# Build:
📐1m_m2  => 🏭Iron_Refinery_Blast
# Operation:
🏭Iron_Refinery_Blast ⚡️1_GW/yr => 🏭Iron_Refinery_Blast ⚙️1m_tons/yr


# Original:
# ⭕Cylinder                 🗿10k tons      📏30 m        📐30k m2      ⭕60 m
# Build:
🗿10k_tons  📏30_m  📐30k_m2  ⭕60_m  => ⭕Cylinder

# Original:
# 🏭Cylinder Printer Farm    🏭300m/yr       🏗️300k        ⚡️30 MW       ♻️100k ton/yr 💰300m    🦾100
# Build:
🏗️300k  💰300m  🦾100  => 🏭Cylinder_Printer_Farm
# Operation:
🏭Cylinder_Printer_Farm ⚡️30_MW/yr ♻️100k_ton/yr => 🏭Cylinder_Printer_Farm 🏭300m/yr

# Original:
# 🏭Cylinder 5-Axis Farm     🏭3b/yr         🏗️10k         ⚡️30 MW       ⚙️10k ton/yr  💰300m    🦾1k
# Build:
🏗️10k  💰300m  🦾1k  => 🏭Cylinder_5_Axis_Farm
# Operation:
🏭Cylinder_5_Axis_Farm ⚡️30_MW/yr ⚙️10k_ton/yr => 🏭Cylinder_5_Axis_Farm 🏭3b/yr

# Original:
# 🏭Cylinder Warehouse       📦30k           📦30k tons    📐30k m2      ⚙️300 tons    💰3m      🦾10    
# Build:
📐30k_m2  ⚙️300_tons  💰3m  🦾10  => 🏭Cylinder_Warehouse
# Operation:
🏭Cylinder_Warehouse => 🏭Cylinder_Warehouse 📦30k 📦30k_tons

# Original:
# 🏫Cylinder Library         👤1m pop        📚10m         📐30k m2      
# Build:
📐30k_m2  📚10m  => 🏫Cylinder_Library
# Operation:
🏫Cylinder_Library => 🏫Cylinder_Library 👤1m_pop/yr

# Original:
# 🏫Cylinder Edu             🎓1k            🏫100         📐10k m2      🪵300 tons    🪞10k m2
# Build:
📐10k_m2  🪵300_tons  🪞10k_m2  🏫100  => 🏫Cylinder_Edu
# Operation:
🏫Cylinder_Edu => 🏫Cylinder_Edu 🎓1k/yr

# Original:
# 🌱Soil-Nullabor Cylinders  🌱10b tons/yr         
# Operation:
🌱Soil_Nullabor_Cylinders => 🌱Soil_Nullabor_Cylinders 🌱10b_tons/yr

# Original:
# 🌱Cylinder Soil            🗿10k tons      📏30 m        📐3k m2     
# Build:
🗿10k_tons  📏30_m  📐3k_m2  => 🌱Cylinder_Soil
# Operation:
🌱Cylinder_Soil => 🌱Cylinder_Soil 🗿10k_tons


# Original:
# 💍ZimShop                  💍3k/yr         🎓300/yr      📐100 m2      💵10m         🥇30 kg/yr
# Build:
📐100_m2  💰10m  => 💍ZimShop
# Operation:
💍ZimShop => 💍ZimShop 💍3k/yr 🎓300/yr 🥇30_kg/yr
# Note: Assuming the 💵10m is a build cost since it's not marked as /yr

# Original:
# 💍ZimShops                 💍10k/y         🎓1m/yr       📐30k m2      💵30b         🥇30 ton/yr
# Build:
📐30k_m2  💰30b  => 💍ZimShops
# Operation:
💍ZimShops => 💍ZimShops 💍10k/yr 🎓1m/yr 🥇30_ton/yr

# Original:
# 🏫ZimSchool                👤10            🎓300         📐1k     
# Build:
📐1k  => 🏫ZimSchool
# Operation:
🏫ZimSchool => 🏫ZimSchool 👤10/yr 🎓300/yr

# Original:
# 🏫ZimSchools               👤100k          🎓3m          📐10b m2      🏫10k
# Build:
📐10b_m2  🏫10k  => 🏫ZimSchools
# Operation:
🏫ZimSchools => 🏫ZimSchools 👤100k/yr 🎓3m/yr

# Original:
# ☕️ZimShop - Coffee         🫘1 ton/yr      ☕️100k        📐30 m2       💵300k
# Build:
📐30_m2  💰300k  => ☕️ZimShop_Coffee
# Operation:
☕️ZimShop_Coffee => ☕️ZimShop_Coffee 🫘1_ton/yr ☕️100k/yr

# Original:
# ☕️ZimShops - Coffee        🫘3k ton/yr     ☕️300m        📐100k m2     💵1b
# Build:
📐100k_m2  💰1b  => ☕️ZimShops_Coffee
# Operation:
☕️ZimShops_Coffee => ☕️ZimShops_Coffee 🫘3k_ton/yr ☕️300m/yr

# Original:
# 🍲ZimShop - Dining         🥔100 ton/yr    🍲1m/yr       📐1k m2       💵100m
# Build:
📐1k_m2  💰100m  => 🍲ZimShop_Dining
# Operation:
🍲ZimShop_Dining => 🍲ZimShop_Dining 🥔100_ton/yr 🍲1m/yr

# Original:
# 🍲ZimShops - Dining        🥔300k ton/yr   🍲3b/yr       📐300k m2     💵300b
# Build:
📐300k_m2  💰300b  => 🍲ZimShops_Dining
# Operation:
🍲ZimShops_Dining => 🍲ZimShops_Dining 🥔300k_ton/yr 🍲3b/yr

# Original:
# 🍲World Kitchen            🍲3b/yr         🥔300k ton/yr 📐3m m2       🌿300k         ✈️10
# Build:
📐3m_m2  🌿300k  ✈️10  => 🍲World_Kitchen
# Operation:
🍲World_Kitchen => 🍲World_Kitchen 🍲3b/yr 🥔300k_ton/yr

# Original:
# ✈️Airplane - Passenger     👤1m pop/yr     🛫3k/yr       ⛽️10k tons    💰100m      
# Build:
💰100m  => ✈️Airplane_Passenger
# Operation:
✈️Airplane_Passenger ⛽️10k_tons/yr => ✈️Airplane_Passenger 👤1m_pop/yr 🛫3k/yr

# Original:
# ✈️Airline                  👤10m pop/yr    🛫30k/yr      ⛽️100k tons   💰1b           ✈️10
# Build:
💰1b  ✈️10  => ✈️Airline
# Operation:
✈️Airline ⛽️100k_tons/yr => ✈️Airline 👤10m_pop/yr 🛫30k/yr

# Original:
# 🌿Bamboo Forest            🪵3k ton/yr     💧3m m3/yr    📐1 km2 
# Build:
📐1_km2  => 🌿Bamboo_Forest
# Operation:
🌿Bamboo_Forest 💧3m_m3/yr => 🌿Bamboo_Forest 🪵3k_ton/yr

# Original:
# 🧪Ammonia NH3 Plant        🧪1m ton/yr     💧3m m3 /yr   ⚡️300 MW      💰1B
# Build:
💰1b => 🧪Ammonia_NH3_Plant
# Operation:
🧪Ammonia_NH3_Plant 💧3m_m3/yr ⚡️300_MW/yr => 🧪Ammonia_NH3_Plant 🧪1m_ton/yr

# Original:
# 🧪Ammonia NH3 Plant Plasma 🧪1m ton/yr     💧3m m3 /yr   ⚡️300 MW      💰300m
# Build:
💰300m => 🧪Ammonia_NH3_Plant_Plasma
# Operation:
🧪Ammonia_NH3_Plant_Plasma 💧3m_m3/yr ⚡️300_MW/yr => 🧪Ammonia_NH3_Plant_Plasma 🧪1m_ton/yr

# Original:
# 🏗️Manufacturing - Mini     🏭100k #/yr     🛠️1           📐100 m2      🎓100 pop/yr   💰10k
# Build:
📐100_m2 🛠️1 💰10k => 🏗️Manufacturing_Mini
# Operation:
🏗️Manufacturing_Mini => 🏗️Manufacturing_Mini 🏭100k_#/yr 🎓100_pop/yr

# Original:
# 🏗️Manufacturing - Major    🏭10m #/yr      🛠️10          📐1k m2       🎓1k pop/yr    💰1m
# Build:
📐1k_m2 🛠️10 💰1m => 🏗️Manufacturing_Major
# Operation:
🏗️Manufacturing_Major => 🏗️Manufacturing_Major 🏭10m_#/yr 🎓1k_pop/yr

# Original:
# 🏗️Manufacturing - Macro    🏭100m #/yr     🛠️100         📐10k m2      🎓10k pop/yr   💰10m
# Build:
📐10k_m2 🛠️100 💰10m => 🏗️Manufacturing_Macro
# Operation:
🏗️Manufacturing_Macro => 🏗️Manufacturing_Macro 🏭100m_#/yr 🎓10k_pop/yr

# Original:
# 🏗️Manufacturing Hubs       🏭1b #/yr       🛠️1k          📐1m m2       🎓1m pop/yr    💰100m
# Build:
📐1m_m2 🛠️1k 💰100m => 🏗️Manufacturing_Hubs
# Operation:
🏗️Manufacturing_Hubs => 🏗️Manufacturing_Hubs 🏭1b_#/yr 🎓1m_pop/yr

# Original:
# 🌊Canal                    ↔️10 m          ↕️10 m        📐100 m2/m    ⛏️300k ton     📏1 km
# Build:
↔️10_m ↕️10_m 📐100_m2/m ⛏️300k_ton 📏1_km => 🌊Canal

# Original:
# 🌊Canal - Deepwater        ↔️100 m         ↕️30 m        📐3k m2/m     ⛏️10m ton      📏1 km
# Build:
↔️100_m ↕️30_m 📐3k_m2/m ⛏️10m_ton 📏1_km => 🌊Canal_Deepwater

# Original:
# 🔼Canal Lock               🗿10k tons      ⚙️30 tons     📐1 km2       ⬆️10 m         💰300k
# Build:
🗿10k_tons ⚙️30_tons 📐1_km2 ⬆️10_m 💰300k => 🔼Canal_Lock

# Original:
# 🔼Canal Lock - Deepwater   🗿100k tons     ⚙️30k tons    📐1 km2       ⬆️10 m         💰10m
# Build:
🗿100k_tons ⚙️30k_tons 📐1_km2 ⬆️10_m 💰10m => 🔼Canal_Lock_Deepwater

# Original:
# 🚢Barge - Concrete         🗿300 tons      📐3k m2       📦3k tons     🏎️3 m/s
# Build:
🗿300_tons 📐3k_m2 => 🚢Barge_Concrete
# Properties:
🚢Barge_Concrete :> 📦3k_tons 🏎️3_m/s

# Original:
# 🚢Barge - Steel            ⚙️3k tons       📐3k m2       📦3k tons     🏎️3 m/s
# Build:
⚙️3k_tons 📐3k_m2 => 🚢Barge_Steel
# Properties:
🚢Barge_Steel :> 📦3k_tons 🏎️3_m/s

# Original:
# 🚢Barge - Bridge           ⚙️3k tons       📐3k m2       📦3k tons     🏎️3 m/s        🌉30          🌉10k/yr
# Build:
⚙️3k_tons 📐3k_m2 🌉30 => 🚢Barge_Bridge
# Properties:
🚢Barge_Bridge :> 📦3k_tons 🏎️3_m/s
# Operation:
🚢Barge_Bridge => 🚢Barge_Bridge 🌉10k/yr

# Original:
# 🚢Cargo Ship               ⚙️100k tons     📏60 m        📦10k tons    🏎️30 m/s
# Build:
⚙️100k_tons 📏60_m => 🚢Cargo_Ship
# Properties:
🚢Cargo_Ship :> 📦10k_tons 🏎️30_m/s

# Original:
# 🚢Barge Factory - Concrete 🗿1m tons/yr    🚢30k/yr
# Build:
🗿1m_tons => 🚢Barge_Factory_Concrete
# Operation:
🚢Barge_Factory_Concrete => 🚢Barge_Factory_Concrete 🚢30k/yr

# Original:
# 🚢Barge Factory - Steel    ⚙️1m tons/yr    🚢3k/yr       ⚡️1 MW        🦾100
# Build:
🦾100 => 🚢Barge_Factory_Steel
# Operation:
🚢Barge_Factory_Steel ⚡️1_MW/yr ⚙️1m_tons/yr => 🚢Barge_Factory_Steel 🚢3k/yr


# Original:
# 🏜️Kalahari Canals - Dig    💧10b ton       ⛏️10b tons    🥔1b ton/yr   🎡100          📏100k km    📐300k km2   💰3b
# Build:
📏100k_km 📐300k_km2 🎡100 💰3b ⛏️10b_tons 💧10b_ton => 🎡100 🏜️Kalahari_Canals_Dig

# Original:
# 🏜️Kalahari Canals - Farms  💧10b ton
# Operation:
🏜️Kalahari_Canals_Farms 💧10b_ton/yr => 🏜️Kalahari_Canals_Farms

# Original:
# 🏜️Kalahari Canals - Barges 📦1b tons/yr    🚢10k         📏1k km       🏎️3 m/s        🔂300k sec   🔁30/yr       
# Build:
📏1k_km 🚢10k => 🏜️Kalahari_Canals_Barges
# Properties:
🏜️Kalahari_Canals_Barges :> 🏎️3_m/s 🔂300k_sec
# Operation:
🏜️Kalahari_Canals_Barges => 🏜️Kalahari_Canals_Barges 📦1b_tons/yr 🔁30/yr

# Original:
# 🏜️Kalahari Canals Bridges  🌉10k/yr        📏10 km       🗿300k ton
# Build:
📏10_km 🗿300k_ton => 🏜️Kalahari_Canals_Bridges
# Operation:
🏜️Kalahari_Canals_Bridges => 🏜️Kalahari_Canals_Bridges 🌉10k/yr

# Original:
# 🌉Bridge - Bailey          ⚙️10 ton        📏10 m        💰30k
# Build:
⚙️10_ton 📏10_m 💰30k => 🌉Bridge_Bailey

# Original:
# 🪨Bridge - Precast         🗿30 ton        📏10 m        💰30k
# Build:
🗿30_ton 📏10_m 💰30k => 🪨Bridge_Precast

# Original:
# 🦾Cobot                    🥉3 kg          ⚙️10 kg       ♻️10 kg       📲100          📐1 m2       💰10k          
# Build:
🥉3_kg ⚙️10_kg ♻️10_kg 📲100 📐1_m2 💰10k => 🦾Cobot

# Original:
# 🦾Cobot Factory            🥉3k ton/yr     ⚙️10k ton/yr  ♻️10k ton/yr  📲100m/yr      📐10k m2     🦾1k           
# Build:
📐10k_m2 🦾1k => 🦾Cobot_Factory
# Operation:
🦾Cobot_Factory 🥉3k_ton/yr ⚙️10k_ton/yr ♻️10k_ton/yr => 🦾Cobot_Factory 📲100m/yr

# Original:
# 🛞Motor Factory - 1 W      🛞1m/yr         🥉3 ton/yr    ⚙️10 ton/yr   🧲3 ton/yr     📐1k m2      💰3m
# Build:
📐1k_m2 💰3m => 🛞Motor_Factory_1W
# Operation:
🛞Motor_Factory_1W 🥉3_ton/yr ⚙️10_ton/yr 🧲3_ton/yr => 🛞Motor_Factory_1W 🛞1m/yr

# Original:
# 🛞Motor Factory - 10 W     🛞1m/yr         🥉100 ton/yr  ⚙️30 ton/yr   🧲10 ton/yr    📐1k m2      💰3m
# Build:
📐1k_m2 💰3m => 🛞Motor_Factory_10W
# Operation:
🛞Motor_Factory_10W 🥉100_ton/yr ⚙️30_ton/yr 🧲10_ton/yr => 🛞Motor_Factory_10W 🛞1m/yr

# Original:
# 🛞Motor Factory - 100 W    🛞1m/yr         🥉300 ton/yr  ⚙️300 ton/yr  🧲30 ton/yr    📐1k m2      💰3m
# Build:
📐1k_m2 💰3m => 🛞Motor_Factory_100W
# Operation:
🛞Motor_Factory_100W 🥉300_ton/yr ⚙️300_ton/yr 🧲30_ton/yr => 🛞Motor_Factory_100W 🛞1m/yr

# Original:
# 🛞Motor Factory - 1 KW     🛞1m/yr         🥉3k ton/yr   ⚙️1k ton/yr   🧲300 ton/yr   📐10k m2     💰10m
# Build:
📐10k_m2 💰10m => 🛞Motor_Factory_1KW
# Operation:
🛞Motor_Factory_1KW 🥉3k_ton/yr ⚙️1k_ton/yr 🧲300_ton/yr => 🛞Motor_Factory_1KW 🛞1m/yr

# Original:
# 🧲Magnet Factory           🧲1k ton/yr     ⚙️1k ton/yr   🪙300 ton/yr  ⚡️300 KW       📐3k m2      💰10m
# Build:
📐3k_m2 💰10m => 🧲Magnet_Factory
# Operation:
🧲Magnet_Factory ⚙️1k_ton/yr 🪙300_ton/yr ⚡️300_KW/yr => 🧲Magnet_Factory 🧲1k_ton/yr

# Original:
# 🛸Drone Factory            🛸1m/yr         🛞3m/yr       ♻️10k ton/yr  📲10m/yr       📐10k m2     💰10m
# Build:
📐10k_m2 💰10m => 🛸Drone_Factory
# Operation:
🛸Drone_Factory 🛞3m/yr ♻️10k_ton/yr => 🛸Drone_Factory 🛸1m/yr 📲10m/yr



# Original:
# 🥉Copper Refinery          🥉1m ton/yr     ⚙️10k ton     ⛏️100m ton/yr ⚡️1 GW         📐100k m2    💰300m
# Build:
📐100k_m2 💰300m ⚙️10k_ton => 🥉Copper_Refinery
# Operation:
🥉Copper_Refinery ⛏️100m_ton/yr ⚡️1_GW/yr => 🥉Copper_Refinery 🥉1m_ton/yr

# Original:
# 🥉Rare Earth Refinery      🪙1k ton/yr     ⚙️10k ton     ⛏️1m ton/yr   ⚡️100 MW       📐30k m2     💰100m
# Build:
📐30k_m2 💰100m ⚙️10k_ton => 🥉Rare_Earth_Refinery
# Operation:
🥉Rare_Earth_Refinery ⛏️1m_ton/yr ⚡️100_MW/yr => 🥉Rare_Earth_Refinery 🪙1k_ton/yr

# Original:
# 🛢️Oil Refinery             🛢️1m ton/yr     ⛽️300k ton/yr ♻️100k ton/yr ⚫️3k ton/yr    📐30k m2     💰300m
# Build:
📐30k_m2 💰300m => 🛢️Oil_Refinery
# Operation:
🛢️Oil_Refinery ♻️100k_ton/yr => 🛢️Oil_Refinery 🛢️1m_ton/yr ⛽️300k_ton/yr ⚫️3k_ton/yr

# Original:
# ⏫Upweller                 ⚙️1k ton        ⬇️100m        🌡️10          ⚡️300kw        📐300 km2    💰1m         ⭕60 m      🌊100b ton/yr
# Build:
⚙️1k_ton ⬇️100m  📐300_km2  💰1m  => ⏫Upweller
# Properties:
⏫Upweller :> 🌡️10C_cooling ⭕60_m 📐300_km2  ⬇️100m  
# Operation:
⏫Upweller ⚡️300kw/yr 🌡️10 🌊100b_ton/yr => ⏫Upweller 🌊100b_ton/yr

# Original:
# ⏫Upweller Array           ⚙️3m ton        ⏫3k          🌊300t ton/yr ⚡️1 GW         📐1m km2     💰3b
# Build:
⚙️3m_ton ⏫3k 📐1m_km2 💰3b => ⏫Upweller_Array
# Operation:
⏫Upweller_Array ⚡️1_GW/yr 🌊300t_ton/yr => ⏫Upweller_Array 🌊300t_ton/yr

# Original:
# 🛣️MicroRoad                📏1km           ↔️1 m         ⚫️300 tons    🪨1k ton       🗿300 ton    ⛏️10k ton
# Build:
📏1_km ↔️1_m ⚫️300_tons 🪨1k_ton 🗿300_ton ⛏️10k_ton => 🛣️MicroRoad

# Original:
# 🛣️Highway - Tar            📐1 m2          ↕️100 mm      ⚫️.3 tons     
# Build:
📐1_m2 ↕️100_mm ⚫️0.3_tons => 🛣️Highway_Tar

# Original:
# 🛣️Highway - 8 Lane         📏1km           ↔️30 m        ⚫️10k tons    🪨30k ton      🗿10k ton    ⛏️300k ton
# Build:
📏1_km ↔️30_m ⚫️10k_tons 🪨30k_ton 🗿10k_ton ⛏️300k_ton => 🛣️Highway_8_Lane

# Original:
# 🇦🇴Angola Highway           📏1k km         ↔️30 m        ⚫️10m tons    🪨30m ton      🗿10m ton    ⛏️300m ton
# Build:
📏1k_km ↔️30_m ⚫️10m_tons 🪨30m_ton 🗿10m_ton ⛏️300m_ton => 🇦🇴Angola_Highway

# Original:
# ⛺️Kspan                    📐300k m2/yr    ⚙️30k m2/yr   👤10          🗓️1 yr         💰3m
# Build:
💰3m 👤10 🗓️1_yr ⚙️30k_m2  📐300k_m2  => 👤10 ⛺️Kspan
# Properties:
⛺️Kspan :> 📐300k_m2

# Original:
# ⛺️Kspan - Team             📐1k m2         ⚙️100 m2      👤10          ⏰1 day        💰10k
# Build:
💰10k 👤10 ⏰1_day => ⛺️Kspan_Team
# Operation:
⛺️Kspan_Team ⚙️100_m2 => ⛺️Kspan_Team 📐1k_m2

# Original:
# ⛺️Kspan - Mass             📐1 m2          ⚙️.1 ton      💰10  
# Build:
⚙️0.1_ton 💰10 📐1_m2 => ⛺️Kspan_Mass
# Properties:
⛺️Kspan_Mass :> 📐1_m2


# Original:
# 🔁Belts                    📏1km           🐚100m ton/yr ⚙️300 ton     ⚡️3 MW         💰1m         🏀10 ton
# Build:
📏1_km ⚙️300_ton 🏀10_ton 💰1m => 🔁Belts
# Operation:
🔁Belts ⚡️3_MW/yr => 🔁Belts 🐚100m_ton/yr

# Original:
# 🚡Cableway                 📏1km           🐚100m ton/yr ⚙️300 ton     ⚡️3 MW         💰3m 
# Build:
📏1_km ⚙️300_ton 💰3m => 🚡Cableway
# Operation:
🚡Cableway ⚡️3_MW/yr => 🚡Cableway 🐚100m_ton/yr

# Original:
# 🔥Calcinator               📐1k m2         🐚1m ton/yr   ⚙️100 ton     ⚡️30 MW        💰100k       
# Build:
📐1k_m2 ⚙️100_ton 💰100k => 🔥Calcinator
# Operation:
🔥Calcinator ⚡️30_MW/yr => 🔥Calcinator 🐚1m_ton/yr

# Original:
# 🏭BWE Fab                  🎡30 /yr        ⚙️300k ton/yr 📐30k m2      ⚡️3 MW         💰30m        🥉100 tons/yr
# Build:
📐30k_m2 💰30m => 🏭BWE_Fab
# Operation:
🏭BWE_Fab ⚡️3_MW/yr ⚙️300k_ton/yr 🥉100_tons/yr => 🏭BWE_Fab 🎡30/yr 

# Original:
# 🔁Nullabor Belts           📏3k km         🐚30b ton/yr  ⚙️1m ton      ⚡️10 GW        💰3b         🏀30k ton
# Build:
📏3k_km ⚙️1m_ton 🏀30k_ton 💰3b => 🔁Nullabor_Belts
# Operation:
🔁Nullabor_Belts ⚡️10_GW/yr => 🔁Nullabor_Belts 🐚30b_ton/yr

# Original:
# 🌊Nullabor Canal Pump      ↕️100 m         💧1b ton/yr   ⚙️3k ton      ⚡️30 MW        💰10m
# Build:
↕️100_m ⚙️3k_ton 💰10m => 🌊Nullabor_Canal_Pump
# Operation:
🌊Nullabor_Canal_Pump ⚡️30_MW/yr => 🌊Nullabor_Canal_Pump 💧1b_ton/yr

# Original:
# 🌊Nullabor Concrete Pump   ↕️100 m         💧30b ton/yr  ⚙️100k ton    ⚡️1 GW         💰300m
# Build:
↕️100_m ⚙️100k_ton 💰300m => 🌊Nullabor_Concrete_Pump
# Operation:
🌊Nullabor_Concrete_Pump ⚡️1_GW/yr => 🌊Nullabor_Concrete_Pump 💧30b_ton/yr


# Original:
# 🌊Nullabor Canals          📏3k km/yr      ⛏️3m ton
# Build:
📏3k_km ⛏️3m_ton => 🌊Nullabor_Canals
# Operation:
🌊Nullabor_Canals => 🌊Nullabor_Canals 📏3k_km/yr

# Original:
# 🌊Nullabor Canal           📏1 km          ↔️100 m       ↕️10 m        📐1k m2        ⛏️3m ton
# Build:
📏1_km ↔️100_m ↕️10_m 📐1k_m2 ⛏️3m_ton => 🌊Nullabor_Canal

# Original:
# 🚢Nullabor Barge           📦30k ton       ↔️30 m        ↗️300 m       ⚡️1 MW         💰3m         🗿10k ton      
# Build:
↔️30_m ↗️300_m 💰3m 🗿10k_ton => 🚢Nullabor_Barge
# Operation:
🚢Nullabor_Barge ⚡️1_MW/yr 📦30k_ton/yr => 🚢Nullabor_Barge 📦30k_ton/yr

# Original:
# 🚢Nullabor Barges          📦30b tons/yr   🚢3k          🗿300k ton    ⚡️3 GW         💰1b
# Build:
🚢3k 🗿300k_ton 💰1b => 🚢Nullabor_Barges
# Operation:
🚢Nullabor_Barges ⚡️3_GW/yr 📦30k_ton/yr => 🚢Nullabor_Barges 📦30b_tons/yr

# Original:
# 🚢Nullabor Barge Cycle     📦10m ton/yr    📏30 km       🔁300/yr      🏎️1 m/s
# Properties:
🚢Nullabor_Barge_Cycle :> 📏30_km 🏎️1_m/s 🔁300/yr
# Operation:
🚢Nullabor_Barge_Cycle 📦10m_ton/yr => 🚢Nullabor_Barge_Cycle 📦10m_ton/yr

# Original:
# 🏭Nullabor Barge Fab       🚢3k /yr        🗿300k ton/yr 📐300k m2     ⚡️30 MW        💰1b
# Build:
📐300k_m2 💰1b => 🏭Nullabor_Barge_Fab
# Operation:
🏭Nullabor_Barge_Fab ⚡️30_MW/yr 🗿300k_ton/yr => 🏭Nullabor_Barge_Fab 🚢3k/yr

# Original:
# 🗿Concrete Mixing Recipe   🗿1m ton/yr     🐚300k ton/yr 🏝️300k ton/yr 🪨300k ton/yr  💧300k ton/yr     
# Operation:
🗿Concrete_Mixing_Recipe 🐚300k_ton/yr 🏝️300k_ton/yr 🪨300k_ton/yr 💧300k_ton/yr => 🗿Concrete_Mixing_Recipe 🗿1m_ton/yr

# Original:
# 🗿Concrete Giga Recipe     🗿1b ton/yr     🐚300m ton/yr 🏝️300m ton/yr 🪨300m ton/yr  💧300m ton/yr  
# Operation:
🗿Concrete_Giga_Recipe 🐚300m_ton/yr 🏝️300m_ton/yr 🪨300m_ton/yr 💧300m_ton/yr => 🗿Concrete_Giga_Recipe 🗿1b_ton/yr

# Original:
# 🗿Nullabor GigaRecipe      🗿100b ton/yr   🐚30b ton/yr  🏝️30b ton/yr  🪨30b ton/yr   💧30b ton/yr 
# Operation:
🗿Nullabor_GigaRecipe 🐚30b_ton/yr 🏝️30b_ton/yr 🪨30b_ton/yr 💧30b_ton/yr => 🗿Nullabor_GigaRecipe 🗿100b_ton/yr

# Original:
# 🇦🇺Outback Farm             👤10b           🥔10b ton/yr  📐1t m2       💧1t ton/yr    💩1t ton
# Build:
📐1t_m2 💩1t_ton => 🇦🇺Outback_Farm
# Operation:
🇦🇺Outback_Farm 💧1t_ton/yr => 🇦🇺Outback_Farm 🥔10b_ton/yr
👤10b/yr  🥔10b_ton/yr => 👤10b/yr 

# Original:
# 🇦🇺Outback Canals           ⚙️1m ton        ⛏️100b ton    📐1t m2       🎡300          💰10b        💧100b ton     ↔️30 m
# Build:
⚙️1m_ton ⛏️100b_ton 📐1t_m2 🎡300 💰10b 💧100b_ton ↔️30_m => 🎡300 🇦🇺Outback_Canals

# Original:
# 🇦🇺Upweller - Aus Bight     ⚙️1m ton        ⏫1k          📐300b m2     ⚡️300 MW       💰1b         💧3t ton/yr
# Build:
⚙️1m_ton ⏫1k 📐300b_m2 💰1b => 🇦🇺Upweller_Aus_Bight
# Operation:
🇦🇺Upweller_Aus_Bight ⚡️300_MW/yr => 🇦🇺Upweller_Aus_Bight 💧3t_ton/yr




# Original:
# ⏫Upweller                 ⚙️1k ton        📐300k km     ⬇️100m        🌡️10C          ⭕60 m       ⚡️300kw        💰1m
# Build:
⚙️1k_ton 📐300k_km ⬇️100m ⭕60_m 💰1m => ⏫Upweller
# Properties:
⏫Upweller :> 🌡️10C_cooling
# Operation:
⏫Upweller ⚡️300kw/yr => ⏫Upweller

# Original:
# 💧Desalination Pop         👤1            💧.1 ton       ⏰1 day       🔁1 day
# Operation:
💧Desalination_Pop ⏰1_day 🌊0.1_ton => 💧Desalination_Pop 👤1 💧0.1_ton 🔁1

# Original:
# 💧Desalination             🚰1b ton/yr     ⚙️1k ton      📐300k m2     ⚡️300 MW       💰1b         💧1b ton/yr    ♻️30k ton
# Build:
⚙️1k_ton 📐300k_m2 💰1b => 💧Desalination
# Operation:
💧Desalination ⚡️300_MW/yr 🌊1b_ton/yr => 💧Desalination 🚰1b_ton/yr ♻️30k_ton/yr

# Original:
# 💧Desalination Nullabor    🚰10t ton/yr    ⚙️100k ton    📐30m m2      ⚡️1 TW         💰3b         💧10t ton/yr   ♻️300k ton
# Build:
⚙️100k_ton 📐30m_m2 💰3b => 💧Desalination_Nullabor
# Operation:
💧Desalination_Nullabor ⚡️1_TW/yr  => 💧Desalination_Nullabor 🚰10t_ton/yr ♻️300k_ton/yr

# Original:
# ⚡️Steam Power Plant        ⚡️1 GW          ⚙️30k ton     📐30k m2      🥉3k ton       💰1b         💨30m ton/yr 
# Build:
⚙️30k_ton 📐30k_m2 🥉3k_ton 💰1b => ⚡️Steam_Power_Plant
# Operation:
⚡️Steam_Power_Plant 💨30m_ton/yr => ⚡️Steam_Power_Plant ⚡️1_GW/yr

# Original:
# ⚡️Steam Turbine            ⚡️1 GW          ⚙️300 ton     📐30k m2      🥉3k ton       💰1m         💨30m ton/yr 
# Build:
⚙️300_ton 📐30k_m2 🥉3k_ton 💰1m => ⚡️Steam_Turbine
# Operation:
⚡️Steam_Turbine 💨30m_ton/yr => ⚡️Steam_Turbine ⚡️1_GW/yr
# Note: one of these is wrong

# Original:
# ⚙️Steel from Hydrogen      ⚙️1 ton         ⚙️1 ton       💨30 kg       
# Operation:
⚙️Steel_from_Hydrogen 💨30_kg => ⚙️Steel_from_Hydrogen ⚙️1_ton

# Original:
# 🏭Iron Ore Reduction       ⚙️10m ton/yr    ⚙️30k ton     📐300k m2     ⚡️3 GW         💰30m
# Build:
⚙️30k_ton 📐300k_m2 💰30m => 🏭Iron_Ore_Reduction
# Operation:
🏭Iron_Ore_Reduction ⚡️3_GW/yr => 🏭Iron_Ore_Reduction ⚙️10m_ton/yr

# Original:
# ⚙️Steel Factory - Only     ⚙️10m ton/yr    ⚙️30k ton     📐300k m2     ⚡️300 MW       💰100m
# Build:
⚙️30k_ton 📐300k_m2 💰100m => ⚙️Steel_Factory_Only
# Operation:
⚙️Steel_Factory_Only ⚡️300_MW/yr => ⚙️Steel_Factory_Only ⚙️10m_ton/yr

# Original:
# ⚙️Steel Factory - H2       ⚙️10m ton/yr    ⚙️300k ton    📐1m m2       ⚡️10 GW        💰300m
# Build:
⚙️300k_ton 📐1m_m2 💰300m => ⚙️Steel_Factory_H2
# Operation:
⚙️Steel_Factory_H2 ⚡️10_GW/yr => ⚙️Steel_Factory_H2 ⚙️10m_ton/yr

# Original:
# ⚙️Steel Factory - SMR      ⚙️10m ton/yr    ⚙️300k ton    📐1m m2       ⚡️10 GW        💰300m
# Build:
⚙️300k_ton 📐1m_m2 💰300m => ⚙️Steel_Factory_SMR
# Operation:
⚙️Steel_Factory_SMR ⚡️10_GW/yr => ⚙️Steel_Factory_SMR ⚙️10m_ton/yr


# Original:
# ⏩NatGas Compressor Gas    ⛽️10m ton/yr    ⚙️3k ton      📏100 km      ⛽️100k ton/yr  💰100k
# Build:
⚙️3k_ton 📏100_km 💰100k => ⏩NatGas_Compressor_Gas
# Operation:
⏩NatGas_Compressor_Gas ⛽️100k_ton/yr => ⏩NatGas_Compressor_Gas ⛽️10m_ton/yr

# Original:
# ⏩NatGas Compressor Solar  ⛽️10m ton/yr    ⚙️3k ton      📏100 km      ⚡️10 MW        💰10m
# Build:
⚙️3k_ton 📏100_km 💰10m => ⏩NatGas_Compressor_Solar
# Operation:
⏩NatGas_Compressor_Solar ⚡️10_MW/yr => ⏩NatGas_Compressor_Solar ⛽️10m_ton/yr

# Original:
# ⛽️NatGas Pipeline          ⛽️10m ton/yr    ⚙️100 ton     📏1 km        ⭕1 m          💰100k 
# Build:
⚙️100_ton 📏1_km ⭕1_m 💰100k => ⛽️NatGas_Pipeline
# Properties:
⛽️NatGas_Pipeline :> ⛽️10m_ton/yr 📏1_km ⭕1_m
# Operation:
⛽️NatGas_Pipeline ⛽️10m_ton/yr => ⛽️NatGas_Pipeline ⛽️10m_ton/yr

# Original:
# ⛽️Nullabor Interconnect    ⛽️30m ton/yr    ⚙️300k ton    📏3k km       ⭕1 m          💰1b         ⏩30
# Build:
⚙️300k_ton 📏3k_km ⭕1_m 💰1b ⏩30 => ⛽️Nullabor_Interconnect
# Properties:
⛽️Nullabor_Interconnect :>  ⛽️30m_ton/yr 📏3k_km ⭕1_m
# Operation:


# Original:
# 💨Hydrogen - Electrolysis  💨300k ton/yr   ⚙️100k ton    📐300k m2     ⚡️3 GW         💰300m
# Build:
⚙️100k_ton 📐300k_m2 💰300m => 💨Hydrogen_Electrolysis
# Operation:
💨Hydrogen_Electrolysis ⚡️3_GW/yr => 💨Hydrogen_Electrolysis 💨300k_ton/yr

# Original:
# 💨Hydrogen - NatGas SMR    💨300k ton/yr   ⚙️30k ton     📐300k m2     ⚡️3 GW         💰300m
# Build:
⚙️30k_ton 📐300k_m2 💰300m => 💨Hydrogen_NatGas_SMR
# Operation:
💨Hydrogen_NatGas_SMR ⚡️3_GW/yr => 💨Hydrogen_NatGas_SMR 💨300k_ton/yr

# Original:
# 💨Hydrogen - NatGas SMR    💨1m ton/yr     ⚙️100k ton    📐300k m2     ⚡️10 GW        💰300m
# Build:
⚙️100k_ton 📐300k_m2 💰300m => 💨Hydrogen_NatGas_SMR_Large
# Operation:
💨Hydrogen_NatGas_SMR_Large ⚡️10_GW/yr => 💨Hydrogen_NatGas_SMR_Large 💨1m_ton/yr

# Original:
# 🪢Seaweed Textile Factory  🪢1b tons/yr    ⚙️30k ton     📐1m m2       ⚡️300MW        💰300m       
# Build:
⚙️30k_ton 📐1m_m2 💰300m => 🪢Seaweed_Textile_Factory
# Operation:
🪢Seaweed_Textile_Factory ⚡️300_MW/yr => 🪢Seaweed_Textile_Factory 🪢1b_tons/yr

# Original:
# 🪢Seaweed Textile Factory  🌿3b tons/yr    💧10b tons    💧1b tons/yr
# Build:
💧10b_tons => 🪢Seaweed_Textile_Factory
# Operation:
🪢Seaweed_Textile_Factory 💧1b_tons/yr => 🪢Seaweed_Textile_Factory 🌿3b_tons/yr

# Original:
# 🪢Seaweed Dyeing          🎨10m tons/yr   🧂10m tons/yr 🧪10m tons/yr
# Operation:
🪢Seaweed_Dyeing 🧂10m_tons/yr 🧪10m_tons/yr => 🪢Seaweed_Dyeing 🎨10m_tons/yr

# Original:
# 🧪Hydrocholoric Acid Plant 🐚300m ton/yr   ⚙️1m          📐3m m2       ⚡️300GW        💰1b         ⚙️1m ton       💨10m ton/yr                                 
# Build:
⚙️1m_ton 📐3m_m2 💰1b => 🧪Hydrocholoric_Acid_Plant
# Operation:
🧪Hydrocholoric_Acid_Plant ⚡️300_GW/yr 💨10m_ton/yr => 🧪Hydrocholoric_Acid_Plant 🐚300m_ton/yr

# Original:
# 🐚Accelerant Factory CaCl  🐚300m ton/yr   ⚙️100k        📐1m m2       ⚡️300MW        💰1b         🗿3m ton       🧪300m ton/yr
# Build:
⚙️100k_ton 📐1m_m2 💰1b => 🐚Accelerant_Factory_CaCl
# Operation:
🐚Accelerant_Factory_CaCl ⚡️300_MW/yr 🗿3m_ton/yr 🧪300m_ton/yr => 🐚Accelerant_Factory_CaCl 🐚300m_ton/yr



# Original:
# 🗿Concrete Mixing Plant    🗿1m ton/yr     ⚙️30          📐300 m2      ⚡️30 KW        💰30k      
# Build:
⚙️30_ton 📐300_m2 💰30k => 🗿Concrete_Mixing_Plant
# Operation:
🗿Concrete_Mixing_Plant ⚡️30_KW/yr => 🗿Concrete_Mixing_Plant 🗿1m_ton/yr

# Original:
# 🗿Concrete GigaMixer       🗿1b ton/yr     ⚙️3k ton      📐300k m2     ⚡️30 MW        💰30m        
# Build:
⚙️3k_ton 📐300k_m2 💰30m => 🗿Concrete_GigaMixer
# Operation:
🗿Concrete_GigaMixer ⚡️30_MW/yr => 🗿Concrete_GigaMixer 🗿1b_ton/yr

# Original:
# 🗿Nullabor GigaMixer       🗿100b ton/yr   ⚙️300k ton    📐300m m2     ⚡️3 GW         💰3b         
# Build:
⚙️300k_ton 📐300m_m2 💰3b => 🗿Nullabor_GigaMixer
# Operation:
🗿Nullabor_GigaMixer ⚡️3_GW/yr => 🗿Nullabor_GigaMixer 🗿100b_ton/yr

# Original:
# 🏝️MSand Machine            🏝️10m ton/yr    ⚙️10 ton      📐100 m2      ⚡️300 kW       💰100k       
# Build:
⚙️10_ton 📐100_m2 💰100k => 🏝️MSand_Machine
# Operation:
🏝️MSand_Machine ⚡️300_kW/yr => 🏝️MSand_Machine 🏝️10m_ton/yr

# Original:
# 🏝️MSand Nullabor Machines  🏝️30b ton/yr    ⚙️30k ton     📐300k m2     ⚡️1 GW         💰300m   
# Build:
⚙️30k_ton 📐300k_m2 💰300m => 🏝️MSand_Nullabor_Machines
# Operation:
🏝️MSand_Nullabor_Machines ⚡️1_GW/yr => 🏝️MSand_Nullabor_Machines 🏝️30b_ton/yr

# Original:
# 🏭Nullabor BWE Fabs        🎡300 /yr       ⚙️3m ton/yr   📐300k m2     ⚡️30 MW        💰300m       🥉1k ton /yr   🏭10
# Build:
📐300k_m2 💰300m 🏭10 => 🏭Nullabor_BWE_Fabs
# Operation:
🏭Nullabor_BWE_Fabs ⚡️30_MW/yr ⚙️3m_ton/yr 🥉1k_ton/yr => 🏭Nullabor_BWE_Fabs 🎡300/yr

# Original:
# 🏭Nullabor Calcinator Fab  🔥10k /yr       ⚙️10m ton/yr  📐300k m2     ⚡️30 MW        💰300m
# Build:
📐300k_m2 💰300m => 🏭Nullabor_Calcinator_Fab
# Operation:
🏭Nullabor_Calcinator_Fab ⚡️30_MW/yr ⚙️10m_ton/yr => 🏭Nullabor_Calcinator_Fab 🔥10k/yr

# Original:
# 🚢Nullabor Lock            🗿100k tons     ⚙️30k tons    📏100 m       💰100m         🚢100m tons/yr 
# Build:
⚙️30k_tons 🗿100k_tons 📏100_m 💰100m => 🚢Nullabor_Lock
# Properties:
🚢Nullabor_Lock :> 🚢100m_tons/yr

# Original:
# ⛺️Nullabor BWE Kspan       📐300k m2       ⚙️30k ton     👤100         ⏰30 day       💰30m
# Build:
⚙️30k_ton 📐300k_m2 👤100 ⏰30_day 💰30m => ⛺️Nullabor_BWE_Kspan
# Properties:
⛺️Nullabor_BWE_Kspan :> 📐300k_m2

# Original:
# ⛺️Nullabor Kiln Kspan      📐10m m2/yr     ⚙️1m ton      👤300         🗓️1 yr         💰1b
# Build:
⚙️1m_ton 📐10m_m2 👤300 🗓️1_yr 💰1b => ⛺️Nullabor_Kiln_Kspan
# Properties:
⛺️Nullabor_Kiln_Kspan :> 📐10m_m2

# Original:
# 🎡Nullabor BWE             🎡300           🐚30b ton/yr  ⚙️1m ton      ⚡️1 GW         💰10b        
# Build:
⚙️1m_ton 💰10b => 🎡Nullabor_BWE
# Operation:
🎡Nullabor_BWE ⚡️1_GW/yr => 🎡Nullabor_BWE 🐚30b_ton/yr

# Original:
# 🔥Nullabor Calcinator      📐10m m2        🔥10k         ⚙️10m ton     ⚡️1 TW         💰3b
# Build:
📐10m_m2 ⚙️10m_ton 💰3b => 🔥Nullabor_Calcinator
# Operation:
🔥Nullabor_Calcinator ⚡️1_TW/yr => 🔥Nullabor_Calcinator 🔥10k/yr


# Original:
# ☢️Tsar                     📐1m m2         ☢️3 mt        💥10k/yr      ⚡️3 TW         💰1b
# Build:
📐1m_m2 💰1b => ☢️Tsar
# Operation:
☢️Tsar 💥10k/yr => ☢️Tsar ☢️3_mt ⚡️3_TW/yr 

# Original:
# 🪨Nullabor CO2 Mixer       💨30b co2/yr    🐚30b ton/yr  🏝️30b ton/yr  🗿100b ton/yr  
# Operation:
🪨Nullabor_CO2_Mixer 🐚30b_ton/yr 🏝️30b_ton/yr  💨30b_co2/yr => 🪨Nullabor_CO2_Mixer 🗿100b_ton/yr 

# Original:
# 🔥Calcinator               📐1k m2         🐚3m ton/yr   ⚙️1k ton      ⚡️30 MW        💰100k   
# Build:
📐1k_m2 ⚙️1k_ton 💰100k => 🔥Calcinator
# Operation:
🔥Calcinator ⚡️30_MW/yr => 🔥Calcinator 🐚3m_ton/yr

# Original:
# 🧪S-50 Tube                📏10 m          ⚙️.3 ton      📐1 m2        ⚡️1 KW 
# Build:
📏10_m ⚙️0.3_ton 📐1_m2 => 🧪S50_Tube
# Operation:
🧪S50_Tube ⚡️1_KW/yr => 🧪S50_Tube

# Original:
# ☢️S-50 Refinery            💥1 #/yr        🧪100         📐1k m2       ⚡️100 KW       ☢️10 kg/yr
# Build:
🧪100 📐1k_m2 => ☢️S50_Refinery
# Operation:
☢️S50_Refinery ⚡️100_KW/yr => ☢️S50_Refinery 💥1/yr ☢️10_kg/yr

# Original:
# ☢️Nullabor Refinery        💥10k #/yr      🧪1m          📐100k m2     ⚡️1 GW         💰3b
# Build:
🧪1m 📐100k_m2 💰3b => ☢️Nullabor_Refinery
# Operation:
☢️Nullabor_Refinery ⚡️1_GW/yr => ☢️Nullabor_Refinery 💥10k/yr  ☢️100k_kg/yr

# Original:
# ☢️Fizzle Fusion            ☢️300 ton
# Properties:
☢️Fizzle_Fusion :> ☢️300_ton

# Original:
# 🏀Rubber Factory           🏀100k ton/yr   ⚙️10k ton     📐100k m2     ⚡️10 MW        💰100m      ⛽10k ton/yr   💧1m ton/yr   
# Build:
⚙️10k_ton 📐100k_m2 💰100m => 🏀Rubber_Factory
# Operation:
🏀Rubber_Factory ⚡️10_MW/yr ⛽10k_ton/yr 💧1m_ton/yr => 🏀Rubber_Factory 🏀100k_ton/yr

# Original:
# ✈️Airplane                 👤100k/yr       👤300         📏10k km      ⛽30k tons/yr  💰100m      💵30m/yr
# Build:
👤300 📏10k_km 💰100m => 👤300 ✈️Airplane
# Operation:
✈️Airplane ⛽30k_tons/yr 👤100k/yr => ✈️Airplane 👤100k/yr 💵30m/yr
# Properties:
✈️Airplane :> 🏎️10k_km


# Original:
# ✈️Airplane Flight          👤300           🛬300         📏10k km      ⛽30 tons      💰30k       💵100k
# Operation:
👤300 🛬300 📏10k_km ⛽30_tons 💰30k ✈️Airplane_Flight => ✈️Airplane_Flight 💵100k 👤300 🛬300

# Original:
# ✈️Airline                  👤1m/yr         ✈️10          📐30k m2      ⛽300k tons/yr 💰1b        💵300m/yr
# Build:
✈️10 📐30k_m2 💰1b => ✈️Airline
# Operation:
✈️Airline ⛽300k_tons/yr 👤1m/yr => ✈️Airline 👤1m/yr 💵300m/yr


# Original:
# 🏗️Crane                    🏗️3 ton         ⚙️30k ton     📏100m        ⚡️30 KW        💰30k      📦300 ton/day  🔁100/day
# Build:
⚙️30k_ton 📏100m 💰30k => 🏗️Crane
# Operation:
🏗️Crane ⚡️30_KW/day => 🏗️Crane 📦300_ton/day 🔁100/day
# Properties:
🏗️Crane :> 🏗️3_ton

# Original:
# ⭕️Cylinder                 👤300           🗿10k ton     📐10k m2      ⚡️300 KW       💰300k
# Build:
🗿10k_ton 📐10k_m2 💰300k => ⭕️Cylinder
# Operation:
⭕️Cylinder ⚡️300_KW => ⭕️Cylinder 👤300/yr 
# what is this?

# Original:
# 🏬Cylinder Tower           👤3k            🗿100k ton    📐100k m2     ⚡️3 MW         💰3m       ⭕️10 
# Build:
🗿100k_ton 📐100k_m2 ⭕️10 💰3m => 🏬Cylinder_Tower
# Operation:
🏬Cylinder_Tower ⚡️3_MW => 🏬Cylinder_Tower 👤3k/yr 

# Original:
# 🅿️Parking Lot              📐1 m2          💰300
# Build:
📐1_m2 💰300 => 🅿️Parking_Lot

# Original:
# 🏬Retail                   📐1 m2          💰3k
# Build:
📐1_m2 💰3k => 🏬Retail

# Original:
# 🏬Luxury Retail            📐1 m2          💰30k
# Build:
📐1_m2 💰30k => 🏬Luxury_Retail

# Original:
# 🏬UltraLuxury Retail       📐1 m2          💰100k
# Build:
📐1_m2 💰100k => 🏬UltraLuxury_Retail

# Original:
# 🇿🇼Zimbabwe                 🥇30 tons/yr    🫘3k ton/yr
# Properties:
🇿🇼Zimbabwe :> 🥇30_tons/yr 🫘3k_ton/yr



# Original:
# 🇦🇴Angola                   👤30m           🏠10m         📐1m km2
# Properties:
🇦🇴Angola :> 👤30m 🏠10m 📐1m_km2

# Original:
# 🇿🇼Zimbabwe                 👤10m           🏠3m          📐300k km2
# Properties:
🇿🇼Zimbabwe :> 👤10m 🏠3m 📐300k_km2

# Original:
# 🇧🇼Botswana                 👤3m            🏠1m          📐300k km2
# Properties:
🇧🇼Botswana :> 👤3m 🏠1m 📐300k_km2

# Original:
# 🇺🇸USA                      👤300m          🏠100m        📐300m km2
# Properties:
🇺🇸USA :> 👤300m 🏠100m 📐300m_km2

# Original:
# 🇪🇺EU                       👤300m          🏠100m        📐3m km2
# Properties:
🇪🇺EU :> 👤300m 🏠100m 📐3m_km2

# Original:
# 🇨🇳China                    👤1b            🏠300m        📐10m km2
# Properties:
🇨🇳China :> 👤1b 🏠300m 📐10m_km2

# Original:
# 🇦🇺Australia                👤30m           🏠10m         📐10m km2
# Properties:
🇦🇺Australia :> 👤30m 🏠10m 📐10m_km2

# Original:
# 🇨🇦Canada                   👤30m           🏠10m         📐10m km2
# Properties:
🇨🇦Canada :> 👤30m 🏠10m 📐10m_km2

# Original:
# 🇮🇳India                    👤1b            🏠100m        📐3m km2
# Properties:
🇮🇳India :> 👤1b 🏠100m 📐3m_km2

# Original:
# 🇷🇺Russia                   👤100m          🏠30m         📐30m km2
# Properties:
🇷🇺Russia :> 👤100m 🏠30m 📐30m_km2

# Original:
# 🇬🇧United Kingdom           👤100m          🏠30m         📐300k km2
# Properties:
🇬🇧United_Kingdom :> 👤100m 🏠30m 📐300k_km2

# Original:
# 🇪🇬Egypt                    👤100m          🏠30m         📐1m km2
# Properties:
🇪🇬Egypt :> 👤100m 🏠30m 📐1m_km2

# Original:
# 🇸🇦Saudi Arabia             👤30m           🏠10m         📐3m km2
# Properties:
🇸🇦Saudi_Arabia :> 👤30m 🏠10m 📐3m_km2

# Original:
# 🇳🇬Nigeria                  👤300m          🏠100m        📐1m km2
# Properties:
🇳🇬Nigeria :> 👤300m 🏠100m 📐1m_km2

# Original:
# 🇵🇰Pakistan                 👤300m          🏠30m         📐1m km2
# Properties:
🇵🇰Pakistan :> 👤300m 🏠30m 📐1m_km2

# Original:
# 🇧🇩Bangladesh               👤100m          🏠30m         📐100k km2
# Properties:
🇧🇩Bangladesh :> 👤100m 🏠30m 📐100k_km2

# Original:
# 🇮🇩Indonesia                👤300m          🏠100m        📐3m km2
# Properties:
🇮🇩Indonesia :> 👤300m 🏠100m 📐3m_km2

# Original:
# 🇹🇷Turkey                   👤100m          🏠30m         📐1m km2
# Properties:
🇹🇷Turkey :> 👤100m 🏠30m 📐1m_km2

# Original:
# 🇵🇭Philippines              👤100m          🏠30m         📐300k km2
# Properties:
🇵🇭Philippines :> 👤100m 🏠30m 📐300k_km2

# Original:
# 🇻🇳Vietnam                  👤100m          🏠30m         📐300k km2
# Properties:
🇻🇳Vietnam :> 👤100m 🏠30m 📐300k_km2

# Original:
# 🇦🇷Argentina                👤30m           🏠10m         📐3m km2
# Properties:
🇦🇷Argentina :> 👤30m 🏠10m 📐3m_km2

# Original:
# 🇰🇷South Korea              👤30m           🏠30m         📐100k km2
# Properties:
🇰🇷South_Korea :> 👤30m 🏠30m 📐100k_km2

# Original:
# 🇯🇵Japan                    👤100m          🏠30m         📐300k km2
# Properties:
🇯🇵Japan :> 👤100m 🏠30m 📐300k_km2

# Original:
# 🇧🇷Brazil                   👤300m          🏠100m        📐10m km2
# Properties:
🇧🇷Brazil :> 👤300m 🏠100m 📐10m_km2

# Original:
# 🇩🇪Germany                  👤100m          🏠30m         📐300k km2
# Properties:
🇩🇪Germany :> 👤100m 🏠30m 📐300k_km2

# Original:
# 🇫🇷France                   👤100m          🏠30m         📐1m km2
# Properties:
🇫🇷France :> 👤100m 🏠30m 📐1m_km2

# Original:
# 🇮🇹Italy                    👤100m          🏠30m         📐300k km2
# Properties:
🇮🇹Italy :> 👤100m 🏠30m 📐300k_km2

# Original:
# 🇲🇽Mexico                   👤100m          🏠30m         📐3m km2
# Properties:
🇲🇽Mexico :> 👤100m 🏠30m 📐3m_km2

# Original:
# 🌍Africa                    👤1b            🏠300m        📐30m km2
# Properties:
🌍Africa :> 👤1b 🏠300m 📐30m_km2

# Original:
# 🌏Asia                      👤3b            🏠300m        📐30m km2
# Properties:
🌏Asia :> 👤3b 🏠300m 📐30m_km2

# Cities:

# Original:
# 🇯🇵Tokyo                    👤30m
# Properties:
🇯🇵Tokyo :> 👤30m

# Original:
# 🇰🇷Seoul                    👤10m
# Properties:
🇰🇷Seoul :> 👤10m

# Original:
# 🇮🇳Delhi                    👤30m
# Properties:
🇮🇳Delhi :> 👤30m

# Original:
# 🇨🇳Chongqing                👤30m
# Properties:
🇨🇳Chongqing :> 👤30m

# Original:
# 🇨🇳Shanghai                 👤30m
# Properties:
🇨🇳Shanghai :> 👤30m

# Original:
# 🇨🇳Guangzhou                👤30m
# Properties:
🇨🇳Guangzhou :> 👤30m

# Original:
# 🇨🇳Beijing                  👤30m
# Properties:
🇨🇳Beijing :> 👤30m

# Original:
# 🇨🇳Tianjin                  👤10m
# Properties:
🇨🇳Tianjin :> 👤10m

# Original:
# 🇨🇳Shenzhen                 👤10m
# Properties:
🇨🇳Shenzhen :> 👤10m

# Original:
# 🇨🇳Wuhan                    👤10m
# Properties:
🇨🇳Wuhan :> 👤10m

# Original:
# 🇨🇳Chengdu                  👤10m
# Properties:
🇨🇳Chengdu :> 👤10m

# Original:
# 🇨🇳Hangzhou                 👤10m
# Properties:
🇨🇳Hangzhou :> 👤10m

# Original:
# 🇨🇳Harbin                   👤10m
# Properties:
🇨🇳Harbin :> 👤10m

# Original:
# 🇨🇳Jinan                    👤10m
# Properties:
🇨🇳Jinan :> 👤10m

# Original:
# 🇨🇳Shenyang                 👤10m
# Properties:
🇨🇳Shenyang :> 👤10m

# Original:
# 🇨🇳Qingdao                  👤10m
# Properties:
🇨🇳Qingdao :> 👤10m

# Original:
# 🇨🇳Nanjing                  👤10m
# Properties:
🇨🇳Nanjing :> 👤10m

# Original:
# 🇨🇳Xi'an                    👤10m
# Properties:
🇨🇳Xi'an :> 👤10m

# Original:
# 🇨🇳Dalian                   👤10m
# Properties:
🇨🇳Dalian :> 👤10m

# Original:
# 🇨🇳Kunming                  👤10m
# Properties:
🇨🇳Kunming :> 👤10m

# Original:
# 🇺🇸New York                👤10m
# Properties:
🇺🇸New_York :> 👤10m

# Original:
# 🇺🇸Los Angeles             👤10m
# Properties:
🇺🇸Los_Angeles :> 👤10m

# Original:
# 🇺🇸Dallas Ft Worth         👤10m
# Properties:
🇺🇸Dallas_Ft_Worth :> 👤10m

# Original:
# 🇺🇸Chicago                 👤10m
# Properties:
🇺🇸Chicago :> 👤10m

# Original:
# 🇲🇽Mexico City             👤10m
# Properties:
🇲🇽Mexico_City :> 👤10m

# Original:
# 🇧🇷São Paulo               👤10m
# Properties:
🇧🇷São_Paulo :> 👤10m

# Original:
# 🇦🇷Buenos Aires            👤10m
# Properties:
🇦🇷Buenos_Aires :> 👤10m

# Original:
# 🇨🇱Santiago                👤10m
# Properties:
🇨🇱Santiago :> 👤10m

# Original:
# 🇬🇧London                  👤10m
# Properties:
🇬🇧London :> 👤10m

# Original:
# 🇫🇷Paris                   👤10m
# Properties:
🇫🇷Paris :> 👤10m

# Original:
# 🇷🇺Moscow                  👤10m
# Properties:
🇷🇺Moscow :> 👤10m

# Original:
# 🇪🇬Cairo                   👤10m
# Properties:
🇪🇬Cairo :> 👤10m

# Original:
# 🇯🇵Osaka                   👤10m
# Properties:
🇯🇵Osaka :> 👤10m

# Original:
# 🇹🇭Bangkok                 👤10m
# Properties:
🇹🇭Bangkok :> 👤10m

# Original:
# 🇵🇭Manila                  👤10m
# Properties:
🇵🇭Manila :> 👤10m

# Original:
# 🇮🇩Jakarta                 👤10m
# Properties:
🇮🇩Jakarta :> 👤10m

# Original:
# 🇮🇩Ho Chi Minh City        👤10m
# Properties:
🇮🇩Ho_Chi_Minh_City :> 👤10m

# Original:
# 🇮🇩Bandung                 👤10m
# Properties:
🇮🇩Bandung :> 👤10m

# Original:
# 🇮🇩Surabaya                👤10m
# Properties:
🇮🇩Surabaya :> 👤10m

# Original:
# 🇻🇳Hanoi                   👤10m
# Properties:
🇻🇳Hanoi :> 👤10m

# Original:
# 🇧🇩Dhaka                   👤10m
# Properties:
🇧🇩Dhaka :> 👤10m

# Original:
# 🇮🇳Mumbai                  👤10m
# Properties:
🇮🇳Mumbai :> 👤10m

# Original:
# 🇮🇳Bangalore               👤10m
# Properties:
🇮🇳Bangalore :> 👤10m

# Original:
# 🇮🇳Hyderabad               👤10m
# Properties:
🇮🇳Hyderabad :> 👤10m

# Original:
# 🇮🇳Chennai                 👤10m
# Properties:
🇮🇳Chennai :> 👤10m

# Original:
# 🇮🇳Surat                   👤10m
# Properties:
🇮🇳Surat :> 👤10m

# Original:
# 🇮🇳Ahmedabad               👤10m
# Properties:
🇮🇳Ahmedabad :> 👤10m

# Original:
# 🇮🇳Pune                    👤10m
# Properties:
🇮🇳Pune :> 👤10m

# Original:
# 🇮🇳Kolkata                 👤10m
# Properties:
🇮🇳Kolkata :> 👤10m

# Original:
# 🇵🇰Karachi                 👤10m
# Properties:
🇵🇰Karachi :> 👤10m

# Original:
# 🇵🇰Lahore                  👤10m
# Properties:
🇵🇰Lahore :> 👤10m

# Original:
# 🇳🇬Lagos                   👤10m
# Properties:
🇳🇬Lagos :> 👤10m

# Original:
# 🇳🇬Kano                    👤10m
# Properties:
🇳🇬Kano :> 👤10m

# Original:
# 🇨🇩Kinshasa                👤10m
# Properties:
🇨🇩Kinshasa :> 👤10m

# Original:
# 🇸🇦Riyadh                  👤10m
# Properties:
🇸🇦Riyadh :> 👤10m

# Original:
# 🇹🇷Istanbul                👤10m
# Properties:
🇹🇷Istanbul :> 👤10m

# Original:
# 🇮🇷Tehran                  👤10m
# Properties:
🇮🇷Tehran :> 👤10m

# ==============  Started preserving unicode:

# Original:
# 🇮🇷 Isfahan                 👤3m
# Properties:
🇮🇷 Isfahan :> 👤3m

# Original:
# 🇸🇦 Jeddah                  👤3m
# Properties:
🇸🇦 Jeddah :> 👤3m

# Original:
# 🇸🇦 Mecca                   👤3m
# Properties:
🇸🇦 Mecca :> 👤3m

# Original:
# 🇵🇰 Islamabad               👤3m
# Properties:
🇵🇰 Islamabad :> 👤3m

# Original:
# 🇵🇰 Faisalabad              👤3m
# Properties:
🇵🇰 Faisalabad :> 👤3m

# Original:
# 🇮🇳 Kanpur                  👤3m
# Properties:
🇮🇳 Kanpur :> 👤3m

# Original:
# 🇹🇷 Ankara                  👤3m
# Properties:
🇹🇷 Ankara :> 👤3m

# Original:
# 🇦🇺 Melbourne               👤3m
# Properties:
🇦🇺 Melbourne :> 👤3m

# Original:
# 🇦🇺 Sydney                  👤3m
# Properties:
🇦🇺 Sydney :> 👤3m

# Original:
# 🇨🇦 Toronto                 👤3m
# Properties:
🇨🇦 Toronto :> 👤3m

# Original:
# 🇩🇪 Berlin                  👤3m
# Properties:
🇩🇪 Berlin :> 👤3m

# Original:
# 🇮🇹 Rome                    👤3m
# Properties:
🇮🇹 Rome :> 👤3m

# Original:
# 🇵🇹 Porto                   👤3m
# Properties:
🇵🇹 Porto :> 👤3m

# Original:
# 🇪🇸 Madrid                  👤3m
# Properties:
🇪🇸 Madrid :> 👤3m

# Original:
# 🇿🇦 Johannesburg            👤3m
# Properties:
🇿🇦 Johannesburg :> 👤3m

# Original:
# 🇩🇰 Copenhagen              👤3m
# Properties:
🇩🇰 Copenhagen :> 👤3m

# Original:
# 🇸🇪 Stockholm               👤3m
# Properties:
🇸🇪 Stockholm :> 👤3m

# Original:
# 🇳🇴 Oslo                    👤3m
# Properties:
🇳🇴 Oslo :> 👤3m

# Original:
# 🇺🇦 Kyiv                    👤3m
# Properties:
🇺🇦 Kyiv :> 👤3m

# Original:
# 🇲🇾 Kuala Lumpur            👤3m
# Properties:
🇲🇾 Kuala_Lumpur :> 👤3m

# Original:
# 🇦🇷 Córdoba                 👤3m
# Properties:
🇦🇷 Córdoba :> 👤3m

# Original:
# 🇨🇴 Bogotá                  👤3m
# Properties:
🇨🇴 Bogotá :> 👤3m

# Original:
# 🇨🇮 Abidjan                 👤3m
# Properties:
🇨🇮 Abidjan :> 👤3m

# Original:
# 🇨🇲 Douala                  👤3m
# Properties:
🇨🇲 Douala :> 👤3m

# Original:
# 🇵🇪 Lima                    👤3m
# Properties:
🇵🇪 Lima :> 👤3m


# Original:
# 🇵🇱 Warsaw                  👤3m
# Properties:
🇵🇱 Warsaw :> 👤3m

# Original:
# 🇳🇱 Amsterdam               👤3m
# Properties:
🇳🇱 Amsterdam :> 👤3m

# Original:
# 🇧🇪 Brussels                👤3m
# Properties:
🇧🇪 Brussels :> 👤3m

# Original:
# 🇧🇬 Sofia                   👤3m
# Properties:
🇧🇬 Sofia :> 👤3m

# Original:
# 🇳🇿 Auckland                👤3m
# Properties:
🇳🇿 Auckland :> 👤3m

# Original:
# 🇷🇴 Bucharest               👤3m
# Properties:
🇷🇴 Bucharest :> 👤3m

# Original:
# 🇷🇸 Belgrade                👤3m
# Properties:
🇷🇸 Belgrade :> 👤3m

# Original:
# 🇯🇴 Amman                   👤3m
# Properties:
🇯🇴 Amman :> 👤3m

# Original:
# 🇦🇿 Baku                    👤3m
# Properties:
🇦🇿 Baku :> 👤3m

# Original:
# 🇭🇺 Budapest                👤3m
# Properties:
🇭🇺 Budapest :> 👤3m

# Original:
# 🇱🇧 Beirut                  👤3m
# Properties:
🇱🇧 Beirut :> 👤3m

# Original:
# 🇬🇷 Athens                  👤3m
# Properties:
🇬🇷 Athens :> 👤3m

# Original:
# 🇮🇶 Baghdad                 👤3m
# Properties:
🇮🇶 Baghdad :> 👤3m

# Original:
# 🇩🇿 Algiers                 👤3m
# Properties:
🇩🇿 Algiers :> 👤3m

# Original:
# 🇲🇦 Casablanca              👤3m
# Properties:
🇲🇦 Casablanca :> 👤3m

# Original:
# 🇻🇪 Caracas                 👤3m
# Properties:
🇻🇪 Caracas :> 👤3m

# Original:
# 🇰🇪 Nairobi                 👤3m
# Properties:
🇰🇪 Nairobi :> 👤3m

# Original:
# 🇹🇳 Tunis                   👤3m
# Properties:
🇹🇳 Tunis :> 👤3m

# Original:
# 🇮🇪 Dublin                  👤3m
# Properties:
🇮🇪 Dublin :> 👤3m

# Original:
# 🇺🇬 Kampala                 👤3m
# Properties:
🇺🇬 Kampala :> 👤3m

# Original:
# 🇲🇿 Maputo                  👤3m
# Properties:
🇲🇿 Maputo :> 👤3m

# Original:
# 🇱🇾 Tripoli                 👤3m
# Properties:
🇱🇾 Tripoli :> 👤3m

# Original:
# 🇲🇬 Antananarivo            👤3m
# Properties:
🇲🇬 Antananarivo :> 👤3m

# Original:
# 🇿🇼 Harare                  👤3m
# Properties:
🇿🇼 Harare :> 👤3m

# Original:
# 🇿🇲 Lusaka                  👤3m
# Properties:
🇿🇲 Lusaka :> 👤3m

# Original:
# 🇹🇿 Dar es Salaam           👤3m
# Properties:
🇹🇿 Dar_es_Salaam :> 👤3m

# Original:
# 🇸🇩 Khartoum                👤3m
# Properties:
🇸🇩 Khartoum :> 👤3m

# Original:
# 🇦🇴 Luanda                  👤3m
# Properties:
🇦🇴 Luanda :> 👤3m

# Original:
# 🇪🇹 Addis Ababa             👤3m
# Properties:
🇪🇹 Addis_Ababa :> 👤3m

# Original:
# 🇲🇲 Yangon                  👤3m
# Properties:
🇲🇲 Yangon :> 👤3m

# Original:
# 🇺🇿 Tashkent                👤3m
# Properties:
🇺🇿 Tashkent :> 👤3m

# Original:
# 🇰🇷 Busan                   👤3m
# Properties:
🇰🇷 Busan :> 👤3m

# Original:
# 🇹🇼 Taipei                  👤3m
# Properties:
🇹🇼 Taipei :> 👤3m

# TODO ===========


# Original:
# 🇰🇿 Almaty                  👤3m
# Properties:
🇰🇿 Almaty :> 👤3m

# Original:
# 🇦🇫 Kabul                   👤3m
# Properties:
🇦🇫 Kabul :> 👤3m

# Original:
# 🇾🇪 Sana'a                  👤3m
# Properties:
🇾🇪 Sana'a :> 👤3m

# Original:
# 🇱🇰 Colombo                 👤3m
# Properties:
🇱🇰 Colombo :> 👤3m

# Original:
# 🇳🇵 Kathmandu               👤3m
# Properties:
🇳🇵 Kathmandu :> 👤3m

# Original:
# 🇧🇩 Chittagong              👤3m
# Properties:
🇧🇩 Chittagong :> 👤3m

# Original:
# 🇫🇮 Helsinki                👤3m
# Properties:
🇫🇮 Helsinki :> 👤3m

# Original:
# 🇧🇼 Gaborone                👤1m
# Properties:
🇧🇼 Gaborone :> 👤1m

# Population Categories:
# Original:
# 👤person                   👤1 pop     
# Properties:
👤person :> 👤1_pop

# Original:
# 🏠neighborhood             👤10 pop 
# Properties:
🏠neighborhood :> 👤10_pop

# Original:
# 🏡suburb                   👤100 pop 
# Properties:
🏡suburb :> 👤100_pop

# Original:
# 🛖village                  👤1k pop 
# Properties:
🛖village :> 👤1k_pop

# Original:
# 🏘️town                     👤10k pop      🏙️100k
# Properties:
🏘️town :> 👤10k_pop 🏙️100k

# Original:
# 🌆small city               👤100k pop     🏙️3k
# Properties:
🌆small_city :> 👤100k_pop 🏙️3k

# Original:
# 🌇big city                 👤1m pop       🏙️1k
# Properties:
🌇big_city :> 👤1m_pop 🏙️1k

# Original:
# 🏙️metropolis               👤10m pop      🏙️100
# Properties:
🏙️metropolis :> 👤10m_pop 🏙️100

# Original:
# 🌁mega city                👤30m pop      🏙️10
# Properties:
🌁mega_city :> 👤30m_pop 🏙️10

# Original:
# 🌎earth                    👤10b pop      
# Properties:
🌎earth :> 👤10b_pop

# Population Density Categories:
# Original:
# 💺seat                     📐.3 m2      👤1
# Properties:
💺seat :> 📐0.3_m2 👤1

# Original:
# 🛏️bunk                     📐1 m2       👤1
# Properties:
🛏️bunk :> 📐1_m2 👤1

# Original:
# 🛏️bed                      📐3 m2       👤1
# Properties:
🛏️bed :> 📐3_m2 👤1

# Original:
# 🛋️room                     📐10 m2      👤1 
# Properties:
🛋️room :> 📐10_m2 👤1

# Original:
# 🛋️apartment                📐30 m2      👤1      
# Properties:
🛋️apartment :> 📐30_m2 👤1

# Original:
# 🏠house                    📐100 m2     👤1 
# Properties:
🏠house :> 📐100_m2 👤1


# Original:
# 🏡mansion                  📐300 m2     👤1   
# Properties:
🏡mansion :> 📐300_m2 👤1

# Original:
# 🏯estate                   📐1k m2      👤1
# Properties:
🏯estate :> 📐1k_m2 👤1

# Original:
# 🏰palace                   📐1k m2      👤1
# Properties:
🏰palace :> 📐1k_m2 👤1

# Economic Classifications:
# Original:
# 🏚️poverty                  💵10k        👤1
# Properties:
🏚️poverty :> 💵10k 👤1

# Original:
# 🏠working                  💵30k        👤1
# Properties:
🏠working :> 💵30k 👤1

# Original:
# 🏡middle                   💵100k       👤1
# Properties:
🏡middle :> 💵100k 👤1

# Original:
# 🏯upper                    💵300k       👤1
# Properties:
🏯upper :> 💵300k 👤1

# Original:
# 🥂elite                    💵1m         👤1
# Properties:
🥂elite :> 💵1m 👤1

# Global Economy:
# Original:
# 💵Global GDP               💵100t   
# Properties:
💵Global_GDP :> 💵100t

# Original:
# 💰Global Assets            💰300t
# Properties:
💰Global_Assets :> 💰300t

# Brand Values:
# Original:
# 🎀Hello Kitty              💰100b 
# Properties:
🎀Hello_Kitty :> 💰100b

# Original:
# 🐢Teenage Mutant Ninja T   💰10b
# Properties:
🐢Teenage_Mutant_Ninja_T :> 💰10b

# Global Geography:
# Original:
# 🌎Earth                    👤10b pop       🏠300m        📐100m km2    ⚡️️e20 j/yr
# Properties:
🌎Earth :> 👤10b_pop 🏠300m 📐100m_km2 ⚡️️e20_j/yr

# Original:
# 🌊Ocean                    📐300m km2
# Properties:
🌊Ocean :> 📐300m_km2

# Original:
# 🏔️Mountain                 📐30m km2
# Properties:
🏔️Mountain :> 📐30m_km2

# Original:
# 🏜️Desert                   📐30m km2
# Properties:
🏜️Desert :> 📐30m_km2

# Original:
# ❄️Polar                    📐30m km2
# Properties:
❄️Polar :> 📐30m_km2

# Original:
# ❄️Siberia                  📐10m km2
# Properties:
❄️Siberia :> 📐10m_km2

# Original:
# ❄️Antarctica               📐10m km2
# Properties:
❄️Antarctica :> 📐10m_km2

# Major Deserts:
# Original:
# 🏜️Outback                  📐10m km2
# Properties:
🏜️Outback :> 📐10m_km2

# Original:
# 🏜️Sahara                   📐10m km2 
# Properties:
🏜️Sahara :> 📐10m_km2

# Original:
# 🏜️Kalahari                 📐1m km2     
# Properties:
🏜️Kalahari :> 📐1m_km2

# Original:
# 🏜️Nullabor                 📐300k km2    
# Properties:
🏜️Nullabor :> 📐300k_km2


# Original:
# 🌊Ocean Crossing           📏10k km
# Properties:
🌊Ocean_Crossing :> 📏10k_km

# Original:
# 🌐Equator                  📏30k km
# Properties:
🌐Equator :> 📏30k_km

# Original:
# ⚡️Power                    ⚡️1 kw          ⚡️1 hp        ⚡️3k j/sec
# Properties:
⚡️Power :> ⚡️1_kw ⚡️1_hp ⚡️3k_j/sec

# Energy Systems:
# Original:
# ⚡️nuke                     ⚡️E16j          ☢️3 mt 
# Properties:
⚡️nuke :> ⚡️E16j ☢️3_mt

# Original:
# ⚡️tsar nuke                ⚡️E17j          ☢️100 mt
# Properties:
⚡️tsar_nuke :> ⚡️E17j ☢️100_mt

# Original:
# ⚡️tsar nuke                ⚡️E21j/yr       ☢️100 mt      ☢️10k/yr
# Properties:
⚡️tsar_nuke :> ⚡️E21j/yr ☢️100_mt ☢️10k/yr

# Original:
# 🌎Humanity Earth           ⚡️E20j/yr
# Properties:
🌎Humanity_Earth :> ⚡️E20j/yr

# Original:
# 🇺🇸usa                      ⚡️E19j/yr
# Properties:
🇺🇸usa :> ⚡️E19j/yr

# Materials Energy:
# Original:
# 🪵biomass                  ⚡️E9j           🪵1 ton
# Properties:
🪵biomass :> ⚡️E9j 🪵1_ton

# Original:
# ⚙️steel                    ⚡️E10j          ⚙️1 ton
# Properties:
⚙️steel :> ⚡️E10j ⚙️1_ton

# Original:
# 🗑️aluminum                 ⚡️E11j          🗑️1 ton
# Properties:
🗑️aluminum :> ⚡️E11j 🗑️1_ton

# Original:
# 📲cvd silicon              ⚡️E12j          📲1 ton
# Properties:
📲cvd_silicon :> ⚡️E12j 📲1_ton

# Astro Civilizations:
# Original:
# ⚡️k0 civ                   ⚡️E10j/yr       👤1 pop
# Properties:
⚡️k0_civ :> ⚡️E10j/yr 👤1_pop

# Original:
# ⚡️k1 civ                   ⚡️E20j/yr       👤10b pop
# Properties:
⚡️k1_civ :> ⚡️E20j/yr 👤10b_pop

# Original:
# ⚡️k2 civ                   ⚡️E30j/yr       👤100bb pop
# Properties:
⚡️k2_civ :> ⚡️E30j/yr 👤100bb_pop

# Original:
# ⚡️k3 civ                   ⚡️E40j/yr       👤1tbb pop
# Properties:
⚡️k3_civ :> ⚡️E40j/yr 👤1tbb_pop

# Original:
# ⚡️k4 civ                   ⚡️E50j/yr       👤10tbbb pop
# Properties:
⚡️k4_civ :> ⚡️E50j/yr 👤10tbbb_pop

# Orbital Systems:
# Original:
# 💫Orbit - GEO              ⌚️300 ms        📏30k km      💾10 MBit/s   🏎️3k  m/s     💫300/yr  
# Properties:
💫Orbit_GEO :> ⌚️300_ms 📏30k_km 💾10_MBit/s 🏎️3k_m/s 💫300/yr

# Original:
# 💫Orbit - LEO              ⌚️30 ms         📏1k km       💾1 GBit/s    🏎️10k m/s     💫3k/yr  
# Properties:
💫Orbit_LEO :> ⌚️30_ms 📏1k_km 💾1_GBit/s 🏎️10k_m/s 💫3k/yr

# Original:
# 💫Orbit - MEO              ⌚️100 ms        📏10k km      💾100 MBit/s  🏎️3k m/s      💫1k/yr  
# Properties:
💫Orbit_MEO :> ⌚️100_ms 📏10k_km 💾100_MBit/s 🏎️3k_m/s 💫1k/yr

# Original:
# 💫Orbit - SSO              ⌚️30 ms         📏1k km       💾1 GBit/s    🏎️10k m/s     💫3k/yr
# Properties:
💫Orbit_SSO :> ⌚️30_ms 📏1k_km 💾1_GBit/s 🏎️10k_m/s 💫3k/yr

# Original:
# 🌈Fiber Optic              ⌚️100 ms        📏10k km      💾1 TBit/s
# Properties:
🌈Fiber_Optic :> ⌚️100_ms 📏10k_km 💾1_TBit/s

# Original:
# 🌈Fiber Optic              ⌚️10 ms         📏1k km       💾100 GBit/s
# Properties:
🌈Fiber_Optic :> ⌚️10_ms 📏1k_km 💾100_GBit/s

# Original:
# 📡Microwave Link           ⌚️3 ms          📏30 km       💾1 GBit/s
# Properties:
📡Microwave_Link :> ⌚️3_ms 📏30_km 💾1_GBit/s

# Original:
# 🗼4G Cell                  ⌚️10 ms         📏30 km       💾100 MBit/s   📐3k km2
# Properties:
🗼4G_Cell :> ⌚️10_ms 📏30_km 💾100_MBit/s 📐3k_km2

# Original:
# 🗼5G Cell                  ⌚️10 ms         📏10 km       💾100 MBit/s   📐300 km2
# Properties:
🗼5G_Cell :> ⌚️10_ms 📏10_km 💾100_MBit/s 📐300_km2

# Original:
# 🗼5G Cell - High speed     ⌚️10 ms         📏1 km        💾1 GBit/s     📐3 km2
# Properties:
🗼5G_Cell_High_speed :> ⌚️10_ms 📏1_km 💾1_GBit/s 📐3_km2

# Original:
# 🛜Wifi                     ⌚️10 ms         📏100 m       💾1 GBit/s     📐.03 km2
# Properties:
🛜Wifi :> ⌚️10_ms 📏100_m 💾1_GBit/s 📐.03_km2

# Original:
# 🔌Ethernet LAN             ⌚️1 ms          📏100 m       💾10 GBit/s
# Properties:
🔌Ethernet_LAN :> ⌚️1_ms 📏100_m 💾10_GBit/s

# Original:
# 🔌Ethernet LAN - Advanced  ⌚️1 ms          📏100 m       💾100 GBit/s
# Properties:
🔌Ethernet_LAN_Advanced :> ⌚️1_ms 📏100_m 💾100_GBit/s

# Original:
# ☁️Personal Cloud           ⚡️30 w          👤1           💾1 TB         📐.03 m2     💰30          🧠.03
# Properties:
☁️Personal_Cloud :> 👤1 💾1_TB 📐.03_m2 🧠.03
# Build:
💰30 📐.03_m2 => ☁️Personal_Cloud
# Operation:
☁️Personal_Cloud ⚡️30_w => ☁️Personal_Cloud 💾1_TB 🧠.03

# Original:
# 💾Data Center - Rack       ⚡️1 kw          🥑1           💾10 TB        📐1 m2       💰30k 
# Properties:
💾Data_Center_Rack :> 💾10_TB 📐1_m2
# Build:
💰30k 📐1_m2 🥑1 => 💾Data_Center_Rack
# Operation:
💾Data_Center_Rack ⚡️1_kw => 💾Data_Center_Rack 💾10_TB

# Original:
# 💾Data Center              ⚡️10 mw         👤1m          💾1m TB        📐10k m2     💰30m         
# Properties:
💾Data_Center :> 👤1m 💾1m_TB 📐10k_m2
# Build:
💰30m 📐10k_m2 => 💾Data_Center
# Operation:
💾Data_Center ⚡️10_mw => 💾Data_Center 💾1m_TB

# Original:
# 💾Data Center - National   ⚡️300 mw        👤30m         💾30m TB       📐300k m2    💰1b
# Properties:
💾Data_Center_National :> 👤30m 💾30m_TB 📐300k_m2
# Build:
💰1b 📐300k_m2 => 💾Data_Center_National
# Operation:
💾Data_Center_National ⚡️300_mw => 💾Data_Center_National 💾30m_TB

# Original:
# 💾Data Center - AI         ⚡️300 mw        🥑1m          💾10m TB       📐300k m2    💰1b          🧠100/yr
# Properties:
💾Data_Center_AI :> 💾10m_TB 📐300k_m2 🧠100/yr
# Build:
💰1b 📐300k_m2 🥑1m => 💾Data_Center_AI
# Operation:
💾Data_Center_AI ⚡️300_mw => 💾Data_Center_AI 💾10m_TB 🧠100/yr

# Original:
# 🧠AI                       ⚡️3 mw          🥑10k         💾100 TB       📐3k m2      💰10m
# Build:
💰10m 📐3k_m2 ⚡️3_mw 💾100_TB 🥑10k => 🧠AI

# Original:
# 🥑GPU                      ⚡️300 w         🥑1           💾.1 TB        📐.3 m2      💰1k          🧠1           📲100         👤30
# Properties:
🥑GPU :> 🥑1 💾.1_TB 📐.3_m2 🧠1 📲100 👤30
# Build:
💰1k 📐.3_m2 📲100 👤30 => 👤30 🥑GPU
# Operation:
🥑GPU ⚡️300_w => 🥑GPU 💾.1_TB 🧠1

# Original:
# 🏥Hospital                 👤1m            🛏️300         🩺100          📐30k m2     💰100m
# Build:
💰100m 📐30k_m2 => 🏥Hospital
# Properties:
🏥Hospital :> 👤1m 📐30k_m2
# Operation:
🏥Hospital 🩺100 => 🏥Hospital 🩺100 🛏️300

# Original:
# 🏥Clinic                   👤30k           🛏️10          🩺10           📐1k m2      💰3m
# Properties:
🏥Clinic :> 👤30k 📐1k_m2
# Build:
💰3m 📐1k_m2 => 🏥Clinic
# Operation:
🏥Clinic 🩺10 => 🏥Clinic 🩺10 🛏️10

# Original:
# 🏥AI Clinics               👤30k           🛏️3           🩺1            📐100 m2     💰300k        🧠1           📱100
# Properties:
🏥AI_Clinics :> 👤30k 📐100_m2
# Build:
💰300k 📐100_m2 📱100 => 🏥AI_Clinics
# Operation:
🏥AI_Clinics 🧠1 🩺1 => 🏥AI_Clinics 🧠1 🩺1 🛏️3 

# Original:
# 📚AI School                👤3k            🎓300         🍎3            📐1k m2      💰100k        🧠1           📱100
# Properties:
📚AI_School :> 👤3k 📐1k_m2
# Build:
💰100k 📐1k_m2 📱100 => 📚AI_School
# Operation:
📚AI_School 👤300 🧠1 🍎3 => 📚AI_School 🧠1 🍎3 🎓300 

# Original:
# 🏫School                   👤3k            🎓300         🍎10           📐1k m2      💰3m
# Properties:
🏫School :> 👤3k 📐1k_m2
# Build:
💰3m 📐1k_m2 => 🏫School
# Operation:
🏫School 🍎10 👤300 => 🏫School 🍎10 🎓300 

# Original:
# 🎭AI Culture Center        👤30k           🎭1k          🎨100          📐3k m2      💰30k         🧠1           📱100
# Properties:
🎭AI_Culture_Center :> 👤30k 📐3k_m2
# Build:
💰30k 📐3k_m2 📱100 => 🎭AI_Culture_Center
# Operation:
🎭AI_Culture_Center 🧠1 🎨100  => 🎭AI_Culture_Center 🧠1 🎭1k 🎨100

# Original:
# 🎭Culture Center           👤30k           🎭1k          🎨100          📐3k m2      💰3m    
# Properties:
🎭Culture_Center :> 👤30k 📐3k_m2
# Build:
💰3m 📐3k_m2 => 🎭Culture_Center
# Operation:
🎭Culture_Center 🎨100 => 🎭Culture_Center 🎨100 🎭1k


# Original:
# 🎭Culture Center - National👤1m            🎭30k         🎨3k           📐100k m2    💰100m
# Properties:
🎭Culture_Center_National :> 👤1m 📐100k_m2
# Build:
💰100m 📐100k_m2 => 🎭Culture_Center_National
# Operation:
🎭Culture_Center_National 🎨3k => 🎭Culture_Center_National 🎭30k 🎨3k

# Original:
# 📰Journalism School        📰10            🎓1k          🍎10           📐10k m2     💰3m          🧠10          📱1k
# Properties:
📰Journalism_School :> 📰10 📐10k_m2 
# Build:
💰3m 📐10k_m2 📱1k => 📰Journalism_School
# Operation:
📰Journalism_School 🧠10 📰10 🍎10 👤1k => 📰Journalism_School 🧠10 📰10  🍎10 🎓1k


# Original:
# 🚀Orion - Super            📦10m ton       ☢️1k          ⭕300 m
# Properties:
🚀Orion_Super :> 📦10m_ton ⭕300_m ☢️100_mt
# Operation:
🚀Orion_Super ☢️1k => 🚀Orion_Super 📦10m_ton

# Original:
# 🚀Orion - Earth to L5      📦3b ton/yr     ☢️3k/yr       ☢️100 mt       🔁300/yr
# Properties:
🚀Orion_Earth_to_L5 :> 🔁300/yr ☢️100_mt
# Operation:
🚀Orion_Earth_to_L5 ☢️3k/yr => 🚀Orion_Earth_to_L5 📦3b_ton/yr

# Original:
# 🚀Orion - Cylinders        📦100m m3       ⭕1k            
# Properties:
🚀Orion_Cylinders :> 📦100m_m3 ⭕1k

# Original:
# 🌾Farm - Earth             🌞1 kw          ⚡️1 kw        📐1 m2
# Build:
📐1_m2 => 🌾Farm_Earth
# Operation:
🌾Farm_Earth 🌞1_kw => 🌾Farm_Earth
🌾Farm_Earth ⚡️1_kw => 🌾Farm_Earth
# ?? takes either sun or electricity (grow lights?)?

# Original:
# 🌾Farm - Space             🌞3 kw          ⚡️3 kw        📐1 m2
# Build:
📐1_m2 => 🌾Farm_Space
# Operation:
🌾Farm_Space 🌞3_kw => 🌾Farm_Space
🌾Farm_Space ⚡️3_kw => 🌾Farm_Space
# ?? takes either sun or electricity (grow lights?)?

# Original:
# 🌾Farm - Plant Efficiency  🌞1 kw          ⚡️10 w        📐1 m2
# Build:
📐1_m2 => 🌾Farm_Plant_Efficiency
# Operation:
🌾Farm_Plant_Efficiency 🌞1_kw => 🌾Farm_Plant_Efficiency
🌾Farm_Plant_Efficiency ⚡️10_w => 🌾Farm_Plant_Efficiency
# ?? takes either sun or electricity (grow lights?)?


# Original:
# 🛰️L5 Farm                  📐300b m2       
# Properties:
🛰️L5_Farm :> 📐300b_m2

# Original:
# 🛰️L5 Farm - Construction   ⚙️10b ton       💧10b ton     💩30b ton     🪞10b ton     💰10t        💨10b ton     🚀30         
# Build:
💰10t ⚙️10b_ton 💧10b_ton 💩30b_ton 🪞10b_ton 💨10b_ton 🚀30 => 🛰️L5_Farm_Construction

# Original:
# 🛰️L5 Farm - Operation      👤10b           🥔10b ton/yr  📦10b ton/yr  🚀3
🛰️L5_Farm :> 👤10b 
# Operation:
🛰️L5_Farm 📦10b_ton/yr 🚀3 => 🛰️L5_Farm 📦10b_ton/yr 🥔10b_ton/yr 


# Original:
# 🪨Ore                      ⚒️1%            ⚖️3 ton/m3    🪨1 ton
# Properties:
🪨Ore :> ⚒️1% ⚖️3_ton/m3 🪨1_ton

# Original:
# 🪨Iron Ore                 ⚒️30%           💰100         🪨1 ton
# Properties:
🪨Iron_Ore :> ⚒️30% ⚖️3_ton/m3 💰100 🪨1_ton

# Original:
# 🪨Copper Ore               ⚒️1%            💰10k         🪨1 ton
# Properties:
🪨Copper_Ore :> ⚒️1% ⚖️3_ton/m3 💰10k 🪨1_ton

# Original:
# 🪨Gold Ore                 ⚒️0.001%        💰30k         🪨1 ton
# Properties:
🪨Gold_Ore :> ⚒️0.001% ⚖️3_ton/m3 💰30k 🪨1_ton

# Original:
# 🪨Silver Ore               ⚒️0.1%          💰1k          🪨1 ton
# Properties:
🪨Silver_Ore :> ⚒️0.1% ⚖️3_ton/m3 💰1k 🪨1_ton

# Original:
# 🪨Bauxite                  ⚒️30%           💰30          🪨1 ton
# Properties:
🪨Bauxite :> ⚒️30% ⚖️3_ton/m3 💰30 🪨1_ton

# Original:
# 🪨Nickel Ore               ⚒️1%            💰10k         🪨1 ton
# Properties:
🪨Nickel_Ore :> ⚒️1% ⚖️3_ton/m3 💰10k 🪨1_ton

# Original:
# 🪨Zinc Ore                 ⚒️10%           💰3k          🪨1 ton
# Properties:
🪨Zinc_Ore :> ⚒️10% ⚖️3_ton/m3 💰3k 🪨1_ton

# Original:
# 🪨Lead Ore                 ⚒️3%            💰3k          🪨1 ton
# Properties:
🪨Lead_Ore :> ⚒️3% ⚖️3_ton/m3 💰3k 🪨1_ton

# Original:
# 🪨Tin Ore                  ⚒️1%            💰10k         🪨1 ton
# Properties:
🪨Tin_Ore :> ⚒️1% ⚖️3_ton/m3 💰10k 🪨1_ton

# Original:
# 🪨Uranium Ore              ⚒️0.1%          💰100k        🪨1 ton
# Properties:
🪨Uranium_Ore :> ⚒️0.1% ⚖️3_ton/m3 💰100k 🪨1_ton

# Original:
# 🪨Platinum Ore             ⚒️0.001%        💰30k         🪨1 ton
# Properties:
🪨Platinum_Ore :> ⚒️0.001% 💰30k 🪨1_ton

# Original:
# 🪨Cobalt Ore               ⚒️0.3%          💰30k         🪨1 ton
# Properties:
🪨Cobalt_Ore :> ⚒️0.3% 💰30k 🪨1_ton

# Original:
# 🪨Lithium Ore              ⚒️1%            💰10k         🪨1 ton
# Properties:
🪨Lithium_Ore :> ⚒️1% 💰10k 🪨1_ton

# Original:
# 🪨Rare Earths              ⚒️0.1%          💰30k         🪨1 ton
# Properties:
🪨Rare_Earths :> ⚒️0.1% 💰30k 🪨1_ton

# Original:
# 🪨Manganese Ore            ⚒️20%           💰100         🪨1 ton
# Properties:
🪨Manganese_Ore :> ⚒️20% 💰100 🪨1_ton

# Original:
# 🪨Chromite Ore             ⚒️30%           💰100         🪨1 ton
# Properties:
🪨Chromite_Ore :> ⚒️30% 💰100 🪨1_ton

# Original:
# 🪨Tungsten Ore             ⚒️1%            💰30k         🪨1 ton
# Properties:
🪨Tungsten_Ore :> ⚒️1% 💰30k 🪨1_ton

# Original:
# 🪨Molybdenum Ore           ⚒️1%            💰30k         🪨1 ton
# Properties:
🪨Molybdenum_Ore :> ⚒️1% 💰30k 🪨1_ton

# Original:
# 🪨Phospherite Ore          ⚒️30%           💰30          🪨1 ton
# Properties:
🪨Phospherite_Ore :> ⚒️30% 💰30 🪨1_ton

# Original:
# 🪨Potassium Ore            ⚒️30%           💰300         🪨1 ton
# Properties:
🪨Potassium_Ore :> ⚒️30% 💰300 🪨1_ton

# Original:
# 🪨Neodymium Ore            ⚒️1%            💰3k          🪨1 ton
# Properties:
🪨Neodymium_Ore :> ⚒️1% 💰3k 🪨1_ton

# Original:
# 💧Water                    ⚖️1 ton/m3      💰1           🪨1 ton
# Properties:
💧Water :> ⚖️1_ton/m3 💰1 🪨1_ton

# Original:
# 💧Water - Bottled          ⚖️1 ton/m3      💰1k          🪨1 ton
# Properties:
💧Water_Bottled :> ⚖️1_ton/m3 💰1k 🪨1_ton

# Original:
# 💧Bottled - Desal          ⚖️1 ton/m3      💰3           🪨1 ton
# Properties:
💧Bottled_Desal :> ⚖️1_ton/m3 💰3 🪨1_ton


# Original:
# 🛢️Oil - Crude              ⚖️1 ton/m3      💰300         🪨1 ton      🛢️10 bbl
# Properties:
🛢️Oil_Crude :> ⚖️1_ton/m3 💰300 🪨1_ton 🛢️10_bbl

# Original:
# 🛢️Oil - Bunker             ⚖️1 ton/m3      💰300         🪨1 ton
# Properties:
🛢️Oil_Bunker :> ⚖️1_ton/m3 💰300 🪨1_ton

# Original:
# 🛢️Gasoline                 ⚖️1 ton/m3      💰1k          🪨1 ton
# Properties:
🛢️Gasoline :> ⚖️1_ton/m3 💰1k 🪨1_ton

# Original:
# ⛽️BioFuel                  ⚖️1 ton/m3      💰1k          🪨1 ton 
# Properties:
⛽️BioFuel :> ⚖️1_ton/m3 💰1k 🪨1_ton

# Original:
# ⛽️Fuel                     ⚖️1 ton/m3      💰1k          🪨1 ton 
# Properties:
⛽️Fuel :> ⚖️1_ton/m3 💰1k 🪨1_ton

# Original:
# ⛽️Rocket Fuel              ⚖️1 ton/m3      💰1k          🪨1 ton 
# Properties:
⛽️Rocket_Fuel :> ⚖️1_ton/m3 💰1k 🪨1_ton

# Original:
# ⛽️NatGas                   ⚖️.1 ton/m3     💰300         🪨1 ton      🔥10 mwh
# Properties:
⛽️NatGas :> ⚖️.1_ton/m3 💰300 🪨1_ton 🔥10_mwh

# Original:
# ⛽️LNG                      ⚖️.3 ton/m3     💰300         🪨1 ton      🔥10 mwh
# Properties:
⛽️LNG :> ⚖️.3_ton/m3 💰300 🪨1_ton 🔥10_mwh

# Original:
# ⚫️Tar                      ⚖️1 ton/m3      💰1k          🪨1 ton
# Properties:
⚫️Tar :> ⚖️1_ton/m3 💰1k 🪨1_ton

# Original:
# ♻️Polymer                  ⚖️1 ton/m3      💰1k          🪨1 ton
# Properties:
♻️Polymer :> ⚖️1_ton/m3 💰1k 🪨1_ton

# Original:
# 🏀Rubber                   ⚖️1 ton/m3      💰1k          🪨1 ton
# Properties:
🏀Rubber :> ⚖️1_ton/m3 💰1k 🪨1_ton

# Original:
# 🧲Magnet                   ⚖️10 ton/m3     💰100k        🪨1 ton
# Properties:
🧲Magnet :> ⚖️10_ton/m3 💰100k 🪨1_ton

# Original:
# 📦Cardboard                ⚖️1 ton/m3      💰100         🪨1 ton
# Properties:
📦Cardboard :> ⚖️1_ton/m3 💰100 🪨1_ton

# Original:
# 🌿Kelp                     ⚖️1 ton/m3      💰30          🪨1 ton
# Properties:
🌿Kelp :> ⚖️1_ton/m3 💰30 🪨1_ton

# Original:
# 🪵Biomass                  ⚖️1 ton/m3      💰30          🪨1 ton      🔥1 mwh
# Properties:
🪵Biomass :> ⚖️1_ton/m3 💰30 🪨1_ton 🔥1_mwh

# Original:
# 🪵Fuelwood                 ⚖️1 ton/m3      💰30          🪨1 ton      🔥1 mwh
# Properties:
🪵Fuelwood :> ⚖️1_ton/m3 💰30 🪨1_ton 🔥1_mwh

# Original:
# 🪵Wood - Softwood          ⚖️1 ton/m3      💰100         🪨1 ton
# Properties:
🪵Wood_Softwood :> ⚖️1_ton/m3 💰100 🪨1_ton

# Original:
# 🪵Wood - Hardwood          ⚖️1 ton/m3      💰300         🪨1 ton
# Properties:
🪵Wood_Hardwood :> ⚖️1_ton/m3 💰300 🪨1_ton

# Original:
# 🎋Wood - Bamboo            ⚖️1 ton/m3      💰100         🪨1 ton
# Properties:
🎋Wood_Bamboo :> ⚖️1_ton/m3 💰100 🪨1_ton

# Original:
# 🧱Bricks                   ⚖️3 ton/m3      💰100         🪨1 ton      #️⃣300
# Properties:
🧱Bricks :> ⚖️3_ton/m3 💰100 🪨1_ton #️⃣300

# Original:
# 🐚Limestone                ⚖️1 ton/m3      💰30          🪨1 ton
# Properties:
🐚Limestone :> ⚖️1_ton/m3 💰30 🪨1_ton

# Original:
# 🪨Gravel                   ⚖️3 ton/m3      💰30          🪨1 ton
# Properties:
🪨Gravel :> ⚖️3_ton/m3 💰30 🪨1_ton

# Original:
# 🪨Aggregate                ⚖️3 ton/m3      💰30          🪨1 ton
# Properties:
🪨Aggregate :> ⚖️3_ton/m3 💰30 🪨1_ton

# Original:
# 🗿Concrete                 ⚖️3 ton/m3      💰100         🪨1 ton
# Properties:
🗿Concrete :> ⚖️3_ton/m3 💰100 🪨1_ton

# Original:
# 🌱Soil                     ⚖️3 ton/m3      💰1k          🪨1 ton
# Properties:
🌱Soil :> ⚖️3_ton/m3 💰1k 🪨1_ton

# Original:
# 🌾Wheat                    ⚖️1 ton/m3      💰300         🪨1 ton
# Properties:
🌾Wheat :> ⚖️1_ton/m3 💰300 🪨1_ton

# Original:
# 🍚Rice                     ⚖️1 ton/m3      💰300         🪨1 ton
# Properties:
🍚Rice :> ⚖️1_ton/m3 💰300 🪨1_ton

# Original:
# 🍞Flour                    ⚖️1 ton/m3      💰300         🪨1 ton
# Properties:
🍞Flour :> ⚖️1_ton/m3 💰300 🪨1_ton

# Original:
# 🌽Corn                     ⚖️1 ton/m3      💰100         🪨1 ton
# Properties:
🌽Corn :> ⚖️1_ton/m3 💰100 🪨1_ton

# Original:
# 🥔Potatoes                 ⚖️1 ton/m3      💰100         🪨1 ton
# Properties:
🥔Potatoes :> ⚖️1_ton/m3 💰100 🪨1_ton

# Original:
# 🫘Coffee Bean              ⚖️1 ton/m3      💰3k          🪨1 ton
# Properties:
🫘Coffee_Bean :> ⚖️1_ton/m3 💰3k 🪨1_ton

# Original:
# 🧪H2SO4 Sulfuric Acid      ⚖️3 ton/m3      💰300         🪨1 ton
# Properties:
🧪H2SO4_Sulfuric_Acid :> ⚖️3_ton/m3 💰300 🪨1_ton

# Original:
# 🧪NH3 Ammonia              ⚖️1 ton/m3      💰300         🪨1 ton
# Properties:
🧪NH3_Ammonia :> ⚖️1_ton/m3 💰300 🪨1_ton

# Original:
# 🧂Chlorine                 ⚖️1 kg/m3       💰100         🪨1 ton
# Properties:
🧂Chlorine :> ⚖️1_kg/m3 💰100 🪨1_ton

# Original:
# 🥑GPU                      ⚖️1 ton/m3      💰300k        🪨1 ton      #️⃣300
# Properties:
🥑GPU :> ⚖️1_ton/m3 💰300k 🪨1_ton #️⃣300

# Original:
# 📚Books                    ⚖️1 ton/m3      💰30k         🪨1 ton      #️⃣3k
# Properties:
📚Books :> ⚖️1_ton/m3 💰30k 🪨1_ton #️⃣3k

# Original:
# 🛰️Satellite - LEO          ⚖️1 ton/m3      💰30m         🪨1 ton
# Properties:
🛰️Satellite_LEO :> ⚖️1_ton/m3 💰30m 🪨1_ton

# Original:
# 🛰️Satellite - GEO          ⚖️1 ton/m3      💰100m        🪨1 ton
# Properties:
🛰️Satellite_GEO :> ⚖️1_ton/m3 💰100m 🪨1_ton

# Original:
# ♻️Plastic                  ⚖️1 ton/m3      💰1k          🪨1 ton
# Properties:
♻️Plastic :> ⚖️1_ton/m3 💰1k 🪨1_ton

# Original:
# 💩Soil                     ⚖️1 ton/m3      💰30          🪨1 ton
# Properties:
💩Soil :> ⚖️1_ton/m3 💰30 🪨1_ton

# Original:
# 💩Fertilizer               ⚖️1 ton/m3      💰300         🪨1 ton
# Properties:
💩Fertilizer :> ⚖️1_ton/m3 💰300 🪨1_ton

# Original:
# 🚽Sewage                   ⚖️1 ton/m3      💰1           🪨1 ton
# Properties:
🚽Sewage :> ⚖️1_ton/m3 💰1 🪨1_ton

# Original:
# 🚽Black Water              ⚖️1 ton/m3      💰1           🪨1 ton
# Properties:
🚽Black_Water :> ⚖️1_ton/m3 💰1 🪨1_ton

# Original:
# 🚿Grey Water               ⚖️1 ton/m3      💰1           🪨1 ton
# Properties:
🚿Grey_Water :> ⚖️1_ton/m3 💰1 🪨1_ton

# Original:
# 🌾Soybeans                 ⚖️1 ton/m3      💰300         🪨1 ton
# Properties:
🌾Soybeans :> ⚖️1_ton/m3 💰300 🪨1_ton

# Original:
# 🌾Barley                   ⚖️1 ton/m3      💰100         🪨1 ton
# Properties:
🌾Barley :> ⚖️1_ton/m3 💰100 🪨1_ton

# Original:
# 🌾Oats                     ⚖️1 ton/m3      💰100         🪨1 ton
# Properties:
🌾Oats :> ⚖️1_ton/m3 💰100 🪨1_ton

# Original:
# 🏝️Sand                     ⚖️1 ton/m3      💰30          🪨1 ton
# Properties:
🏝️Sand :> ⚖️1_ton/m3 💰30 🪨1_ton

# Original:
# 🪨Iron                     ⚖️10 ton/m3     💰300         🪨1 ton
# Properties:
🪨Iron :> ⚖️10_ton/m3 💰300 🪨1_ton

# Original:
# ⚙️Steel                    ⚖️10 ton/m3     💰1k          🪨1 ton
# Properties:
⚙️Steel :> ⚖️10_ton/m3 💰1k 🪨1_ton

# Original:
# 🪞Glass                    ⚖️3 ton/m3      💰300         🪨1 ton      📐100 m2      ↕️3 mm
# Properties:
🪞Glass :> ⚖️3_ton/m3 💰300 🪨1_ton 📐100_m2 ↕️3_mm

# Original:
# 🥉Copper                   ⚖️10 ton/m3     💰10k         🪨1 ton
# Properties:
🥉Copper :> ⚖️10_ton/m3 💰10k 🪨1_ton

# Original:
# 🥇Gold                     ⚖️30 ton/m3     💰100m        🪨1 ton
# Properties:
🥇Gold :> ⚖️30_ton/m3 💰100m 🪨1_ton

# Original:
# 🥈Silver                   ⚖️10 ton/m3     💰30k         🪨1 ton
# Properties:
🥈Silver :> ⚖️10_ton/m3 💰30k 🪨1_ton

# Original:
# 🗑️Aluminum                 ⚖️3 ton/m3      💰3k          🪨1 ton
# Properties:
🗑️Aluminum :> ⚖️3_ton/m3 💰3k 🪨1_ton

# Original:
# 🪙Nickel                   ⚖️10 ton/m3     💰30k         🪨1 ton
# Properties:
🪙Nickel :> ⚖️10_ton/m3 💰30k 🪨1_ton

# Original:
# 🪙Zinc                     ⚖️10 ton/m3     💰3k          🪨1 ton
# Properties:
🪙Zinc :> ⚖️10_ton/m3 💰3k 🪨1_ton

# Original:
# 🪙Lead                     ⚖️10 ton/m3     💰3k          🪨1 ton
# Properties:
🪙Lead :> ⚖️10_ton/m3 💰3k 🪨1_ton

# Original:
# 🥫Tin                      ⚖️10 ton/m3     💰30k         🪨1 ton
# Properties:
🥫Tin :> ⚖️10_ton/m3 💰30k 🪨1_ton

# Original:
# ☢️Uranium                  ⚖️30 ton/m3     💰300k        🪨1 ton
# Properties:
☢️Uranium :> ⚖️30_ton/m3 💰300k 🪨1_ton

# Original:
# 🪙Platinum                 ⚖️30 ton/m3     💰30m         🪨1 ton
# Properties:
🪙Platinum :> ⚖️30_ton/m3 💰30m 🪨1_ton

# Original:
# 🪙Cobalt                   ⚖️10 ton/m3     💰30m         🪨1 ton
# Properties:
🪙Cobalt :> ⚖️10_ton/m3 💰30m 🪨1_ton

# Original:
# 🪙Lithium                  ⚖️.3 ton/m3     💰10m         🪨1 ton
# Properties:
🪙Lithium :> ⚖️.3_ton/m3 💰10m 🪨1_ton

# Original:
# 🪙Rare Earths              ⚖️3 ton/m3      💰100k        🪨1 ton
# Properties:
🪙Rare_Earths :> ⚖️3_ton/m3 💰100k 🪨1_ton

# Original:
# 🪙Maganese                 ⚖️10 ton/m3     💰300         🪨1 ton
# Properties:
🪙Maganese :> ⚖️10_ton/m3 💰300 🪨1_ton

# Original:
# 🪙Chromite                 ⚖️3 ton/m3      💰300         🪨1 ton
# Properties:
🪙Chromite :> ⚖️3_ton/m3 💰300 🪨1_ton

# Original:
# 💡Tungsten                 ⚖️30 ton/m3     💰30k         🪨1 ton
# Properties:
💡Tungsten :> ⚖️30_ton/m3 💰30k 🪨1_ton

# Original:
# 🪙Molybdenum               ⚖️10 ton/m3     💰30k         🪨1 ton
# Properties:
🪙Molybdenum :> ⚖️10_ton/m3 💰30k 🪨1_ton

# Original:
# 🪙Phospherous              ⚖️3 ton/m3      💰1k          🪨1 ton
# Properties:
🪙Phospherous :> ⚖️3_ton/m3 💰1k 🪨1_ton

# Original:
# 🪙Potassium                ⚖️3 ton/m3      💰1k          🪨1 ton
# Properties:
🪙Potassium :> ⚖️3_ton/m3 💰1k 🪨1_ton

# Original:
# 🪙Neodymium                ⚖️3 ton/m3      💰100k        🪨1 ton
# Properties:
🪙Neodymium :> ⚖️3_ton/m3 💰100k 🪨1_ton

# Original:
# 🧂Chlorine                 ⚖️1 kg/m3       💰100         🪨1 ton
# Properties:
🧂Chlorine :> ⚖️1_kg/m3 💰100 🪨1_ton

# Original:
# 💨Hydrogen                 ⚖️.1 kg/m3      💰10k         🪨1 ton
# Properties:
💨Hydrogen :> ⚖️.1_kg/m3 💰10k 🪨1_ton

# Original:
# 💨Helium                   ⚖️1 kg/m3       💰3k          🪨1 ton
# Properties:
💨Helium :> ⚖️1_kg/m3 💰3k 🪨1_ton

# Original:
# 💨Nitrogen                 ⚖️1 kg/m3       💰1k          🪨1 ton
# Properties:
💨Nitrogen :> ⚖️1_kg/m3 💰1k 🪨1_ton

# Original:
# 💨Argon                    ⚖️.1 kg/m3      💰1k          🪨1 ton
# Properties:
💨Argon :> ⚖️.1_kg/m3 💰1k 🪨1_ton

# Original:
# 💨Oxygen (O₂)              ⚖️1 kg/m3       💰300         🪨1 ton
# Properties:
💨Oxygen :> ⚖️1_kg/m3 💰300 🪨1_ton

# Original:
# 💨Neon (Ne)                ⚖️1 kg/m3       💰300         🪨1 ton
# Properties:
💨Neon :> ⚖️1_kg/m3 💰300 🪨1_ton

# Original:
# 💨Krypton (Kr)             ⚖️3 kg/m3       💰3k          🪨1 ton
# Properties:
💨Krypton :> ⚖️3_kg/m3 💰3k 🪨1_ton

# Original:
# 💨Xenon (Xe)               ⚖️3 kg/m3       💰10k         🪨1 ton
# Properties:
💨Xenon :> ⚖️3_kg/m3 💰10k 🪨1_ton

# Original:
# 💨Radon (Rn)               ⚖️10 kg/m3      💰100         🪨1 ton
# Properties:
💨Radon :> ⚖️10_kg/m3 💰100 🪨1_ton

# Original:
# 💨Methane (CH₄)            ⚖️1 kg/m3       💰300         🪨1 ton
# Properties:
💨Methane :> ⚖️1_kg/m3 💰300 🪨1_ton

# Original:
# 💨Ethane (C₂H₆)            ⚖️1 kg/m3       💰300         🪨1 ton
# Properties:
💨Ethane :> ⚖️1_kg/m3 💰300 🪨1_ton

# Original:
# 💨Propane (C₃H₈)           ⚖️3 kg/m3       💰300         🪨1 ton
# Properties:
💨Propane :> ⚖️3_kg/m3 💰300 🪨1_ton

# Original:
# 💨Butane (C₄H₁₀)           ⚖️3 kg/m3       💰1k          🪨1 ton
# Properties:
💨Butane :> ⚖️3_kg/m3 💰1k 🪨1_ton

# Original:
# 💨Carbon Dioxide (CO₂)     ⚖️3 kg/m3       💰30          🪨1 ton
# Properties:
💨Carbon_Dioxide :> ⚖️3_kg/m3 💰30 🪨1_ton

# Original:
# 💨Nitrous Oxide (N₂O)      ⚖️3 kg/m3       💰100         🪨1 ton
# Properties:
💨Nitrous_Oxide :> ⚖️3_kg/m3 💰100 🪨1_ton

# Original:
# 💨Sulfur Hexafluoride (SF₆)⚖️10 kg/m3      💰30k         🪨1 ton 
# Properties:
💨Sulfur_Hexafluoride :> ⚖️10_kg/m3 💰30k 🪨1_ton

# Original:
# 🪞Glass                    📏3mm           📐1 m2        💰30
# Properties:
🪞Glass :> 📏3_mm 📐1_m2 💰30

# Original:
# 🪞Glass                    📏10mm          📐1 m2        💰300
# Properties:
🪞Glass :> 📏10_mm 📐1_m2 💰300

# Original:
# 📚Library                  📚300           📐1 m2        📏3 m
# Properties:
📚Library :> 📚300 📐1_m2 📏3_m

# Original:
# 📚Library Storage          📚3k            📐1 m2        📏3 m
# Properties:
📚Library_Storage :> 📚3k 📐1_m2 📏3_m

# Original:
# 🛠️3D printer               🏭1k #/yr       ⚡️100 watt     📐.1 m2      💰1k          ♻️1 ton/yr
# Build:
📐.1_m2 💰1k => 🛠️3D_printer
# Operation:
🛠️3D_printer ⚡️100_watt => 🛠️3D_printer 🏭1k_#/yr ♻️1_ton/yr

# Original:
# 🛠️5 Axis CNC               🏭30k #/yr      ⚡️3  kw        📐3 m2       💰30k         ⚙️100 ton/yr
# Build:
📐3_m2 💰30k => 🛠️5_Axis_CNC
# Operation:
🛠️5_Axis_CNC ⚡️3_kw => 🛠️5_Axis_CNC 🏭30k_#/yr ⚙️100_ton/yr

# Original:
# 🛠️Laser CNC                🏭100k #/yr     ⚡️10 kw        📐3 m2       💰10k         🪵10 ton/yr
# Build:
📐3_m2 💰10k => 🛠️Laser_CNC
# Operation:
🛠️Laser_CNC ⚡️10_kw => 🛠️Laser_CNC 🏭100k_#/yr 🪵10_ton/yr

# Original:
# 🛠️Circuit Mill             🏭30k #/yr      ⚡️1 kw         📐.3 m2      💰3k          🥉1 ton/yr
# Build:
📐.3_m2 💰3k => 🛠️Circuit_Mill
# Operation:
🛠️Circuit_Mill ⚡️1_kw => 🛠️Circuit_Mill 🏭30k_#/yr 🥉1_ton/yr

# Original:
# 🌾 Rice                    🌾 1b tons/yr   💵300b
# Properties:
🌾Rice :> 🌾1_b_tons/yr 💵300_b

# TODO ============



# Original:
# 🌾Rice                    🌾1b tons/yr   💵300b
# Properties:
🌾Rice :> 🌾1b_tons/yr 💵300b

# Original:
# 🌽Corn                    🌽1b tons/yr   💵300b
# Properties:
🌽Corn :> 🌽1b_tons/yr 💵300b

# Original:
# 🥔Potato                  🥔300m tons/yr 💵100b
# Properties:
🥔Potato :> 🥔300m_tons/yr 💵100b

# Original:
# 🍞Wheat                   🍞300m tons/yr 💵100b
# Properties:
🍞Wheat :> 🍞300m_tons/yr 💵100b

# Original:
# 🍅Tomatoes                🍅300m tons/yr 💵100b
# Properties:
🍅Tomatoes :> 🍅300m_tons/yr 💵100b

# Original:
# 🍚Barley                  🍚300m tons/yr 💵30b
# Properties:
🍚Barley :> 🍚300m_tons/yr 💵30b

# Original:
# 🍇Grapes                  🍇100m tons/yr 💵100b
# Properties:
🍇Grapes :> 🍇100m_tons/yr 💵100b

# Original:
# 🥜Soybeans                🥜100m tons/yr 💵100b
# Properties:
🥜Soybeans :> 🥜100m_tons/yr 💵100b

# Original:
# 🥒Cucumbers               🥒100m tons/yr 💵30b
# Properties:
🥒Cucumbers :> 🥒100m_tons/yr 💵30b

# Original:
# 🌶️Peppers                 🌶️100m tons/yr 💵30b
# Properties:
🌶️Peppers :> 🌶️100m_tons/yr 💵30b

# Original:
# 🍠Sweet Potatoes          🍠100m tons/yr 💵30b
# Properties:
🍠Sweet_Potatoes :> 🍠100m_tons/yr 💵30b

# Original:
# 🍌Bananas                 🍌100m tons/yr 💵30b
# Properties:
🍌Bananas :> 🍌100m_tons/yr 💵30b

# Original:
# 🍍Pineapples              🍍100m tons/yr 💵30b
# Properties:
🍍Pineapples :> 🍍100m_tons/yr 💵30b

# Original:
# 🍊Oranges                 🍊100m tons/yr 💵30b
# Properties:
🍊Oranges :> 🍊100m_tons/yr 💵30b

# Original:
# 🍏Apples                  🍏100m tons/yr 💵30b
# Properties:
🍏Apples :> 🍏100m_tons/yr 💵30b

# Original:
# 🍉 Watermelons             🍉 100m tons/yr 💵30b
# Properties:
🍉Watermelons :> 🍉100m_tons/yr 💵30b

# Original:
# 🍋 Lemons                  🍋 100m tons/yr 💵30b
# Properties:
🍋Lemons :> 🍋100m_tons/yr 💵30b

# Original:
# 🥥 Coconuts                🥥 100m tons/yr 💵30b
# Properties:
🥥Coconuts :> 🥥100m_tons/yr 💵30b

# Original:
# 🥦 Broccoli                🥦 100m tons/yr 💵10b
# Properties:
🥦Broccoli :> 🥦100m_tons/yr 💵10b

# Original:
# 🥬 Cabbages                🥬 100m tons/yr 💵10b
# Properties:
🥬Cabbages :> 🥬100m_tons/yr 💵10b

# Original:
# 🥕 Carrots                 🥕 100m tons/yr 💵10b
# Properties:
🥕Carrots :> 🥕100m_tons/yr 💵10b

# Original:
# 🌰 Nuts                    🌰 30m tons/yr  💵30b
# Properties:
🌰Nuts :> 🌰30m_tons/yr 💵30b

# Original:
# 🍓 Strawberries            🍓 30m tons/yr  💵10b
# Properties:
🍓Strawberries :> 🍓30m_tons/yr 💵10b

# Original:
# 🍑 Peaches                 🍑 30m tons/yr  💵10b
# Properties:
🍑Peaches :> 🍑30m_tons/yr 💵10b

# Original:
# 🍒 Cherries                🍒 30m tons/yr  💵10b
# Properties:
🍒Cherries :> 🍒30m_tons/yr 💵10b

# Original:
# 🥭 Mangoes                 🥭 30m tons/yr  💵10b
# Properties:
🥭Mangoes :> 🥭30m_tons/yr 💵10b

# Original:
# 🍈 Avocados                🍈 30m tons/yr  💵10b
# Properties:
🍈Avocados :> 🍈30m_tons/yr 💵10b

# Original:
# 🍈 Sorghum                 🍈 30m tons/yr  💵3b
# Properties:
🍈Sorghum :> 🍈30m_tons/yr 💵3b

# Original:
# 🍆 Eggplants               🍆 30m tons/yr  💵3b
# Properties:
🍆Eggplants :> 🍆30m_tons/yr 💵3b

# Original:
# 🍐 Pears                   🍐 30m tons/yr  💵3b
# Properties:
🍐Pears :> 🍐30m_tons/yr 💵3b



# Original:
# 🏞️km2                      📐1m m2   📐100 ha
# Properties:
📐1_m_m2 <=> 🏞️km2
📐100_ha <=> 🏞️km2


# Original:
# 📐ha                       📐10k m2  📐3 acres
# Properties:
📐ha <=> 📐10k_m2
📐ha <=> 📐3_acres

# Original:
# 📐m2                       📐10 ft2
# Properties:
📐m2 <=> 📐10_ft2


# Original:
# 📏Inch                     📏.1 m    📏1 in
# Properties:
📏Inch <=> 📏.1_m
📏Inch <=> 📏1_in

# Original:
# 📏Foot                     📏.3 m    📏1 ft
# Properties:
📏Foot <=> 📏.3_m

# Original:
# 📏Meter                    📏1 m     📏1 yrd
# Properties:
📏Meter <=> 📏1_m
📏Meter <=> 📏1_yrd

# Original:
# 📏Kilometer                📏1m m    📏1 km
# Properties:
📏Kilometer <=> 📏1m_m
📏Kilometer <=> 📏1_km

# Original:
# 📦m3                       ↔️1 m  ↕️1 m  ↗️1 m  📏1 m   📐1 m2
# Properties:
📦m3 :> ↔️1_m ↕️1_m ↗️1_m
📦m3 :> 📏1_m 📐1_m2

# Original:
# ↔️Width                    ↔️1 m
# Properties:
↔️Width <=> ↔️1_m

# Original:
# ↕️Height                   ↕️1 m
# Properties:
↕️Height <=> ↕️1_m

# Original:
# ↗️Depth                    ↗️1 m
# Properties:
↗️Depth <=> ↗️1_m



# Original:
# ⚖️Atmosphere               ⚖️1 atm      ⚖️ 1 ton/m2  ⚖️10 psi ⚖️1 bar 
# Properties:
⚖️Atmosphere <=> ⚖️1_atm
⚖️Atmosphere <=> ⚖️1_ton/m2
⚖️Atmosphere <=> ⚖️10_psi
⚖️Atmosphere <=> ⚖️1_bar


# Original:
# 💧Water                    ⚖️1 ton/m3  
# Properties:
💧Water :> ⚖️1_ton/m3

# Original:
# ⬇️Depth                    ⚖️1 atm      ⬇️10 m        
# Properties:
⬇️Depth <=> ⚖️1_atm
⬇️Depth <=> ⬇️10_m


# Original:
# 🗓️Year                     🗓️1 📆10 📅30 ⏰300 🕰️10k  ⏲️300k  ⏱️30m   ⌚️30b
# Properties:
🗓️Year <=> 🗓️1
🗓️Year <=> 📆10
🗓️Year <=> 📅30
🗓️Year <=> ⏰300
🗓️Year <=> 🕰️10k
🗓️Year <=> ⏲️300k
🗓️Year <=> ⏱️30m
🗓️Year <=> ⌚️30b

# Original:
# 📆Month                        📆1  📅3  ⏰30  🕰️1k   ⏲️30k   ⏱️3m    ⌚️3b
# Properties:
📆Month <=> 📆1
📆Month <=> 📅3
📆Month <=> ⏰30
📆Month <=> 🕰️1k
📆Month <=> ⏲️30k
📆Month <=> ⏱️3m
📆Month <=> ⌚️3b

# Original: 
# 📅Week                              📅1  ⏰10  🕰️300  ⏲️10k   ⏱️1m    ⌚️1b
# Properties:
📅Week <=> 📅1
📅Week <=> ⏰10
📅Week <=> 🕰️300
📅Week <=> ⏲️10k
📅Week <=> ⏱️1m
📅Week <=> ⌚️1b

# Original:
# ⏰Day                                    ⏰1   🕰️30   ⏲️1k    ⏱️100k  ⌚️100m
# Properties:
⏰Day <=> ⏰1
⏰Day <=> 🕰️30
⏰Day <=> ⏲️1k
⏰Day <=> ⏱️100k
⏰Day <=> ⌚️100m

# Original:
# 🕰️Hour                                         🕰️1    ⏲️100   ⏱️3k    ⌚️3m
# Properties:
🕰️Hour <=> 🕰️1
🕰️Hour <=> ⏲️100
🕰️Hour <=> ⏱️3k
🕰️Hour <=> ⌚️3m

# Original:
# ⏲️Minute                                              ⏲️1     ⏱️100   ⌚️100k
# Properties:
⏲️Minute <=> ⏲️1
⏲️Minute <=> ⏱️100
⏲️Minute <=> ⌚️100k

# Original:
# ⏱️Second                                                      ⏱️1     ⌚️1k
# Properties:
⏱️Second <=> ⏱️1
⏱️Second <=> ⌚️1k

# Original:
# ⌚️Millisec                                                            ⌚️1
# Properties:
⌚️Millisec <=> ⌚️1


# Original:
# 🚶‍♀️Walk                     🏎️1 m/s         📦10 kg       
# Operation:
🚶‍♀️Walk 📦10_kg => 🚶‍♀️Walk 🏎️1_m/s 📦10_kg

# Original: 
# 🏃Run                      🏎️3 m/s         📦1 kg
# Operation:
🏃Run 📦1_kg => 🏃Run 🏎️3_m/s 📦1_kg

# Original:
# 🚲Bike                     🏎️10 m/s        📦10 kg       ⚙️.01 ton    
# Build:
⚙️.01_ton => 🚲Bike
# Operation:
🚲Bike 📦10_kg => 🚲Bike 🏎️10_m/s 📦10_kg


# Original:
# 🚲EBike                    🏎️10 m/s        📦10 kg       ⚙️.01 ton     🔋3 kg        🔋1 kwh      
# Build:
⚙️.01_ton 🔋3_kg => 🚲EBike
# Operation:
🚲EBike 🔋1_kwh 📦10_kg => 🚲EBike 🏎️10_m/s 📦10_kg


# Original:
# 🚗Car - Electric           🏎️30 m/s        📦1 ton       ⚙️1 ton       🔋.3 ton      🔋100 kwh
# Build:
⚙️1_ton 🔋.3_ton => 🚗Car_Electric
# Operation:
🚗Car_Electric 🔋100_kwh 📦1_ton => 🚗Car_Electric 🏎️30_m/s 📦1_ton


# Original:
# 🚢Ship                     🏎️10 m/s        📦100k ton    ⚙️100k ton    ⛽️3k ton
# Build:
⚙️100k_ton ⛽️3k_ton => 🚢Ship
# Operation:
🚢Ship ⛽️3k_ton 📦100k_ton => 🚢Ship 🏎️10_m/s 📦100k_ton

# Original:
# 🚗Car                      🏎️30 m/s        📦1 ton       ⚙️1 ton       ⛽️.03 ton  
# Build:
⚙️1_ton => 🚗Car
# Operation:
🚗Car ⛽️.03_ton 📦1_ton => 🚗Car 🏎️30_m/s 📦1_ton

# Original:
# 🚄Train - Cargo            🏎️30 m/s        📦10k ton     ⚙️3k ton      ⛽️10 ton
# Build:
⚙️3k_ton => 🚄Train_Cargo
# Operation:
🚄Train_Cargo ⛽️10_ton 📦10k_ton => 🚄Train_Cargo 🏎️30_m/s 📦10k_ton


# Original:
# 🚄Train - Passenger        🏎️30 m/s        📦1k ton      ⚙️1k ton      ⛽️10 ton
# Build:
⚙️1k_ton => 🚄Train_Passenger
# Operation:
🚄Train_Passenger ⛽️10_ton 📦1k_ton => 🚄Train_Passenger 🏎️30_m/s 📦1k_ton

# Original:
# 🚄Train - High Speed       🏎️100 m/s       📦1k ton      ⚙️1k ton      ⛽️10 ton
# Build:
⚙️1k_ton => 🚄Train_High_Speed
# Operation:
🚄Train_High_Speed ⛽️10_ton 📦1k_ton => 🚄Train_High_Speed 🏎️100_m/s 📦1k_ton

# Original:
# ✈️Plane                    🏎️300 m/s       📦10 ton      ⚙️300 ton     ⛽️10 ton
# Build:
⚙️300_ton => ✈️Plane
# Operation:
✈️Plane ⛽️10_ton 📦10_ton => ✈️Plane 🏎️300_m/s 📦10_ton

# Original:
# 🚀Starship                 🏎️10k m/s       📦100 ton     ⚙️100 ton     ⛽️1k ton     
# Build:
⚙️100_ton => 🚀Starship
# Operation:
🚀Starship ⛽️1k_ton 📦100_ton => 🚀Starship 🏎️10k_m/s 📦100_ton


# Original:
# 🚀Orion                    🏎️300k m/s      📦10k ton     ☢️300         ⭕30 m
# Properties:
🚀Orion :> ⭕30_m
# Operation:
🚀Orion ☢️300 📦10k_ton => 🚀Orion 🏎️300k_m/s 📦10k_ton

# Original:
# 🚀Orion - Super            🏎️10m m/s       📦10m ton     ☢️1k          ⭕300 m
# Properties:
🚀Orion_Super :> ⭕300_m
# Operation:
🚀Orion_Super ☢️1k 📦10m_ton => 🚀Orion_Super 🏎️10m_m/s 📦10m_ton


# Original:
# 📦Shipping Container       📦10 ton        📏10 m        📏3 m         📐30 m2 
# Properties:
📦Shipping_Container :> 📏10_m 📏3_m 📐30_m2


# Original:
# 🚶‍♀️Walk                     🏎️1 m/s         🏎️3 km/hr
# Properties:
🚶‍♀️Walk <=> 🏎️1_m/s 
🚶‍♀️Walk <=> 🏎️3_km/hr


# Original:
# 🏃Run                      🏎️3 m/s         🏎️10 km/hr
# Properties:
🏃Run <=> 🏎️3_m/s 
🏃Run <=> 🏎️10_km/hr


# Original:
# ✈️Mach 1                   🏎️300 m/s       🏎️1k km/hr
# Properties:
✈️Mach_1 <=> 🏎️300_m/s 
✈️Mach_1 <=> 🏎️1k_km/hr

# Original:
# 🚀Escape Velocity          🏎️10k m/s   
# Properties:
🚀Escape_Velocity <=> 🏎️10k_m/s


# Original:
# 🔆Lightspeed               🏎️300m m/s
# Properties:
🔆Lightspeed <=> 🏎️300m_m/s


# Original:
# ⌚️Latency                  ⌚️1 ms
# Properties:
⌚️Latency <=> ⌚️1_ms


# Original:
# 🌞Solar Energy Surface     ⚡️1 KW          📐1 m2
# Properties:
🌞Solar_Energy_Surface :> ⚡️1_KW 📐1_m2

# Original:
# 🌞Solar PV Earth           ⚡️300w          📐1 m2        %30           🕰️3k hrs/yr  
# Properties:
🌞Solar_PV_Earth :> ⚡️300_w 📐1_m2 %30 🕰️3k_hrs/yr

# Original:
# 🌞Solar PV Space           ⚡️300w          📐1 m2        %30           🕰️10k hrs/yr  
# Properties:
🌞Solar_PV_Space :> ⚡️300_w 📐1_m2 %30 🕰️10k_hrs/yr


# Original:
# 🏜️desert                   🌧️0 m/m2/yr     📐1 m2
# Properties:
🏜️Desert :> 🌧️0_m/m2/yr 📐1_m2

# Original:
# 🏞️plains                   🌧️1 m/m2/yr     📐1 m2
# Properties:
🏞️Plains :> 🌧️1_m/m2/yr 📐1_m2

# Original:
# 🎋jungle                   🌧️3 m/m2/yr     📐1 m2
# Properties:
🎋Jungle :> 🌧️3_m/m2/yr 📐1_m2

# Original:
# 🌴rainforest               🌧️10 m/m2/yr    📐1 m2
# Properties:
🌴Rainforest :> 🌧️10_m/m2/yr 📐1_m2

# Original:
# 🔥heat                     🔥1 mwh 
# Properties:
🔥Heat <=> 🔥1_mwh

# Original:
# 🌡️temperature (c)          🌡️1 c           💧1 m3        🔥kwh
# Operation:
💧1_m3 🔥1_kwh => 💧1_m3 🌡️1_c


# Original:
# 💧Water - Survival         💧10 kg         👤1 pop        ⏰1 day 
# Operation:
💧10_kg 👤1_pop => 👤1_pop ⏰1_day

# Original:
# 💧Water - Daily            💧100 kg        👤1 pop        ⏰1 day
# Operation:
💧100_kg 👤1_pop => 👤1_pop ⏰1_day

# Original:
# 💧Water - Agriculture      💧1 ton         👤1 pop        ⏰1 day
# Operation:
💧1_ton 👤1_pop => 👤1_pop ⏰1_day

# Original:
# 💧Water - Cash Crops       💧10 ton        👤1 pop        ⏰1 day
# Operation:
💧10_ton 👤1_pop => 👤1_pop ⏰1_day

# Original:
# 💧olympic pool             💧3k ton
# Properties:
💧Olympic_Pool :> 💧3k_ton



# Original:
# 🏢Residential - Floor      ↕️3 m 
# Properties:
🏢Residential_Floor :> ↕️3_m

# Original:
# 🏢Residential - Wood       🪵1 ton         👤1 pop
# Properties:
🏢Residential_Wood :> 🪵1_ton 👤1_pop


# Original:
# 🏢Residential - Steel      ⚙️3 ton         👤1 pop
# Properties:
🏢Residential_Steel :> ⚙️3_ton 👤1_pop

# Original:
# 🏢Residential - Concrete   🗿10 ton        👤1 pop
# Properties:
🏢Residential_Concrete :> 🗿10_ton 👤1_pop

# Original:
# 🏢Residential              📐10 m2         👤1 pop
# Properties:
🏢Residential :> 📐10_m2 👤1_pop

# Original:
# 🏢Office                   📐3 m2          👤1 pop
# Properties:
🏢Office :> 📐3_m2 👤1_pop

# Original:
# 🏭Industrial - Heavy       🗿3 ton         📐1 m2 
# Properties:
🏭Industrial_Heavy :> 🗿3_ton 📐1_m2

# Original:
# 🏭Industrial - Medium      🗿1 ton         📐1 m2 
# Properties:
🏭Industrial_Medium :> 🗿1_ton 📐1_m2

# Original:
# 🏭Industrial - Light       🗿.1 ton        📐1 m2 
# Properties:
🏭Industrial_Light :> 🗿.1_ton 📐1_m2


# Original:
# 👤Human                    🍖30 kg         📐10 m2       💨3 m3/hr     💧.1 ton/day  🥔3 kg/day 🔥100 w ⚡️️1 kw  ⛽️1 kd/day
👤Human <=> 👤1_pop
# Operation:
👤Human 🍖30_kg/yr 📐10_m2 💨3_m3/hr 💧.1_ton/day 🥔3_kg/day ⚡️️1_kw ⛽️1_kg/day => 👤Human 📐10_m2 🔥100_w
# 
# From Claude: (after long prompt chain)
# Human Survival - Minimum requirements and outputs
👤Human_Survival <=> 👤1_pop
# Operation:
👤Human_Survival 🍖30_kg/yr 🥔3_kg/day 📐10_m2 💨3_m3/hr 💧.003_ton/day ⚡️.1_kw ⛽️.1_kg/day => 👤Human_Survival 📐10_m2 🚽.003_ton/day 🌫️10_kg/day 🔥100_w/hr
# Human Comfortable - Modern lifestyle requirements and outputs
👤Human_Comfortable <=> 👤1_pop
# Operation:
👤Human_Comfortable 🍖100_kg/yr 🥔10_kg/day 📐30_m2 💨3_m3/hr 💧.3_ton/day ⚡️3_kw ⛽️1_kg/day => 👤Human_Comfortable 📐30_m2 🚿.1_ton/day 🚽.03_ton/day 🌫️30_kg/day 🔥100_w/hr


# Original:
# 🇺🇸USA                      ⚡️️30 kwh/day    👤1 pop
# Operation:
🇺🇸USA 👤1_pop ⚡️️30_kwh/day => 🇺🇸USA 👤1_pop

# Original:
# 🇨🇦Canada                   ⚡️️30 kwh/day    👤1 pop
# Operation:
🇨🇦Canada 👤1_pop ⚡️️30_kwh/day => 🇨🇦Canada 👤1_pop

# Original:
# 🇨🇳China                    ⚡️️10 kwh/day    👤1 pop
# Operation:
🇨🇳China 👤1_pop ⚡️️10_kwh/day => 🇨🇳China 👤1_pop

# Original:
# 🇬🇧China                    ⚡️️10 kwh/day    👤1 pop
# Operation:
🇬🇧China 👤1_pop ⚡️️10_kwh/day => 🇬🇧China 👤1_pop

# Original:
# 🇮🇳India                    ⚡️️3 kwh/day     👤1 pop
# Operation:
🇮🇳India 👤1_pop ⚡️️3_kwh/day => 🇮🇳India 👤1_pop

# Original:
# 🇧🇷Brazil                   ⚡️️3 kwh/day     👤1 pop
# Operation:
🇧🇷Brazil 👤1_pop ⚡️️3_kwh/day => 🇧🇷Brazil 👤1_pop

# Original:
# 🇳🇬Nigeria                  ⚡️️1 kwh/day     👤1 pop
# Operation:
🇳🇬Nigeria 👤1_pop ⚡️️1_kwh/day => 🇳🇬Nigeria 👤1_pop


# Original:
# 🌐World                   🌫️30b tons/yr
# Operation:
🌐World 🌫️30b_tons/yr => 🌐World

# Original:
# 🇨🇳China                   🌫️10k tons/yr
# Operation:
🇨🇳China 🌫️10k_tons/yr => 🇨🇳China

# Original: 
# 🇺🇸United States           🌫️10k tons/yr
# Operation:
🇺🇸United_States 🌫️10k_tons/yr => 🇺🇸United_States

# Original:
# 🇮🇳India                   🌫️3k tons/yr
# Operation:
🇮🇳India 🌫️3k_tons/yr => 🇮🇳India

# Original:
# 🇷🇺Russia                  🌫️3k tons/yr
# Operation:
🇷🇺Russia 🌫️3k_tons/yr => 🇷🇺Russia

# Original:
# 🇯🇵Japan                   🌫️1k tons/yr
# Operation:
🇯🇵Japan 🌫️1k_tons/yr => 🇯🇵Japan 

# Original:
# 🇩🇪Germany                 🌫️1k tons/yr
# Operation:
🇩🇪Germany 🌫️1k_tons/yr => 🇩🇪Germany

# Original: 
# 🇮🇷Iran                    🌫️1k tons/yr
# Operation:
🇮🇷Iran 🌫️1k_tons/yr => 🇮🇷Iran

# Original:
# 🇸🇦Saudi Arabia            🌫️1k tons/yr
# Operation:
🇸🇦Saudi_Arabia 🌫️1k_tons/yr => 🇸🇦Saudi_Arabia

# Original:
# 🇰🇷South Korea             🌫️1k tons/yr
# Operation:
🇰🇷South_Korea 🌫️1k_tons/yr => 🇰🇷South_Korea

# Original:
# 🇨🇦Canada                  🌫️300 tons/yr
# Operation:
🇨🇦Canada 🌫️300_tons/yr => 🇨🇦Canada

# Original:
# 🇧🇷Brazil                  🌫️300 tons/yr
# Operation:
🇧🇷Brazil 🌫️300_tons/yr => 🇧🇷Brazil

# Original:
# 🇮🇩Indonesia               🌫️300 tons/yr
# Operation:
🇮🇩Indonesia 🌫️300_tons/yr => 🇮🇩Indonesia  

# Original:
# 🇲🇽Mexico                  🌫️300 tons/yr
# Operation:
🇲🇽Mexico 🌫️300_tons/yr => 🇲🇽Mexico

# Original:
# 🇬🇧United Kingdom          🌫️300 tons/yr
# Operation:
🇬🇧United_Kingdom 🌫️300_tons/yr => 🇬🇧United_Kingdom

# Original:
# 🇹🇷Turkey                  🌫️300 tons/yr
# Operation:
🇹🇷Turkey 🌫️300_tons/yr => 🇹🇷Turkey

# Original:
# 🇮🇹Italy                   🌫️300 tons/yr
# Operation:
  🇮🇹Italy 🌫️300_tons/yr => 🇮🇹Italy

# Original:
# 🇿🇦South Africa            🌫️300 tons/yr
# Operation:
🇿🇦South_Africa 🌫️300_tons/yr => 🇿🇦South_Africa

# Original:
# 🇦🇺Australia               🌫️300 tons/yr
# Operation:
🇦🇺Australia 🌫️300_tons/yr => 🇦🇺Australia  

# Original:
# 🇫🇷France                  🌫️300 tons/yr
# Operation:
🇫🇷France 🌫️300_tons/yr => 🇫🇷France

# Original:
# 🇵🇱Poland                  🌫️300 tons/yr
# Operation:
🇵🇱Poland 🌫️300_tons/yr => 🇵🇱Poland



# RESOURCES:
# example starting resources:

# Properties:
💼Inventory <=> 💼
💰Capex <=> 💰
💼 :> 💰1b
# now we can expand out to all possible inventories from here

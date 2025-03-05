# Please format the following bulk list of projects into a more functional build-recipe-style format.
# Consider the following examples for a guide on how to do this conversion.  You will be breaking down the list of info into separate recipes, particularly distinguishing between build and operation aspects.
# Be thoughtful about the nature of what is being represented.  Where it makes sense to change standard formatting, interject with a #Note please do so to explain your choices.
# Be very careful to preserve the original units and quantities.  All the original data must be included in the new recipes format.  Leave a #Note if that's ever violated or if you're unsure how to reformat.

# Output the TODO list in the new recipes format as per the examples.  Use # Original:, # Build:, # Operation: sections exactly as shown in the examples.  Process every line from the TODO list of notes as a separate recipe set.

# Hints: usually operations costs are measured in energy or money per year.  These are not always correctly labelled in the original data and so need to be reasoned out.  Sometime electricity/money/etc may be a build cost or even a production output.  Infer based on the nature of the data notes.

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
# 🚢🛥️Kariba Lock              🗿100k tons     ⚙️30k tons    📏100 m       💰💵100m        🚢100m tons/yr 
# Build:
🗿100k_tons  ⚙️30k_tons  📏100_m  💰💵100m  => 🚢🛥️Kariba_Lock
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
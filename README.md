# SIGNAMANCY - Axiomatic Game Engine Crafting Rules

A symbolic rule engine for expressing game and system mechanics through token-based asynchronous state transitions.  Testing how complex game rules can be expressed through simple token transformations and sum up to complex systems.  These rules aim to always compile down to token transitions which can run in tensor batches on a GPU, making their simplicity deceptively efficient.

Emojis are for flavor.  Any string can be used to represent a token, with only a few syntax constraints reserved for special behavior, like representing quantities or marking priority. See `axiom_types.txt` for a deeper guide through the syntax choices.

## Status and Goals

STATUS: WIP research notes.  Not rigorous design docs yet

GOALS: 
- Formalize the discovery and creation of these rules from base observations of states in an arbitrary game/system.  These are human walkthroughs attempting to create rules naively, but they may still use a bit too much cleverness for an arbitrary AI or offline algorithm to just derive by trial and error.  This is why we push for such a simplistic rule syntax.  Need to go through these games again with a blindfold on and formalize the process so it can be automated.

## Overview

This engine allows you to express game mechanics through simple token-based rules in the form:

\```
🪓 🌳 => 🪓 🤎3  # chop tree to get wood
\```

Rules can be chained together to create complex game behaviors while maintaining readability through emoji.

## Key Features

- Pure functional approach - all state changes are expressed as token transitions
- Emoji-based syntax for improved readability and expressiveness
- Support for quantities (e.g. 🍎3 instead of 🍎 🍎 🍎)
- Conditional rules through catalyst tokens (unchanged on both sides)
- Substitution rules for equivalent tokens (marked by <=>)
- Listeners for conditional rules based on neighboring squares (e.g. "if any adjacent squares contain water, the current square is wet")


## Example Games

The repo contains several example game implementations:

### Crafter
A Minecraft-inspired survival game with:
- Resource gathering and crafting
- Health/hunger/thirst management  
- Day/night cycle
- Combat with enemies

### Baba Is You
A puzzle game about manipulating the rules themselves:
- Rules constructed from word objects
- Push mechanics
- Win conditions

### MiniGrid
A simple grid-based environment for RL:
- Movement and rotation
- Object interaction
- Keys and doors
- Goal-based missions

### Pokemon Red
The classic gameboy game, implemented up til the first rival battle:
- Combat
- Trainer battles
- Item management
- Menu navigation
- Player movement


\```
# Example Rules

# Basic Resource Gathering
🪓 🌳 => 🪓 🤎3  # Chop tree for wood
⛏️ ⬜ => ⛏️ ⛰2  # Mine stone for resources

# Complex Crafting with Requirements
👣(🧰) 🤎3 => 👣(🧰) ⛏️🤎  # Craft wooden pickaxe at workbench
👣(🔥) 🥈 🖤 🌳 => 👣(🔥) 🥈⛏️  # Craft iron pickaxe at furnace

# Conditional State Changes
❗ 🌱 💧3 ☀️ => ☀️ 🌳  # Plant grows if well-watered (❗ marks priority)
🌱 ☀️ => ☀️  # Otherwise withers

# Combat System
❗ ⚔️ ❤️2 => ❤️ # Take damage from enemy
🧍 ❤️ => 💀  # Die when health depleted

# Day/Night Cycle with Events
🌞 ⌛100 => ⌛100 🌛  # Day turns to night

\```

## License

MIT

## Acknowledgments

https://arxiv.org/abs/2109.06780 - Benchmarking the Spectrum of Agent Capabilities - where Crafter was systematically turned into rules for an LLM agent

Chris!  For insatiable enthusiasm on emojis

The webcomic Erfworld and its "Signamancy" mechanic concept, for a powerful demonstration of how metaphors can be used to express complex living worlds

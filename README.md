# BlackjackAnalysis

A blackjack analysis toolkit that determines optimal strategy through three independent approaches: exact probability calculation, Monte Carlo simulation, and reinforcement learning. Each approach is self-contained and produces strategy matrices that can be compared against each other.

## Installation

```
pip install -r requirements.txt
```

## Project Structure

```
BlackjackAnalysis/
├── blackjack.py                        # Core game engine (shared by all modules)
├── data/                               # Precomputed probability tables (JSON)
├── strategy_matrices/                  # Verified optimal strategy CSVs
├── calculator/
│   ├── blackjack_calc.py               # Exact EV calculator (probability trees)
│   ├── calc_ev.py                      # Print EV tables for a given rule set
│   ├── game.py                         # Interactive strategy chart + game EV
│   └── run_calc.py                     # Regenerate data/JSON files
├── sim/
│   ├── blackjack_sim.py                # Monte Carlo strategy simulator
│   ├── plot_sim.py                     # Plot simulator convergence
│   └── iterations_from_confidence.py   # Compute required iterations per cell
└── reinforcement_learning/
    ├── blackjack_rl.py                 # Train Q-table via reinforcement learning
    └── plot_rl.py                      # Plot RL convergence
```

## Rule Flags

Most scripts share a common set of rule flags:

| Flag               | Description                            | Default |
| ------------------ | -------------------------------------- | ------- |
| `--decks N`        | Number of decks (1, 2, 4, 6, 8)        | 6       |
| `--s17` / `--h17`  | Dealer stands or hits on soft 17       | S17     |
| `--enhc` / `--us`  | European no-hole-card vs. US peek      | US      |
| `--das` / `--ndas` | Double after split allowed/not allowed | DAS     |

---

## Calculator

The calculator uses recursive probability trees against precomputed dealer outcome tables to compute exact expected values. No sampling — results are mathematically precise.

**Print EV tables for a rule set:**

```
python calculator/calc_ev.py [--decks N] [--s17|--h17] [--enhc|--us] [--das|--ndas]
```

Prints hard, soft, and split EV tables showing the exact expected value of each action for every hand vs. every upcard.

**Display strategy chart and game EV:**

```
python calculator/game.py [--decks N] [--s17|--h17] [--enhc|--us] [--das|--ndas] [--surrender|--no-surrender] [--ra N] [--bet N]
```

Prints color-coded basic strategy charts (hard, soft, pairs) and computes the overall player EV under optimal play, including hourly win/loss estimates.

**Regenerate the Data/ JSON lookup tables:**

```
python calculator/run_calc.py <hit|double|stand|dealer|split> [--workers N]
```

Runs across all rule combinations (5 deck counts × 2 soft-17 rules × 2 peek rules) in parallel and writes updated JSON files to `data/`. Only needed if you want to rebuild the precomputed tables from scratch.

---

## Simulation

The Monte Carlo simulator plays out hands using the core game engine and builds strategy matrices from sampled outcomes. Accuracy is checked against the verified strategy matrices in `strategy_matrices/`.

**Run a simulation:**

```
python sim/blackjack_sim.py [--decks N] [--s17|--h17] [--enhc] [--das|--ndas] [--confidence N] [--workers N] [--iterations N]
```

- Without `--iterations`: computes the required iterations per cell to distinguish the best action from the second-best at the given confidence level, then runs the simulation using those counts.
- With `--iterations N`: skips the confidence calculation and uses a fixed iteration count for every cell.

Outputs strategy CSVs and prints an accuracy report comparing simulated decisions against verified optimal strategy.

**Plot convergence:**

```
python sim/plot_sim.py [--decks N] [--s17|--h17] [--enhc] [--das|--ndas] [--workers N]
```

Runs the simulator at increasing iteration counts (100 → 1K → 10K → 100K) and plots the number of incorrect decisions at each level. Saves to `sim_convergence_plot.png`.

**Compute required iterations:**

```
python sim/iterations_from_confidence.py [--confidence N]
```

Uses worst-case rules (8D H17 ENHC) as an upper bound to compute the minimum iterations per cell needed at a given confidence level. Outputs CSV files to the script directory.

---

## Reinforcement Learning

The RL module trains a Q-table by playing out millions of random hands and updating action values based on actual outcomes. No access to the probability tables — strategy is learned purely from experience.

**Train and output a strategy:**

```
python reinforcement_learning/blackjack_rl.py [--decks N] [--s17|--h17] [--enhc] [--das|--ndas] [--episodes N]
```

Trains a Q-table using an incremental learning rate (1/n visits) and epsilon-greedy exploration with linear decay. Outputs strategy CSVs and prints an accuracy report against verified optimal strategy.

**Plot convergence:**

```
python reinforcement_learning/plot_rl.py [--decks N] [--s17|--h17] [--enhc] [--das|--ndas] [--episodes N]
```

Same as above but generates a convergence plot showing how strategy accuracy improves over training episodes.

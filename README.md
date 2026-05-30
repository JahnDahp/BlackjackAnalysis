# BlackjackAnalysis

A blackjack analysis project that determines optimal strategy through three approaches: exact probability calculation, Monte Carlo simulation, and reinforcement learning. Each approach is measured by the amount of correct strategy decisions each method produces.

## Installation

```
pip install -r requirements.txt
```

## Project Structure

```
BlackjackAnalysis/
├── blackjack.py                        # Game engine
├── data/                               # Precomputed probability tables (JSON)
├── strategy_matrices/                  # Verified optimal strategy tables (CSV)
├── calculator/
│   ├── blackjack_calc.py               # Exact EV calculator
│   ├── calc_ev.py                      # Print EV tables for a given rule set
│   ├── game.py                         # Strategy chart + EV by ruleset
│   ├── plot_ra.py                      # Plot SD/hour vs. risk-aversion coefficient
│   └── run_calc.py                     # Regenerate data files
├── sim/
│   ├── blackjack_sim.py                # Monte Carlo strategy simulator
│   └── plot_sim.py                     # Plot simulator convergence
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

The calculator uses recursive probability trees against precomputed dealer outcome tables to compute exact expected values.

**Print EV tables for a rule set:**

```
python calculator/calc_ev.py [--decks N] [--s17|--h17] [--enhc|--us] [--das|--ndas]
```

Prints hard, soft, and split EV tables showing the exact expected value of each action for every hand vs. every upcard.

**Display strategy chart and game EV:**

```
python calculator/game.py [--decks N] [--s17|--h17] [--enhc|--us] [--das|--ndas] [--surrender|--no-surrender] [--ra N] [--bet N]
```

Prints color-coded hard, soft, and pair basic strategy charts and computes the overall player EV under optimal play, including hourly EV and standard deviation estimates given a flat bet size. Also allows for generating risk-averse basic strategy charts and hourly EV and standard deviation given a risk-aversion coefficient using the certainty equivalent formula.

**Plot EV ± 1 SD vs. risk aversion:**

```
python calculator/plot_ra.py [--decks N] [--s17|--h17] [--enhc|--us] [--das|--ndas] [--surrender|--no-surrender] [--bet N]
```

Plots EV/hour, EV + 1 SD, and EV − 1 SD as three separate lines at λ = 0.00 through 0.25 in steps of 0.01 using the exact probability calculator. Shows how risk-averse strategy trades EV for reduced variance. Saves to `ra_ev_plot.png`.

**Regenerate the Data/ JSON lookup tables:**

```
python calculator/run_calc.py <hit|double|stand|dealer|split> [--workers N]
```

Runs across all rule combinations (5 deck counts x 2 soft-17 rules x 2 peek rules) in parallel and writes updated JSON files to `data/`. Only needed if you want to rebuild the precomputed tables from scratch and to show how they were obtained.

---

## Simulation

The Monte Carlo simulator plays out hands using the core game engine and builds strategy matrices from sampled outcomes. Accuracy is checked against the verified strategy matrices in `strategy_matrices/`.

**Run a simulation:**

```
python sim/blackjack_sim.py [--decks N] [--s17|--h17] [--enhc] [--das|--ndas] [--confidence N] [--workers N] [--iterations N]
```

- Without `--iterations N`: computes the required iterations per cell to distinguish the best action from the second-best at the given confidence level, then runs the simulation using those counts. Only useful because EV and variance is known due to the calculator method.
- With `--iterations N`: skips the confidence calculation and uses a fixed iteration count for every cell.

Surrender is always evaluated — if -0.5 beats the best simulated EV the cell is marked `Rh`, `Rs`, or `Rp`. Players without surrender available simply use the fallback action (the letter after R).

Outputs strategy CSVs and prints an accuracy report comparing simulated decisions against verified optimal strategy. Can be run in parallel using `--workers N`.

**Plot convergence:**

```
python sim/plot_sim.py [--decks N] [--s17|--h17] [--enhc] [--das|--ndas] [--workers N]
```

Runs the simulator at increasing iteration counts (100 → 1K → 10K → 100K) and plots the number of incorrect decisions at each level. Saves to `sim_convergence_plot.png`.

---

## Reinforcement Learning

The RL module trains a Q-table by playing out millions of random hands and updating action values based on outcomes.

The RL equivalent of an iteration is an episode — a single sampled hand against a single upcard, training one action at one cell. There are 1,580 state-action pairs: 180 hard cells × 4 actions + 90 soft cells × 4 actions + 100 pair cells × 5 actions (hit, stand, double, split, surrender) = 720 + 360 + 500 = 1,580. Surrender is always included — the Q-value for surrender converges to its fixed reward of -0.5, so surrender cells naturally output `Rh`/`Rs`/`Rp`. Players without surrender use the fallback action. The convergence plot uses 1,210× the simulator's iteration milestones (the no-surrender baseline) so the x-axes remain directly comparable.

**Train and output a strategy:**

```
python reinforcement_learning/blackjack_rl.py [--decks N] [--s17|--h17] [--enhc] [--das|--ndas] [--episodes N]
```

Trains a Q-table using an incremental learning rate (1/n visits by cell) and epsilon-greedy exploration with linear decay. Outputs strategy CSVs and prints an accuracy report against verified optimal strategy.

**Plot convergence:**

```
python reinforcement_learning/plot_rl.py [--decks N] [--s17|--h17] [--enhc] [--das|--ndas]
```

Runs training at increasing episode counts and generates a convergence plot showing how strategy accuracy improves over training episodes.

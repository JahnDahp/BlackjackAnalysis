"""
Run.py

Usage:
    python Run.py <hit|double|stand|dealer|split|removed> [--remove-pair-card] [--data-dir PATH] [--workers N]

The --remove-pair-card flag only applies to the split decision.

The 'removed' decision generates hit_removed.json, stand_removed.json, and
double_removed.json — each containing precomputed probs for every rule config
with one extra card of each rank (1-10) removed from the shoe. Used to make
split --remove-pair-card near-instant via lookup instead of recursion.
"""

from __future__ import annotations

import argparse
import json
import multiprocessing
import os
import sys
from typing import Any


def _serialize_hand(hand: list) -> list:
    return [{"rank": c.rank} if hasattr(c, "rank") else c for c in hand]


def _serialize_rows(rows: list) -> list:
    return [[_serialize_hand(row[0])] + list(row[1:]) for row in rows]


def _serialize_split_ev(ev: any) -> any:
    if isinstance(ev, dict):
        return {k: _serialize_split_ev(v) for k, v in ev.items()}
    if isinstance(ev, list):
        return [_serialize_split_ev(i) for i in ev]
    if hasattr(ev, "rank"):
        return {"rank": ev.rank}
    return ev


# ---------------------------------------------------------------------------
# Existing workers (unchanged)
# ---------------------------------------------------------------------------

def worker_dealer(config: dict, data_dir: str) -> dict:
    from Calculator import Calculator, DealerSettingsObject
    decks, s17, enhc = config["decks"], config["S17"], config["ENHC"]
    base = config["baseSettings"]
    settings = DealerSettingsObject(decks=decks, S17=s17, ENHC=enhc,
        BJPay=base["BJPay"], DAS=base["DAS"], drawAces=base["drawAces"])
    instance = Calculator.create(settings, data_dir)
    rule = f"{decks}D {'S17' if s17 else 'H17'} {'ENHC' if enhc else 'US'}"
    print(f"Starting dealer: {rule}", flush=True)
    result = instance.run_dealer_sim(normalize=True)
    print(f"Done: {rule}", flush=True)
    return {"decks": decks, "S17": s17, "ENHC": enhc, "result": result}


def worker_double(config: dict, data_dir: str) -> dict:
    from Calculator import Calculator, DealerSettingsObject
    decks, s17, enhc = config["decks"], config["S17"], config["ENHC"]
    base = config["baseSettings"]
    settings = DealerSettingsObject(decks=decks, S17=s17, ENHC=enhc,
        BJPay=base["BJPay"], DAS=base["DAS"], drawAces=base["drawAces"])
    instance = Calculator.create(settings, data_dir)
    rule = f"{decks}D {'S17' if s17 else 'H17'} {'ENHC' if enhc else 'US'}"
    print(f"Starting double: {rule}", flush=True)
    hard: list[list[Any]] = []
    for up_card in range(1, 11):
        up_label = "A" if up_card == 1 else str(up_card)
        upcard_results: list[Any] = []
        for total_target in range(4, 22):
            print(f"{rule} | double hard {total_target} vs {up_label}", flush=True)
            candidate_hands = instance.run_hand_sim(total_target, up_card, False)["allHands"]
            for hand in candidate_hands:
                if instance.total(hand["hand"]) == total_target and len(hand["hand"]) == 2:
                    upcard_results.append([hand["hand"], hand["totalProb"],
                        instance.calc_double(hand["hand"], up_card)])
        hard.append(upcard_results)
    soft: list[list[Any]] = []
    for up_card in range(1, 11):
        up_label = "A" if up_card == 1 else str(up_card)
        upcard_results = []
        for total_target in range(12, 22):
            print(f"{rule} | double soft {total_target} vs {up_label}", flush=True)
            candidate_hands = instance.run_hand_sim(total_target, up_card, True)["allHands"]
            for hand in candidate_hands:
                if instance.total(hand["hand"]) == total_target and len(hand["hand"]) == 2:
                    upcard_results.append([hand["hand"], hand["totalProb"],
                        instance.calc_double(hand["hand"], up_card)])
        soft.append(upcard_results)
    print(f"Done: {rule}", flush=True)
    return {"decks": decks, "S17": s17, "ENHC": enhc,
            "hard": [_serialize_rows(u) for u in hard],
            "soft": [_serialize_rows(u) for u in soft]}


def worker_hit(config: dict, data_dir: str) -> dict:
    from Calculator import Calculator, DealerSettingsObject
    decks, s17, enhc = config["decks"], config["S17"], config["ENHC"]
    base = config["baseSettings"]
    settings = DealerSettingsObject(decks=decks, S17=s17, ENHC=enhc,
        BJPay=base["BJPay"], DAS=base["DAS"], drawAces=base["drawAces"])
    instance = Calculator.create(settings, data_dir)
    rule = f"{decks}D {'S17' if s17 else 'H17'} {'ENHC' if enhc else 'US'}"
    print(f"Starting hit: {rule}", flush=True)
    hard: list[list[Any]] = []
    for up_card in range(1, 11):
        up_label = "A" if up_card == 1 else str(up_card)
        upcard_results: list[Any] = []
        for total_target in range(4, 22):
            print(f"{rule} | hit hard {total_target} vs {up_label}", flush=True)
            candidate_hands = instance.run_hand_sim(total_target, up_card, False)["allHands"]
            for hand in candidate_hands:
                if instance.total(hand["hand"]) == total_target:
                    upcard_results.append([hand["hand"], hand["totalProb"],
                        instance.calc_hit(hand["hand"], up_card)])
        hard.append(upcard_results)
    soft: list[list[Any]] = []
    for up_card in range(1, 11):
        up_label = "A" if up_card == 1 else str(up_card)
        upcard_results = []
        for total_target in range(12, 22):
            print(f"{rule} | hit soft {total_target} vs {up_label}", flush=True)
            candidate_hands = instance.run_hand_sim(total_target, up_card, True)["allHands"]
            for hand in candidate_hands:
                if instance.total(hand["hand"]) == total_target:
                    upcard_results.append([hand["hand"], hand["totalProb"],
                        instance.calc_hit(hand["hand"], up_card)])
        soft.append(upcard_results)
    print(f"Done: {rule}", flush=True)
    return {"decks": decks, "S17": s17, "ENHC": enhc,
            "hard": [_serialize_rows(u) for u in hard],
            "soft": [_serialize_rows(u) for u in soft]}


def worker_split(config: dict, data_dir: str) -> dict:
    from Calculator import Calculator, DealerSettingsObject, Card
    decks, s17, enhc = config["decks"], config["S17"], config["ENHC"]
    base = config["baseSettings"]
    remove_pair_card: bool = config.get("removePairCard", False)
    rule = f"{decks}D {'S17' if s17 else 'H17'} {'ENHC' if enhc else 'US'}"
    if remove_pair_card:
        rule += " [remove-pair-card]"
    settings_das = DealerSettingsObject(decks=decks, S17=s17, ENHC=enhc,
        BJPay=base["BJPay"], DAS=True, drawAces=base["drawAces"])
    instance_das = Calculator.create(settings_das, data_dir)
    print(f"Starting DAS: {rule}", flush=True)
    DAS_results: list[list[Any]] = []
    for up_card in range(1, 11):
        up_label = "A" if up_card == 1 else str(up_card)
        print(f"{rule} | DAS upcard {up_label}", flush=True)
        upcard_results: list[Any] = []
        for pair_val in range(1, 11):
            ev = instance_das.calc_split([Card(rank=pair_val), Card(rank=pair_val)],
                up_card, remove_pair_card)
            upcard_results.append([[{"rank": pair_val}, {"rank": pair_val}], _serialize_split_ev(ev)])
        DAS_results.append(upcard_results)
    settings_ndas = DealerSettingsObject(decks=decks, S17=s17, ENHC=enhc,
        BJPay=base["BJPay"], DAS=False, drawAces=base["drawAces"])
    instance_ndas = Calculator.create(settings_ndas, data_dir)
    print(f"Starting nDAS: {rule}", flush=True)
    nDAS_results: list[list[Any]] = []
    for up_card in range(1, 11):
        up_label = "A" if up_card == 1 else str(up_card)
        print(f"{rule} | nDAS upcard {up_label}", flush=True)
        upcard_results = []
        for pair_val in range(1, 11):
            ev = instance_ndas.calc_split([Card(rank=pair_val), Card(rank=pair_val)],
                up_card, remove_pair_card)
            upcard_results.append([[{"rank": pair_val}, {"rank": pair_val}], _serialize_split_ev(ev)])
        nDAS_results.append(upcard_results)
    print(f"Done: {rule}", flush=True)
    return {"decks": decks, "S17": s17, "ENHC": enhc, "DAS": DAS_results, "nDAS": nDAS_results}


def worker_stand(config: dict, data_dir: str) -> dict:
    from Calculator import Calculator, DealerSettingsObject
    decks, s17, enhc = config["decks"], config["S17"], config["ENHC"]
    base = config["baseSettings"]
    settings = DealerSettingsObject(decks=decks, S17=s17, ENHC=enhc,
        BJPay=base["BJPay"], DAS=base["DAS"], drawAces=base["drawAces"])
    instance = Calculator.create(settings, data_dir)
    rule = f"{decks}D {'S17' if s17 else 'H17'} {'ENHC' if enhc else 'US'}"
    print(f"Starting stand: {rule}", flush=True)
    hard: list[list[Any]] = []
    for up_card in range(1, 11):
        up_label = "A" if up_card == 1 else str(up_card)
        upcard_results: list[Any] = []
        for total_target in range(4, 22):
            print(f"{rule} | stand hard {total_target} vs {up_label}", flush=True)
            candidate_hands = instance.run_hand_sim(total_target, up_card, False)["allHands"]
            for hand in candidate_hands:
                if instance.total(hand["hand"]) == total_target:
                    upcard_results.append([hand["hand"], hand["totalProb"],
                        instance.calc_stand(hand["hand"], up_card)])
        hard.append(upcard_results)
    soft: list[list[Any]] = []
    for up_card in range(1, 11):
        up_label = "A" if up_card == 1 else str(up_card)
        upcard_results = []
        for total_target in range(12, 22):
            print(f"{rule} | stand soft {total_target} vs {up_label}", flush=True)
            candidate_hands = instance.run_hand_sim(total_target, up_card, True)["allHands"]
            for hand in candidate_hands:
                if instance.total(hand["hand"]) == total_target:
                    upcard_results.append([hand["hand"], hand["totalProb"],
                        instance.calc_stand(hand["hand"], up_card)])
        soft.append(upcard_results)
    print(f"Done: {rule}", flush=True)
    return {"decks": decks, "S17": s17, "ENHC": enhc,
            "hard": [_serialize_rows(u) for u in hard],
            "soft": [_serialize_rows(u) for u in soft]}


# ---------------------------------------------------------------------------
# New: removed worker — hit/stand/double with one extra rank removed
# ---------------------------------------------------------------------------

def worker_removed(config: dict, data_dir: str) -> dict:
    """
    Computes stand, hit, and double probs with one extra card of removed_rank
    removed from the shoe. Dependency order per rank:
      1. stand  (self-contained)
      2. hit    (loaded from the stand_remove_X.json just written)
      3. double (loaded from the stand_remove_X.json just written)
    Each decision is written to disk immediately so the next can load it.
    """
    from Calculator import Calculator, DealerSettingsObject, Card, ShoeCount
    decks, s17, enhc = config["decks"], config["S17"], config["ENHC"]
    base = config["baseSettings"]
    removed_rank: int = config["removedRank"]
    removed_label = "A" if removed_rank == 1 else str(removed_rank)
    rule = f"{decks}D {'S17' if s17 else 'H17'} {'ENHC' if enhc else 'US'} [removed={removed_label}]"

    settings = DealerSettingsObject(decks=decks, S17=s17, ENHC=enhc,
        BJPay=base["BJPay"], DAS=base["DAS"], drawAces=base["drawAces"])
    instance = Calculator.create(settings, data_dir)

    exclude = [Card(rank=removed_rank)]
    deck_map = {1:"oneDeck",2:"twoDeck",4:"fourDeck",6:"sixDeck",8:"eightDeck"}
    s17_key = "S17" if s17 else "H17"
    peek_key = "enhc" if enhc else "us"

    print(f"Starting removed: {rule}", flush=True)

    # ── Step 1: stand (self-contained) ───────────────────────────────
    def _stand_table(soft: bool, total_range: range) -> list[list[Any]]:
        table: list[list[Any]] = []
        for up_card in range(1, 11):
            up_label = "A" if up_card == 1 else str(up_card)
            upcard_results: list[Any] = []
            for total_target in total_range:
                print(f"{rule} | stand {'soft' if soft else 'hard'} {total_target} vs {up_label}", flush=True)
                for hand in instance.run_hand_sim(total_target, up_card, soft)["allHands"]:
                    if instance.total(hand["hand"]) == total_target:
                        upcard_results.append([
                            _serialize_hand(hand["hand"]), hand["totalProb"],
                            instance.calc_stand(hand["hand"], up_card, exclude),
                        ])
            table.append(upcard_results)
        return table

    stand_hard = _stand_table(False, range(4, 22))
    stand_soft = _stand_table(True,  range(12, 22))
    stand_data = {"probs": {deck_map[decks]: {s17_key: {peek_key: {"hard": stand_hard, "soft": stand_soft}}}}}

    # Write stand immediately so hit/double can load it
    stand_path = os.path.join(data_dir, f"stand_remove_{removed_label}.json")
    with open(stand_path, "w", encoding="utf-8") as f:
        json.dump(stand_data, f)
    print(f"  Wrote {os.path.basename(stand_path)}", flush=True)

    # Reload into instance so hit/double use it
    instance.stand_data = stand_data

    # ── Step 2: hit (uses the precomputed removed-stand via instance.stand_data) ─
    def _hit_table(soft: bool, total_range: range) -> list[list[Any]]:
        table: list[list[Any]] = []
        for up_card in range(1, 11):
            up_label = "A" if up_card == 1 else str(up_card)
            upcard_results: list[Any] = []
            for total_target in total_range:
                print(f"{rule} | hit {'soft' if soft else 'hard'} {total_target} vs {up_label}", flush=True)
                for hand in instance.run_hand_sim(total_target, up_card, soft)["allHands"]:
                    if instance.total(hand["hand"]) == total_target:
                        upcard_results.append([
                            _serialize_hand(hand["hand"]), hand["totalProb"],
                            instance.calc_hit(hand["hand"], up_card, exclude),
                        ])
            table.append(upcard_results)
        return table

    hit_hard = _hit_table(False, range(4, 22))
    hit_soft = _hit_table(True,  range(12, 22))
    hit_data = {"probs": {deck_map[decks]: {s17_key: {peek_key: {"hard": hit_hard, "soft": hit_soft}}}}}

    hit_path = os.path.join(data_dir, f"hit_remove_{removed_label}.json")
    with open(hit_path, "w", encoding="utf-8") as f:
        json.dump(hit_data, f)
    print(f"  Wrote {os.path.basename(hit_path)}", flush=True)

    # ── Step 3: double (uses the precomputed removed-stand) ──────────
    def _double_table(soft: bool, total_range: range) -> list[list[Any]]:
        table: list[list[Any]] = []
        for up_card in range(1, 11):
            up_label = "A" if up_card == 1 else str(up_card)
            upcard_results: list[Any] = []
            for total_target in total_range:
                print(f"{rule} | double {'soft' if soft else 'hard'} {total_target} vs {up_label}", flush=True)
                for hand in instance.run_hand_sim(total_target, up_card, soft)["allHands"]:
                    if instance.total(hand["hand"]) == total_target and len(hand["hand"]) == 2:
                        upcard_results.append([
                            _serialize_hand(hand["hand"]), hand["totalProb"],
                            instance.calc_double(hand["hand"], up_card, exclude),
                        ])
            table.append(upcard_results)
        return table

    double_hard = _double_table(False, range(4, 22))
    double_soft = _double_table(True,  range(12, 22))
    double_data = {"probs": {deck_map[decks]: {s17_key: {peek_key: {"hard": double_hard, "soft": double_soft}}}}}

    double_path = os.path.join(data_dir, f"double_remove_{removed_label}.json")
    with open(double_path, "w", encoding="utf-8") as f:
        json.dump(double_data, f)
    print(f"  Wrote {os.path.basename(double_path)}", flush=True)

    print(f"Done: {rule}", flush=True)
    # Files already written — return minimal result for assemble_results
    return {
        "decks": decks, "S17": s17, "ENHC": enhc,
        "removedRank": removed_rank,
    }


# ---------------------------------------------------------------------------
# Dispatcher
# ---------------------------------------------------------------------------

WORKER_MAP = {
    "dealer":  worker_dealer,
    "double":  worker_double,
    "hit":     worker_hit,
    "split":   worker_split,
    "stand":   worker_stand,
    "removed": worker_removed,
}


def _run_worker(args: tuple) -> dict:
    worker_fn, config, data_dir = args
    try:
        return worker_fn(config, data_dir)
    except Exception as exc:
        import traceback
        print(f"WORKER CRASH: {exc}\n{traceback.format_exc()}", file=sys.stderr, flush=True)
        raise


def assemble_results(decision: str, results: list[dict]) -> dict:
    deck_name_map = {1: "oneDeck", 2: "twoDeck", 4: "fourDeck", 6: "sixDeck", 8: "eightDeck"}
    by_decks: dict[int, Any] = {}

    if decision == "dealer":
        for r in results:
            decks, s17, enhc = r["decks"], r["S17"], r["ENHC"]
            if decks not in by_decks:
                by_decks[decks] = {"H17": {"us": None, "enhc": None}, "S17": {"us": None, "enhc": None}}
            by_decks[decks]["S17" if s17 else "H17"]["enhc" if enhc else "us"] = r["result"]
        return {"outcomes": {deck_name_map[d]: by_decks[d] for d in [1, 2, 4, 6, 8]}}

    elif decision == "split":
        for r in results:
            decks, s17, enhc = r["decks"], r["S17"], r["ENHC"]
            if decks not in by_decks:
                by_decks[decks] = {"H17": {"us": None, "enhc": None}, "S17": {"us": None, "enhc": None}}
            by_decks[decks]["S17" if s17 else "H17"]["enhc" if enhc else "us"] = {
                "DAS": r["DAS"], "nDAS": r["nDAS"]}
        return {"probs": {deck_name_map[d]: by_decks[d] for d in [1, 2, 4, 6, 8]}}

    elif decision == "removed":
        # Files are already written per-config inside worker_removed.
        # Nothing to assemble — return empty sentinel.
        return {"removed": True}

    else:
        for r in results:
            decks, s17, enhc = r["decks"], r["S17"], r["ENHC"]
            if decks not in by_decks:
                by_decks[decks] = {"H17": {"us": None, "enhc": None}, "S17": {"us": None, "enhc": None}}
            by_decks[decks]["S17" if s17 else "H17"]["enhc" if enhc else "us"] = {
                "hard": r["hard"], "soft": r["soft"]}
        return {"probs": {deck_name_map[d]: by_decks[d] for d in [1, 2, 4, 6, 8]}}


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Generate blackjack strategy JSON data files.")
    parser.add_argument("decision", choices=list(WORKER_MAP.keys()),
        help="Which decision table to compute. Use 'removed' to generate hit/stand/double with each rank removed.")
    parser.add_argument("--remove-pair-card", action="store_true", default=False,
        help="Split only: remove one extra copy of the pair rank from the shoe.")
    parser.add_argument("--data-dir", default=None,
        help="Path to the directory containing the JSON data files.")
    parser.add_argument("--workers", type=int, default=None,
        help="Number of parallel worker processes. Defaults to cpu_count - 4.")
    args = parser.parse_args()

    decision = args.decision
    remove_pair_card = args.remove_pair_card
    worker_fn = WORKER_MAP[decision]

    if remove_pair_card and decision != "split":
        print("Warning: --remove-pair-card has no effect for non-split decisions.", flush=True)

    if args.data_dir:
        data_dir = os.path.normpath(os.path.abspath(args.data_dir))
    else:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        data_dir = os.path.normpath(
            os.path.join(script_dir, "..", "..", "..", "..", "public", "data"))

    if not os.path.isdir(data_dir):
        print(f"ERROR: data directory not found: {data_dir}", file=sys.stderr)
        print("Use --data-dir to specify the correct path.", file=sys.stderr)
        sys.exit(1)

    output_file = os.path.join(data_dir, f"new_{decision}.json")

    base_settings = {
        "decks": 6, "S17": True, "ENHC": False,
        "BJPay": 1.5, "DAS": True, "drawAces": False,
        "doubles": [9, 10, 11],
    }

    configs: list[dict] = []
    if decision == "removed":
        # One config per (decks, s17, enhc, removed_rank) — 20 rule combos × 10 ranks = 200 configs
        for removed_rank in range(1, 11):
            for decks in [1, 2, 4, 6, 8]:
                for s17 in [False, True]:
                    for enhc in [False, True]:
                        configs.append({
                            "decks": decks, "S17": s17, "ENHC": enhc,
                            "baseSettings": base_settings,
                            "removedRank": removed_rank,
                        })
    else:
        for decks in [1, 2, 4, 6, 8]:
            for s17 in [False, True]:
                for enhc in [False, True]:
                    configs.append({
                        "decks": decks, "S17": s17, "ENHC": enhc,
                        "baseSettings": base_settings,
                        "removePairCard": remove_pair_card,
                    })

    cpu_count = os.cpu_count() or 1
    max_workers = args.workers if args.workers else max(1, cpu_count - 4)
    max_workers = min(max_workers, 20)
    print(f"Detected {cpu_count} logical CPUs. Running {len(configs)} configs with {max_workers} parallel workers.", flush=True)
    print("Use --workers N to adjust if your computer becomes unresponsive.", flush=True)

    tasks = [(worker_fn, config, data_dir) for config in configs]

    with multiprocessing.Pool(processes=max_workers) as pool:
        try:
            results: list[dict] = pool.map(_run_worker, tasks)
        except Exception as exc:
            print(f"Worker failed: {exc}", file=sys.stderr)
            pool.terminate()
            sys.exit(1)

    cache = assemble_results(decision, results)

    if decision == "removed":
        print("All removed files written by workers.")
    else:
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(cache, f)
        print(f"Wrote {os.path.basename(output_file)}")


if __name__ == "__main__":
    multiprocessing.freeze_support()
    main()
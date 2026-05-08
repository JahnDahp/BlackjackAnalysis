import * as fs from "fs";
import * as path from "path";
import { Worker } from "worker_threads";
import { fileURLToPath } from "url";
const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const dataDir = path.join(__dirname, "../../../../public/data");
const decision = process.argv[2];
if (!decision ||
    !["hit", "double", "stand", "dealer", "split"].includes(decision)) {
    console.error("Usage: node dist/run.js <hit|double|stand|dealer|split>");
    process.exit(1);
}
const workerFile = `worker${decision.charAt(0).toUpperCase() + decision.slice(1)}.js`;
const outputFile = `${decision}.json`;
const baseSettings = {
    decks: 6,
    S17: true,
    ENHC: false,
    BJPay: 1.5,
    DAS: true,
    drawAces: false,
    doubles: [9, 10, 11],
};
const configs = [];
for (const decks of [1, 2, 4, 6, 8])
    for (const S17 of [false, true])
        for (const ENHC of [false, true])
            configs.push({ decks, S17, ENHC });
const results = [];
const promises = configs.map(({ decks, S17, ENHC }) => {
    return new Promise((resolve, reject) => {
        const worker = new Worker(path.join(__dirname, workerFile), {
            workerData: { decks, S17, ENHC, baseSettings, dataDir },
            stdout: true,
            stderr: true,
        });
        worker.stdout.on("data", (data) => {
            data
                .toString()
                .split("\n")
                .filter(Boolean)
                .forEach((line) => {
                process.stdout.write(line + "\n");
            });
        });
        worker.stderr.on("data", (data) => process.stderr.write(data));
        worker.on("message", (result) => {
            if (result.type === "log") {
                process.stdout.write(result.msg + "\n");
            }
            else {
                results.push(result);
            }
        });
        worker.on("error", (err) => {
            console.error(`Worker error (${decks}D ${S17 ? "S17" : "H17"} ${ENHC ? "ENHC" : "US"}):`, err);
            reject(err);
        });
        worker.on("exit", (code) => {
            if (code !== 0)
                reject(new Error(`Worker exited with code ${code}`));
            else
                resolve();
        });
    });
});
Promise.all(promises).then(() => {
    const byDecks = {};
    if (decision === "dealer") {
        for (const { decks, S17, ENHC, result } of results) {
            byDecks[decks] ??= {
                H17: { us: null, enhc: null },
                S17: { us: null, enhc: null },
            };
            byDecks[decks][S17 ? "S17" : "H17"][ENHC ? "enhc" : "us"] = result;
        }
        const cache = {
            outcomes: {
                oneDeck: byDecks[1],
                twoDeck: byDecks[2],
                fourDeck: byDecks[4],
                sixDeck: byDecks[6],
                eightDeck: byDecks[8],
            },
        };
        fs.writeFileSync(path.join(dataDir, outputFile), JSON.stringify(cache));
    }
    else if (decision === "split") {
        for (const { decks, S17, ENHC, DAS, nDAS } of results) {
            byDecks[decks] ??= {
                H17: { us: null, enhc: null },
                S17: { us: null, enhc: null },
            };
            byDecks[decks][S17 ? "S17" : "H17"][ENHC ? "enhc" : "us"] = {
                DAS,
                nDAS,
            };
        }
        const cache = {
            probs: {
                oneDeck: byDecks[1],
                twoDeck: byDecks[2],
                fourDeck: byDecks[4],
                sixDeck: byDecks[6],
                eightDeck: byDecks[8],
            },
        };
        fs.writeFileSync(path.join(dataDir, outputFile), JSON.stringify(cache));
    }
    else {
        for (const { decks, S17, ENHC, hard, soft } of results) {
            byDecks[decks] ??= {
                H17: { us: null, enhc: null },
                S17: { us: null, enhc: null },
            };
            byDecks[decks][S17 ? "S17" : "H17"][ENHC ? "enhc" : "us"] = {
                hard,
                soft,
            };
        }
        const cache = {
            probs: {
                oneDeck: byDecks[1],
                twoDeck: byDecks[2],
                fourDeck: byDecks[4],
                sixDeck: byDecks[6],
                eightDeck: byDecks[8],
            },
        };
        fs.writeFileSync(path.join(dataDir, outputFile), JSON.stringify(cache));
    }
    console.log(`Wrote ${outputFile}`);
});

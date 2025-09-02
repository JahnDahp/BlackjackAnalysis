import { Route, Routes, useLocation } from "react-router-dom";
import Home from "./HomeComponents/Home";
import Play from "./PlayComponents/Play";
import "./App.css";
import { useEffect, useState } from "react";
import Game from "./GameComponents/Game";
import {
  BankrollSettingsObject,
  DealerSettingsObject,
  CountingSettingsObject,
  GameSettingsObject,
  StrategySettingsObject,
} from "./SettingsObjects";
import Calculator from "./CalculatorComponents/Calculator";

function App() {
  const EMPTY = -100;
  const location = useLocation();

  const [dealerSettingsObject, setDealerSettingsObject] =
    useState<DealerSettingsObject>({
      decks: 6,
      S17: true,
      ENHC: false,
      DAS: true,
      doubles: [
        2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21,
      ],
      splits: 3,
      LS: true,
      BJPay: 1.5,
      RSA: false,
      drawAces: false,
    });

  const [gameSettingsObject, setGameSettingsObject] =
    useState<GameSettingsObject>({
      decks: 6,
      S17: true,
      DAS: true,
      doubles: [
        2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21,
      ],
      splits: 3,
      LS: "Yes",
      BJPay: 1.5,
      pen: 52,
      RSA: false,
      drawAces: false,
    });
  const [bankrollSettingsObject, setBankrollSettingsObject] =
    useState<BankrollSettingsObject>({
      bankroll: 10000,
      tableMin: 25,
      tableMax: 1000,
    });
  const [strategySettingsObject, setStrategySettingsObject] =
    useState<StrategySettingsObject>({
      showErrors: true,
      hardMatrix: [
        [0, 0, 0, 0, 0, 0, 0, 0, 0, 0], // 21
        [0, 0, 0, 0, 0, 0, 0, 0, 0, 0], // 20
        [0, 0, 0, 0, 0, 0, 0, 0, 0, 0], // 19
        [0, 0, 0, 0, 0, 0, 0, 0, 0, 0], // 18
        [0, 0, 0, 0, 0, 0, 0, 0, 0, 0], // 17
        [0, 0, 0, 0, 0, 1, 1, 1, 1, 1], // 16
        [0, 0, 0, 0, 0, 1, 1, 1, 1, 1], // 15
        [0, 0, 0, 0, 0, 1, 1, 1, 1, 1], // 14
        [0, 0, 0, 0, 0, 1, 1, 1, 1, 1], // 13
        [1, 1, 0, 0, 0, 1, 1, 1, 1, 1], // 12
        [2, 2, 2, 2, 2, 2, 2, 2, 2, 1], // 11
        [2, 2, 2, 2, 2, 2, 2, 2, 1, 1], // 10
        [1, 2, 2, 2, 2, 1, 1, 1, 1, 1], // 9
        [1, 1, 1, 1, 1, 1, 1, 1, 1, 1], // 8
        [1, 1, 1, 1, 1, 1, 1, 1, 1, 1], // 7
        [1, 1, 1, 1, 1, 1, 1, 1, 1, 1], // 6
        [1, 1, 1, 1, 1, 1, 1, 1, 1, 1], // 5
        [1, 1, 1, 1, 1, 1, 1, 1, 1, 1], // 4
      ],
      softMatrix: [
        [0, 0, 0, 0, 0, 0, 0, 0, 0, 0], // A,10
        [0, 0, 0, 0, 0, 0, 0, 0, 0, 0], // A,9
        [0, 0, 0, 0, 0, 0, 0, 0, 0, 0], // A,8
        [0, 3, 3, 3, 3, 0, 0, 1, 1, 1], // A,7
        [1, 2, 2, 2, 2, 1, 1, 1, 1, 1], // A,6
        [1, 1, 2, 2, 2, 1, 1, 1, 1, 1], // A,5
        [1, 1, 2, 2, 2, 1, 1, 1, 1, 1], // A,4
        [1, 1, 1, 2, 2, 1, 1, 1, 1, 1], // A,3
        [1, 1, 1, 2, 2, 1, 1, 1, 1, 1], // A,2
        [1, 1, 1, 1, 2, 1, 1, 1, 1, 1], // A,A
      ],
      splitMatrix: [
        [1, 1, 1, 1, 1, 1, 1, 1, 1, 1], // A,A
        [0, 0, 0, 0, 0, 0, 0, 0, 0, 0], // 10,10
        [1, 1, 1, 1, 1, 0, 1, 1, 0, 0], // 9,9
        [1, 1, 1, 1, 1, 1, 1, 1, 1, 1], // 8,8
        [1, 1, 1, 1, 1, 1, 0, 0, 0, 0], // 7,7
        [2, 1, 1, 1, 1, 0, 0, 0, 0, 0], // 6,6
        [0, 0, 0, 0, 0, 0, 0, 0, 0, 0], // 5,5
        [0, 0, 0, 2, 2, 0, 0, 0, 0, 0], // 4,4
        [2, 2, 1, 1, 1, 1, 0, 0, 0, 0], // 3,3
        [2, 2, 1, 1, 1, 1, 0, 0, 0, 0], // 2,2
      ],
      surrenderMatrix: [
        [0, 0, 0, 0, 0, 0, 0, 0, 0, 0], // 21
        [0, 0, 0, 0, 0, 0, 0, 0, 0, 0], // 20
        [0, 0, 0, 0, 0, 0, 0, 0, 0, 0], // 19
        [0, 0, 0, 0, 0, 0, 0, 0, 0, 0], // 18
        [0, 0, 0, 0, 0, 0, 0, 0, 0, 0], // 17
        [0, 0, 0, 0, 0, 0, 0, 1, 1, 1], // 16
        [0, 0, 0, 0, 0, 0, 0, 0, 1, 0], // 15
        [0, 0, 0, 0, 0, 0, 0, 0, 0, 0], // 14
        [0, 0, 0, 0, 0, 0, 0, 0, 0, 0], // 13
        [0, 0, 0, 0, 0, 0, 0, 0, 0, 0], // 12
        [0, 0, 0, 0, 0, 0, 0, 0, 0, 0], // 11
        [0, 0, 0, 0, 0, 0, 0, 0, 0, 0], // 10
        [0, 0, 0, 0, 0, 0, 0, 0, 0, 0], // 9
        [0, 0, 0, 0, 0, 0, 0, 0, 0, 0], // 8
        [0, 0, 0, 0, 0, 0, 0, 0, 0, 0], // 7
        [0, 0, 0, 0, 0, 0, 0, 0, 0, 0], // 6
        [0, 0, 0, 0, 0, 0, 0, 0, 0, 0], // 5
        [0, 0, 0, 0, 0, 0, 0, 0, 0, 0], // 4
        [0, 0, 0, 0, 0, 0, 0, 0, 0, 0], // A,A
        [0, 0, 0, 0, 0, 0, 0, 0, 0, 0], // 10,10
        [0, 0, 0, 0, 0, 0, 0, 0, 0, 0], // 9,9
        [0, 0, 0, 0, 0, 0, 0, 0, 0, 0], // 8,8
        [0, 0, 0, 0, 0, 0, 0, 0, 0, 0], // 7,7
        [0, 0, 0, 0, 0, 0, 0, 0, 0, 0], // 6,6
        [0, 0, 0, 0, 0, 0, 0, 0, 0, 0], // 5,5
        [0, 0, 0, 0, 0, 0, 0, 0, 0, 0], // 4,4
        [0, 0, 0, 0, 0, 0, 0, 0, 0, 0], // 3,3
        [0, 0, 0, 0, 0, 0, 0, 0, 0, 0], // 2,2
      ],
    });
  const [countingSettingsObject, setCountingSettingsObject] =
    useState<CountingSettingsObject>({
      tags: [1, 1, 1, 1, 1, 0, 0, 0, -1, -1],
      IRCs: [0, 0, 0, 0, 0],
      divisor: "Full deck",
      calculation: "Round",
      countTableCards: false,
      hitStandMatrix: [
        [EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY], // 21
        [EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY], // 20
        [EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY], // 19
        [EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY], // 18
        [EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY], // 17
        [EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY], // 16
        [EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY], // 15
        [EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY], // 14
        [EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY], // 13
        [EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY], // 12
        [EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY], // A,10
        [EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY], // A,9
        [EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY], // A,8
        [EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY], // A,7
        [EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY], // A,6
        [EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY], // A,5
        [EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY], // A,4
        [EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY], // A,3
        [EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY], // A,2
        [EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY], // A,A
      ],
      doubleMatrix: [
        [EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY], // 11
        [EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY], // 10
        [EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY], // 9
        [EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY], // 8
        [EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY], // 7
        [EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY], // 6
        [EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY], // 5
        [EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY], // 4
        [EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY], // A,10
        [EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY], // A,9
        [EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY], // A,8
        [EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY], // A,7
        [EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY], // A,6
        [EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY], // A,5
        [EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY], // A,4
        [EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY], // A,3
        [EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY], // A,2
        [EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY], // A,A
      ],
      splitMatrix: [
        [EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY], // A,A
        [EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY], // 10,10
        [EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY], // 9,9
        [EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY], // 8,8
        [EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY], // 7,7
        [EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY], // 6,6
        [EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY], // 5,5
        [EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY], // 4,4
        [EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY], // 3,3
        [EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY], // 2,2
      ],
      surrenderMatrix: [
        [EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY], // 21
        [EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY], // 20
        [EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY], // 19
        [EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY], // 18
        [EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY], // 17
        [EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY], // 16
        [EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY], // 15
        [EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY], // 14
        [EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY], // 13
        [EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY], // 12
        [EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY], // 11
        [EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY], // 10
        [EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY], // 9
        [EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY], // 8
        [EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY], // 7
        [EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY], // 6
        [EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY], // 5
        [EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY], // 4
        [EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY], // A,A
        [EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY], // 10,10
        [EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY], // 9,9
        [EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY], // 8,8
        [EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY], // 7,7
        [EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY], // 6,6
        [EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY], // 5,5
        [EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY], // 4,4
        [EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY], // 3,3
        [EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY], // 2,2
      ],
    });

  useEffect(() => {
    document.body.style.backgroundColor =
      location.pathname === "/play-settings" || location.pathname === "/game"
        ? "#121212"
        : "white";
  }, [location]);

  return (
    <div>
      <Routes>
        <Route path="/" element={<Home />} />
        <Route
          path="/play-settings"
          element={
            <Play
              gameSettingsObject={gameSettingsObject}
              setGameSettingsObject={setGameSettingsObject}
              bankrollSettingsObject={bankrollSettingsObject}
              setBankrollSettingsObject={setBankrollSettingsObject}
              strategySettingsObject={strategySettingsObject}
              setStrategySettingsObject={setStrategySettingsObject}
              countingSettingsObject={countingSettingsObject}
              setCountingSettingsObject={setCountingSettingsObject}
            />
          }
        />
        <Route
          path="/game"
          element={
            <Game
              gameSettingsObject={gameSettingsObject}
              bankrollSettingsObject={bankrollSettingsObject}
              strategySettingsObject={strategySettingsObject}
              countingSettingsObject={countingSettingsObject}
            />
          }
        />
        <Route
          path="/calculator"
          element={
            <Calculator
              dealerSettingsObject={dealerSettingsObject}
              setDealerSettingsObject={setDealerSettingsObject}
            />
          }
        />
        <Route path="/sim" element={<div>Coming Soon!</div>} />
      </Routes>
    </div>
  );
}

export default App;

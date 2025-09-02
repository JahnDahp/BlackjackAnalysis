import "../GameStyles/Game.css";
import { BlackjackGame } from "./Blackjack";
import { useEffect, useRef, useState } from "react";
import Dealer from "./Dealer";
import MainScreen from "./MainScreen";
import {
  BankrollSettingsObject,
  CountingSettingsObject,
  GameSettingsObject,
  StrategySettingsObject,
} from "../SettingsObjects";
import GameHands from "./GameHands";
import GameButtons from "./GameButtons";

interface Props {
  gameSettingsObject: GameSettingsObject;
  bankrollSettingsObject: BankrollSettingsObject;
  strategySettingsObject: StrategySettingsObject;
  countingSettingsObject: CountingSettingsObject;
}

const Game = ({
  gameSettingsObject,
  bankrollSettingsObject,
  strategySettingsObject,
  countingSettingsObject,
}: Props) => {
  const [updateCounter, setUpdateCounter] = useState(false);
  const [showStrategyErrorMessage, setShowStrategyErrorMessage] =
    useState(false);
  const [showDeviationErrorMessage, setShowDeviationErrorMessage] =
    useState(false);
  const [correctChoice, setCorrectChoice] = useState(-1);
  const [blackjackGame, setBlackjackGame] = useState<BlackjackGame | null>(
    null
  );

  const started = useRef(false);

  useEffect(() => {
    if (started.current) return;
    started.current = true;
    const game = new BlackjackGame(
      gameSettingsObject,
      strategySettingsObject,
      countingSettingsObject,
      bankrollSettingsObject.bankroll
    );
    game.playGame();
    setBlackjackGame(game);
    setUpdateCounter((prev) => !prev);
  }, []);

  return (
    <div className="game">
      <MainScreen
        gameSettingsObject={gameSettingsObject}
        strategySettingsObject={strategySettingsObject}
        countingSettingsObject={countingSettingsObject}
        blackjackGame={blackjackGame}
        showStrategyErrorMessage={showStrategyErrorMessage}
        showDeviationErrorMessage={showDeviationErrorMessage}
        correctChoice={correctChoice}
        updateCounter={updateCounter}
      />
      <Dealer blackjackGame={blackjackGame} updateCounter={updateCounter} />
      <GameHands blackjackGame={blackjackGame} updateCounter={updateCounter} />
      <GameButtons
        blackjackGame={blackjackGame}
        bankrollSettingsObject={bankrollSettingsObject}
        countingSettingsObject={countingSettingsObject}
        setShowStrategyErrorMessage={setShowStrategyErrorMessage}
        setShowDeviationErrorMessage={setShowDeviationErrorMessage}
        setCorrectChoice={setCorrectChoice}
        updateCounter={updateCounter}
      />
    </div>
  );
};

export default Game;

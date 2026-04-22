import "../GameStyles/Game.css";
import {
  BankrollSettingsObject,
  CountingSettingsObject,
} from "../SettingsObjects";
import { BlackjackGame } from "./Blackjack";
import Button from "./Button";
import HandOver from "./HandOver";
import { useState } from "react";

interface Props {
  blackjackGame: BlackjackGame | null;
  bankrollSettingsObject: BankrollSettingsObject;
  countingSettingsObject: CountingSettingsObject;
  setShowStrategyErrorMessage: (val: boolean) => void;
  setShowDeviationErrorMessage: (val: boolean) => void;
  setCorrectChoice: (val: number) => void;
  setBlackjackGame: React.Dispatch<React.SetStateAction<BlackjackGame | null>>;
}

const GameButtons = ({
  blackjackGame,
  bankrollSettingsObject,
  countingSettingsObject,
  setShowStrategyErrorMessage,
  setShowDeviationErrorMessage,
  setCorrectChoice,
  setBlackjackGame,
}: Props) => {
  function refreshGame() {
    setBlackjackGame((prev) =>
      Object.assign(Object.create(Object.getPrototypeOf(prev!)), prev),
    );
  }

  function getCardsLeft() {
    let cardsLeft = blackjackGame?.shoe.size();
    if (cardsLeft == undefined) return 0;
    if (!blackjackGame?.handOver && !countingSettingsObject.countTableCards) {
      let cardsOnTable = 0;
      blackjackGame?.hands.map((hand) => (cardsOnTable += hand.cards.length));
      cardsOnTable += 2;
      cardsLeft += cardsOnTable;
    }
    return cardsLeft;
  }

  function getTrue() {
    const RC = blackjackGame?.getRunningCount() ?? 0;
    const cardsLeft = getCardsLeft();
    let divisor = 1;
    let TC = 0;
    switch (countingSettingsObject.divisor) {
      case "Quarter deck":
        divisor = 0.25;
        break;
      case "Half deck":
        divisor = 0.5;
        break;
      default:
        divisor = 1;
        break;
    }
    TC = Math.round(RC / (cardsLeft / BlackjackGame.DECK_SIZE) / divisor);
    switch (countingSettingsObject.calculation) {
      case "Floor":
        TC = Math.floor(TC);
        break;
      case "Truncate":
        TC = Math.trunc(TC);
        break;
      default:
        TC = Math.round(TC);
        break;
    }
    return TC;
  }

  function showMessage(choice: number) {
    setShowStrategyErrorMessage(false);
    setShowDeviationErrorMessage(false);
    if (!blackjackGame) return;
    let trueCount: number | undefined;
    if (countingSettingsObject.divisor != "No true count")
      trueCount = getTrue();
    const deviation = blackjackGame.getCorrectDeviation(trueCount);
    const correct =
      deviation == BlackjackGame.EMPTY
        ? blackjackGame.getCorrectChoice()
        : deviation;
    setCorrectChoice(correct);
    deviation == BlackjackGame.EMPTY
      ? setShowStrategyErrorMessage(correct != choice)
      : setShowDeviationErrorMessage(correct != choice);
  }

  return (
    <div className="game-buttons">
      <HandOver
        blackjackGame={blackjackGame}
        bankrollSettingsObject={bankrollSettingsObject}
        setShowStrategyErrorMessage={setShowStrategyErrorMessage}
        setShowDeviationErrorMessage={setShowDeviationErrorMessage}
        setBlackjackGame={setBlackjackGame}
      />
      {blackjackGame?.showHit && (
        <Button
          name="Hit"
          onClick={() => {
            showMessage(BlackjackGame.HIT);
            blackjackGame.choice = BlackjackGame.HIT;
            blackjackGame.playGame();
            refreshGame();
          }}
          width="100px"
        />
      )}
      {blackjackGame?.showStand && (
        <Button
          name="Stand"
          onClick={() => {
            showMessage(BlackjackGame.STAND);
            blackjackGame.choice = BlackjackGame.STAND;
            blackjackGame.playGame();
            refreshGame();
          }}
          width="100px"
        />
      )}
      {blackjackGame?.showDouble && (
        <Button
          name="Double"
          onClick={() => {
            showMessage(BlackjackGame.DOUBLE);
            blackjackGame.choice = BlackjackGame.DOUBLE;
            blackjackGame.playGame();
            refreshGame();
          }}
          width="100px"
        />
      )}
      {blackjackGame?.showSplit && (
        <Button
          name="Split"
          onClick={() => {
            showMessage(BlackjackGame.SPLIT);
            blackjackGame.choice = BlackjackGame.SPLIT;
            blackjackGame.playGame();
            refreshGame();
          }}
          width="100px"
        />
      )}
      {blackjackGame?.showSurrender && (
        <Button
          name="Surrender"
          onClick={() => {
            showMessage(BlackjackGame.SURRENDER);
            blackjackGame.choice = BlackjackGame.SURRENDER;
            blackjackGame.playGame();
            refreshGame();
          }}
          width="100px"
        />
      )}
      {blackjackGame?.showInsurance && (
        <div className="game-buttons">
          <Button
            name="Insurance"
            onClick={() => {
              blackjackGame.choice = BlackjackGame.INSURANCE;
              blackjackGame.playGame();
              refreshGame();
            }}
            width="100px"
          />
          <Button
            name="No Insure"
            onClick={() => {
              blackjackGame.choice = BlackjackGame.NO_INSURANCE;
              blackjackGame.playGame();
              refreshGame();
            }}
            width="100px"
          />
        </div>
      )}
    </div>
  );
};

export default GameButtons;

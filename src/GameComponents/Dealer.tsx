import { useState } from "react";
import "../GameStyles/Game.css";
import { BlackjackGame } from "./Blackjack";
import PlayingCard from "./PlayingCard";

interface Props {
  blackjackGame: BlackjackGame | null;
  updateCounter: boolean;
}

const Dealer = ({ blackjackGame, updateCounter }: Props) => {
  const handHeight = 120;
  const dealerCardSpacing = 120 * 0.8;
  const dealerCards = [...(blackjackGame?.dealer.cards || [])];
  if (!blackjackGame?.showHole) dealerCards.pop();
  const dealerHandWidth =
    (dealerCards.length - 1) * dealerCardSpacing + 50 * 0.8;

  return (
    <div
      className="game-dealer"
      key={`dealer-${updateCounter}`}
      style={{
        width: `${dealerHandWidth}px`,
        height: `${handHeight * 0.8}px`,
      }}
    >
      {dealerCards.map((card, cardIndex) => {
        if (card.rank === 0) return;
        let offset = 0;
        if (cardIndex === 0) offset += 0;
        else if (cardIndex === 1) offset += dealerCardSpacing;
        else offset += -(dealerCardSpacing * (cardIndex - 1));
        return (
          <div
            className="game-playing-card"
            key={cardIndex}
            style={{
              position: "absolute",
              left: "50%",
              transform: `translateX(calc(-50% + ${offset}px)) scale(${0.8})`,
            }}
          >
            <PlayingCard rank={card.rank} suit={card.suit} />
          </div>
        );
      })}
    </div>
  );
};

export default Dealer;

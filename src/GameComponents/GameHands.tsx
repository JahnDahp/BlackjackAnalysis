import { BlackjackGame } from "./Blackjack";
import PlayingCard from "./PlayingCard";
import "../GameStyles/Game.css";

interface Props {
  blackjackGame: BlackjackGame | null;
  updateCounter: boolean;
}

const GameHands = ({ blackjackGame, updateCounter }: Props) => {
  const handCount = blackjackGame?.hands.length ?? 0;
  const handWidth = 100;
  const handHeight = 120;
  const scale = handCount <= 4 ? 0.8 : handCount <= 6 ? 0.7 : 0.6;
  const cardSpacing = 35 * scale;

  function getCardTransform(
    cardIndex: number,
    numCards: number,
    cardSpacing: number,
    handWidth: number,
    scale: number,
  ): string {
    const totalCardSpread = (numCards - 1) * cardSpacing;
    const centerOffsetX = totalCardSpread / 2 + handWidth / 2;

    const verticalOverlap = 50;
    const yOffsetPerCard =
      numCards <= 3 ? verticalOverlap : verticalOverlap * (3 / numCards);

    const translateX = cardIndex * cardSpacing - centerOffsetX;
    const translateY = cardIndex * -yOffsetPerCard * scale;

    return `translate(${translateX}px, ${translateY}px) scale(${scale})`;
  }

  return (
    <div
      className="game-hands"
      key={`hands-${updateCounter}`}
      style={{
        gap: `${handCount <= 4 ? 150 : 100 * scale}px`,
      }}
    >
      {blackjackGame?.hands.map((hand, handIndex) => (
        <div
          key={handIndex}
          className="game-hand"
          style={{
            width: `${handWidth}px`,
            height: `${handHeight * scale}px`,
          }}
        >
          <div className="game-hand-cards">
            {hand.cards.map((card, cardIndex) => {
              return (
                <div
                  className="game-playing-card"
                  key={cardIndex}
                  style={{
                    transform: getCardTransform(
                      cardIndex,
                      hand.cards.length,
                      cardSpacing,
                      handWidth,
                      scale,
                    ),
                  }}
                >
                  <PlayingCard rank={card.rank} suit={card.suit} />
                </div>
              );
            })}
          </div>
          {handIndex === blackjackGame.currentHand &&
            blackjackGame.hands.length > 1 && (
              <div className="current-hand-indicator" />
            )}
          <h1
            className="game-label"
            style={{ top: "135%" }}
          >{`Bet: ${hand.bet}`}</h1>
        </div>
      ))}
    </div>
  );
};

export default GameHands;

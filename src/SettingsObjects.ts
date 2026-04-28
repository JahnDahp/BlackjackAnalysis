export interface Setting {
  label: string;
  options: string[];
}

export interface GameSettingsObject {
  decks: number;
  S17: boolean;
  DAS: boolean;
  doubles: number[];
  splits: number;
  LS: string;
  BJPay: number;
  pen: number;
  RSA: boolean;
  drawAces: boolean;
}

export interface BankrollSettingsObject {
  bankroll: number;
  tableMin: number;
  tableMax: number;
}

export interface StrategySettingsObject {
  showErrors: boolean;
  hardMatrix: number[][];
  softMatrix: number[][];
  splitMatrix: number[][];
  surrenderMatrix: number[][];
}

export interface CountingSettingsObject {
  tags: number[];
  IRCs: number[];
  divisor: string;
  calculation: string;
  countTableCards: boolean;
  hitStandMatrix: number[][];
  doubleMatrix: number[][];
  splitMatrix: number[][];
  surrenderMatrix: number[][];
}

export interface DealerSettingsObject {
  decks: number;
  S17: boolean;
  ENHC: boolean;
  DAS: boolean;
  BJPay: number;
  drawAces: boolean;
}

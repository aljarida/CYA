export type BackendSender = 'user' | 'system' | 'error' | 'gamemaster' | 'assistant';

export type BackendMessage = {
  sender?: BackendSender;
  role?: BackendSender;
  content: string;
};

export type BackendGameSave = {
  playerName: string;
  playerDescription: string;
  worldTheme: string;
  gameOverSummary: string;
  gameOver: boolean;
  createdAt: string;
  updatedAt: string;
  objectIDString: string;
  chatHistory: BackendMessage[];
};

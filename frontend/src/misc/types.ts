import type {
    ChangeEvent,
    KeyboardEvent,
} from 'react';

export type MessageResponse = {
  sender: 'user' | 'system' | 'error' | 'gamemaster';
  content: string;
  hitPoints?: number;
  gameOverSummary?: string;
}

export type GameInfo = {
  playerName: string;
  worldTheme: string;
  playerDescription: string;
};

export type FormFieldProps = {
  id: string;
  name: keyof GameInfo;
  label: string;
  type?: string;
  value: string;
  onChange: (e: ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => void;
  placeholder?: string;
  required?: boolean;
  isTextarea?: boolean;
};

export type SetupFormProps = {
  gameInfo: GameInfo;
  existingGames: GameSave[];
  isLoadingSaves: boolean;
  selectedSave: GameSave | null;
  setSelectedSave: (save: GameSave | null) => void;
  isFormValid: boolean;
  handleInputChange: (e: ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => void;
  onSubmit: (save: GameSave | null) => Promise<void>;
  deleteGame: (save: GameSave) => void;
};

export type SetupModalProps = {
  showModal: boolean;
  formSubmitted: boolean;
  gameInfo: GameInfo;
  isFormValid: boolean;
  handleInputChange: (e: ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => void;
  onSubmit: (save: GameSave | null) => Promise<void>;
  setIsFormValid: (val: boolean) => void;
};

export type MessageProps = {
  message: Message;
  index: number;
};

export type Message = {
  sender: 'user' | 'system' | 'error' | 'gamemaster';
  content: string;
};

export type LoadMessage = {
  objectIDString: string;
};

export type ChatHistoryMessage = {
  role: 'user' | 'system' | 'error' | 'gamemaster';
  content: string,
}


export type ChatMessagesProps = {
  messages: Message[];
};

export type ChatInputProps = {
  input: string;
  setInput: React.Dispatch<React.SetStateAction<string>>;
  onSend: () => void;
  onKeyPress: (e: KeyboardEvent<HTMLInputElement>) => void;
};

export type GameSave = {
  playerName: string
  playerDescription: string
  worldTheme: string
  gameOverSummary: string
  gameOver: boolean
  createdAt: string
  updatedAt: string
  objectIDString: string
  chatHistory: any[]
}

export type BackButtonProps = {
  unloadGame: () => void;
}
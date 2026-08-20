import type {
    ChangeEvent,
    KeyboardEvent,
} from 'react';

import type { DraftStartingState } from '../features/setup/setupTypes';

export type InventoryItem = {
  id: string;
  name: string;
  description: string;
  weightKg: number;
  quantity: number;
};

export type PlayerAttributes = {
  ageYears: number | null;
  heightCm: number | null;
  bodyWeightKg: number | null;
  maxCarryWeightKg: number;
};

export type Quest = {
  id: string;
  title: string;
  description: string;
  status: 'active' | 'resolved';
  currentStep: string;
  stepHistory: string[];
  outcome: string;
};

export type StoryMoment = {
  id: string;
  caption: string;
  imageSrc: string;
};

export type WorldState = {
  currentLocation: string;
  inventory: InventoryItem[];
  totalInventoryWeightKg: number;
  conditions: string[];
  knownNpcs: Record<string, string>;
  relationships: Record<string, string>;
  quests: Quest[];
  worldFlags: Record<string, unknown>;
};

export type MessageResponse = {
  sender: 'user' | 'system' | 'error' | 'gamemaster';
  content: string;
  hitPoints?: number;
  gameOverSummary?: string;
  worldState?: WorldState;
  playerAttributes?: PlayerAttributes;
  storySummary?: string;
  unresolvedThreads?: string[];
  moment?: StoryMoment;
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
  setupStep: 'form' | 'summary';
  draftState: DraftStartingState | null;
  onDraftChange: (next: DraftStartingState) => void;
  onRegenerateDraft: () => void;
  isRegeneratingDraft: boolean;
  onConfirmDraft: () => void;
};

export type MessageProps = {
  message: Message;
  index: number;
  gameId: string | null;
  onSuggestionClick: (suggestion: string) => void;
  closeSignal?: number;
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
  gameId: string | null;
  onSuggestionClick: (suggestion: string) => void;
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
  chatHistory: ChatHistoryMessage[]
}

export type BackButtonProps = {
  unloadGame: () => void;
}

import type {
    ChangeEvent,
    KeyboardEvent,
    FormEvent
} from 'react';

export type GameInfo = {
  playerName: string;
  worldTheme: string;
  playerDescription: string;
  worldDescription: string;
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
  isFormValid: boolean;
  handleInputChange: (e: ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => void;
  onSubmit: (e: FormEvent) => void;
};

export type SetupModalProps = {
  showModal: boolean;
  formSubmitted: boolean;
  gameInfo: GameInfo;
  isFormValid: boolean;
  handleInputChange: (e: ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => void;
  onSubmit: (e: FormEvent) => void;
};

export type MessageProps = {
  message: Message;
  index: number;
};

export type Message = {
  sender: 'user' | 'system';
  content: string;
};


export type ChatMessagesProps = {
  messages: Message[];
};

export type ChatInputProps = {
  input: string;
  setInput: React.Dispatch<React.SetStateAction<string>>;
  onSend: () => void;
  onKeyPress: (e: KeyboardEvent<HTMLInputElement>) => void;
};
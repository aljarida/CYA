import type { BackendMessage, BackendSender } from './types';
import type { ChatHistoryMessage, Message, MessageResponse } from '../misc/types';

export function toFrontendSender(sender: BackendSender | undefined): Message['sender'] {
  if (sender === 'assistant') return 'gamemaster';
  if (sender === 'user' || sender === 'system' || sender === 'error' || sender === 'gamemaster') {
    return sender;
  }
  return 'system';
}

export function toFrontendMessage(message: BackendMessage): Message {
  return {
    sender: toFrontendSender(message.sender ?? message.role),
    content: message.content,
  };
}

export function toChatHistoryMessage(message: BackendMessage): ChatHistoryMessage {
  return {
    role: toFrontendSender(message.role ?? message.sender),
    content: message.content,
  };
}

export function toMessageResponse<T extends BackendMessage & Partial<MessageResponse>>(
  response: T,
): MessageResponse {
  return {
    ...response,
    sender: toFrontendSender(response.sender ?? response.role),
    content: response.content,
  };
}

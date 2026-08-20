import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { useState } from 'react';
import { describe, expect, it, vi } from 'vitest';

import ChatInput from './ChatInput';

describe('ChatInput', () => {
  it('updates input text, sends clicks, and forwards keyboard events', async () => {
    const user = userEvent.setup();
    const setInputSpy = vi.fn();
    const onSend = vi.fn();
    const onKeyPress = vi.fn();

    function ControlledChatInput() {
      const [input, setInput] = useState('look around');

      return (
        <ChatInput
          input={input}
          setInput={(value) => {
            setInputSpy(value);
            setInput(value);
          }}
          onSend={onSend}
          onKeyPress={onKeyPress}
        />
      );
    }

    render(<ControlledChatInput />);

    const input = screen.getByPlaceholderText('What would you like to do?');
    expect(input).toHaveValue('look around');

    await user.clear(input);
    await user.type(input, 'open door{Enter}');
    await user.click(screen.getByRole('button', { name: /send/i }));

    expect(setInputSpy).toHaveBeenCalledWith('');
    expect(setInputSpy).toHaveBeenLastCalledWith('open door');
    expect(input).toHaveValue('open door');
    expect(onKeyPress).toHaveBeenCalled();
    expect(onSend).toHaveBeenCalledTimes(1);
  });
});

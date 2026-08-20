import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { getSuggestedResponses } from '../api/suggestions';
import Message from './Message';

vi.mock('../api/suggestions', () => ({
  getSuggestedResponses: vi.fn(),
}));

const mockedGetSuggestedResponses = vi.mocked(getSuggestedResponses);

describe('Message', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders normal message content without suggestion controls', () => {
    render(
      <Message
        message={{ sender: 'user', content: 'I check the map.' }}
        index={0}
        gameId="game-1"
        onSuggestionClick={vi.fn()}
      />,
    );

    expect(screen.getByText('I check the map.')).toBeInTheDocument();
    expect(screen.queryByTitle('Open response suggestions')).not.toBeInTheDocument();
  });

  it('loads and selects suggested responses for gamemaster messages', async () => {
    const user = userEvent.setup();
    const onSuggestionClick = vi.fn();
    mockedGetSuggestedResponses.mockResolvedValue(['Light a torch', 'Search the walls', 'Search the walls']);

    render(
      <Message
        message={{ sender: 'gamemaster', content: 'The corridor gets darker.' }}
        index={0}
        gameId="game-1"
        onSuggestionClick={onSuggestionClick}
      />,
    );

    await user.click(screen.getByTitle('Open response suggestions'));

    await screen.findByRole('button', { name: /light a torch/i });

    expect(mockedGetSuggestedResponses).toHaveBeenCalledWith('game-1', 3);
    expect(screen.getAllByText('Search the walls')).toHaveLength(1);

    await user.click(screen.getByRole('button', { name: /search the walls/i }));

    expect(onSuggestionClick).toHaveBeenCalledWith('Search the walls');
    await waitFor(() => {
      expect(screen.queryByRole('button', { name: /search the walls/i })).not.toBeInTheDocument();
    });
  });

  it('toggles the suggestion drawer from the same button', async () => {
    const user = userEvent.setup();
    mockedGetSuggestedResponses.mockResolvedValue(['Light a torch']);

    render(
      <Message
        message={{ sender: 'gamemaster', content: 'The corridor gets darker.' }}
        index={0}
        gameId="game-1"
        onSuggestionClick={vi.fn()}
      />,
    );

    await user.click(screen.getByTitle('Open response suggestions'));
    await screen.findByRole('button', { name: /light a torch/i });

    await user.click(screen.getByTitle('Close response suggestions'));

    expect(screen.queryByRole('button', { name: /light a torch/i })).not.toBeInTheDocument();
  });

  it('does not request suggestions without a game id', async () => {
    const user = userEvent.setup();

    render(
      <Message
        message={{ sender: 'gamemaster', content: 'A locked gate blocks you.' }}
        index={0}
        gameId={null}
        onSuggestionClick={vi.fn()}
      />,
    );

    await user.click(screen.getByTitle('Open response suggestions'));

    expect(mockedGetSuggestedResponses).not.toHaveBeenCalled();
    expect(screen.queryByText('Generating suggestions...')).not.toBeInTheDocument();
  });
});

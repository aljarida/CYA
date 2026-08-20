import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';

import Portrait from './Portrait';

describe('Portrait', () => {
  it('renders nothing without an image source', () => {
    const { container } = render(<Portrait src="" />);

    expect(container).toBeEmptyDOMElement();
  });

  it('opens and closes the enlarged portrait modal', async () => {
    const user = userEvent.setup();
    render(<Portrait src="/portrait.png" />);

    await user.click(screen.getByAltText('Player Portrait'));

    expect(screen.getByAltText('Enlarged Portrait')).toHaveAttribute('src', '/portrait.png');

    await user.click(document.body);

    expect(screen.queryByAltText('Enlarged Portrait')).not.toBeInTheDocument();
  });
});

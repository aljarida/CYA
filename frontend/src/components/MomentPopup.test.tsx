import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';

import MomentPopup from './MomentPopup';
import type { StoryMoment } from '../misc/types';

const moment: StoryMoment = {
  id: 'moment-1',
  caption: 'Iris drives back the tide-wraith.',
  imageSrc: 'data:image/png;base64,abc',
};

class InstantImage {
  onload: (() => void) | null = null;

  set src(_value: string) {
    queueMicrotask(() => this.onload?.());
  }
}

describe('MomentPopup', () => {
  it('renders nothing when there is no active moment', () => {
    const { container } = render(<MomentPopup moment={null} onDismiss={vi.fn()} />);

    expect(container).toBeEmptyDOMElement();
  });

  it('shows the caption once the image preloads and dismisses on Continue', async () => {
    vi.stubGlobal('Image', InstantImage);
    const user = userEvent.setup();
    const onDismiss = vi.fn();

    render(<MomentPopup moment={moment} onDismiss={onDismiss} />);

    expect(await screen.findByText('Iris drives back the tide-wraith.')).toBeTruthy();
    expect(screen.getByAltText('Iris drives back the tide-wraith.')).toHaveAttribute(
      'src',
      'data:image/png;base64,abc',
    );

    await user.click(screen.getByRole('button', { name: /continue/i }));

    expect(onDismiss).toHaveBeenCalledOnce();

    vi.unstubAllGlobals();
  });
});

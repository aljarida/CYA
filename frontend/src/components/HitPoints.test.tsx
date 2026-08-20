import { render } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import HitPoints from './HitPoints';

describe('HitPoints', () => {
  it('renders nothing before hit points are known', () => {
    const { container } = render(<HitPoints hitPoints={-1} />);

    expect(container).toBeEmptyDOMElement();
  });

  it('renders five heart icons once hit points are known', () => {
    const { container } = render(<HitPoints hitPoints={3} />);

    expect(container.querySelectorAll('svg')).toHaveLength(5);
    expect(container.querySelectorAll('.fill-current')).toHaveLength(3);
  });
});

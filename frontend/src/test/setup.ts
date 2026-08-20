import '@testing-library/jest-dom/vitest';
import { cleanup } from '@testing-library/react';
import { afterEach } from 'vitest';
import { vi } from 'vitest';

Element.prototype.scrollIntoView = vi.fn();

afterEach(() => {
  cleanup();
});

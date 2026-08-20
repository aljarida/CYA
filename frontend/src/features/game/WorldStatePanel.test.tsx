import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';

import WorldStatePanel from './WorldStatePanel';
import type { PlayerAttributes, StoryMoment, WorldState } from '../../misc/types';

const emptyWorldState: WorldState = {
  currentLocation: '',
  inventory: [],
  totalInventoryWeightKg: 0,
  conditions: [],
  knownNpcs: {},
  relationships: {},
  quests: [],
  worldFlags: {},
};

const fullWorldState: WorldState = {
  currentLocation: 'Glass Market',
  inventory: [
    { id: 'item-1', name: 'brass key', description: 'an ornate key', weightKg: 0.1, quantity: 1 },
    { id: 'item-2', name: 'coin purse', description: '', weightKg: 0.3, quantity: 2 },
  ],
  totalInventoryWeightKg: 0.7,
  conditions: ['tired'],
  knownNpcs: { Iris: 'glassmaker', Edo: 'merchant' },
  relationships: { Iris: 'ally' },
  quests: [
    {
      id: 'quest-1',
      title: 'find the lantern',
      description: '',
      status: 'active',
      currentStep: 'check the cellar',
      stepHistory: [],
      outcome: '',
    },
    {
      id: 'quest-2',
      title: 'cross the causeway',
      description: '',
      status: 'resolved',
      currentStep: '',
      stepHistory: ['ask the ferryman'],
      outcome: 'Made it across safely.',
    },
  ],
  worldFlags: { gate_open: true },
};

const fullPlayerAttributes: PlayerAttributes = {
  ageYears: 29,
  heightCm: 170,
  bodyWeightKg: 65,
  maxCarryWeightKg: 20,
};

const emptyPlayerAttributes: PlayerAttributes = {
  ageYears: null,
  heightCm: null,
  bodyWeightKg: null,
  maxCarryWeightKg: 40,
};

const fullMoments: StoryMoment[] = [
  { id: 'moment-1', caption: 'Iris drives back the tide-wraith.', imageSrc: 'data:image/png;base64,abc' },
];

describe('WorldStatePanel', () => {
  it('renders nothing visible when closed', () => {
    const { container } = render(
      <WorldStatePanel
        worldState={fullWorldState}
        playerAttributes={fullPlayerAttributes}
        isOpen={false}
        onClose={vi.fn()}
        onDiscard={vi.fn()}
      />,
    );

    const panel = container.querySelector('.translate-x-0');
    expect(panel).toBeNull();
  });

  it('slides in when open', () => {
    const { container } = render(
      <WorldStatePanel
        worldState={fullWorldState}
        playerAttributes={fullPlayerAttributes}
        isOpen={true}
        onClose={vi.fn()}
        onDiscard={vi.fn()}
      />,
    );

    const panel = container.querySelector('.translate-x-0');
    expect(panel).not.toBeNull();
  });

  it('shows placeholder message when worldState is null', () => {
    render(
      <WorldStatePanel
        worldState={null}
        playerAttributes={null}
        isOpen={true}
        onClose={vi.fn()}
        onDiscard={vi.fn()}
      />,
    );

    expect(screen.getByText(/no game state available/i)).toBeTruthy();
  });

  it('displays location, inventory items with weight, and NPC names', () => {
    render(
      <WorldStatePanel
        worldState={fullWorldState}
        playerAttributes={fullPlayerAttributes}
        isOpen={true}
        onClose={vi.fn()}
        onDiscard={vi.fn()}
      />,
    );

    expect(screen.getByText('Glass Market')).toBeTruthy();
    expect(screen.getByText('brass key')).toBeTruthy();
    expect(screen.getByText('an ornate key')).toBeTruthy();
    expect(screen.getByText('coin purse')).toBeTruthy();
    expect(screen.getByText('x2')).toBeTruthy();
    expect(screen.getByText('Iris')).toBeTruthy();
    expect(screen.getByText('Edo')).toBeTruthy();
  });

  it('shows the character section with age, height, and body weight', () => {
    render(
      <WorldStatePanel
        worldState={fullWorldState}
        playerAttributes={fullPlayerAttributes}
        isOpen={true}
        onClose={vi.fn()}
        onDiscard={vi.fn()}
      />,
    );

    expect(screen.getByText('29')).toBeTruthy();
    expect(screen.getByText('170cm')).toBeTruthy();
    expect(screen.getByText('65kg')).toBeTruthy();
  });

  it('shows dash placeholder for empty character attributes', () => {
    render(
      <WorldStatePanel
        worldState={emptyWorldState}
        playerAttributes={emptyPlayerAttributes}
        isOpen={true}
        onClose={vi.fn()}
        onDiscard={vi.fn()}
      />,
    );

    const dashes = screen.getAllByText('—');
    expect(dashes.length).toBeGreaterThan(0);
  });

  it('shows the carry weight bar when inventory is non-empty', () => {
    render(
      <WorldStatePanel
        worldState={fullWorldState}
        playerAttributes={fullPlayerAttributes}
        isOpen={true}
        onClose={vi.fn()}
        onDiscard={vi.fn()}
      />,
    );

    expect(screen.getByText('0.7 / 20.0 kg')).toBeTruthy();
  });

  it('calls onDiscard with the item id when the discard button is clicked', async () => {
    const onDiscard = vi.fn();
    render(
      <WorldStatePanel
        worldState={fullWorldState}
        playerAttributes={fullPlayerAttributes}
        isOpen={true}
        onClose={vi.fn()}
        onDiscard={onDiscard}
      />,
    );

    await userEvent.click(screen.getByTitle('Discard brass key'));

    expect(onDiscard).toHaveBeenCalledWith('item-1');
  });

  it('shows relationship under NPC name', () => {
    render(
      <WorldStatePanel
        worldState={fullWorldState}
        playerAttributes={fullPlayerAttributes}
        isOpen={true}
        onClose={vi.fn()}
        onDiscard={vi.fn()}
      />,
    );

    expect(screen.getByText('ally')).toBeTruthy();
  });

  it('shows active quests with their current step', () => {
    render(
      <WorldStatePanel
        worldState={fullWorldState}
        playerAttributes={fullPlayerAttributes}
        isOpen={true}
        onClose={vi.fn()}
        onDiscard={vi.fn()}
      />,
    );

    expect(screen.getByText('find the lantern')).toBeTruthy();
    expect(screen.getByText('Next: check the cellar')).toBeTruthy();
  });

  it('shows resolved quests with their outcome text', () => {
    render(
      <WorldStatePanel
        worldState={fullWorldState}
        playerAttributes={fullPlayerAttributes}
        isOpen={true}
        onClose={vi.fn()}
        onDiscard={vi.fn()}
      />,
    );

    expect(screen.getByText('cross the causeway')).toBeTruthy();
    expect(screen.getByText('Made it across safely.')).toBeTruthy();
  });

  it('labels the conditions section as Health Status', () => {
    render(
      <WorldStatePanel
        worldState={fullWorldState}
        playerAttributes={fullPlayerAttributes}
        isOpen={true}
        onClose={vi.fn()}
        onDiscard={vi.fn()}
      />,
    );

    expect(screen.getByText('Health Status')).toBeTruthy();
    expect(screen.getByText('tired')).toBeTruthy();
  });

  it('shows dash placeholder for empty inventory', () => {
    render(
      <WorldStatePanel
        worldState={emptyWorldState}
        playerAttributes={emptyPlayerAttributes}
        isOpen={true}
        onClose={vi.fn()}
        onDiscard={vi.fn()}
      />,
    );

    const dashes = screen.getAllByText('—');
    expect(dashes.length).toBeGreaterThan(0);
  });

  it('calls onClose when backdrop is clicked', async () => {
    const onClose = vi.fn();
    const { container } = render(
      <WorldStatePanel
        worldState={fullWorldState}
        playerAttributes={fullPlayerAttributes}
        isOpen={true}
        onClose={onClose}
        onDiscard={vi.fn()}
      />,
    );

    const backdrop = container.querySelector('.bg-black\\/30');
    await userEvent.click(backdrop!);

    expect(onClose).toHaveBeenCalledOnce();
  });

  it('calls onClose when X button is clicked', async () => {
    const onClose = vi.fn();
    render(
      <WorldStatePanel
        worldState={fullWorldState}
        playerAttributes={fullPlayerAttributes}
        isOpen={true}
        onClose={onClose}
        onDiscard={vi.fn()}
      />,
    );

    await userEvent.click(screen.getByRole('button', { name: '' }));

    expect(onClose).toHaveBeenCalledOnce();
  });

  it('hides conditions and quests sections when empty', () => {
    render(
      <WorldStatePanel
        worldState={emptyWorldState}
        playerAttributes={emptyPlayerAttributes}
        isOpen={true}
        onClose={vi.fn()}
        onDiscard={vi.fn()}
      />,
    );

    expect(screen.queryByText(/health status/i)).toBeNull();
    expect(screen.queryByText(/quests/i)).toBeNull();
  });

  it('hides story so far and moments sections when there is no story data', () => {
    render(
      <WorldStatePanel
        worldState={emptyWorldState}
        playerAttributes={emptyPlayerAttributes}
        isOpen={true}
        onClose={vi.fn()}
        onDiscard={vi.fn()}
      />,
    );

    expect(screen.queryByText(/story so far/i)).toBeNull();
    expect(screen.queryByText(/^moments$/i)).toBeNull();
  });

  it('shows the story summary and unresolved threads', () => {
    render(
      <WorldStatePanel
        worldState={emptyWorldState}
        playerAttributes={emptyPlayerAttributes}
        isOpen={true}
        onClose={vi.fn()}
        onDiscard={vi.fn()}
        storySummary="Iris crossed the flooded causeway."
        unresolvedThreads={['Find the lantern']}
      />,
    );

    expect(screen.getByText('Story So Far')).toBeTruthy();
    expect(screen.getByText('Iris crossed the flooded causeway.')).toBeTruthy();
    expect(screen.getByText('Find the lantern')).toBeTruthy();
  });

  it('shows a moment thumbnail and enlarges it on click', async () => {
    render(
      <WorldStatePanel
        worldState={emptyWorldState}
        playerAttributes={emptyPlayerAttributes}
        isOpen={true}
        onClose={vi.fn()}
        onDiscard={vi.fn()}
        moments={fullMoments}
      />,
    );

    expect(screen.getByText('Moments')).toBeTruthy();
    const thumbnails = screen.getAllByAltText('Iris drives back the tide-wraith.');
    expect(thumbnails).toHaveLength(1);

    await userEvent.click(thumbnails[0]);

    expect(screen.getAllByAltText('Iris drives back the tide-wraith.')).toHaveLength(2);
  });
});

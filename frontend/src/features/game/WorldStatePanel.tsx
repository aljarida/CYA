import { useState } from 'react';
import { ChevronDown, ChevronRight, Trash2, X } from 'lucide-react';
import type { InventoryItem, PlayerAttributes, Quest, StoryMoment, WorldState } from '../../misc/types';

type WorldStatePanelProps = {
  worldState: WorldState | null;
  playerAttributes: PlayerAttributes | null;
  isOpen: boolean;
  onClose: () => void;
  onDiscard: (itemId: string) => void;
  moments?: StoryMoment[];
  storySummary?: string;
  unresolvedThreads?: string[];
};

type SectionProps = {
  title: string;
  children: React.ReactNode;
  isEmpty?: boolean;
};

function Section({ title, children, isEmpty }: SectionProps) {
  const [expanded, setExpanded] = useState(true);

  return (
    <div className="border-b border-white/10 last:border-0">
      <button
        className="flex w-full items-center gap-2 px-4 py-2.5 text-white/50 hover:text-white/80 text-xs uppercase tracking-widest transition-colors"
        onClick={() => setExpanded(e => !e)}
      >
        {expanded
          ? <ChevronDown size={11} className="shrink-0" />
          : <ChevronRight size={11} className="shrink-0" />
        }
        {title}
      </button>
      {expanded && (
        <div className="px-4 pb-3">
          {isEmpty
            ? <p className="text-white/25 text-sm italic">—</p>
            : children
          }
        </div>
      )}
    </div>
  );
}

function BulletList({ items }: { items: string[] }) {
  return (
    <ul className="space-y-1">
      {items.map(item => (
        <li key={item} className="text-white/75 text-sm flex items-start gap-2">
          <span className="text-white/30 mt-0.5 shrink-0">•</span>
          <span>{item}</span>
        </li>
      ))}
    </ul>
  );
}

function InventoryWeightBar({ totalWeightKg, maxCarryWeightKg }: { totalWeightKg: number; maxCarryWeightKg: number }) {
  const ratio = maxCarryWeightKg > 0 ? Math.min(1, totalWeightKg / maxCarryWeightKg) : 0;
  const isNearCapacity = ratio > 0.85;

  return (
    <div className="px-4 pb-2">
      <div className="flex items-center justify-between text-[11px] text-white/40 mb-1">
        <span>Carry weight</span>
        <span>{totalWeightKg.toFixed(1)} / {maxCarryWeightKg.toFixed(1)} kg</span>
      </div>
      <div className="h-1 rounded-full bg-white/10 overflow-hidden">
        <div
          className={`h-full rounded-full transition-all ${isNearCapacity ? 'bg-amber-400/70' : 'bg-white/40'}`}
          style={{ width: `${ratio * 100}%` }}
        />
      </div>
    </div>
  );
}

function InventoryList({ items, onDiscard }: { items: InventoryItem[]; onDiscard: (itemId: string) => void }) {
  return (
    <ul className="space-y-2">
      {items.map(item => (
        <li key={item.id} className="flex items-start justify-between gap-2 text-sm">
          <div className="flex-1 min-w-0">
            <p className="text-white/75 flex items-baseline gap-1.5">
              <span className="truncate">{item.name}</span>
              {item.quantity > 1 && <span className="text-white/40 text-xs shrink-0">x{item.quantity}</span>}
              <span className="text-white/30 text-xs shrink-0">{item.weightKg}kg</span>
            </p>
            {item.description && (
              <p className="text-white/45 text-xs mt-0.5 leading-relaxed">{item.description}</p>
            )}
          </div>
          <button
            onClick={() => onDiscard(item.id)}
            className="p-1 rounded hover:bg-white/10 text-white/30 hover:text-red-400/80 transition-colors shrink-0"
            title={`Discard ${item.name}`}
          >
            <Trash2 size={13} />
          </button>
        </li>
      ))}
    </ul>
  );
}

function QuestList({ quests }: { quests: Quest[] }) {
  const activeQuests = quests.filter(q => q.status === 'active');
  const resolvedQuests = quests.filter(q => q.status === 'resolved');

  return (
    <>
      {activeQuests.length > 0 && (
        <div className="mb-3">
          <p className="text-white/35 text-xs uppercase tracking-wider mb-1.5">Active</p>
          <ul className="space-y-2">
            {activeQuests.map(q => (
              <li key={q.id} className="text-sm flex items-start gap-2">
                <span className="text-amber-400/60 mt-0.5 shrink-0">◆</span>
                <div>
                  <p className="text-white/75">{q.title}</p>
                  {q.currentStep && (
                    <p className="text-white/45 text-xs mt-0.5">Next: {q.currentStep}</p>
                  )}
                </div>
              </li>
            ))}
          </ul>
        </div>
      )}
      {resolvedQuests.length > 0 && (
        <div>
          <p className="text-white/35 text-xs uppercase tracking-wider mb-1.5">Resolved</p>
          <ul className="space-y-2">
            {resolvedQuests.map(q => (
              <li key={q.id} className="text-sm flex items-start gap-2">
                <span className="text-white/20 mt-0.5 shrink-0">◆</span>
                <div>
                  <p className="text-white/35 line-through">{q.title}</p>
                  {q.outcome && (
                    <p className="text-white/40 text-xs mt-0.5">{q.outcome}</p>
                  )}
                </div>
              </li>
            ))}
          </ul>
        </div>
      )}
    </>
  );
}

function MomentGallery({ moments }: { moments: StoryMoment[] }) {
  const [enlarged, setEnlarged] = useState<StoryMoment | null>(null);

  return (
    <>
      <div className="grid grid-cols-3 gap-2">
        {moments.map(moment => (
          <button
            key={moment.id}
            onClick={() => setEnlarged(moment)}
            className="aspect-square rounded-md overflow-hidden border border-white/10 hover:border-white/30 transition-colors"
          >
            <img src={moment.imageSrc} alt={moment.caption} className="w-full h-full object-cover" />
          </button>
        ))}
      </div>

      {enlarged && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4"
          onClick={() => setEnlarged(null)}
        >
          <div className="max-w-xl w-full" onClick={e => e.stopPropagation()}>
            <img
              src={enlarged.imageSrc}
              alt={enlarged.caption}
              className="w-full rounded-xl object-contain max-h-[70vh]"
            />
            <p className="text-white/80 text-sm text-center mt-3 italic">{enlarged.caption}</p>
          </div>
        </div>
      )}
    </>
  );
}

function WorldStatePanel({
  worldState,
  playerAttributes,
  isOpen,
  onClose,
  onDiscard,
  moments = [],
  storySummary = '',
  unresolvedThreads = [],
}: WorldStatePanelProps) {
  const hasConditions = (worldState?.conditions.length ?? 0) > 0;
  const hasQuests = (worldState?.quests.length ?? 0) > 0;
  const hasFlags = Object.keys(worldState?.worldFlags ?? {}).length > 0;
  const hasPeople = Object.keys(worldState?.knownNpcs ?? {}).length > 0;
  const hasAttributes = Boolean(
    playerAttributes && (playerAttributes.ageYears || playerAttributes.heightCm || playerAttributes.bodyWeightKg)
  );
  const hasStorySummary = Boolean(storySummary.trim()) || unresolvedThreads.length > 0;
  const hasMoments = moments.length > 0;

  return (
    <>
      {isOpen && (
        <div
          className="absolute inset-0 z-20 bg-black/30 backdrop-blur-[1px]"
          onClick={onClose}
        />
      )}
      <div
        className={`absolute inset-y-0 left-0 z-30 w-72 bg-neutral-900/95 backdrop-blur-md flex flex-col overflow-hidden transition-transform duration-300 ease-in-out ${
          isOpen ? 'translate-x-0' : '-translate-x-full'
        }`}
      >
        <div className="flex items-center justify-between px-4 py-3 border-b border-white/10 shrink-0">
          <h2 className="text-white/70 font-medium text-sm tracking-wide">Journal</h2>
          <button
            onClick={onClose}
            className="p-1.5 rounded-full hover:bg-white/10 text-white/40 hover:text-white/70 transition-colors"
          >
            <X size={14} />
          </button>
        </div>

        {!worldState ? (
          <p className="p-4 text-white/30 text-sm italic">No game state available.</p>
        ) : (
          <div className="overflow-y-auto flex-1 scrollbar-thin">
            <Section title="Location" isEmpty={!worldState.currentLocation}>
              <p className="text-white/75 text-sm">{worldState.currentLocation}</p>
            </Section>

            {hasStorySummary && (
              <Section title="Story So Far">
                <div className="space-y-3">
                  {storySummary.trim() && (
                    <p className="text-white/75 text-sm leading-relaxed">{storySummary}</p>
                  )}
                  {unresolvedThreads.length > 0 && (
                    <div>
                      <p className="text-white/35 text-xs uppercase tracking-wider mb-1.5">Unresolved</p>
                      <BulletList items={unresolvedThreads} />
                    </div>
                  )}
                </div>
              </Section>
            )}

            <Section title="Character" isEmpty={!hasAttributes}>
              <dl className="space-y-1">
                {playerAttributes?.ageYears != null && (
                  <div className="flex gap-2 items-baseline">
                    <dt className="text-white/45 text-xs shrink-0">Age:</dt>
                    <dd className="text-white/70 text-xs">{playerAttributes.ageYears}</dd>
                  </div>
                )}
                {playerAttributes?.heightCm != null && (
                  <div className="flex gap-2 items-baseline">
                    <dt className="text-white/45 text-xs shrink-0">Height:</dt>
                    <dd className="text-white/70 text-xs">{playerAttributes.heightCm}cm</dd>
                  </div>
                )}
                {playerAttributes?.bodyWeightKg != null && (
                  <div className="flex gap-2 items-baseline">
                    <dt className="text-white/45 text-xs shrink-0">Weight:</dt>
                    <dd className="text-white/70 text-xs">{playerAttributes.bodyWeightKg}kg</dd>
                  </div>
                )}
              </dl>
            </Section>

            <Section title="Inventory" isEmpty={worldState.inventory.length === 0}>
              <InventoryList items={worldState.inventory} onDiscard={onDiscard} />
            </Section>
            {worldState.inventory.length > 0 && playerAttributes && (
              <InventoryWeightBar
                totalWeightKg={worldState.totalInventoryWeightKg}
                maxCarryWeightKg={playerAttributes.maxCarryWeightKg}
              />
            )}

            {hasConditions && (
              <Section title="Health Status">
                <BulletList items={worldState.conditions} />
              </Section>
            )}

            <Section title="People" isEmpty={!hasPeople}>
              <dl className="space-y-3">
                {Object.entries(worldState.knownNpcs).map(([name, desc]) => (
                  <div key={name}>
                    <dt className="text-white/80 text-sm font-medium">{name}</dt>
                    {worldState.relationships[name] && (
                      <dd className="text-white/40 text-xs italic ml-2 mt-0.5">
                        {worldState.relationships[name]}
                      </dd>
                    )}
                    {desc && (
                      <dd className="text-white/55 text-xs ml-2 mt-0.5 leading-relaxed">{desc}</dd>
                    )}
                  </div>
                ))}
              </dl>
            </Section>

            {hasQuests && (
              <Section title="Quests">
                <QuestList quests={worldState.quests} />
              </Section>
            )}

            {hasMoments && (
              <Section title="Moments">
                <MomentGallery moments={moments} />
              </Section>
            )}

            {hasFlags && (
              <Section title="World Flags">
                <dl className="space-y-1">
                  {Object.entries(worldState.worldFlags).map(([k, v]) => (
                    <div key={k} className="flex gap-2 items-baseline">
                      <dt className="text-white/45 text-xs shrink-0">{k}:</dt>
                      <dd className="text-white/70 text-xs">{String(v)}</dd>
                    </div>
                  ))}
                </dl>
              </Section>
            )}
          </div>
        )}
      </div>
    </>
  );
}

export default WorldStatePanel;

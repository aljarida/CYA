import { useState } from 'react';

import { generateStartingState } from '../../api/chargen';
import { discardItem as discardItemApi } from '../../api/inventory';
import { initializeGame, loadGame } from '../../api/games';
import { getMoments } from '../../api/moments';
import type { DraftStartingState } from '../setup/setupTypes';
import type {
  GameInfo,
  GameSave,
  LoadMessage,
  Message,
  MessageResponse,
  PlayerAttributes,
  StoryMoment,
  WorldState,
} from '../../misc/types';

const emptyGameInfo: GameInfo = {
  playerName: '',
  worldTheme: '',
  playerDescription: '',
};

type SetupStep = 'form' | 'summary';

type UseGameSessionArgs = {
  addMessage: (message: Message) => void;
  clearMessages: () => void;
};

export function useGameSession({ addMessage, clearMessages }: UseGameSessionArgs) {
  const [showModal, setShowModal] = useState(true);
  const [formSubmitted, setFormSubmitted] = useState(false);
  const [setupStep, setSetupStep] = useState<SetupStep>('form');
  const [draftState, setDraftState] = useState<DraftStartingState | null>(null);
  const [isRegeneratingDraft, setIsRegeneratingDraft] = useState(false);
  const [portraitSrc, setPortraitSrc] = useState<string>('');
  const [worldBackdropSrc, setWorldBackdropSrc] = useState<string>('');
  const [hitPoints, setHitPoints] = useState<number>(-1);
  const [gameId, setGameId] = useState<string | null>(null);
  const [gameInfo, setGameInfo] = useState(emptyGameInfo);
  const [isFormValid, setIsFormValid] = useState(false);
  const [worldState, setWorldState] = useState<WorldState | null>(null);
  const [playerAttributes, setPlayerAttributes] = useState<PlayerAttributes | null>(null);
  const [storySummary, setStorySummary] = useState<string>('');
  const [unresolvedThreads, setUnresolvedThreads] = useState<string[]>([]);
  const [moments, setMoments] = useState<StoryMoment[]>([]);
  const [activeMoment, setActiveMoment] = useState<StoryMoment | null>(null);

  const loadMoments = async (id: string) => {
    setMoments(await getMoments(id));
  };

  const updateSessionMedia = (data: {
    gameId?: string;
    hitPoints: number;
    portraitSrc: string;
    worldBackdropSrc: string;
  }) => {
    if (data.gameId) {
      setGameId(data.gameId);
    }
    setHitPoints(data.hitPoints);
    setPortraitSrc(data.portraitSrc);
    setWorldBackdropSrc(data.worldBackdropSrc);
  };

  const startOrLoadGame = async (selectedSave: GameSave) => {
    setFormSubmitted(true);

    const loadMessage: LoadMessage = {
      objectIDString: selectedSave.objectIDString,
    };
    const result = await loadGame(loadMessage);
    const data = result.data;

    if (!result.ok) {
      addMessage({ sender: 'error', content: data.content || `Failed to load game. Status: ${result.status}` });
      setFormSubmitted(false);
      return;
    }

    addMessage({ sender: data.sender, content: data.content });

    selectedSave.chatHistory.forEach((message, idx) => {
      if (idx === 0) return;
      addMessage({ sender: message.role, content: message.content });
    });

    if (selectedSave.gameOverSummary) {
      addMessage({ sender: 'system', content: 'Oh, no! Unfortunately, you have died!' });
      addMessage({ sender: 'system', content: selectedSave.gameOverSummary });
    }

    updateSessionMedia(data);
    if (data.worldState) setWorldState(data.worldState);
    if (data.playerAttributes) setPlayerAttributes(data.playerAttributes);
    setStorySummary(data.storySummary ?? '');
    setUnresolvedThreads(data.unresolvedThreads ?? []);
    if (data.gameId) void loadMoments(data.gameId);

    setShowModal(false);
    setGameInfo(emptyGameInfo);
  };

  const generateDraft = async (info: GameInfo) => {
    setFormSubmitted(true);

    const result = await generateStartingState(info);

    if (!result.ok) {
      addMessage({
        sender: 'error',
        content: (result.data as { content?: string })?.content || `Failed to generate character. Status: ${result.status}`,
      });
      setFormSubmitted(false);
      return;
    }

    setDraftState(result.data);
    setSetupStep('summary');
    setFormSubmitted(false);
  };

  const regenerateDraft = async () => {
    setIsRegeneratingDraft(true);

    const result = await generateStartingState(gameInfo);

    if (!result.ok) {
      addMessage({
        sender: 'error',
        content: (result.data as { content?: string })?.content || `Failed to regenerate character. Status: ${result.status}`,
      });
    } else {
      setDraftState(result.data);
    }

    setIsRegeneratingDraft(false);
  };

  const confirmAndStart = async () => {
    if (!draftState) return;

    setFormSubmitted(true);
    const result = await initializeGame(gameInfo, draftState);
    const data = result.data;

    if (!result.ok) {
      addMessage({
        sender: 'error',
        content: data.content || `Failed to initialize game. Status: ${result.status}`,
      });
      setFormSubmitted(false);
      return;
    }

    addMessage({
      sender: 'system',
      content: `Welcome to your adventure, ${gameInfo.playerName}! Simply start typing to get started!`,
    });
    updateSessionMedia(data);
    if (data.worldState) setWorldState(data.worldState);
    if (data.playerAttributes) setPlayerAttributes(data.playerAttributes);
    setStorySummary(data.storySummary ?? '');
    setUnresolvedThreads(data.unresolvedThreads ?? []);
    setMoments([]);

    setShowModal(false);
    setGameInfo(emptyGameInfo);
    setDraftState(null);
    setSetupStep('form');
  };

  const applyResponseEffects = (data: MessageResponse | null) => {
    if (!data) return;

    if (typeof data.hitPoints === 'number') {
      setHitPoints((previousHitPoints) => {
        const lostHitpoints = previousHitPoints - data.hitPoints!;
        if (lostHitpoints > 0 && data.hitPoints! > 0) {
          addMessage({ sender: 'system', content: `You lost ${lostHitpoints} health!` });
        }
        return data.hitPoints!;
      });
    }

    if (data.worldState) {
      setWorldState(data.worldState);
    }

    if (data.playerAttributes) {
      setPlayerAttributes(data.playerAttributes);
    }

    if (typeof data.storySummary === 'string') {
      setStorySummary(data.storySummary);
    }

    if (data.unresolvedThreads) {
      setUnresolvedThreads(data.unresolvedThreads);
    }

    if (data.moment) {
      const moment = data.moment;
      setMoments(previousMoments => [...previousMoments, moment]);
      setActiveMoment(moment);
    }
  };

  const dismissMoment = () => {
    setActiveMoment(null);
  };

  const discardItem = async (itemId: string) => {
    if (!gameId) return;

    const result = await discardItemApi(gameId, itemId);
    const data = result.data;

    if (result.ok) {
      addMessage({ sender: 'system', content: data.content });
      if (data.worldState) setWorldState(data.worldState);
    } else {
      addMessage({ sender: 'error', content: data.content || 'Failed to discard item.' });
    }
  };

  const unloadGame = () => {
    clearMessages();
    setPortraitSrc('');
    setWorldBackdropSrc('');
    setHitPoints(-1);
    setFormSubmitted(false);
    setSetupStep('form');
    setDraftState(null);
    setGameId(null);
    setWorldState(null);
    setPlayerAttributes(null);
    setStorySummary('');
    setUnresolvedThreads([]);
    setMoments([]);
    setActiveMoment(null);
    setShowModal(true);
  };

  return {
    showModal,
    formSubmitted,
    setupStep,
    draftState,
    setDraftState,
    isRegeneratingDraft,
    portraitSrc,
    worldBackdropSrc,
    hitPoints,
    gameId,
    gameInfo,
    setGameInfo,
    isFormValid,
    setIsFormValid,
    worldState,
    playerAttributes,
    storySummary,
    unresolvedThreads,
    moments,
    activeMoment,
    dismissMoment,
    startOrLoadGame,
    generateDraft,
    regenerateDraft,
    confirmAndStart,
    applyResponseEffects,
    discardItem,
    unloadGame,
  };
}

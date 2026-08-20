# Frontend Structure Review

## Current Shape

The frontend is small enough to understand, but several responsibilities are currently concentrated in a few places:

- `App.tsx` owns setup form state, game session state, API calls for starting/loading games, chat orchestration, health updates, media state, and layout.
- `useChat` owns both chat UI state and the `/api/response` side effect.
- `SetupModal` owns save-list fetching, save deletion, form validation, selected-save state, and modal rendering.
- `Message` renders a message bubble, fetches suggested responses, owns suggestion popover state, and handles click-away behavior.
- `misc/types.ts` mixes UI prop types, API DTOs, domain-ish types, and utility payloads in one file.

None of this requires an object-oriented rewrite. The main opportunity is to introduce clearer functional boundaries around API access, data normalization, and state orchestration.

## Main Problems

### 1. API Contracts Are Spread Across UI Components

API URLs and request details are used directly from components and hooks:

- `App.tsx` calls initialize/load endpoints.
- `SetupModal.tsx` fetches existing games and deletes saves.
- `useChat.ts` posts chat responses.
- `Message.tsx` fetches suggestions.

This makes components harder to test and makes backend contract changes show up as UI rewrites. It also allows subtle mismatches, such as saved chat history using backend `assistant` roles while UI messages expect `gamemaster`.

Recommended direction:

- Create a small `src/api/` folder.
- Keep fetch mechanics in one `client.ts`.
- Put endpoint-specific functions in modules such as `games.ts`, `chat.ts`, and `suggestions.ts`.
- Normalize backend response shapes before they reach components.

Example target structure:

```text
src/api/
  client.ts
  games.ts
  chat.ts
  suggestions.ts
```

The API layer should return frontend-ready types. For example, a saved message with backend role `assistant` should become a UI message with sender `gamemaster` before `App` or `ChatMessages` sees it.

### 2. `App.tsx` Is Doing Too Much Orchestration

`App.tsx` currently acts as page component, game controller, setup controller, and chat-health coordinator. That is why changes tend to touch it even when the UI change is local.

Recommended direction:

- Keep `App.tsx` mostly as composition/layout.
- Move game session behavior into a hook, for example `useGameSession`.
- Let that hook own:
  - `gameId`
  - `hitPoints`
  - `portraitSrc`
  - `worldBackdropSrc`
  - start game
  - load game
  - unload game
  - apply response effects such as health loss messages

This is not OOD. It is just extracting related state transitions into a functional state hook.

Example target structure:

```text
src/features/game/
  useGameSession.ts
  gameMappers.ts
  gameTypes.ts
```

### 3. Chat State and Game Response Effects Are Coupled

`useChat` handles message input, message history, post-response rendering, and backend calls. `App.tsx` then adds health-related system messages after `sendMessage` returns.

That split makes health updates easy to duplicate. In fact, the same health-loss logic appears once for normal send and once for suggestion click.

Recommended direction:

- Keep `useChat` focused on chat draft/history mechanics.
- Put "send player action to backend and apply resulting game effects" in one place.
- Expose one handler for both typed input and suggestion clicks.

This would remove the duplicate health-loss block in `App.tsx` and make it easier to test game-response behavior directly.

### 4. Setup Modal Mixes Data Loading, Form Rules, and Rendering

`SetupModal` currently:

- Fetches existing saves.
- Deletes saves.
- Computes whether the new-game form is valid.
- Tracks selected save.
- Renders the modal shell.

`SetupForm` also owns the two-click delete confirmation behavior.

Recommended direction:

- Extract save-list behavior into `useSavedGames`.
- Extract setup form validity into a pure function such as `isValidGameInfo(gameInfo, existingGames)`.
- Keep `SetupModal` as a coordinator between the modal shell and `SetupForm`.

Example target structure:

```text
src/features/setup/
  SetupModal.tsx
  SetupForm.tsx
  useSavedGames.ts
  setupValidation.ts
```

This keeps form logic testable without rendering the modal.

### 5. Types Need Separation by Purpose

`misc/types.ts` has become a catch-all. It includes:

- UI component props.
- Backend response shapes.
- Domain concepts like game saves and messages.
- Request payloads.

As the app grows, this file will become a dependency magnet.

Recommended direction:

- Keep prop types near their components unless shared widely.
- Put API DTO types near API modules.
- Put frontend domain types in a small domain file.

Example target structure:

```text
src/domain/
  messages.ts
  game.ts

src/api/
  gameDtos.ts
```

A useful distinction:

- DTO types describe what the backend sends.
- Domain/UI types describe what the frontend wants to work with.
- Mapper functions convert DTOs to domain/UI types.

This would have caught the `assistant` versus `gamemaster` mismatch more clearly.

### 6. `misc` Is Too Vague

`misc` currently contains request helpers, enums/constants, timestamp formatting, and types. The name does not tell future readers what belongs there.

Recommended direction:

- Rename by responsibility over time.
- Possible replacements:
  - `api/` for request helpers and endpoint functions.
  - `utils/` for pure formatting helpers.
  - `domain/` for shared app types.
  - `constants/` only if constants remain truly cross-cutting.

Avoid creating a large `utils` bucket that becomes the new `misc`.

## Suggested Target Layout

One practical end-state:

```text
src/
  api/
    client.ts
    chat.ts
    games.ts
    suggestions.ts
    types.ts

  domain/
    game.ts
    messages.ts

  features/
    chat/
      ChatInput.tsx
      ChatMessages.tsx
      Message.tsx
      useChatDraft.ts
      useSuggestions.ts

    game/
      GameScreen.tsx
      useGameSession.ts
      gameMappers.ts

    setup/
      SetupModal.tsx
      SetupForm.tsx
      useSavedGames.ts
      setupValidation.ts

  components/
    BackButton.tsx
    FormField.tsx
    HitPoints.tsx
    LoadingState.tsx
    Portrait.tsx
    WorldBackdrop.tsx

  utils/
    prettyTimestamp.ts

  App.tsx
  main.tsx
```

This keeps shared visual primitives in `components/`, while feature-specific components live next to the feature state and API glue they depend on.

## Refactor Order

### Step 1. Add API Functions Without Moving UI

Create endpoint wrappers first:

- `getExistingGames`
- `deleteGame`
- `initializeGame`
- `loadGame`
- `sendChatMessage`
- `getSuggestedResponses`

Keep existing components in place, but replace direct `fetch`, `postJsonRequest`, and URL imports with these functions.

This is a low-risk first step because it changes imports and call sites without reorganizing the whole tree.

### Step 2. Add DTO-to-UI Mappers

Add mapper functions for backend data:

- saved game DTO to frontend `GameSave`
- backend chat role to frontend message sender
- response payload to frontend game/session update

This is where the saved `assistant` role should be converted to `gamemaster`.

### Step 3. Extract Game Session State From `App`

Move start/load/unload/send behavior into `useGameSession`.

The goal is for `App.tsx` to read more like:

```tsx
const game = useGameSession();
return <GameScreen game={game} />;
```

It does not need classes, service objects, or inheritance. A hook plus a few pure helpers is enough.

### Step 4. Extract Save Management From `SetupModal`

Move existing-save loading and deletion into `useSavedGames`.

After this, `SetupModal` should not know how URLs work or how saves are sorted. It should receive/load save state and pass actions to `SetupForm`.

### Step 5. Split Types Last

Once API modules and feature hooks exist, move types near their natural owners. Doing this too early can create churn because the final homes are not obvious until the boundaries exist.

## Testing Improvements

The current frontend tests are useful at the component level. As structure improves, add smaller tests around the extracted pure pieces:

- `setupValidation.test.ts`
- `gameMappers.test.ts`
- `useSavedGames.test.ts`
- API client tests for query/body behavior
- `useGameSession` tests for start/load/send/unload flows

These will be more stable than tests that need to render `App.tsx`.

## Immediate Wins

The highest-value cleanup items are:

1. Add an API layer so components stop knowing endpoint details.
2. Add mapper functions so backend DTO quirks do not leak into UI state.
3. Extract duplicated health-loss handling from `App.tsx`.
4. Move save-list fetch/delete logic out of `SetupModal`.
5. Split `misc/types.ts` only after the new boundaries exist.

That sequence should make the codebase feel less tangled without introducing an object-oriented architecture or a heavy framework pattern.

# Laboratory Work No. 3 Report: Memory Scramble - Concurrent Multiplayer Game

**Course:** Programare în Rețea (Network Programming)

**Author:** Țugui Artur, FAF-231

**Based on:** MIT 6.102 Problem Set 4 - Memory Scramble

---

## 1. Project Overview

### 1.1 What is Memory Scramble?

Memory Scramble is a networked multiplayer version of the classic Memory (Concentration) card game where players flip cards to find matching pairs. Unlike traditional Memory, multiple players can play **simultaneously** and **asynchronously**, making concurrency control the core challenge.

### 1.2 Key Differences from Traditional Memory:

- **Concurrent Play**: Multiple players flip cards at the same time (no turn-taking)
- **Card Waiting**: Players can wait for cards controlled by others
- **Delayed Cleanup**: Cards stay face-up until the controlling player makes another move
- **Asynchronous Operations**: All game operations are non-blocking

---

## 2. Implementation Architecture

### 2.1 Directory Structure:

```
MIT-6.102-ps4/
├── src/
│   ├── board.ts              # Core game logic (Board ADT)
│   ├── commands.ts           # HTTP API command handlers
│   ├── server.ts             # Express web server
│   ├── simulation.ts         # Multi-player game simulation
│   ├── simulation-watch.ts  # Watch functionality demo
│   └── simulation-map.ts    # Map functionality demo
├── test/
│   └── board.test.ts        # Comprehensive test suite (1261 lines)
├── boards/                   # Game board files
│   ├── perfect.txt          # 3×3 rainbow/unicorn board
│   ├── ab.txt               # 5×5 board
│   └── test-boards/         # Test case boards
├── public/
│   └── index.html           # Web UI client
├── Dockerfile                # Docker container definition
├── docker-compose.yml        # Docker Compose configuration
├── .dockerignore             # Docker ignore file
├── package.json
├── tsconfig.json
└── eslint.config.mjs
```

### 2.2 Core ADTs (Abstract Data Types):

| ADT             | Purpose           | Key Features                                        |
| --------------- | ----------------- | --------------------------------------------------- |
| **Board**       | Game board state  | Thread-safe, async operations, change notifications |
| **Card**        | Individual card   | Content, face-up/down state                         |
| **Position**    | Board coordinates | Immutable (row, col) pair                           |
| **PlayerState** | Player game state | Controlled cards, cleanup queue                     |

---

## 3. Docker Configuration

### 3.1 Dockerfile:

```dockerfile
# Use Node.js 20 LTS as base image
FROM node:20-slim

# Set working directory inside container
WORKDIR /app

# Copy package files
COPY package*.json ./
COPY tsconfig.json ./
COPY eslint.config.mjs ./

# Install dependencies
RUN npm install

# Copy source code
COPY src/ ./src/
COPY test/ ./test/
COPY boards/ ./boards/
COPY public/ ./public/

# Compile TypeScript
RUN npm run compile

# Expose port 8080 for the HTTP server
EXPOSE 8080

# Set default command to run the server
# Default board is perfect.txt, can be overridden with docker run arguments
CMD ["node", "dist/src/server.js", "8080", "boards/perfect.txt"]
```

### 3.2 Docker Compose File:

```yaml
services:
  memory-scramble:
    build: .
    container_name: pr_lab3_memory_scramble
    ports:
      - "8080:8080"
    volumes:
      # Mount boards directory for easy board updates
      - ./boards:/app/boards:ro
      # Mount public directory for UI updates
      - ./public:/app/public:ro
    environment:
      - NODE_ENV=production
    restart: unless-stopped
    command: ["node", "dist/src/server.js", "8080", "boards/perfect.txt"]
```

---

## 4. Docker Setup

### 4.1 Build and Start:

```bash
# Build the container
docker-compose build

# Start the server
docker-compose up -d

# Check status
docker ps

# View logs
docker logs pr_lab3_memory_scramble -f
```

### 4.2 After Code Changes:

```bash
# Rebuild and restart
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

### 4.3 Run with Different Board:

```bash
# Using docker-compose with custom board
docker-compose run --rm -p 8080:8080 memory-scramble \
  node dist/src/server.js 8080 boards/ab.txt

# Using docker directly
docker run -p 8080:8080 -v $(pwd)/boards:/app/boards:ro \
  pr_lab3_memory_scramble node dist/src/server.js 8080 boards/zoom.txt
```

### 4.4 Run Tests in Docker:

```bash
# Run the test suite inside container
docker-compose run --rm memory-scramble npm test

# Run simulations
docker-compose run --rm memory-scramble npm run simulation
docker-compose run --rm memory-scramble npm run simulation-watch
docker-compose run --rm memory-scramble npm run simulation-map
```

---

## 5. Problem Solutions

### 5.1 Problem 1: Game Board ADT

**Implementation Highlights:**

✅ **Comprehensive Specifications**: Every class and method has detailed TypeDoc comments

✅ **Rep Invariant Checking**: Rigorous `checkRep()` validates:

- Board dimensions (rows > 0, cols > 0)
- Player can control at most 2 cards
- Controlled cards are face-up and exist on the board
- No position controlled by multiple players

✅ **Safety from Rep Exposure**:

- All fields are `private` and `readonly`
- Position and Card objects never leaked to clients
- Defensive copying where necessary

**Key Methods:**

```typescript
// Factory method for parsing board files
public static async parseFromFile(filename: string): Promise<Board>

// Core game operation
public async flipCard(position: Position, playerId: string): Promise<void>

// Board state query
public getBoardState(playerId: string): string
```

### 5.2 Problem 2: Web Server Integration

**Implementation:** Simple glue code in `commands.ts` (< 3 lines per function)

```typescript
export async function look(board: Board, playerId: string): Promise<string> {
  return board.getBoardState(playerId);
}

export async function flip(
  board: Board,
  playerId: string,
  row: number,
  column: number
): Promise<string> {
  await board.flipCard(new TestPosition(row, column), playerId);
  return board.getBoardState(playerId);
}
```

**Server Features:**

- Express-based HTTP server
- RESTful API endpoints:
  - `GET /look/:playerId` - View board state
  - `GET /flip/:playerId/:row,:col` - Flip a card
  - `GET /replace/:playerId/:from/:to` - Map card transformation
  - `GET /watch/:playerId` - Wait for board changes
- CORS enabled for cross-origin requests
- Static file serving for web UI

### 5.3 Problem 3: Concurrency Control

**Challenge:** Handle multiple players flipping cards simultaneously without race conditions or deadlocks.

**Solution Strategy:**

1. **Deferred Promises** for waiting:

```typescript
class Deferred<T> {
  public readonly promise: Promise<T>;
  public resolve!: (value: T) => void;
  public reject!: (reason?: unknown) => void;
}
```

2. **Wait Queues** for controlled cards:

```typescript
private readonly waitQueues: Map<string, Deferred<void>[]>;
```

3. **Atomic Operations**: Each card flip is atomic - board never reaches inconsistent state

**Game Rules Implementation:**

| Rule                                     | Implementation                              |
| ---------------------------------------- | ------------------------------------------- |
| **1-A**: No card → fail                  | Return immediately, no state change         |
| **1-B**: Face-down card → flip & control | Atomic flip + add to controlled             |
| **1-C**: Face-up uncontrolled → control  | Add to controlled list                      |
| **1-D**: Controlled by other → wait      | Add to wait queue, await promise            |
| **2-A**: No card (2nd flip) → fail       | Relinquish first card, notify waiters       |
| **2-B**: Controlled (2nd flip) → fail    | Relinquish without waiting (avoid deadlock) |
| **2-C**: Face-down (2nd flip) → flip     | Flip card face-up                           |
| **2-D**: Match → keep control            | Add to `toCleanUp` queue, keep controlled   |
| **2-E**: No match → relinquish           | Move to `toCleanUp`, clear controlled       |
| **3-A**: Cleanup matched → remove        | Remove from board, notify waiters           |
| **3-B**: Cleanup unmatched → flip down   | Flip down if not controlled by others       |

### 5.4 Problem 4: Map Operation

**Challenge:** Transform all cards atomically while maintaining pairwise consistency.

**Solution:**

```typescript
public async mapCards(f: (card: string) => Promise<string>): Promise<void> {
    // Group cards by content
    const contentToPositions = new Map<string, Position[]>();

    // For each unique content, transform once
    for (const [originalContent, positions] of contentToPositions.entries()) {
        const newContent = await f(originalContent);

        // Atomically update all matching cards
        for (const pos of positions) {
            this.cards[pos.row]![pos.col] = new Card(newContent, card.faceUp);
        }
    }

    this.notifyChangeListeners(); // Notify watchers
}
```

**Key Properties:**

- ✅ Maintains pairwise consistency (matching cards stay matched)
- ✅ Allows interleaving with other operations
- ✅ Preserves face-up/down and control state
- ✅ Mathematical function guarantee (same input → same output)

### 5.5 Problem 5: Watch Notifications

**Challenge:** Notify clients when board changes without polling.

**Solution: Observer Pattern with Deferred Promises**

```typescript
private readonly changeListeners: Deferred<void>[];

public async waitForChange(): Promise<void> {
    const deferred = new Deferred<void>();
    this.changeListeners.push(deferred);
    return deferred.promise;
}

private notifyChangeListeners(): void {
    const listeners = this.changeListeners.splice(0);
    for (const listener of listeners) {
        listener.resolve();
    }
}
```

**Changes Detected:**

- Card flips face up
- Card flips face down
- Card removed from board
- Card content changes (via map)

**Note:** Control changes (without face state change) do NOT trigger notifications.

---

## 6. Testing Strategy

### 6.1 Test Coverage (1261 lines of tests)

**Test Categories:**

1. **File Parsing Tests** (12 tests)

   - Valid files (3×3, 5×5 boards)
   - Invalid files (empty, wrong dimensions, bad format)
   - Edge cases (1×1 board, emoji cards)

2. **Helper Class Tests** (18 tests)

   - Card: content, matching, toString
   - Position: equality, toString
   - PlayerState: control tracking

3. **Game Rules Tests** (30+ tests)

   - Rule 1 (First Card): A, B, C, D variations
   - Rule 2 (Second Card): A, B, C, D, E variations
   - Rule 3 (Cleanup): A (matched removal), B (flip down)
   - Integration tests (complete game flows)

4. **Concurrency Tests** (15+ tests)

   - Multiple players waiting for same card
   - Card removed while players waiting
   - Deadlock avoidance (Rule 2-B no waiting)
   - Cleanup with pending waits

5. **Map Operation Tests** (6 tests)

   - Simple transformations
   - Pairwise consistency during transformation
   - Preserving face/control state
   - Interleaving with flips

6. **Watch Tests** (8 tests)
   - Single/multiple watchers
   - Different change types (flip up/down, remove, map)
   - Interleaving with game operations

### 6.2 Test Execution:

```bash
npm install     # Install dependencies
npm test        # Run test suite (compile + lint + mocha)
```

**Test Results:** ✅ **All tests passing** (no errors or warnings)

---

## 7. Simulations

### 7.1 Multi-Player Simulation

**File:** `src/simulation.ts`

**Configuration (as required):**

```typescript
const players = 4; // 4 concurrent players
const tries = 100; // 100 moves each
const maxDelayMilliseconds = 2; // 0-2ms random delays
```

**Run:**

```bash
npm run simulation
```

**What it tests:**

- ✅ Concurrent gameplay without crashes
- ✅ Waiting behavior (Rule 1-D)
- ✅ Card control and cleanup (Rules 3-A, 3-B)
- ✅ Match/mismatch detection
- ✅ No deadlocks or hangs

**Sample Output:**

```
Starting simulation with 4 player(s) on a 3x3 board
Each player will attempt 100 flips
============================================================

  [player0] FIRST card at (1, 2)
  [player0]   ➜ Rule 1-B/C: Card '🌈' controlled
  [player1] FIRST card at (0, 0)
  [player1]   ➜ Rule 1-B/C: Card '🦄' controlled
  [player0] SECOND card at (2, 2)
  [player0]   ➜ Rule 2-D: MATCH! Both '🌈' will be removed on next flip

  ... [player stats at end]
```

### 7.2 Watch Simulation

**File:** `src/simulation-watch.ts`

**Run:**

```bash
npm run simulation-watch
```

**What it demonstrates:**

- ✅ Watchers receive notifications on board changes
- ✅ Multiple watchers can observe simultaneously
- ✅ Watch doesn't block gameplay
- ✅ Change counting and card removal tracking

### 7.3 Map Simulation

**File:** `src/simulation-map.ts`

**Run:**

```bash
npm run simulation-map
```

**What it demonstrates:**

- ✅ Card transformations work correctly
- ✅ Pairwise consistency maintained
- ✅ Face-up/down state preserved

---

## 8. Running the Web Server

### 8.1 Start Server:

```bash
npm start 8080 boards/perfect.txt
```

**Parameters:**

- `8080` - Port number (use 0 for random port)
- `boards/perfect.txt` - Board file to load

**Server Output:**

```
server now listening at http://localhost:8080
```

### 8.2 Play in Browser:

1. Open http://localhost:8080 in your browser
2. The UI randomly generates a player ID
3. Open multiple tabs to simulate multiple players
4. Click cards to flip them
5. Switch between "update by polling" and "update by watching" modes

### 8.3 Connect to Friend's Server:

1. Open `public/index.html` directly in browser
2. Enter friend's IP address in the UI
3. Play together over the network

---

## 9. Code Quality Highlights

### 9.1 Specifications

✅ **Every class has:**

- Clear purpose description
- Abstraction function (AF)
- Representation invariant (RI)
- Safety from rep exposure argument

✅ **Every method has:**

- `@param` documentation
- `@returns` documentation
- `@throws` documentation where applicable
- Preconditions and postconditions

### 9.2 Type Safety

✅ TypeScript strict mode enabled
✅ No `any` types used
✅ Proper async/await usage throughout
✅ No compiler errors or warnings

### 9.3 Immutability

✅ Position class is immutable
✅ Card content is `readonly`
✅ Board dimensions are `readonly`
✅ Defensive copying prevents mutation

### 9.4 Thread Safety

✅ No busy-waiting (uses promises/async)
✅ Atomic operations on shared state
✅ No race conditions (validated by tests)
✅ Deadlock avoidance (Rule 2-B)

---

## 10. Technical Achievements

### 10.1 Concurrency Patterns Used:

1. **Deferred Promises** - Transform callbacks into promises
2. **Wait Queues** - FIFO ordering for card access
3. **Observer Pattern** - Change notifications for watchers
4. **Atomic Updates** - Consistent state transitions

### 10.2 Advanced Features:

✅ **Logging for Debugging**: `flipCardWithLogging()` method provides detailed rule traces

✅ **Comprehensive Error Handling**: All failure cases handled per specification

✅ **Flexible Map Operation**: Supports async transformations (e.g., API calls)

## ✅ **Efficient Watching**: Minimal memory overhead, instant notifications

## 11. Lessons Learned

### 11.1 Concurrency Challenges:

- **Deadlock Prevention**: Rule 2-B (second card doesn't wait) is crucial
- **Promise Chaining**: Async/await makes complex flows readable
- **Atomic Operations**: Careful state management prevents race conditions

### 11.2 Testing Insights:

- **Timing is Hard**: Used short timeouts (1-10ms) to test interleavings
- **Comprehensive Coverage**: 50+ tests ensure correctness
- **Simulation Value**: Multi-player simulation caught edge cases

### 11.3 Design Decisions:

- **Deferred vs Callbacks**: Deferred promises cleaner for storing/resolving later
- **Map Atomicity**: Transform all matching cards together maintains consistency
- **Watch Granularity**: Single change notification (not per-card) reduces complexity

---

## 12. Running Commands Summary

```bash
# Install dependencies
npm install

# Run tests (compile + lint + test)
npm test

# Start web server (local)
npm start 8080 boards/perfect.txt

# Docker commands
docker-compose build                  # Build container
docker-compose up -d                  # Start in background
docker-compose down                   # Stop container
docker logs pr_lab3_memory_scramble   # View logs

# Run simulations
npm run simulation          # Multi-player game
npm run simulation-watch    # Watch functionality
npm run simulation-map      # Map functionality

# Compile TypeScript
npm run compile

# Run linter
npm run lint
```

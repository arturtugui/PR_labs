# Memory Scramble - Implementation Plan

## Problem 1: Design and Implement Board ADT

### Task 1: Design Your Data Types (ADTs)

#### 1.1 Decide on Your Class Structure
- Will you have a single `Board` class or multiple classes (e.g., `Board`, `Card`, `PlayerState`, `Position`)?
- What will be **mutable** vs **immutable**?
- What fields/attributes does each class need?

#### 1.2 Define the Operations/Methods
For the `Board` class, you need:
- `parseFromFile(filename)` - required by spec
- Some way to flip cards for a player
- Some way to get the board state for a player (for `look()`)
- Helper methods for game logic

Think about:
- What parameters does each method need?
- What does each method return?
- When should methods throw errors vs return normally?
- Should operations be synchronous or asynchronous? (Start simple with synchronous for now)

---

### Task 2: Write Specifications

#### 2.1 Write Method Specifications
For each public method, write:
- **Purpose statement**: What does it do?
- **@param**: Describe each parameter and its constraints
- **@returns**: What it returns
- **@throws**: When and why it throws errors

#### 2.2 Document Abstraction Function (AF)
- How do your concrete fields represent the abstract game board concept?
- Example: "AF(cards, players) = a Memory Scramble board where..."

#### 2.3 Document Representation Invariant (RI)
- What must always be true about your fields?
- Example: "rows > 0", "no two players control same card", etc.

#### 2.4 Document Safety from Rep Exposure (SRE)
- How do you prevent clients from breaking your RI?
- Which fields are private/readonly?
- Do you return copies vs direct references?

---

### Task 3: Plan Your Testing Strategy

#### 3.1 Partition the Input Space for `parseFromFile()`
Think about different cases:
- Board sizes: 1x1, 2x2, larger boards
- Card content: text vs emoji vs mixed
- Card matching: all pairs, no pairs, some pairs
- File validity: valid format, invalid dimensions, wrong number of cards, invalid card characters

#### 3.2 Partition for Board State Queries
- Empty board vs partially filled vs full
- Player has no cards vs controls one vs controls two
- Cards face up vs face down
- What does player see vs what other players see?

#### 3.3 Partition for Card Flipping (Game Rules)
For **first card flip** (rules 1-A through 1-D):
- Empty space
- Face down card
- Face up, not controlled by anyone
- Face up, controlled by another player

For **second card flip** (rules 2-A through 2-E):
- Empty space
- Controlled by someone (self or other)
- Face down, cards match
- Face down, cards don't match
- Face up uncontrolled, cards match
- Face up uncontrolled, cards don't match

For **cleanup on next move** (rules 3-A and 3-B):
- Player had matching pair → cards removed
- Player had non-matching pair → cards flip down (if not controlled)
- Previous unmatched card now controlled by someone else → stays up

#### 3.4 Think About Edge Cases
- What if player flips the same card twice?
- What if the card disappears between first and second flip?
- Multiple players trying to flip same card (save this for after basic implementation)

---

### Task 4: Write Test Cases

#### 4.1 Start with Parsing Tests
Write tests for:
- Valid board files from the `boards/` directory
- Creating boards of different sizes
- Boards with different card types
- (Later) Invalid boards that should throw errors

#### 4.2 Write Basic Gameplay Tests
Test individual game rules in isolation:
- Single player flipping one card (rule 1-B)
- Single player flipping two cards that match (rules 2-D, 3-A)
- Single player flipping two cards that don't match (rules 2-E, 3-B)
- Trying to flip empty space (rules 1-A, 2-A)

#### 4.3 Write Multi-Player Tests (Without Concurrency Yet)
Test with sequential operations:
- Alice flips card, Bob flips same card (rule 1-C after Alice relinquishes)
- Alice controls card, Bob tries to flip it (should fail, rule 2-B)
- Alice has unmatched cards, Bob flips one of them (should stay up per rule 3-B)

**Don't worry about concurrency/waiting yet** - just test the game logic with one operation at a time.

---

### Task 5: Implement Basic Board (No Concurrency)

#### 5.1 Implement Data Structures
- Create your classes and their fields
- Initialize everything in constructors
- Implement `checkRep()` method

#### 5.2 Implement `parseFromFile()`
- Read the file
- Parse dimensions (first line: "RxC")
- Parse cards (remaining lines)
- Validate format
- Create and populate Board
- Throw errors for invalid input

#### 5.3 Implement Board State Query
- Method to get current state of board for a player
- Show cards as: "none", "down", "my <card>", "up <card>"
- Return in the protocol format

#### 5.4 Implement Flip Logic (Synchronous First)
Implement the game rules **without waiting**:
- Track which cards each player controls
- Track which cards are face up
- Implement rules 1-A, 1-B, 1-C (skip 1-D for now)
- Implement rules 2-A, 2-B, 2-C, 2-D, 2-E
- Implement rules 3-A, 3-B

For rule 1-D (waiting), just throw an error for now - you'll implement waiting later.

---

### Task 6: Run and Debug Tests

#### 6.1 Run Your Tests
```bash
npm test
```

#### 6.2 Fix Failures
- Use test output to identify what's wrong
- Add `console.log()` or use debugger
- Check that `checkRep()` isn't failing

#### 6.3 Iterate
- Add more tests as you find gaps
- Refine your implementation
- Keep checking AF, RI, SRE

---

### Milestone Check for Problem 1

After Task 6, you should have:
- ✅ A `Board` class that can be created from files
- ✅ Game rules working for single-player sequential play
- ✅ Tests passing for basic gameplay
- ✅ Complete specifications (AF, RI, SRE, method specs)
- ✅ A `checkRep()` that validates your RI

---

## Problem 2: Connect to Server

### Task 1: Understand the Server Protocol

#### 1.1 Read the Protocol Specification
- How does `look` work? What format does it return?
- How does `flip` work? What parameters does it take?
- What error messages are expected?

#### 1.2 Test with Manual Commands
- Start the server
- Use `curl` or browser to test commands
- Verify the format matches the spec

---

### Task 2: Implement `look()` in commands.ts

#### 2.1 Write Specification
- What does `look` do?
- What parameters does it need?
- What does it return?

#### 2.2 Implement (Should be ≤3 lines)
- Call the appropriate Board method
- Return the result in protocol format

#### 2.3 Test
- Write tests for `look()`
- Test with different board states
- Test with different players

---

### Task 3: Implement `flip()` in commands.ts

#### 3.1 Write Specification
- What does `flip` do?
- What parameters does it need?
- What does it return?
- When does it throw errors?

#### 3.2 Implement (Should be ≤3 lines)
- Call the appropriate Board method
- Return the result in protocol format
- Let errors propagate up

#### 3.3 Test
- Write tests for `flip()`
- Test all game rules through the command interface
- Test error cases

---

### Milestone Check for Problem 2

After Task 3, you should have:
- ✅ `look()` and `flip()` commands working
- ✅ Can play the game through the web interface
- ✅ Tests passing for both commands
- ✅ Simple glue code (≤3 lines per command)

---

## Problem 3: Add Concurrency and Waiting

### Task 1: Understand Promise-Based Waiting

#### 1.1 Learn `Promise.withResolvers()`
- How to create a promise that you can resolve later
- How to store promises in a queue
- How to chain promises

#### 1.2 Design Waiting Strategy
- Where will you store waiting players?
- How will you notify them when cards become available?
- How will you handle cleanup (rule 3)?

---

### Task 2: Implement Rule 1-D (Wait for Controlled Card)

#### 2.1 Modify flip() to Return Promise
- Change signature to `async flip()`
- Return `Promise<void>`

#### 2.2 Add Waiting Queue
- Data structure to track who's waiting for which cards
- Method to add a player to the queue
- Method to notify waiting players

#### 2.3 Implement Waiting Logic
- When card is controlled by another player, add to queue
- Don't return until card becomes available
- Then proceed with normal flip logic

---

### Task 3: Implement Notification on Card Release

#### 3.1 Identify When Cards Are Released
- When matching pair is removed (rule 3-A)
- When unmatched cards flip down (rule 3-B)
- When player makes a second flip (releases first card control)

#### 3.2 Notify Waiting Players
- When a card is released, check if anyone is waiting
- Resolve their promise so they can continue
- Handle queue in FIFO order

---

### Task 4: Test Concurrent Operations

#### 4.1 Write Concurrent Tests
- Two players trying to flip same card simultaneously
- One player waits while another plays
- Multiple players in waiting queue
- Verify FIFO ordering

#### 4.2 Test with Simulation
- Use the provided simulation code
- Run 4 players with random delays
- Verify no deadlocks
- Verify no race conditions

---

### Task 5: Ensure No Busy-Waiting

#### 5.1 Review Your Code
- No `while` loops checking conditions
- No `setTimeout` polling
- Only `await` on promises

#### 5.2 Test Performance
- Waiting should not consume CPU
- Use debugger or profiler to verify

---

### Milestone Check for Problem 3

After Task 5, you should have:
- ✅ Rule 1-D implemented (waiting for controlled cards)
- ✅ All flip operations are asynchronous
- ✅ No busy-waiting
- ✅ Concurrent tests passing
- ✅ 4-player simulation works correctly

---

## Problem 4: Implement `map()` Command

### Task 1: Understand the Requirements

#### 1.1 What Does map() Do?
- Applies a transformer function to all cards
- Must maintain consistency during transformation
- Other operations can interleave

#### 1.2 Design Considerations
- How to ensure all cards get transformed?
- What if cards are removed during transformation?
- What if new cards are added during transformation?

---

### Task 2: Implement map() in Board

#### 2.1 Write Specification
- What parameters does it take?
- What does it return?
- What guarantees does it provide?

#### 2.2 Implement Transformation
- Iterate through all cards
- Apply transformer function
- Handle concurrent modifications

#### 2.3 Test
- Transform all cards on a board
- Test with concurrent flips
- Test with concurrent removes

---

### Task 3: Connect to Commands

#### 3.1 Implement map() in commands.ts
- Parse transformer function from request
- Call Board.map()
- Return result

#### 3.2 Test
- Test through server interface
- Test various transformations

---

### Milestone Check for Problem 4

After Task 3, you should have:
- ✅ `map()` implemented in Board
- ✅ `map()` command working in server
- ✅ Tests passing for map operations
- ✅ Consistency maintained during transformation

---

## Problem 5: Implement `watch()` Command

### Task 1: Understand the Requirements

#### 1.1 What Does watch() Do?
- Waits for board changes
- Notifies client when change occurs
- Makes UI more responsive

#### 1.2 Design Observer Pattern
- How to register watchers?
- How to notify them of changes?
- When to send notifications?

---

### Task 2: Implement Change Notification

#### 2.1 Add Listener Support to Board
- Method to register a listener
- Method to notify all listeners
- Decide when to trigger notifications

#### 2.2 Track Board Changes
- After every flip
- After every map
- After cards are removed
- After cards flip down

#### 2.3 Implement Notification
- Call all registered listeners
- Pass board state or change info
- Handle errors in listeners

---

### Task 3: Implement watch() Command

#### 3.1 Write Specification
- What parameters does it take?
- What does it return?
- When does it return?

#### 3.2 Implement in commands.ts
- Register a listener with Board
- Wait for change notification
- Return updated board state

#### 3.3 Handle Timeouts
- Don't wait forever
- Return after reasonable timeout
- Document timeout behavior

---

### Task 4: Test watch()

#### 4.1 Write Tests
- Watch while another player makes moves
- Watch when no changes occur
- Watch with multiple watchers

#### 4.2 Test with UI
- Verify UI updates automatically
- Check responsiveness

---

### Milestone Check for Problem 5

After Task 4, you should have:
- ✅ `watch()` implemented in Board
- ✅ `watch()` command working in server
- ✅ Tests passing for watch operations
- ✅ UI updates automatically

---

## Final Testing and Polish

### Task 1: Run Full Test Suite
- All unit tests passing
- All integration tests passing
- 4-player simulation works correctly

### Task 2: Check All Specifications
- All types have AF, RI, SRE, checkRep()
- All methods have complete specs
- All public methods documented

### Task 3: Code Review
- Follow SFB, ETU, RFC principles
- Check for rep exposure
- Verify thread safety
- Review error handling

### Task 4: Manual Testing
- Play the game through web interface
- Try edge cases
- Test with multiple players

### Task 5: Submit
- Commit all changes
- Push to repository
- Submit on Didit
- Check feedback

---

## Quick Reference: Game Rules

### Rule 1: First Card Flip
- **1-A**: Flip empty space → fails
- **1-B**: Flip face-down card → turn it face-up, player controls it
- **1-C**: Flip face-up uncontrolled → player controls it
- **1-D**: Flip face-up controlled by other → wait until available, then apply 1-B or 1-C

### Rule 2: Second Card Flip
- **2-A**: Flip empty space → fails, player loses control of first card
- **2-B**: Flip card controlled by someone → fails, no change
- **2-C**: Flip face-down or face-up uncontrolled → turn face-up, player controls both
- **2-D**: If cards match → both stay face-up and controlled
- **2-E**: If cards don't match → both stay face-up and controlled (for now)

### Rule 3: Cleanup on Next First Card Flip
- **3-A**: If player had matching pair → remove both cards
- **3-B**: If player had unmatched pair → flip down any not controlled by others

---

## Testing Commands

```bash
# Run all tests
npm test

# Run specific test file
npm test -- test/board.test.ts

# Run with coverage
npm test -- --coverage

# Run in watch mode
npm test -- --watch

# Start server
npm start

# Test server with curl
curl http://localhost:8789/look/BOARD/PLAYER
curl http://localhost:8789/flip/BOARD/PLAYER/ROW/COL
```

---

## Common Issues and Solutions

### Issue: Tests timing out
**Solution**: Make sure async functions use `await` and return promises properly

### Issue: Race conditions
**Solution**: Use proper synchronization with promises, not busy-waiting

### Issue: Rep exposure
**Solution**: Return copies of mutable data, use `readonly` for immutable references

### Issue: Deadlock
**Solution**: Follow rule 2-B (don't wait on second flip of controlled card)

### Issue: Type errors
**Solution**: Use `assert` to tell TypeScript about runtime checks you've made

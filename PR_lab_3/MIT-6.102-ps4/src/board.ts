/* Copyright (c) 2021-25 MIT 6.102/6.031 course staff, all rights reserved.
 * Redistribution of original or derived work requires permission of course staff.
 */

import assert from 'node:assert';
import fs from 'node:fs';

/**
 * Deferred promise utility for async coordination.
 * Allows storing a promise to be resolved later.
 */
class Deferred<T> {
    public readonly promise: Promise<T>;
    public resolve!: (value: T) => void;
    public reject!: (reason?: unknown) => void;

    constructor() {
        this.promise = new Promise<T>((resolve, reject) => {
            this.resolve = resolve;
            this.reject = reject;
        });
    }
}

/**
 * Represents a mutable game board for Memory Scramble.
 * 
 * The board is a rectangular grid of cards. Players can flip cards to reveal their content,
 * and match pairs of cards with the same content. Matched pairs are removed from the board.
 * 
 * This class is thread-safe for concurrent access by multiple players.
 */
export class Board {

    // fields
    private readonly rows : number;
    private readonly cols : number;
    private readonly cards : (Card | undefined)[][];
    private readonly playerStates: Map<string, PlayerState>;
    private readonly waitQueues: Map<string, Deferred<void>[]>; // Map from position key to waiting promises

    // Abstraction function:
    //   AF(rows, cols, cards, playerStates) = a Memory Scramble game board with dimensions
    //   rows × cols, where cards[r][c] represents the card at position (r,c), or undefined
    //   if that card has been removed (matched). playerStates maps each active player's ID
    //   to their current game state (which cards they control).
    //
    // Representation invariant:
    //   rows > 0, cols > 0
    //   cards.length === rows
    //   for all i: cards[i].length === cols
    //   cards[i][j] is either a Card or undefined (for removed cards)
    //   for all players in playerStates:
    //     - player.playerId matches the map key
    //     - player controls 0, 1, or 2 cards
    //     - all controlled positions are valid (0 <= row < rows, 0 <= col < cols)
    //     - all controlled positions refer to existing cards (not undefined)
    //     - all controlled cards are face-up
    //   no position is controlled by more than one player
    //
    // Safety from rep exposure:
    //   rows, cols are private, readonly, and immutable primitive types
    //   cards is private and readonly (the array reference)
    //     - never returned directly; methods return copies or immutable views
    //     - Card objects are mutable (faceUp can change) but not exposed to clients
    //   playerStates is private and readonly (the Map reference)
    //     - never returned directly
    //     - PlayerState objects are internal implementation details

    // constructor
    private constructor(rows: number, cols: number, cards: (Card | undefined)[][]) {
        this.rows = rows;
        this.cols = cols;
        this.cards = cards;
        this.playerStates = new Map<string, PlayerState>();
        this.waitQueues = new Map<string, Deferred<void>[]>();
        this.checkRep();
    }

    public getRows(): number {
        return this.rows;
    }

    public getColumns(): number {
        return this.cols;
    }

    /**
     * Check that the representation invariant holds.
     */
    private checkRep(): void {
        // RI: rows > 0, cols > 0
        assert(this.rows > 0, 'rows must be positive');
        assert(this.cols > 0, 'cols must be positive');
        
        // RI: cards array has correct dimensions
        assert(this.cards.length === this.rows, 'cards array must have rows rows');
        for (const row of this.cards) {
            assert(row.length === this.cols, 'each row must have cols columns');
        }
        
        // RI: playerStates map is consistent
        for (const [playerId, state] of this.playerStates) {
            assert(state.playerId === playerId, 'playerId must match map key');
            
            // RI: each player controls 0, 1, or 2 cards
            assert(state.controlled.length <= 2, 'player can control at most 2 cards');
            
            // RI: controlled positions are valid and refer to existing cards
            for (const pos of state.controlled) {
                assert(pos.row >= 0 && pos.row < this.rows, 'controlled position row must be valid');
                assert(pos.col >= 0 && pos.col < this.cols, 'controlled position col must be valid');
                
                const card = this.cards[pos.row]?.[pos.col];
                assert(card !== undefined, 'controlled position must have a card');
                
                // RI: controlled cards must be face-up
                assert(card.faceUp, 'controlled card must be face-up');
            }
        }
        
        // RI: no position is controlled by more than one player
        const controlledPositions = new Set<string>();
        for (const state of this.playerStates.values()) {
            for (const pos of state.controlled) {
                const key = pos.toString();
                assert(!controlledPositions.has(key), 
                       `position ${key} cannot be controlled by multiple players`);
                controlledPositions.add(key);
            }
        }
    }


    /**
     * Make a new board by parsing a file.
     * 
     * PS4 instructions: the specification of this method may not be changed.
     * 
     * @param filename path to game board file
     * @returns a new board with the size and cards from the file
     * @throws Error if the file cannot be read or is not a valid game board
     */
    public static async parseFromFile(filename: string): Promise<Board> {
        let data;
        
        try {
            data = await fs.promises.readFile(filename, 'utf-8');
        } catch (error) {
            throw new Error('Invalid game board file');
        }

        // Split on both \r\n (Windows) and \n (Unix) line endings
        const strArray : string[] = data.split(/\r?\n/).map(line => line.trim()).filter(line => line.length > 0);

        if (strArray.length < 2) {
            throw new Error('Invalid game board file');
        }

        // Parse dimensions
        const firstLine = strArray[0];
        assert(firstLine !== undefined);
        const dimensions = firstLine.split('x');
        if (dimensions.length !== 2) {
            throw new Error('Invalid board dimensions format');
        }
        
        const rows = Number(dimensions[0]);
        const cols = Number(dimensions[1]);
        
        // Check if rows and cols are valid positive numbers
        if (isNaN(rows) || isNaN(cols) || rows <= 0 || cols <= 0) {
            throw new Error('Invalid board dimensions: must be positive numbers');
        }
        
        // Parse cards
        const cardsArray = strArray.slice(1);
        
        // Validate card count
        if (cardsArray.length !== rows * cols) {
            throw new Error(`Expected ${rows * cols} cards, but found ${cardsArray.length}`);
        }

        // Create 2D array of cards
        const cards: (Card | undefined)[][] = [];
        for (let r = 0; r < rows; r++) {
            const rowCards: (Card | undefined)[] = [];
            for (let c = 0; c < cols; c++) {
                const cardContent = cardsArray[r * cols + c];
                if (cardContent) {
                    rowCards.push(new Card(cardContent));
                } else {
                    rowCards.push(undefined);
                }
            }
            cards.push(rowCards);
        }

        return new Board(rows, cols, cards);
    }

    /**
     * Flip a card with detailed logging for simulation/debugging.
     * Returns a message describing what happened.
     * 
     * @param position the position of the card to flip
     * @param playerId the ID of the player flipping the card
     * @returns a description of what happened during the flip
     */
    public async flipCardWithLogging(position: Position, playerId: string): Promise<string> {
        // Validate bounds first
        if (position.row < 0 || position.row >= this.rows || 
            position.col < 0 || position.col >= this.cols) {
            return `Invalid position (out of bounds)`;
        }

        const card = this.cards[position.row]?.[position.col];
        const cardContent = card ? `'${card.content}'` : 'none';
        
        let state = this.playerStates.get(playerId);
        if (!state) {
            state = new PlayerState(playerId);
            this.playerStates.set(playerId, state);
        }

        const wasControlling = state.controlled.length;
        const hadCleanup = state.toCleanUp.length;
        
        try {
            await this.flipCard(position, playerId);
            
            const nowControlling = state.controlled.length;
            const nowCleanup = state.toCleanUp.length;
            
            // Figure out what happened
            if (wasControlling === 0) {
                // Was trying first card
                if (hadCleanup === 2 && nowCleanup === 0) {
                    // Cleanup was performed
                    if (nowControlling === 1) {
                        return `Rule 3-A/B cleanup done, then Rule 1-B/C: card ${cardContent} controlled`;
                    } else {
                        return `Rule 3-A/B cleanup done, then Rule 1-A: no card (failed)`;
                    }
                }
                
                if (card === undefined) {
                    return `Rule 1-A: No card at position`;
                }
                
                if (nowControlling === 1) {
                    return `Rule 1-B/C: Card ${cardContent} controlled`;
                }
                
                if (nowControlling === 0 && nowCleanup === 0 && hadCleanup === 0) {
                    // This can happen after waiting: tried to flip, waited, card became available 
                    // but got taken by someone else, so we waited again multiple times, eventually
                    // card was removed or some other condition caused us to not get it
                    return `Rule 1-D: Waited for card but it became unavailable`;
                }
                
                // Unexpected state
                return `? First card flip (wasCtrl=${wasControlling}, nowCtrl=${nowControlling}, cleanup=${nowCleanup})`;
                
            } else if (wasControlling === 1) {
                // Was trying second card
                const firstPos = state.toCleanUp[0] ?? state.controlled[0];
                const firstCard = firstPos ? this.cards[firstPos.row]?.[firstPos.col] : undefined;
                const firstContent = firstCard ? `'${firstCard.content}'` : 'none';
                
                if (card === undefined) {
                    if (nowControlling === 0) {
                        return `Rule 2-A: No card at position (first card ${firstContent} relinquished)`;
                    }
                }
                
                if (nowControlling === 0 && nowCleanup === 0) {
                    return `Rule 2-B: Card ${cardContent} already controlled (first card ${firstContent} relinquished)`;
                }
                
                if (nowCleanup === 2) {
                    // Check if they match
                    if (card && firstCard && card.matches(firstCard)) {
                        return `Rule 2-D: MATCH! Both ${cardContent} will be removed on next flip`;
                    } else {
                        return `Rule 2-E: NO MATCH (${firstContent} and ${cardContent}) - will flip down on next flip`;
                    }
                }
                
                // Unexpected state
                return `? Second card flip (wasCtrl=${wasControlling}, nowCtrl=${nowControlling}, cleanup=${nowCleanup})`;
            } else if (wasControlling === 2) {
                // Was controlling 2 matched cards, now trying to flip
                if (hadCleanup === 2 && nowCleanup === 0) {
                    // Cleanup was performed
                    if (nowControlling === 1) {
                        return `Rule 3-A cleanup done (matched pair removed), then Rule 1-B/C: card ${cardContent} controlled`;
                    } else {
                        return `Rule 3-A cleanup done (matched pair removed), then Rule 1-A: no card (failed)`;
                    }
                }
                return `? Unclear after match (wasCtrl=${wasControlling}, nowCtrl=${nowControlling}, cleanup=${nowCleanup})`;
            }
            
            return `? Unclear (wasCtrl=${wasControlling}, nowCtrl=${nowControlling}, cleanup=${nowCleanup})`;
            
        } catch (err) {
            if (err instanceof Error) {
                if (err.message.includes('controlled by another player')) {
                    return `Rule 1-D: Card ${cardContent} controlled by another player (waiting)`;
                }
                if (err.message.includes('Invalid position')) {
                    return `Invalid position`;
                }
                return `Error: ${err.message}`;
            }
            return `Unknown error`;
        }
    }

    // Game logic methods (flip, look, etc.) would go here
    public async flipCard(position: Position, playerId: string, retryingAfterWait: boolean = false): Promise<void> {
        // Validate position bounds
        if (position.row < 0 || position.row >= this.rows || 
            position.col < 0 || position.col >= this.cols) {
            throw new Error('Invalid position');
        }

        const card = this.cards[position.row]?.[position.col];

        // Get or create player state
        let state = this.playerStates.get(playerId);
        if (!state) {
            state = new PlayerState(playerId);
            this.playerStates.set(playerId, state);
        }

        // CASE 1: First card flip (player controls 0 cards OR has cards to clean up)
        // Check for cleanup first, regardless of controlled.length
        if (state.toCleanUp.length === 2 || state.controlled.length === 0) {
            // First, check if there are cards to clean up from previous play
            // BUT: if we're retrying after a wait, skip cleanup (it was already done)
            if (!retryingAfterWait && state.toCleanUp.length === 2) {
                const firstPos = state.toCleanUp[0];
                const secondPos = state.toCleanUp[1];
                assert(firstPos !== undefined);
                assert(secondPos !== undefined);
                
                const firstCard = this.cards[firstPos.row]?.[firstPos.col];
                const secondCard = this.cards[secondPos.row]?.[secondPos.col];

                // Rule 3-A: if they match, remove them from board
                if (firstCard !== undefined && secondCard !== undefined && firstCard.matches(secondCard)) {
                    this.cards[firstPos.row]![firstPos.col] = undefined;
                    this.cards[secondPos.row]![secondPos.col] = undefined;
                    
                    // Notify anyone waiting on these positions that they're now available
                    this.notifyWaiters(firstPos);
                    this.notifyWaiters(secondPos);
                } else {
                    // Rule 3-B: flip down unmatched cards if still face-up and uncontrolled
                    if (firstCard !== undefined && firstCard.faceUp && !this.isCardControlled(firstPos)) {
                        this.flipCardDown(firstCard, firstPos);
                    }
                    if (secondCard !== undefined && secondCard.faceUp && !this.isCardControlled(secondPos)) {
                        this.flipCardDown(secondCard, secondPos);
                    }
                }
                
                // Clear cleanup list AND controlled (in case of matched pair that stayed controlled)
                state.toCleanUp = [];
                state.controlled = [];
                
                // Notify waiters after relinquishing control
                this.notifyWaiters(firstPos);
                this.notifyWaiters(secondPos);
            }
            
            // Now process the new first card flip
            // Re-read the card in case it was just removed during cleanup
            const currentCard = this.cards[position.row]?.[position.col];
            
            // Rule 1-A: no card there → operation fails
            if (currentCard === undefined) {
                return; // Operation fails silently
            }

            // Rule 1-B: card is face down → flip it up and control it
            if (!currentCard.faceUp) {
                this.flipCardUp(currentCard, position);
                state.controlled.push(position);
                this.checkRep();
                return;
            }

            // Card is face up...
            // Rule 1-C: not controlled by anyone → take control
            if (!this.isCardControlled(position)) {
                state.controlled.push(position);
                this.checkRep();
                return;
            }

            // Rule 1-D: controlled by another player → wait
            await this.waitForCard(position);
            // After waiting, recursively try to flip again
            // Pass true to skip cleanup logic (cleanup was already done before waiting)
            return this.flipCard(position, playerId, true);
        }

        // CASE 2: Second card flip (player controls 1 card)
        if (state.controlled.length === 1) {
            const firstPos = state.controlled[0];
            assert(firstPos !== undefined);
            const firstCard = this.cards[firstPos.row]?.[firstPos.col];
            assert(firstCard !== undefined); // RI guarantees this

            // Rule 2-A: no card there → operation fails, relinquish first card
            if (card === undefined) {
                state.controlled = []; // Relinquish control
                this.notifyWaiters(firstPos); // Notify waiters
                this.checkRep();
                return;
            }

            // Rule 2-B: card is controlled (by anyone, including self) → fail, relinquish
            if (this.isCardControlled(position)) {
                state.controlled = []; // Relinquish control
                this.notifyWaiters(firstPos); // Notify waiters
                this.checkRep();
                return;
            }

            // Card is either face-down or face-up uncontrolled...
            
            // Rule 2-C: if face down, flip it up
            if (!card.faceUp) {
                this.flipCardUp(card, position);
            }

            // Rule 2-D: if cards match → keep control of both, mark for cleanup
            if (card.matches(firstCard)) {
                // Cards match - mark for cleanup, but KEEP them in controlled
                // They stay as "my" cards until cleanup removes them
                state.controlled.push(position); // Add second card to controlled
                state.toCleanUp = [firstPos, position];
                // DON'T clear controlled - cards remain controlled until cleanup
                this.checkRep();
                return;
            }

            // Now control the second card (for non-matching case)
            state.controlled.push(position);

            // Rule 2-E: cards don't match → relinquish control, mark for cleanup
            const secondPos = position;
            state.toCleanUp = [firstPos, secondPos];
            state.controlled = [];
            // Notify waiters since we relinquished both cards
            this.notifyWaiters(firstPos);
            this.notifyWaiters(secondPos);
            this.checkRep();
            return;
        }

        this.checkRep();
    }

    /**
     * Convert a position to a string key for map lookups.
     */
    private positionKey(position: Position): string {
        return `${position.row},${position.col}`;
    }

    /**
     * Wait for a card to become available (not controlled by anyone).
     * Returns a promise that resolves when the card is released.
     */
    private async waitForCard(position: Position): Promise<void> {
        const key = this.positionKey(position);
        const deferred = new Deferred<void>();
        
        // Add this deferred to the wait queue for this position
        const queue = this.waitQueues.get(key) ?? [];
        queue.push(deferred);
        this.waitQueues.set(key, queue);
        
        // Wait for the promise to be resolved
        await deferred.promise;
    }

    /**
     * Notify all players waiting on a specific position that it's now available.
     */
    private notifyWaiters(position: Position): void {
        const key = this.positionKey(position);
        const queue = this.waitQueues.get(key);
        
        if (queue && queue.length > 0) {
            // Resolve all waiting promises
            for (const deferred of queue) {
                deferred.resolve();
            }
            // Clear the queue
            this.waitQueues.delete(key);
        }
    }

    /**
     * Return the card at a given position or undefined if none (removed).
     */
    private getCardAtPosition(position: Position): Card | undefined {
        if (position.row < 0 || position.row >= this.rows || position.col < 0 || position.col >= this.cols) {
            return undefined;
        }
        return this.cards[position.row]?.[position.col];
    }

    private isCardControlled(position: Position): boolean {
        for (const state of this.playerStates.values()) {
            // Only check controlled, not toCleanUp
            // Cards in toCleanUp from mismatches should be available to other players
            if (state.controlled.some(p => p.equals(position))) {
                return true;
            }
        }
        return false;
    }

    /**
     * Flip a card face up. Validates that the card exists and is currently face down.
     * 
     * @param card the card to flip face up
     * @param position the position of the card (for error messages)
     * @throws Error if card is already face up (indicates a bug in game logic)
     */
    private flipCardUp(card: Card, position: Position): void {
        if (card.faceUp) {
            throw new Error(`Bug: Attempted to flip face-up card at ${position.toString()} face up again`);
        }
        card.faceUp = true;
    }

    /**
     * Flip a card face down. Validates that the card exists and is currently face up.
     * Also checks that the card is not controlled by any player (controlled cards should never be flipped down).
     * 
     * @param card the card to flip face down
     * @param position the position of the card (for error messages)
     * @throws Error if card is already face down or is controlled (indicates a bug in game logic)
     */
    private flipCardDown(card: Card, position: Position): void {
        if (!card.faceUp) {
            throw new Error(`Bug: Attempted to flip face-down card at ${position.toString()} face down again`);
        }
        
        if (this.isCardControlled(position)) {
            throw new Error(`Bug: Attempted to flip down controlled card at ${position.toString()}`);
        }
        
        card.faceUp = false;
    }

    /**
     * Find all positions of cards with the given content.
     * 
     * @param content the content to search for
     * @returns array of positions where cards with matching content exist (not removed)
     */
    public findCardPositions(content: string): Position[] {
        const positions: Position[] = [];
        for (let row = 0; row < this.rows; row++) {
            for (let col = 0; col < this.cols; col++) {
                const card = this.cards[row]?.[col];
                if (card !== undefined && card.content === content) {
                    positions.push(new Position(row, col));
                }
            }
        }
        return positions;
    }

    public getBoardState(playerId: string): string {
        const lines: string[] = [];
        lines.push(`${this.rows}x${this.cols}`);
        
        // Get or create player state
        let state = this.playerStates.get(playerId);
        if (!state) {
            state = new PlayerState(playerId);
            this.playerStates.set(playerId, state);
        }
        
        // Add each card's state in row-major order
        for (let row = 0; row < this.rows; row++) {
            for (let col = 0; col < this.cols; col++) {
                const card = this.cards[row]?.[col];
                const position = new Position(row, col);
                
                if (card === undefined) {
                    lines.push('none');
                } else if (!card.faceUp) {
                    lines.push('down');
                } else {
                    // Card is face-up
                    const isControlledByMe = state.controlled.some(pos => pos.equals(position));
                    if (isControlledByMe) {
                        lines.push(`my ${card.content}`);
                    } else {
                        lines.push(`up ${card.content}`);
                    }
                }
            }
        }
        
        return lines.join('\n');
    }

    public doesPlayerExist(playerId: string): boolean {
        return this.playerStates.has(playerId);
    }
}

/**
 * Represents a card in the Memory Scramble game.
 * Mutable: faceUp state can change.
 */
class Card {
    // Abstraction function:
    //   AF(content, faceUp) = a game card with content 'content',
    //   which is face-up if faceUp is true, face-down otherwise
    // Representation invariant:
    //   content is a non-empty string with no whitespace
    // Safety from rep exposure:
    //   content is readonly and string is immutable
    //   faceUp is public but boolean is immutable
    //   All fields are primitive types

    constructor(
        public readonly content: string,
        public faceUp: boolean = false
    ) {
        this.checkRep();
    }

    private checkRep(): void {
        assert(this.content.length > 0, 'Card content must be non-empty');
        assert(!this.content.match(/\s/), 'Card content must not contain whitespace');
    }

    /**
     * Check if this card matches another card (same content).
     * @param other the card to compare with
     * @returns true if the cards have the same content, false otherwise
     */
    public matches(other: Card): boolean {
        return this.content === other.content;
    }

    /**
     * Get string representation of this card.
     * @returns string representation showing content and face state
     */
    public toString(): string {
        return `Card(${this.content}, ${this.faceUp ? 'up' : 'down'})`;
    }
}

/**
 * Represents a position on the game board.
 * Immutable.
 */
class Position {
    // Abstraction function:
    //   AF(row, col) = a position at row 'row' and column 'col' on the game board,
    //   using 0-indexed coordinates with (0,0) at the top-left
    // Representation invariant:
    //   row >= 0, col >= 0
    // Safety from rep exposure:
    //   All fields are readonly and primitive types (immutable)

    constructor(
        public readonly row: number,
        public readonly col: number
    ) {
        this.checkRep();
    }

    private checkRep(): void {
        assert(this.row >= 0, 'Row must be non-negative');
        assert(this.col >= 0, 'Column must be non-negative');
    }

    /**
     * Check if this position equals another position.
     * @param other the position to compare with
     * @returns true if both row and column are equal, false otherwise
     */
    public equals(other: Position): boolean {
        return this.row === other.row && this.col === other.col;
    }

    /**
     * Get string representation of this position.
     * @returns string in format "(row, col)"
     */
    public toString(): string {
        return `(${this.row}, ${this.col})`;
    }
}

/**
 * Represents a player's state in the game.
 * Mutable: controlled cards can change.
 */
class PlayerState {
    // Abstraction function:
    //   AF(playerId, controlled, toCleanUp) = the state of player 'playerId',
    //   who currently controls the cards at positions in 'controlled',
    //   and has cards at positions in 'toCleanUp' that need to be flipped down
    //   on their next first card flip
    // Representation invariant:
    //   playerId is non-empty
    //   controlled.length is 0, 1, or 2
    //   toCleanUp.length is 0 or 2
    //   all positions in controlled are distinct
    //   all positions in toCleanUp are distinct
    // Safety from rep exposure:
    //   playerId is readonly and string is immutable
    //   controlled is public but we never return the array directly
    //   toCleanUp is public but we never return the array directly

    public readonly playerId: string;
    public controlled: Position[]; // 0, 1, or 2 positions of currently flipped cards
    public toCleanUp: Position[]; // 0 or 2 positions that need cleanup on next first flip

    constructor(playerId: string) {
        this.playerId = playerId;
        this.controlled = [];
        this.toCleanUp = [];
        this.checkRep();
    }

    private checkRep(): void {
        assert(this.playerId.length > 0, 'Player ID must be non-empty');
        assert(this.controlled.length <= 2, 'Player can control at most 2 cards');
        assert(this.toCleanUp.length === 0 || this.toCleanUp.length === 2, 
               'Player can have 0 or 2 cards to clean up');
        // Check for distinct positions
        if (this.controlled.length === 2) {
            assert(!this.controlled[0]?.equals(this.controlled[1]!), 
                   'Controlled positions must be distinct');
        }
    }

    public addControlledPosition(position: Position): void {
        if (this.controlled.length >= 2) {
            throw new Error('Cannot control more than 2 positions');
        }
        this.controlled.push(position);
    }

    /**
     * Check if player has no cards controlled.
     * @returns true if player controls no cards
     */
    public hasNoCards(): boolean {
        return this.controlled.length === 0;
    }

    /**
     * Check if player has exactly one card controlled.
     * @returns true if player controls exactly one card
     */
    public hasOne(): boolean {
        return this.controlled.length === 1;
    }

    /**
     * Check if player has two cards controlled.
     * @returns true if player controls two cards
     */
    public hasTwo(): boolean {
        return this.controlled.length === 2;
    }

    /**
     * Get string representation of this player state.
     * @returns string showing player ID and controlled positions
     */
    public toString(): string {
        const positions = this.controlled.map(pos => pos.toString()).join(', ');
        return `Player(${this.playerId}, [${positions}])`;
    }
}

// Export for testing purposes only
// In production, these would remain unexported (internal implementation details)
export { Card as TestCard, Position as TestPosition, PlayerState as TestPlayerState };

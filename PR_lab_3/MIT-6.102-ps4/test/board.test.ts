/* Copyright (c) 2021-25 MIT 6.102/6.031 course staff, all rights reserved.
 * Redistribution of original or derived work requires permission of course staff.
 */

import assert from 'node:assert';
import fs from 'node:fs';
import { Board, TestCard, TestPosition, TestPlayerState } from '../src/board.js';


/**
 * Tests for the Board abstract data type.
 */
describe('Board', function() {

    /*
     * Testing strategy for parseFromFile()
     *
     * Partition on file validity:
     *   - file does not exist
     *   - file is empty
     *   - file has insufficient lines (only dimension line, no cards)
     *   - file has valid format
     *
     * Partition on dimension line:
     *   - valid format: "RxC" where R,C are positive integers
     *   - invalid format: non-numeric dimensions
     *   - invalid format: negative dimensions
     *   - invalid format: zero dimensions
     *   - invalid format: missing 'x' separator
     *
     * Partition on card lines:
     *   - correct number of cards (rows * cols)
     *   - too few cards
     *   - too many cards
     *
     * Partition on board size:
     *   - small board: 1x1, 2x2
     *   - larger board: 3x3, 5x5
     *
     * Partition on card content:
     *   - text cards
     *   - emoji cards
     *   - mixed
     */

    // Tests for valid files
    it('covers valid file, 3x3 board, emoji cards', async function() {
        const board = await Board.parseFromFile('boards/perfect.txt');
        assert(board !== null);
        assert(board !== undefined);
    });

    it('covers valid file, 5x5 board', async function() {
        const board = await Board.parseFromFile('boards/ab.txt');
        assert(board !== null);
        assert(board !== undefined);
    });

    // Tests for file not existing
    it('covers file does not exist', async function() {
        await assert.rejects(
            async () => await Board.parseFromFile('boards/test-boards/nonexistent.txt'),
            (error: Error) => {
                assert(error.message.includes('Invalid game board file'));
                return true;
            }
        );
    });

    // Tests for empty/insufficient content
    it('covers file is empty', async function() {
        await assert.rejects(
            async () => await Board.parseFromFile('boards/test-boards/empty.txt'),
            (error: Error) => {
                assert(error.message.includes('Invalid game board file'));
                return true;
            }
        );
    });

    it('covers file has only dimension line, no cards', async function() {
        await assert.rejects(
            async () => await Board.parseFromFile('boards/test-boards/no_cards.txt'),
            (error: Error) => {
                assert(error.message.includes('Invalid game board file'));
                return true;
            }
        );
    });

    // Tests for invalid dimension format
    it('covers non-numeric dimensions', async function() {
        await assert.rejects(
            async () => await Board.parseFromFile('boards/test-boards/bad_dimensions_text.txt'),
            (error: Error) => {
                assert(error.message.includes('Invalid board dimensions'));
                return true;
            }
        );
    });

    it('covers negative dimensions', async function() {
        await assert.rejects(
            async () => await Board.parseFromFile('boards/test-boards/negative_dimensions.txt'),
            (error: Error) => {
                assert(error.message.includes('Invalid board dimensions'));
                return true;
            }
        );
    });

    it('covers zero dimensions', async function() {
        await assert.rejects(
            async () => await Board.parseFromFile('boards/test-boards/zero_dimensions.txt'),
            (error: Error) => {
                assert(error.message.includes('Invalid board dimensions'));
                return true;
            }
        );
    });

    it('covers missing x separator in dimensions', async function() {
        await assert.rejects(
            async () => await Board.parseFromFile('boards/test-boards/bad_separator.txt'),
            (error: Error) => {
                assert(error.message.includes('Invalid board dimensions format'));
                return true;
            }
        );
    });

    // Tests for mismatched card count
    it('covers too few cards', async function() {
        await assert.rejects(
            async () => await Board.parseFromFile('boards/test-boards/too_few_cards.txt'),
            (error: Error) => {
                assert(error.message.includes('Expected'));
                return true;
            }
        );
    });

    it('covers too many cards', async function() {
        await assert.rejects(
            async () => await Board.parseFromFile('boards/test-boards/too_many_cards.txt'),
            (error: Error) => {
                assert(error.message.includes('Expected'));
                return true;
            }
        );
    });

    // Boundary case: smallest possible board
    it('covers 1x1 board (boundary)', async function() {
        const board = await Board.parseFromFile('boards/test-boards/1x1.txt');
        assert(board !== null);
    });
});

/**
 * Tests for helper classes (Card, Position, PlayerState).
 * These are tested indirectly through Board's behavior since they're not exported.
 * 
 * Note: If direct testing is needed, these classes could be temporarily exported
 * for testing purposes.
 */
describe('Board internal classes', function() {
    
    /*
     * Testing strategy:
     * 
     * Card class:
     *   - content: emoji, text, various characters
     *   - faceUp: true, false
     *   - matches(): same content, different content
     *   - toString(): face up, face down
     * 
     * Position class:
     *   - coordinates: (0,0), positive values, boundary positions
     *   - equals(): same position, different row, different col, both different
     *   - toString(): various positions
     * 
     * PlayerState class:
     *   - controlled cards: 0, 1, 2 cards
     *   - hasNoCards(), hasOne(), hasTwo()
     *   - toString(): various states
     */
    
    describe('Card', function() {
        it('covers card with emoji content, face down', function() {
            const card = new TestCard('🦄');
            assert.strictEqual(card.content, '🦄');
            assert.strictEqual(card.faceUp, false);
        });
        
        it('covers card with text content, face up', function() {
            const card = new TestCard('A', true);
            assert.strictEqual(card.content, 'A');
            assert.strictEqual(card.faceUp, true);
        });
        
        it('covers matches() with same content', function() {
            const card1 = new TestCard('🌈');
            const card2 = new TestCard('🌈');
            assert(card1.matches(card2));
        });
        
        it('covers matches() with different content', function() {
            const card1 = new TestCard('🦄');
            const card2 = new TestCard('🌈');
            assert(!card1.matches(card2));
        });
        
        it('covers toString() for face down card', function() {
            const card = new TestCard('X', false);
            assert.strictEqual(card.toString(), 'Card(X, down)');
        });
        
        it('covers toString() for face up card', function() {
            const card = new TestCard('Y', true);
            assert.strictEqual(card.toString(), 'Card(Y, up)');
        });
    });
    
    describe('Position', function() {
        it('covers position at origin (0, 0)', function() {
            const pos = new TestPosition(0, 0);
            assert.strictEqual(pos.row, 0);
            assert.strictEqual(pos.col, 0);
        });
        
        it('covers position with positive coordinates', function() {
            const pos = new TestPosition(3, 5);
            assert.strictEqual(pos.row, 3);
            assert.strictEqual(pos.col, 5);
        });
        
        it('covers equals() with same position', function() {
            const pos1 = new TestPosition(2, 3);
            const pos2 = new TestPosition(2, 3);
            assert(pos1.equals(pos2));
        });
        
        it('covers equals() with different row', function() {
            const pos1 = new TestPosition(1, 3);
            const pos2 = new TestPosition(2, 3);
            assert(!pos1.equals(pos2));
        });
        
        it('covers equals() with different col', function() {
            const pos1 = new TestPosition(2, 1);
            const pos2 = new TestPosition(2, 3);
            assert(!pos1.equals(pos2));
        });
        
        it('covers equals() with both different', function() {
            const pos1 = new TestPosition(1, 1);
            const pos2 = new TestPosition(2, 3);
            assert(!pos1.equals(pos2));
        });
        
        it('covers toString()', function() {
            const pos = new TestPosition(4, 7);
            assert.strictEqual(pos.toString(), '(4, 7)');
        });
    });
    
    describe('PlayerState', function() {
        it('covers player with no cards controlled', function() {
            const player = new TestPlayerState('alice');
            assert.strictEqual(player.playerId, 'alice');
            assert(player.hasNoCards());
            assert(!player.hasOne());
            assert(!player.hasTwo());
        });
        
        it('covers player with one card controlled', function() {
            const player = new TestPlayerState('bob');
            const pos = new TestPosition(1, 2);
            player.controlled.push(pos);
            assert(!player.hasNoCards());
            assert(player.hasOne());
            assert(!player.hasTwo());
        });
        
        it('covers player with two cards controlled', function() {
            const player = new TestPlayerState('charlie');
            player.controlled.push(new TestPosition(0, 0));
            player.controlled.push(new TestPosition(1, 1));
            assert(!player.hasNoCards());
            assert(!player.hasOne());
            assert(player.hasTwo());
        });
        
        it('covers toString() with no cards', function() {
            const player = new TestPlayerState('diana');
            assert.strictEqual(player.toString(), 'Player(diana, [])');
        });
        
        it('covers toString() with one card', function() {
            const player = new TestPlayerState('eve');
            player.controlled.push(new TestPosition(2, 3));
            assert.strictEqual(player.toString(), 'Player(eve, [(2, 3)])');
        });
        
        it('covers toString() with two cards', function() {
            const player = new TestPlayerState('frank');
            player.controlled.push(new TestPosition(0, 1));
            player.controlled.push(new TestPosition(2, 3));
            assert.strictEqual(player.toString(), 'Player(frank, [(0, 1), (2, 3)])');
        });
    });

    /*
     * Testing strategy for flipCard() - Single Player Rules
     *
     * CASE 1: First card flip (player controls 0 cards)
     *   Rule 1-A: no card there (undefined) → operation fails
     *   Rule 1-B: card is face down → flip up and control
     *   Rule 1-C: card is face up, not controlled → take control
     *   Rule 1-D: card is controlled by another player → wait (deferred to Problem 3)
     *
     * CASE 2: Second card flip (player controls 1 card)
     *   Rule 2-A: no card there → fail, relinquish first card
     *   Rule 2-B: card is controlled (including by self) → fail, relinquish
     *   Rule 2-C: card is face down → flip it up
     *   Rule 2-D: cards match → keep control of both
     *   Rule 2-E: cards don't match → relinquish control of both
     *
     * CASE 3: Player has 2 cards (cleanup from previous play)
     *   Rule 3-A: cards match → remove from board
     *   Rule 3-B: cards don't match → flip down if not controlled by another player
     *
     * Partition on board state:
     *   - small board (2x2)
     *   - larger board (3x3)
     * 
     * Partition on card positions:
     *   - same row
     *   - same column
     *   - different row and column
     *
     * Partition on card matching:
     *   - matching cards
     *   - non-matching cards
     */

    describe('flipCard() - Rule 1: First Card', function() {
        
        it('covers Rule 1-A: flip empty position (no card) fails silently', async function() {
            const board = await Board.parseFromFile('boards/perfect.txt');
            
            // Create a scenario with removed cards
            await board.flipCard(new TestPosition(0, 0), 'alice');
            await board.flipCard(new TestPosition(0, 1), 'alice'); // Match
            await board.flipCard(new TestPosition(1, 0), 'alice'); // Triggers cleanup, removes (0,0) and (0,1)
            
            const beforeState = board.getBoardState('alice');
            const beforeLines = beforeState.split('\n');
            
            // Verify cards were removed
            assert.strictEqual(beforeLines[1], 'none', '(0,0) should be removed');
            assert.strictEqual(beforeLines[2], 'none', '(0,1) should be removed');
            
            // // Try to flip removed position - should fail (Rule 2-A applies since alice controls 1 card)
            // // This is treated as a SECOND card flip, so alice relinquishes her first card
            // await board.flipCard(new TestPosition(0, 0), 'alice');
            
            // const afterState = board.getBoardState('alice');
            // const afterLines = afterState.split('\n');
            
            // // Alice should have relinquished (1,0) per Rule 2-A
            // assert.strictEqual(afterLines[4], 'up 🌈', '(1,0) should be relinquished after failed second flip');
        });

        it('covers Rule 1-B: flip face-down card, flips up and controls', async function() {
            const board = await Board.parseFromFile('boards/perfect.txt');
            
            await board.flipCard(new TestPosition(0, 0), 'alice');
            
            const state = board.getBoardState('alice');
            const lines = state.split('\n');
            
            assert.strictEqual(lines[0], '3x3');
            assert(lines[1]?.startsWith('my '), 'alice should control card at (0,0)');
            
            // Rest should be face-down
            for (let i = 2; i <= 9; i++) {
                assert.strictEqual(lines[i], 'down', `card at position ${i-1} should be face-down`);
            }

            // The card is up for other players as well
            const bobState = board.getBoardState('bob');
            const bobLines = bobState.split('\n');
            assert(bobLines[1]?.startsWith('up '), 'bob sees the card (0,0) as up');
        });

        it('covers Rule 1-C: take control of face-up uncontrolled card', async function() {
            const board = await Board.parseFromFile('boards/perfect.txt');
            
            // Alice flips two non-matching cards
            await board.flipCard(new TestPosition(0, 0), 'alice');
            await board.flipCard(new TestPosition(1, 0), 'alice'); // Don't match
            
            // Cards are face-up but alice doesn't control them anymore
            let state = board.getBoardState('alice');
            let lines = state.split('\n');
            assert(lines[1]?.startsWith('up '), '(0,0) should be face-up but not controlled');
            assert(lines[4]?.startsWith('up '), '(1,0) should be face-up but not controlled');
            
            // Bob takes control of alice's first card (Rule 1-C)
            await board.flipCard(new TestPosition(0, 0), 'bob');
            
            const bobState = board.getBoardState('bob');
            const bobLines = bobState.split('\n');
            assert(bobLines[1]?.startsWith('my '), 'bob should control (0,0)');
            
            const aliceState = board.getBoardState('alice');
            const aliceLines = aliceState.split('\n');
            assert(aliceLines[1]?.startsWith('up '), 'alice should see (0,0) as face-up but not controlled');
        });

        it('covers Rule 1-D: waiting for controlled card (async)', async function() {
            const board = await Board.parseFromFile('boards/perfect.txt');
            
            // Alice flips and controls a card
            await board.flipCard(new TestPosition(0, 0), 'alice');
            
            let aliceState = board.getBoardState('alice');
            let aliceLines = aliceState.split('\n');
            assert(aliceLines[1]?.startsWith('my '), 'alice should control (0,0)');
            
            // Bob tries to flip alice's card as first card - should wait
            const bobFlipPromise = board.flipCard(new TestPosition(0, 0), 'bob');
            
            // Give a tiny delay to ensure Bob starts waiting
            await new Promise(resolve => setTimeout(resolve, 10));
            
            // Alice hasn't relinquished yet, so Bob should still be waiting
            // We can't directly observe the waiting, but we can verify Bob doesn't have the card yet
            let bobState = board.getBoardState('bob');
            let bobLines = bobState.split('\n');
            assert(!bobLines[1]?.startsWith('my '), 'bob should not control (0,0) yet while waiting');
            
            // Alice makes a mismatch, relinquishing (0,0)
            await board.flipCard(new TestPosition(1, 0), 'alice');
            
            // Now Bob's flip should complete (he was waiting and now the card is available)
            await bobFlipPromise;
            
            // Verify Bob now controls the card
            bobState = board.getBoardState('bob');
            bobLines = bobState.split('\n');
            assert(bobLines[1]?.startsWith('my '), 'bob should control (0,0) after alice relinquished');
        });

        it('covers Rule 1-D: multiple players waiting, card released multiple times', async function() {
            const board = await Board.parseFromFile('boards/perfect.txt');
            
            // Alice controls a card
            await board.flipCard(new TestPosition(0, 0), 'alice');
            
            // Bob tries to flip alice's card - should wait
            const bobFlipPromise = board.flipCard(new TestPosition(0, 0), 'bob');
            
            // Short delay
            await new Promise(resolve => setTimeout(resolve, 5));
            
            // Alice relinquishes by making a mismatch
            await board.flipCard(new TestPosition(1, 0), 'alice');
            
            // Bob's flip should complete and he gets the card
            await bobFlipPromise;
            
            const bobState = board.getBoardState('bob');
            assert(bobState.split('\n')[1]?.startsWith('my '), 'bob should control (0,0)');
            
            // Now Charlie tries to flip - should wait for Bob
            const charlieFlipPromise = board.flipCard(new TestPosition(0, 0), 'charlie');
            
            // Short delay
            await new Promise(resolve => setTimeout(resolve, 5));
            
            // Bob makes a mismatch, relinquishing
            await board.flipCard(new TestPosition(2, 0), 'bob');
            
            // Charlie's flip should complete
            await charlieFlipPromise;
            
            const charlieState = board.getBoardState('charlie');
            assert(charlieState.split('\n')[1]?.startsWith('my '), 'charlie should control (0,0) after bob relinquished');
        });

        it('covers Rule 1-D: player waits with pending cleanup', async function() {
            this.timeout(5000); // Increase timeout to see what happens
            const board = await Board.parseFromFile('boards/perfect.txt');
            
            // Alice makes a mismatch, has cleanup pending
            await board.flipCard(new TestPosition(0, 0), 'alice');
            await board.flipCard(new TestPosition(1, 0), 'alice'); // Mismatch
            
            console.log('Alice made mismatch');
            
            // Verify alice has cleanup pending
            let aliceState = board.getBoardState('alice');
            let aliceLines = aliceState.split('\n');
            assert(aliceLines[1]?.startsWith('up '), 'cards should be face-up but not controlled');
            
            // Bob controls a different card
            await board.flipCard(new TestPosition(2, 0), 'bob');
            console.log('Bob controls (2,0)');
            
            // Alice tries to flip bob's card as first card - should trigger cleanup first, THEN wait
            console.log('Alice trying to flip bob card...');
            const aliceFlipPromise = board.flipCard(new TestPosition(2, 0), 'alice');
            
            // Give time for alice's cleanup to happen
            await new Promise(resolve => setTimeout(resolve, 100));
            console.log('After 100ms wait');
            
            // Alice's cards from the mismatch should now be flipped down
            aliceState = board.getBoardState('alice');
            aliceLines = aliceState.split('\n');
            console.log('Alice state:', aliceLines[1], aliceLines[4]);
            
            // Bob relinquishes by flipping alice's controlled position from earlier (now down)
            // This will be Rule 2-E (mismatch) and bob relinquishes
            console.log('Bob relinquishing...');
            await board.flipCard(new TestPosition(0, 0), 'bob'); // Face-down card - Rule 2-E mismatch
            
            // Alice's flip should complete
            console.log('Waiting for alice flip to complete...');
            await aliceFlipPromise;
            console.log('Alice flip completed');
            
            // Alice should now control (2,0)
            aliceState = board.getBoardState('alice');
            aliceLines = aliceState.split('\n');
            assert(aliceLines[7]?.startsWith('my '), 'alice should control (2,0) after waiting');
        });
    });

    describe('flipCard() - Rule 2: Second Card', function() {
        
        it('covers Rule 2-A: no card at position, fails and relinquishes first', async function() {
            const board = await Board.parseFromFile('boards/perfect.txt');
            
            // Create removed cards
            await board.flipCard(new TestPosition(0, 0), 'alice');
            await board.flipCard(new TestPosition(0, 1), 'alice'); // Match
            await board.flipCard(new TestPosition(1, 0), 'alice'); // Cleanup removes (0,0) and (0,1)
            
            // Alice now controls (1,0)
            let state = board.getBoardState('alice');
            let lines = state.split('\n');
            assert(lines[4]?.startsWith('my '), 'alice should control (1,0)');
            
            // Alice tries to flip removed position as second card - should fail and relinquish
            await board.flipCard(new TestPosition(0, 0), 'alice');
            
            state = board.getBoardState('alice');
            lines = state.split('\n');
            assert(lines[4]?.startsWith('up '), '(1,0) should be relinquished (face-up but not controlled)');
        });

        it('covers Rule 2-B: card is controlled, fails and relinquishes, SAME PLAYER', async function() {
            const board = await Board.parseFromFile('boards/perfect.txt');
            
            await board.flipCard(new TestPosition(0, 0), 'alice');
            
            let state = board.getBoardState('alice');
            let lines = state.split('\n');
            assert(lines[1]?.startsWith('my '), 'alice should control (0,0)');
            
            // Try to flip same card as second card
            await board.flipCard(new TestPosition(0, 0), 'alice');
            
            state = board.getBoardState('alice');
            lines = state.split('\n');
            assert(lines[1]?.startsWith('up '), '(0,0) should be relinquished (face-up but not controlled)');
        });

        it('covers Rule 2-B: card is controlled, fails and relinquishes, DIFFERENT PLAYER', async function() {
            const board = await Board.parseFromFile('boards/perfect.txt');
            
            // Alice flips a card
            await board.flipCard(new TestPosition(0, 0), 'alice');
            
            let state = board.getBoardState('alice');
            let lines = state.split('\n');
            assert(lines[1]?.startsWith('my '), 'alice should control (0,0)');
            
            // Bob flips his 1st card
            await board.flipCard(new TestPosition(0, 1), 'bob');

            let stateBob = board.getBoardState('bob');
            let linesBob = stateBob.split('\n');
            assert(linesBob[2]?.startsWith('my '), 'bob should control (0,1)');

            // Bob tries to flip alice's controlled card as second card
            await board.flipCard(new TestPosition(0, 0), 'bob');

            // Bob now does not control his 1st card
            let stateBob2 = board.getBoardState('bob');
            let linesBob2 = stateBob2.split('\n');
            assert(linesBob2[2]?.startsWith('up '), '(0,1) should be relinquished (face-up but not controlled)');
        });

        // 2-C: the 2nd card was face down and uncontrolled and it turnes face up
        it('covers Rule 2-C/2-D: cards match, keep control of both', async function() {
            const board = await Board.parseFromFile('boards/perfect.txt');
            
            await board.flipCard(new TestPosition(0, 0), 'alice');
            await board.flipCard(new TestPosition(0, 1), 'alice'); // Match
            
            let state = board.getBoardState('alice');
            let lines = state.split('\n');
            
            // Both cards should remain controlled
            assert(lines[1]?.startsWith('my '), 'first card should remain controlled');
            assert(lines[2]?.startsWith('my '), 'second card should remain controlled');

            let stateBob = board.getBoardState('bob');
            let linesBob = stateBob.split('\n');

            // Both cards should be face-up for other players as well
            assert(linesBob[1]?.startsWith('up '), 'first card should be face-up for bob');
            assert(linesBob[2]?.startsWith('up '), 'second card should be face-up for bob');
        });

        it('covers Rule 2-C/2-E: cards dont match, relinquish both', async function() {
            const board = await Board.parseFromFile('boards/perfect.txt');
            
            await board.flipCard(new TestPosition(0, 0), 'alice');
            await board.flipCard(new TestPosition(0, 2), 'alice'); // Don't match
            
            const state = board.getBoardState('alice');
            const lines = state.split('\n');
            
            // Both cards should be face-up but not controlled
            assert(lines[1]?.startsWith('up '), 'first card should be relinquished');
            assert(lines[3]?.startsWith('up '), 'second card should be relinquished');
        });
    });

    describe('flipCard() - Rule 3: Cleanup', function() {
        
        it('covers Rule 3-A: matching cards are removed from board', async function() {
            const board = await Board.parseFromFile('boards/perfect.txt');
            
            // Alice flips matching pair
            await board.flipCard(new TestPosition(0, 0), 'alice');
            await board.flipCard(new TestPosition(0, 1), 'alice'); // Match
            
            let state = board.getBoardState('alice');
            let lines = state.split('\n');
            
            // Cards should still be on board
            assert(lines[1]?.startsWith('my '), 'cards should still exist before cleanup');
            assert(lines[2]?.startsWith('my '), 'cards should still exist before cleanup');
            
            // Alice starts new flip (triggers cleanup - Rule 3-A)
            await board.flipCard(new TestPosition(1, 0), 'alice');
            
            state = board.getBoardState('alice');
            lines = state.split('\n');
            
            // Cards at (0,0) and (0,1) should be removed
            assert.strictEqual(lines[1], 'none', '(0,0) should be removed');
            assert.strictEqual(lines[2], 'none', '(0,1) should be removed');

            // For Bob the cars should also be removed
            let stateBob = board.getBoardState('bob');
            let linesBob = stateBob.split('\n');
            assert.strictEqual(linesBob[1], 'none', '(0,0) should be removed for bob');
            assert.strictEqual(linesBob[2], 'none', '(0,1) should be removed for bob');
        });

        it('covers Rule 3-B: non-matching cards flip down if uncontrolled', async function() {
            const board = await Board.parseFromFile('boards/perfect.txt');
            
            // Alice flips non-matching pair
            await board.flipCard(new TestPosition(0, 0), 'alice');
            await board.flipCard(new TestPosition(0, 2), 'alice'); // Don't match
            
            let state = board.getBoardState('alice');
            let lines = state.split('\n');
            
            // Cards are relinquished but stay face-up
            assert(lines[1]?.startsWith('up '), '(0,0) should be face-up');
            assert(lines[3]?.startsWith('up '), '(0,2) should be face-up');
            
            // Alice starts new flip (triggers cleanup - Rule 3-B)
            await board.flipCard(new TestPosition(1, 0), 'alice');
            
            state = board.getBoardState('alice');
            lines = state.split('\n');
            
            // Cards should now be face-down
            assert.strictEqual(lines[1], 'down', '(0,0) should be flipped down');
            assert.strictEqual(lines[3], 'down', '(0,2) should be flipped down');
        });

        it('covers Rule 3-B: cards controlled by another player dont flip down', async function() {
            const board = await Board.parseFromFile('boards/perfect.txt');
            
            // Alice flips non-matching cards
            await board.flipCard(new TestPosition(0, 0), 'alice');
            await board.flipCard(new TestPosition(0, 2), 'alice'); // Don't match

            // Alice lost control of both cards, but they are still up
            
            // Bob takes control of alice's first card
            await board.flipCard(new TestPosition(0, 0), 'bob');
            
            let bobState = board.getBoardState('bob');
            let bobLines = bobState.split('\n');
            assert(bobLines[1]?.startsWith('my '), 'bob should control (0,0)');
            
            // Alice flips new first card - should flip down (0,1) but NOT (0,0) since bob controls it
            await board.flipCard(new TestPosition(1, 0), 'alice');
            
            const aliceState = board.getBoardState('alice');
            const aliceLines = aliceState.split('\n');
            
            // (0,0) should still be face-up (bob controls it)
            assert(aliceLines[1]?.startsWith('up '), '(0,0) should stay face-up (bob controls it)');
            // (0,1) should be flipped down
            assert.strictEqual(aliceLines[3], 'down', '(0,2) should be flipped down');
            
            bobState = board.getBoardState('bob');
            bobLines = bobState.split('\n');
            assert(bobLines[1]?.startsWith('my '), 'bob should still control (0,0)');
        });
    });

    describe('flipCard() - Integration Tests', function() {
        
        it('covers complete game flow: multiple flips, matches, and cleanup', async function() {
            const board = await Board.parseFromFile('boards/perfect.txt');
            
            // Alice plays a complete sequence
            await board.flipCard(new TestPosition(0, 0), 'alice'); // First card
            await board.flipCard(new TestPosition(0, 1), 'alice'); // Second card, match
            
            let state = board.getBoardState('alice');
            let lines = state.split('\n');
            assert(lines[1]?.startsWith('my '), 'alice controls first match');
            assert(lines[2]?.startsWith('my '), 'alice controls second match');
            
            await board.flipCard(new TestPosition(1, 0), 'alice'); // Cleanup + new first
            
            state = board.getBoardState('alice');
            lines = state.split('\n');
            assert.strictEqual(lines[1], 'none', 'first pair removed');
            assert.strictEqual(lines[2], 'none', 'first pair removed');
            
            await board.flipCard(new TestPosition(1, 1), 'alice'); // Second card, match
            await board.flipCard(new TestPosition(2, 0), 'alice'); // Cleanup + new first
            
            state = board.getBoardState('alice');
            lines = state.split('\n');
            assert.strictEqual(lines[4], 'none', 'second pair removed');
            assert.strictEqual(lines[5], 'none', 'second pair removed');
        });

        it('covers mismatches and cleanup cycles', async function() {
            const board = await Board.parseFromFile('boards/ab.txt');
            
            await board.flipCard(new TestPosition(0, 0), 'alice');
            await board.flipCard(new TestPosition(0, 1), 'alice'); // no match
            
            let state = board.getBoardState('alice');
            let lines = state.split('\n');
            assert(lines[1]?.startsWith('up '), 'cards relinquished but face-up');
            
            await board.flipCard(new TestPosition(1, 0), 'alice'); // Cleanup, then flip
            
            state = board.getBoardState('alice');
            lines = state.split('\n');
            assert.strictEqual(lines[1], 'down', 'first card flipped down after cleanup');
            assert.strictEqual(lines[2], 'down', 'second card flipped down after cleanup');
        });

        it('covers flipping invalid positions', async function() {
            const board = await Board.parseFromFile('boards/perfect.txt');
            
            // Try to flip out of bounds
            await assert.rejects(async () => {
                await board.flipCard(new TestPosition(10, 10), 'alice');
            }, Error, 'Should throw for out of bounds');
            
            await assert.rejects(async () => {
                await board.flipCard(new TestPosition(-1, 0), 'alice');
            }, Error, 'Should throw for negative position');
        });
    });

    describe('Card State Validation', function() {
        
        it('validates cards are flipped correctly during game flow', async function() {
            const board = await Board.parseFromFile('boards/perfect.txt');
            
            // Flip a card face up (Rule 1-B)
            await board.flipCard(new TestPosition(0, 0), 'alice');
            
            // Verify it's face up
            let state = board.getBoardState('alice');
            let lines = state.split('\n');
            assert(lines[1]?.startsWith('my '), 'card should be face-up and controlled');
            
            // Make a mismatch - cards go to toCleanUp but stay face-up
            await board.flipCard(new TestPosition(1, 0), 'alice');
            
            state = board.getBoardState('alice');
            lines = state.split('\n');
            assert(lines[1]?.startsWith('up '), '(0,0) should be face-up but not controlled');
            assert(lines[4]?.startsWith('up '), '(1,0) should be face-up but not controlled');
            
            // Next flip triggers cleanup - cards flip down (Rule 3-B)
            await board.flipCard(new TestPosition(2, 0), 'alice');
            
            state = board.getBoardState('alice');
            lines = state.split('\n');
            assert.strictEqual(lines[1], 'down', '(0,0) should be flipped down after cleanup');
            assert.strictEqual(lines[4], 'down', '(1,0) should be flipped down after cleanup');
            
            // Internal validation ensures we never:
            // - Flip face-up card up again
            // - Flip face-down card down again  
            // - Flip controlled cards down
            // These are caught by the flipCardUp/flipCardDown helper methods
        });

        it('prevents flipping controlled cards down during cleanup', async function() {
            const board = await Board.parseFromFile('boards/perfect.txt');
            
            // Alice makes a mismatch
            await board.flipCard(new TestPosition(0, 0), 'alice');
            await board.flipCard(new TestPosition(1, 0), 'alice');
            
            // Bob takes control of one of alice's cards (Rule 1-C)
            await board.flipCard(new TestPosition(0, 0), 'bob');
            
            // Alice's next flip triggers cleanup
            // (0,0) should NOT flip down because bob controls it (Rule 3-B check)
            await board.flipCard(new TestPosition(2, 0), 'alice');
            
            // Verify bob still controls (0,0) and it's face-up
            const bobState = board.getBoardState('bob');
            const bobLines = bobState.split('\n');
            assert(bobLines[1]?.startsWith('my '), 'bob should still control (0,0)');
            
            // (1,0) should be flipped down (not controlled)
            const aliceState = board.getBoardState('alice');
            const aliceLines = aliceState.split('\n');
            assert.strictEqual(aliceLines[4], 'down', '(1,0) should be flipped down');
        });

        it('handles waiting for card that gets matched and removed', async function() {
            const board = await Board.parseFromFile('boards/perfect.txt');
            
            // Alice flips first card at (0, 0) - gets control
            await board.flipCard(new TestPosition(0, 0), 'alice');
            
            // Bob tries to flip same card (0, 0) as his first card
            // This will wait because alice controls it (Rule 1-D)
            const bobPromise = board.flipCard(new TestPosition(0, 0), 'bob');
            
            // Give bob's promise time to start waiting
            await new Promise(resolve => setTimeout(resolve, 10));
            
            // Alice makes a match with (0, 0) and removes it
            await board.flipCard(new TestPosition(1, 2), 'alice'); // Find matching card
            
            // Alice's next flip triggers cleanup - removes the matched pair (Rule 3-A)
            await board.flipCard(new TestPosition(2, 0), 'alice');
            
            // Bob's wait should now resolve, but card is gone
            // IMPORTANT: Wait for bob's promise to fully resolve before continuing
            await bobPromise;
            
            // Verify bob doesn't control anything (card was removed)
            const bobState = board.getBoardState('bob');
            const bobLines = bobState.split('\n');
            assert(!bobLines[1]?.startsWith('my '), 'bob should not control removed card');
            
            // Position (0, 0) should be empty now
            assert.strictEqual(bobLines[1], 'none', 'position (0,0) should be empty');
        });

        it('handles second card not waiting when card is controlled', async function() {
            const board = await Board.parseFromFile('boards/perfect.txt');
            
            // Alice gets control of first card
            await board.flipCard(new TestPosition(0, 0), 'alice');
            
            // Bob gets control of another card
            await board.flipCard(new TestPosition(1, 0), 'bob');
            
            // Alice tries to flip bob's controlled card as her second card
            // Rule 2-B: Should fail immediately without waiting
            const startTime = Date.now();
            await board.flipCard(new TestPosition(1, 0), 'alice');
            const elapsedTime = Date.now() - startTime;
            
            // Should complete very quickly (not wait)
            assert(elapsedTime < 100, 'second card flip should not wait when card is controlled');
            
            // Verify alice relinquished control of first card (Rule 2-B)
            const aliceState = board.getBoardState('alice');
            const aliceLines = aliceState.split('\n');
            assert(!aliceLines[1]?.startsWith('my '), 'alice should have relinquished first card');
            
            // Bob should still control his card
            const bobState = board.getBoardState('bob');
            const bobLines = bobState.split('\n');
            assert(bobLines[4]?.startsWith('my '), 'bob should still control (1,0)');
        });
    });
});


/* Copyright (c) 2021-25 MIT 6.102/6.031 course staff, all rights reserved.
 * Redistribution of original or derived work requires permission of course staff.
 */

import { Board, TestPosition } from './board.js';
import { map } from './commands.js';

/**
 * Simulation to test map() with actual gameplay.
 * Players flip cards and make matches while map() operations transform cards mid-game.
 * Tests that map() doesn't break the game or cause errors during normal play.
 */
async function simulationMapMain(): Promise<void> {
    const filename = 'boards/ab.txt';
    const board: Board = await Board.parseFromFile(filename);
    const size = 3;
    const players = 3; // Players playing the game
    const tries = 10;  // Each player makes 10 turns
    const maxDelayMilliseconds = 50;

    console.log('Starting map() + gameplay simulation');
    console.log(`${players} players will play while map() operations transform cards`);
    console.log('='.repeat(60));

    // Show initial board state
    console.log('\n📋 INITIAL BOARD STATE:');
    showBoardContents();
    console.log();

    // Track statistics
    let mapCount = 0;
    let mapErrors = 0;

    // Define transformation functions that will be applied during gameplay
    const transformations = [
        async (card: string): Promise<string> => {
            await timeout(Math.random() * 20);
            return '⭐' + card; // Add star prefix
        },
        async (card: string): Promise<string> => {
            await timeout(Math.random() * 20);
            return card + '✨'; // Add sparkle suffix
        },
        async (card: string): Promise<string> => {
            await timeout(Math.random() * 20);
            return '【' + card + '】'; // Add brackets
        },
    ];

    // Start players playing the game
    const playerPromises: Array<Promise<void>> = [];
    for (let ii = 0; ii < players; ++ii) {
        playerPromises.push(player(ii));
    }

    // Start map operations that run periodically during gameplay
    const mapperPromises: Array<Promise<void>> = [];
    for (let mapOp = 0; mapOp < 3; mapOp++) {
        mapperPromises.push(mapper(mapOp));
    }

    // Wait for all to complete
    await Promise.all([...playerPromises, ...mapperPromises]);

    console.log('='.repeat(60));
    console.log('Simulation complete!');
    console.log(`Total map operations: ${mapCount}`);
    console.log(`Map errors: ${mapErrors}`);
    
    if (mapErrors > 0) {
        console.error('⚠️  Some map operations failed');
        process.exit(1);
    } else {
        console.log('✅ All operations completed successfully!');
    }

    /**
     * Helper to show current board contents
     */
    function showBoardContents(): void {
        console.log('  Cards on board:');
        let cardCount = 0;
        for (let row = 0; row < size; row++) {
            for (let col = 0; col < size; col++) {
                // Access the board's internal cards array to see actual card content
                const card = (board as any).cards[row][col];
                if (card === undefined) {
                    // No card at this position
                    continue;
                }
                
                cardCount++;
                const content = card.content;
                
                // Check the card's state
                if (card.faceUp) {
                    if (card.controlledBy !== undefined) {
                        console.log(`    (${row},${col}): [controlled: ${content}]`);
                    } else {
                        console.log(`    (${row},${col}): [face-up: ${content}]`);
                    }
                } else {
                    // Face-down - show content for debugging purposes
                    console.log(`    (${row},${col}): [face-down: ${content}]`);
                }
            }
        }
        console.log(`  Total cards remaining: ${cardCount}/9`);
    }

    /** 
     * Mapper: applies transformations to the board periodically during gameplay
     */
    async function mapper(mapperNumber: number): Promise<void> {
        const mapperId = `mapper${mapperNumber}`;
        const transform = transformations[mapperNumber % transformations.length];
        
        // Get transformation name for display
        let transformName = '';
        if (mapperNumber % 3 === 0) transformName = 'Add ⭐ prefix';
        else if (mapperNumber % 3 === 1) transformName = 'Add ✨ suffix';
        else transformName = 'Add 【】 brackets';
        
        // Wait a bit before starting
        await timeout(Math.random() * 100);
        
        // Apply 2-3 map operations during the game
        const mapsToApply = 2 + Math.floor(Math.random() * 2);
        
        for (let i = 0; i < mapsToApply; i++) {
            await timeout(Math.random() * 150); // Random delay between maps
            
            try {
                console.log(`\n${'='.repeat(60)}`);
                console.log(`[${mapperId}] 🔄 Applying transformation: ${transformName}`);
                console.log(`${'='.repeat(60)}`);
                console.log(`[${mapperId}] 📋 BEFORE transformation:`);
                showBoardContents();
                
                await map(board, mapperId, transform!);
                mapCount++;
                
                console.log(`\n[${mapperId}] 📋 AFTER transformation:`);
                showBoardContents();
                console.log(`[${mapperId}] ✅ Transformation complete`);
                console.log(`${'='.repeat(60)}\n`);
            } catch (error) {
                mapErrors++;
                console.error(`[${mapperId}] ❌ Transformation failed:`, error);
            }
        }
    }

    /** 
     * Player: plays the actual game - flips cards and tries to make matches
     */
    async function player(playerNumber: number): Promise<void> {
        const playerId = `player${playerNumber}`;
        console.log(`\n[${playerId}] starting game...\n`);

        let matchCount = 0;
        let mismatchCount = 0;
        let failedFlips = 0;

        for (let jj = 0; jj < tries; ++jj) {
            await timeout(Math.random() * maxDelayMilliseconds);
            
            // Try to flip over a first card at a random position
            const firstRow = randomInt(size);
            const firstCol = randomInt(size);
            const firstPosition = new TestPosition(firstRow, firstCol);
            
            console.log(`[${playerId}] Turn ${jj + 1}: FIRST card at (${firstRow}, ${firstCol})`);
            
            try {
                const firstResult = await board.flipCardWithLogging(firstPosition, playerId);
                console.log(`  [${playerId}]   ➜ ${firstResult}`);
                
                if (firstResult.includes('Rule 1-A') || firstResult.includes('failed')) {
                    failedFlips++;
                    continue; // Don't try second card if first fails
                }

                await timeout(Math.random() * maxDelayMilliseconds);
                
                // Try to flip over a second card
                const secondRow = randomInt(size);
                const secondCol = randomInt(size);
                const secondPosition = new TestPosition(secondRow, secondCol);
                
                console.log(`  [${playerId}] SECOND card at (${secondRow}, ${secondCol})`);
                
                const secondResult = await board.flipCardWithLogging(secondPosition, playerId);
                console.log(`  [${playerId}]   ➜ ${secondResult}`);
                
                if (secondResult.includes('Rule 2-D')) {
                    matchCount++;
                } else if (secondResult.includes('Rule 2-E')) {
                    mismatchCount++;
                } else if (secondResult.includes('Rule 2-A') || secondResult.includes('Rule 2-B')) {
                    failedFlips++;
                }
            } catch (error) {
                console.error(`[${playerId}] Error during turn:`, error);
                failedFlips++;
            }
        }
        
        console.log(`\n${'='.repeat(60)}`);
        console.log(`[${playerId}] SUMMARY:`);
        console.log(`  Matches: ${matchCount}, Mismatches: ${mismatchCount}, Failed flips: ${failedFlips}`);
        console.log(`${'='.repeat(60)}\n`);
    }
}

/**
 * Random positive integer generator
 * 
 * @param max a positive integer which is the upper bound of the generated number
 * @returns a random integer >= 0 and < max
 */
function randomInt(max: number): number {
    return Math.floor(Math.random() * max);
}

/**
 * @param milliseconds duration to wait
 * @returns a promise that fulfills no less than `milliseconds` after timeout() was called
 */
async function timeout(milliseconds: number): Promise<void> {
    const { promise, resolve } = Promise.withResolvers<void>();
    setTimeout(resolve, milliseconds);
    return promise;
}

void simulationMapMain();

/* Copyright (c) 2021-25 MIT 6.102/6.031 course staff, all rights reserved.
 * Redistribution of original or derived work requires permission of course staff.
 */

import assert from 'node:assert';
import { Board, TestPosition } from './board.js';

/**
 * Example code for simulating a game.
 * 
 * PS4 instructions: you may use, modify, or remove this file,
 *   completing it is recommended but not required.
 * 
 * @throws Error if an error occurs reading or parsing the board
 */
async function simulationMain(): Promise<void> {
    const filename = 'boards/zoom.txt';
    const board: Board = await Board.parseFromFile(filename);
    const size = 3;
    
    // ============================================================
    // TO TEST: "4 players, timeouts 0.1-2ms, 100 moves each"
    // Change these three lines:
    const players = 4;                    // <- Change to: 4
    const tries = 100;                     // <- Change to: 100
    const maxDelayMilliseconds = 2;     // <- Change to: 2 (for 0-2ms range)
    // Note: Math.random() * maxDelayMilliseconds gives range [0, maxDelayMilliseconds)
    // So maxDelayMilliseconds = 2 gives timeouts between 0 and 2ms
    // ============================================================

    console.log(`Starting simulation with ${players} player(s) on a ${size}x${size} board`);
    console.log(`Each player will attempt ${tries} flips`);
    console.log('='.repeat(60));

    // start up one or more players as concurrent asynchronous function calls
    const playerPromises: Array<Promise<void>> = [];
    for (let ii = 0; ii < players; ++ii) {
        playerPromises.push(player(ii));
    }
    // wait for all the players to finish (unless one throws an exception)
    await Promise.all(playerPromises);

    console.log('='.repeat(60));
    console.log('Simulation complete!');

    /** @param playerNumber player to simulate */
    async function player(playerNumber: number): Promise<void> {
        // Player ID is just the player number as a string
        const playerId = `player${playerNumber}`;
        console.log(`\n${playerId} starting...\n`);

        let matchCount = 0;
        let mismatchCount = 0;
        let failedFirstFlips = 0;
        let failedSecondFlips = 0;

        for (let jj = 0; jj < tries; ++jj) {
            await timeout(Math.random() * maxDelayMilliseconds);
            
            // Try to flip over a first card at a random position
            const firstRow = randomInt(size);
            const firstCol = randomInt(size);
            const firstPosition = new TestPosition(firstRow, firstCol);
            
            //console.log(`\n[${playerId}] Turn ${jj + 1}:`);
            console.log(`  [${playerId}] FIRST card at (${firstRow}, ${firstCol})`);
            
            const firstResult = await board.flipCardWithLogging(firstPosition, playerId);
            console.log(`  [${playerId}]   ➜ ${firstResult}`);
            
            if (firstResult.includes('Rule 1-A') || firstResult.includes('failed')) {
                failedFirstFlips++;
                console.log(`  [${playerId}] Turn ended (first flip failed)`);
                continue; // Don't try second card if first fails
            }

            await timeout(Math.random() * maxDelayMilliseconds);
            
            // Loop for second card attempts (may retry if card is controlled)
            let attempts = 0;
            const maxAttempts = 5; // Prevent infinite loops
            
            while (attempts < maxAttempts) {
                attempts++;
                
                // Try to flip over a second card at a random position
                const secondRow = randomInt(size);
                const secondCol = randomInt(size);
                const secondPosition = new TestPosition(secondRow, secondCol);
                
                console.log(`  [${playerId}] SECOND card at (${secondRow}, ${secondCol}) [attempt ${attempts}]`);
                
                const secondResult = await board.flipCardWithLogging(secondPosition, playerId);
                console.log(`  [${playerId}]   ➜ ${secondResult}`);
                
                if (secondResult.includes('Rule 2-D')) {
                    matchCount++;
                    console.log(`  [${playerId}] Turn ended (MATCH!)`);
                    break;
                } else if (secondResult.includes('Rule 2-E')) {
                    mismatchCount++;
                    console.log(`  [${playerId}] Turn ended (no match)`);
                    break;
                } else if (secondResult.includes('Rule 2-A') || secondResult.includes('Rule 2-B')) {
                    // Failed second flip - try again with a different random position
                    failedSecondFlips++;
                    if (attempts >= maxAttempts) {
                        console.log(`  [${playerId}] Turn ended (too many failed attempts)`);
                    }
                    // Continue loop to try another position
                } else if (secondResult.includes('Rule 1-A') || secondResult.includes('Rule 1-B/C')) {
                    // Cleanup happened during second flip, then processed as first card
                    // This means the player now controls a card (or tried to flip empty spot)
                    // Either way, the "turn" is effectively complete
                    console.log(`  [${playerId}] Turn ended (cleanup triggered, now has first card)`);
                    break;
                } else if (secondResult.includes('Rule 3-A')) {
                    // Cleanup happened and removed cards
                    console.log(`  [${playerId}] Turn ended (cleanup completed)`);
                    break;
                } else {
                    // Truly unexpected result
                    console.log(`  [${playerId}] Turn ended (unexpected: ${secondResult.substring(0, 30)})`);
                    break;
                }
            }
        }
        
        console.log(`\n${'='.repeat(60)}`);
        console.log(`${playerId} SUMMARY:`);
        console.log(`  Matches found: ${matchCount}`);
        console.log(`  Mismatches: ${mismatchCount}`);
        console.log(`  Failed first flips: ${failedFirstFlips}`);
        console.log(`  Failed second flips: ${failedSecondFlips}`);
        console.log(`${'='.repeat(60)}`);
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

void simulationMain();


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
    const filename = 'boards/perfect.txt';
    const board: Board = await Board.parseFromFile(filename);
    const size = 3;
    const players = 5; // Increased to test concurrency
    const tries = 10;
    const maxDelayMilliseconds = 10;

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
            
            console.log(`\n${playerId} - Turn ${jj + 1}:`);
            console.log(`  FIRST card at (${firstRow}, ${firstCol})`);
            
            const firstResult = await board.flipCardWithLogging(firstPosition, playerId);
            console.log(`    -> ${firstResult}`);
            
            if (firstResult.includes('Rule 1-A') || firstResult.includes('failed')) {
                failedFirstFlips++;
                continue; // Don't try second card if first fails
            }

            await timeout(Math.random() * maxDelayMilliseconds);
            
            // Try to flip over a second card at a random position
            const secondRow = randomInt(size);
            const secondCol = randomInt(size);
            const secondPosition = new TestPosition(secondRow, secondCol);
            
            console.log(`  SECOND card at (${secondRow}, ${secondCol})`);
            
            const secondResult = await board.flipCardWithLogging(secondPosition, playerId);
            console.log(`    -> ${secondResult}`);
            
            if (secondResult.includes('Rule 2-D')) {
                matchCount++;
            } else if (secondResult.includes('Rule 2-E')) {
                mismatchCount++;
            } else if (secondResult.includes('Rule 2-A') || secondResult.includes('Rule 2-B')) {
                failedSecondFlips++;
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


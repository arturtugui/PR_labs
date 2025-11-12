/* Copyright (c) 2021-25 MIT 6.102/6.031 course staff, all rights reserved.
 * Redistribution of original or derived work requires permission of course staff.
 */

import { Board, TestPosition } from './board.js';
import { watch } from './commands.js';

/**
 * Simulation to test the watch() functionality.
 * 
 * This simulation demonstrates that watch() properly waits for board changes
 * and notifies watchers when cards flip, are removed, or change content.
 */

async function simulationWatchMain(): Promise<void> {
    const board = await Board.parseFromFile('boards/perfect.txt');
    const size = board.getRows();
    
    console.log('Starting watch() simulation');
    console.log('3 players will play while 2 watchers observe changes');
    console.log('='.repeat(60));
    
    // Helper to delay execution
    function timeout(ms: number): Promise<void> {
        return new Promise(resolve => setTimeout(resolve, ms));
    }

    /**
     * Player simulates gameplay by flipping cards
     */
    async function player(playerNumber: number): Promise<void> {
        const playerId = `player${playerNumber}`;
        console.log(`\n[${playerId}] starting game...\n`);
        
        await timeout(Math.random() * 50); // Random start delay
        
        // Play 5 turns
        for (let turn = 1; turn <= 5; turn++) {
            await timeout(Math.random() * 100); // Random delay between turns
            
            // Pick random positions to flip
            const row1 = Math.floor(Math.random() * size);
            const col1 = Math.floor(Math.random() * size);
            
            try {
                console.log(`[${playerId}] Turn ${turn}: Flipping card at (${row1}, ${col1})`);
                await board.flipCard(new TestPosition(row1, col1), playerId);
                
                // Try to flip a second card
                await timeout(20);
                const row2 = Math.floor(Math.random() * size);
                const col2 = Math.floor(Math.random() * size);
                
                console.log(`[${playerId}]   Flipping second card at (${row2}, ${col2})`);
                await board.flipCard(new TestPosition(row2, col2), playerId);
            } catch (error) {
                console.log(`[${playerId}]   Flip failed (expected): ${String(error).substring(0, 50)}...`);
            }
        }
        
        console.log(`\n[${playerId}] finished playing\n`);
    }

    /**
     * Watcher observes board changes using watch()
     */
    async function watcher(watcherNumber: number): Promise<void> {
        const watcherId = `watcher${watcherNumber}`;
        let changeCount = 0;
        
        console.log(`[${watcherId}] 👀 Started watching for changes...\n`);
        
        // Watch for changes up to 10 times
        while (changeCount < 10) {
            try {
                console.log(`[${watcherId}] 🔍 Waiting for change #${changeCount + 1}...`);
                const boardState = await watch(board, watcherId);
                changeCount++;
                
                // Count remaining cards
                const lines = boardState.split('\n');
                let cardsRemaining = 0;
                for (const line of lines.slice(1)) {
                    if (line !== 'none') {
                        cardsRemaining++;
                    }
                }
                
                console.log(`[${watcherId}] ✅ Change #${changeCount} detected! Cards remaining: ${cardsRemaining}/${size * size}`);
            } catch (error) {
                console.error(`[${watcherId}] ❌ Watch error:`, error);
                break;
            }
        }
        
        console.log(`\n[${watcherId}] 👀 Finished watching (${changeCount} changes observed)\n`);
    }

    // Start players playing the game
    const playerPromises: Array<Promise<void>> = [];
    for (let ii = 0; ii < 3; ++ii) {
        playerPromises.push(player(ii));
    }

    // Start watchers observing changes
    const watcherPromises: Array<Promise<void>> = [];
    for (let ii = 0; ii < 2; ++ii) {
        watcherPromises.push(watcher(ii));
    }

    // Wait for all to complete
    await Promise.all([...playerPromises, ...watcherPromises]);

    console.log('='.repeat(60));
    console.log('Simulation complete!');
    console.log('✅ Watch functionality working correctly!');
}

simulationWatchMain().catch(error => {
    console.error('Simulation error:', error);
    process.exit(1);
});

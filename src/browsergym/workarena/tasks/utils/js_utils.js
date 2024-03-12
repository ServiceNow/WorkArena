/*
Javascript utility functions for tasks

*/

/**
 * Function that registers to the gsft_main afterload event and sets a flag when it is loaded
 */
function registerGsftMainLoaded(){
    // Check that the script is running in the main iframe
    if (window.frameElement?.id === 'gsft_main'){
        waitForCondition(() => typeof window.addAfterPageLoadedEvent !== 'undefined', 100)
        .then(
            function (){
                window.addAfterPageLoadedEvent(
                    function(){
                                window.WORKARENA_LOAD_COMPLETE = true;
                                waLog('WorkArena detected gsft_main load completed.')
                    }
                );
                waLog('Registered to gsft_main afterload event.');
            }
        );
    }
}

/**
 * Function to wait for a condition to be met (asynchronous)
 * use as: waitForCondition(condition, 100).then(function)
 *
 * @param {function} condition - function that returns true when condition is met
 * @param {number} pollInterval - interval in ms to poll condition
 */
function waitForCondition(condition, pollInterval=100) {
    return new Promise((resolve, reject) => {
        const interval = setInterval(() => {
            if (condition()) {
                clearInterval(interval);
                resolve();
            }
        }, pollInterval);
    });
}

/**
 * WorkArena Logger
 *
 * @param {string} msg - message to log
 * @param {string} level - log level (info, warn, error)
 */
function waLog(msg, level) {
    if (level === undefined) {
        level = 'info';
    }
    console[level]('WorkArena: ' + msg);
}

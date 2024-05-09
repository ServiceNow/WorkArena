/*
Javascript utility functions for tasks

*/


/*
* Function to find an element in multiple nested shadow DOMs
*
* @param {string} selector - query selector to find the element
* @param {HTMLElement} root - root element to start the search
*
* @returns {HTMLElement} - element with the given id or null if not found
*/
function findElementInShadowDOM(selector, root = document) {
    // Check if current root has the element
    const element = root.querySelector(selector);
    if (element) {
        return element;
    }

    // If not found, search in the shadow DOM of each node
    const shadowRoots = Array.from(root.querySelectorAll('*'))
                              .map(el => el.shadowRoot)
                              .filter(sr => sr !== null);

    for (const shadowRoot of shadowRoots) {
        const foundElement = findElementInShadowDOM(selector, shadowRoot);
        if (foundElement) {
            return foundElement;
        }
    }

    // Return null if the element is not found in any shadow root
    return null;
}


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
 * @param {string} callerName - name of the function that called the logger
 * @param {string} level - log level (info, warn, error)
 */
function waLog(msg, callerName, level) {
    if (level === undefined) {
        level = 'info';
    }
    // Get current time
    const now = new Date();
    const timeString = now.toTimeString().split(' ')[0]; // Format as "HH:MM:SS"

    // Get the current frame's id (if it's top level, replace by "top")
    let frameId = window.frameElement?.id;
    if (frameId === undefined) {
        frameId = 'top';
    }


    if (callerName != undefined) {
        console[level](`WorkArena - ${callerName} - ${frameId}: [${timeString}] ${msg}`);
    } else {
        console[level](`WorkArena - ${frameId}: [${timeString}] ${msg}`);
    }
}


/**
 * Protects the execution of a function by URL
 *
 * @param {function} func - function to protect
 * @param {string} url - url to check
 *
 * @returns {function} - protected function (returns null if URL is not valid)
 */
async function protectExecutionByURL(func, url) {
    // Get the name of func
    const funcName = func.name;

    // Wait until the window has finished navigating
    await waitForCondition(() => window.location.href !== 'about:blank', 100);

    // Decode URL components in the current window location and the url argument
    const decodedCurrentUrl = decodeURIComponent(window.location.href);
    const decodedExpectedUrl = decodeURIComponent(url);

    if (decodedCurrentUrl.includes(decodedExpectedUrl)) {
        waLog(`URL is valid. Proceeding...`, funcName, 'info');
        return func;
    } else {
        return null;
    }
}


/**
 * Run a function only in the gsft_main iframe
 *
 * @param {function} func - function to protect
 */
function runOnlyInGsftMain(func){
    // Get the name of func
    const funcName = func.name;

    if (window.frameElement?.id === 'gsft_main'){
        waLog(`gsft_main detected. Proceeding...`, funcName, 'info');

        // Wait for the iframe to be fully loaded
        waitForCondition(() => window.WORKARENA_LOAD_COMPLETE === true, 100)
        .then(
            function(){
                waLog(`gsft_main has finished loading. Proceeding...`, funcName, 'info');
                func();
            }
        );
    }
}


/**
 * Function to run a function in gsft_main only if the URL matches
 *
 * @param {function} func - function to protect
 * @param {string} url - url to check
 */
async function runInGsftMainOnlyAndProtectByURL(func, url){
    // Protect the function by URL
    const protectedFunc = await protectExecutionByURL(func, url);
    if (protectedFunc === null) {
        return;
    }

    // Run the protected function in gsft_main
    runOnlyInGsftMain(protectedFunc);
}

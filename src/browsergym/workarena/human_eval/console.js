document.addEventListener('DOMContentLoaded', function() {

    // Disable right-click in all frames to prevent people from opening new tabs that don't have the main header
    document.addEventListener('contextmenu', function(event) {
        event.preventDefault();
    });

    // Disable Command/Ctrl + Click for the same reasons
    document.addEventListener('click', function(event) {
        if (event.metaKey || event.ctrlKey) {
            event.preventDefault();
        }
    });

    // Disable middle-click for the same reasons
    document.addEventListener('auxclick', function(event) {
        if (event.button === 1) {
            event.preventDefault();
        }
    });

    if (window != top) {
        return; // Do nothing if not in top window
    }

    // Check if the div already exists
    let newDiv = document.getElementById("humanEvalConsole");
    if (!newDiv) {
        // Create a new div element if it doesn't exist
        newDiv = document.createElement("div");
        newDiv.id = "humanEvalConsole";

        // Create a title for the div
        const title = document.createElement("h3");
        title.innerText = "Human Evaluation Console";
        title.style.textAlign = "center";
        newDiv.appendChild(title);

        // Progress status indicator
        const progressDiv = document.createElement("div");
        progressDiv.id = "progressDiv";
        progressDiv.style.marginTop = "-5px";
        progressDiv.style.marginBottom = "5px";
        newDiv.appendChild(progressDiv);

        // Create the 'New tab' button
        const newTabButton = document.createElement("button");
        newTabButton.innerText = "+";
        newTabButton.style.backgroundColor = "yellow";
        newTabButton.style.color = "black";
        newTabButton.style.border = "none";
        newTabButton.style.padding = "5px 5px";
        newTabButton.style.marginRight = "10px";
        newTabButton.setAttribute("title", "New Tab");
        newTabButton.onclick = function() {
            window.open(window.location.href, '_blank');
        };

        // Create the 'Validate' button
        const validateButton = document.createElement("button");
        validateButton.innerText = "Validate";
        validateButton.style.backgroundColor = "green";
        validateButton.style.color = "white";
        validateButton.style.border = "none";
        validateButton.style.padding = "10px 20px";
        validateButton.style.marginRight = "10px";
        validateButton.onclick = function() {
            window.NEED_VALIDATION = 1;
            console.log("Validation flag set:", window.NEED_VALIDATION);
            document.getElementById("taskStatusDiv").innerText = "Validation in progress...";
        };

        // Create the 'Give up' button
        const giveUpButton = document.createElement("button");
        giveUpButton.innerText = "Give up";
        giveUpButton.style.backgroundColor = "red";
        giveUpButton.style.color = "white";
        giveUpButton.style.border = "none";
        giveUpButton.style.padding = "10px 20px";
        giveUpButton.style.marginRight = "10px";
        giveUpButton.onclick = function() {
            window.HUMAN_ABANDON = 1;
            console.log("Give up flag set:", window.HUMAN_ABANDON);
            document.getElementById("taskStatusDiv").innerText = "Human abandoned task.";
        };

        // Create the 'Infeasible' button
        const infeasibleButton = document.createElement("button");
        infeasibleButton.innerText = "Infeasible";
        infeasibleButton.style.backgroundColor = "blue";
        infeasibleButton.style.color = "white";
        infeasibleButton.style.border = "none";
        infeasibleButton.style.padding = "10px 20px";
        infeasibleButton.onclick = function() {
            let reasonTextBox = document.getElementById("reasonTextBox");
            if (!reasonTextBox) {
                // Show a new div to get the reason
                const reasonTextBox = document.createElement("input");
                reasonTextBox.id = "reasonTextBox";
                reasonTextBox.type = "text";
                reasonTextBox.setAttribute("placeholder", "Reason: e.g., Field 'Bob' does not exist.");
                reasonTextBox.style.width = "300px";
                reasonTextBox.style.marginRight = "10px";
                newDiv.appendChild(reasonTextBox)
                reasonTextBox.focus()

                const reasonButton = document.createElement("button");
                reasonButton.innerText = "Submit";
                reasonButton.style.backgroundColor = "black";
                reasonButton.style.color = "white";
                reasonButton.style.border = "none";
                reasonButton.onclick = function() {
                    window.HUMAN_INFEASIBLE = 1;
                    console.log("Infeasible flag set:", window.HUMAN_ABANDON);
                    document.getElementById("taskStatusDiv").innerText = "Human marked task as infeasible.";
                };
                newDiv.appendChild(reasonButton)
            }
        };

        // Append buttons to the div
        newDiv.appendChild(newTabButton)
        newDiv.appendChild(validateButton);
        newDiv.appendChild(giveUpButton);
        newDiv.appendChild(infeasibleButton);

        // Create a status div below the buttons
        const taskStatusDiv = document.createElement("div");
        taskStatusDiv.id = "taskStatusDiv";
        taskStatusDiv.innerText = "Waiting for action...";
        taskStatusDiv.style.marginTop = "10px";
        newDiv.appendChild(taskStatusDiv); // Append the status div to the main div

        // Append the div to the body of the document
        document.body.appendChild(newDiv);
    }

    // Ensure the div is draggable vertically
    newDiv.style.position = "fixed";
    newDiv.style.right = "10px";
    newDiv.style.bottom = "10px";
    newDiv.style.zIndex = "1000";
    newDiv.style.backgroundColor = "#f0f0f0";
    newDiv.style.border = "1px solid black";
    newDiv.style.padding = "10px";
    newDiv.style.borderRadius = "8px"; // Rounded corners
    newDiv.style.cursor = "ns-resize"; // Cursor indicates vertical movement

    let isDragging = false;

    newDiv.onmousedown = function(event) {
        event.preventDefault(); // Prevent default text selection
        isDragging = true;
        let startY = event.clientY;
        let startBottom = parseInt(window.getComputedStyle(newDiv).bottom, 10);

        function onMouseMove(event) {
            if (isDragging) {
                let newBottom = startBottom - (event.clientY - startY);
                newDiv.style.bottom = newBottom + 'px'; // Update bottom position only
            }
        }

        document.addEventListener('mousemove', onMouseMove);

        document.onmouseup = function() {
            document.removeEventListener('mousemove', onMouseMove);
            newDiv.onmouseup = null;
            isDragging = false; // Stop dragging
        };
    };

    newDiv.ondragstart = function() {
        return false; // Prevent default dragging behavior
    };
});

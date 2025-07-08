// script.js (Consolidated JavaScript for both Monitoring and Chatbot, compatible with new styling)

// --- Monitoring Section Logic ---
(function() {
    document.addEventListener('DOMContentLoaded', () => {
        // Get DOM elements for the monitoring section
        const uploadForm = document.getElementById('uploadForm');
        const videoFile = document.getElementById('videoFile');
        const responseMessage = document.getElementById('responseMessage');
        const videoPlayerContainer = document.getElementById('videoPlayerContainer');
        const videoPlayer = document.getElementById('videoPlayer');
        const progressBar = document.getElementById('progressBar');
        const predictionTableBody = document.getElementById('predictionTableBody');
        const detectionIntervalSelect = document.getElementById('detectionInterval');
        const enableTreeDetectionCheckbox = document.getElementById('enableTreeDetection');
        const currentVideoStatus = document.getElementById('currentVideoStatus');
        const processedFramesStatus = document.getElementById('processedFramesStatus');
        const totalFramesStatus = document.getElementById('totalFramesStatus');

        // State variables for video processing
        let uploadedVideoURL = null;
        let progressIntervalId = null;
        let detectionsIntervalId = null;

        /**
         * Clears any active monitoring intervals (progress and detections).
         */
        function clearMonitoringIntervals() {
            if (progressIntervalId) {
                clearInterval(progressIntervalId);
                progressIntervalId = null;
            }
            if (detectionsIntervalId) {
                clearInterval(detectionsIntervalId);
                detectionsIntervalId = null;
            }
        }

        /**
         * Handles the video file upload and initiates monitoring.
         * @param {Event} event - The form submission event.
         */
        uploadForm.addEventListener('submit', async function(event) {
            event.preventDefault(); // Prevent default form submission

            const form = event.target;
            const formData = new FormData(form);

            // Append selected detection interval and tree detection preference
            formData.append('detectionInterval', detectionIntervalSelect.value);
            formData.append('enableTreeDetection', enableTreeDetectionCheckbox.checked);

            // Update UI to show uploading state
            responseMessage.textContent = 'Uploading video and starting monitoring... Please wait, this may take a moment.';
            responseMessage.className = 'message-box uploading'; // Add 'message-box' class
            videoPlayerContainer.style.display = 'none';
            progressBar.style.width = '0%';
            progressBar.textContent = '0%';
            currentVideoStatus.textContent = 'Preparing video for monitoring.';
            processedFramesStatus.textContent = 'Processed: 0 frames';
            totalFramesStatus.textContent = 'Total: 0 frames';
            predictionTableBody.innerHTML = '<tr><td colspan="5" class="no-data">No predictions yet.</td></tr>'; // Use 'no-data' class

            clearMonitoringIntervals(); // Clear any previous monitoring sessions

            try {
                const response = await fetch('http://localhost:5002/upload_video', {
                    method: 'POST',
                    body: formData
                });

                const data = await response.json();

                if (response.ok) {
                    responseMessage.textContent = `Success! Monitoring initiated. Server message: ${JSON.stringify(data.status || data, null, 2)}`;
                    responseMessage.className = 'message-box success'; // Add 'message-box' class
                    
                    // Revoke previous video URL if exists to free memory
                    if (uploadedVideoURL) {
                        URL.revokeObjectURL(uploadedVideoURL);
                    }
                    
                    const videoFileObj = videoFile.files.item(0);
                    if (videoFileObj) {
                        // Create a local URL for the uploaded video file for immediate playback
                        uploadedVideoURL = URL.createObjectURL(videoFileObj);
                        videoPlayer.src = uploadedVideoURL;
                        videoPlayerContainer.style.display = 'block';
                        videoPlayer.load(); // Load the video
                        videoPlayer.play(); // Start playback
                        currentVideoStatus.textContent = `Monitoring video: ${videoFileObj.name}`;
                    }

                    // Start polling for progress and detections
                    progressIntervalId = setInterval(fetchProgress, 1000); // Every 1 second
                    detectionsIntervalId = setInterval(fetchPredictions, 3000); // Every 3 seconds

                } else {
                    // Handle server-side errors
                    responseMessage.textContent = `Error! Failed to upload or start monitoring. Server response: ${JSON.stringify(data.error || data, null, 2)}\nStatus: ${response.status}`;
                    responseMessage.className = 'message-box error'; // Add 'message-box' class
                    clearMonitoringIntervals(); // Stop any pending intervals
                }
            } catch (error) {
                // Handle network errors or issues reaching the server
                responseMessage.textContent = `Network error: Could not connect to the monitoring server (http://localhost:5002). Please ensure the backend is running. Details: ${error.message}`;
                responseMessage.className = 'message-box error'; // Add 'message-box' class
                clearMonitoringIntervals(); // Stop any pending intervals
            }
        });

        /**
         * Fetches the latest predictions from the monitoring API and updates the table.
         */
        async function fetchPredictions() {
            const url = 'http://localhost:5002/api/monitoring/detections';
            
            try {
                const response = await fetch(url);
                if (response.ok) {
                    const predictions = await response.json();
                    displayPredictions(predictions);
                } else {
                    console.error(`Failed to fetch predictions: HTTP Status ${response.status}`);
                    predictionTableBody.innerHTML = '<tr><td colspan="5" class="no-data">Failed to load predictions. Please check server.</td></tr>'; // Use 'no-data' class
                }
            } catch (error) {
                console.error('Error fetching predictions:', error);
                predictionTableBody.innerHTML = '<tr><td colspan="5" class="no-data">Network error fetching predictions. Ensure API is running.</td></tr>'; // Use 'no-data' class
            }
        }

        /**
         * Fetches the current processing progress from the monitoring API.
         */
        async function fetchProgress() {
            try {
                const response = await fetch('http://localhost:5002/api/monitoring/progress');
                if (response.ok) {
                    const progressData = await response.json();
                    updateProgress(
                        progressData.processed_frames, 
                        progressData.total_frames, 
                        progressData.is_monitoring_active
                    );
                } else {
                    console.error(`Failed to fetch progress: HTTP Status ${response.status}`);
                    updateProgress(0, 0, false); // Reset progress on error
                }
            } catch (error) {
                console.error('Error fetching progress:', error);
                updateProgress(0, 0, false); // Reset progress on network error
            }
        }

        /**
         * Displays the fetched predictions in the table.
         * @param {Array<Object>} predictions - An array of prediction objects.
         */
        function displayPredictions(predictions) {
            predictionTableBody.innerHTML = ''; // Clear existing rows

            if (predictions && predictions.length > 0) {
                // Sort predictions by timestamp in descending order (newest first)
                predictions.sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp));

                predictions.forEach(prediction => {
                    const row = document.createElement('tr'); 

                    // Time Cell
                    const timeCell = document.createElement('td');
                    // Format time to be more readable, e.g., HH:MM:SS
                    timeCell.textContent = new Date(prediction.timestamp).toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
                    row.appendChild(timeCell);

                    // Fruit Type Cell
                    const fruitCell = document.createElement('td');
                    let fruitText = prediction.fruit_type && prediction.fruit_type.toLowerCase() !== 'unknown' ? prediction.fruit_type : 'N/A';
                    if (prediction.confidence_fruit !== null && prediction.confidence_fruit !== undefined) {
                        fruitText += ` (${(prediction.confidence_fruit * 100).toFixed(2)}%)`;
                    }
                    fruitCell.textContent = fruitText;
                    row.appendChild(fruitCell);

                    // Ripeness Cell
                    const ripenessCell = document.createElement('td');
                    let ripenessText = prediction.ripeness && prediction.ripeness.toLowerCase() !== 'unknown' ? prediction.ripeness : 'N/A';
                    if (prediction.confidence_ripeness !== null && prediction.confidence_ripeness !== undefined) {
                        ripenessText += ` (${(prediction.confidence_ripeness * 100).toFixed(2)}%)`;
                    }
                    ripenessCell.textContent = ripenessText;
                    row.appendChild(ripenessCell);

                    // Disease Cell
                    const diseaseCell = document.createElement('td');
                    let diseaseText = prediction.disease && prediction.disease.toLowerCase() !== 'unknown' ? prediction.disease : 'N/A';
                    if (prediction.confidence_disease !== null && prediction.confidence_disease !== undefined) {
                        diseaseText += ` (${(prediction.confidence_disease * 100).toFixed(2)}%)`;
                    }
                    diseaseCell.textContent = diseaseText;
                    row.appendChild(diseaseCell);

                    // Notes Cell
                    const notesCell = document.createElement('td');
                    notesCell.textContent = prediction.notes && prediction.notes.toLowerCase() !== 'unknown' ? prediction.notes : '';
                    row.appendChild(notesCell);

                    predictionTableBody.appendChild(row);
                });
            } else {
                const noPredictionsRow = document.createElement('tr');
                const noPredictionsCell = document.createElement('td');
                noPredictionsCell.colSpan = 5;
                noPredictionsCell.classList.add('no-data'); // Add 'no-data' class
                noPredictionsCell.textContent = 'No predictions yet. Upload a video to start monitoring!';
                predictionTableBody.appendChild(noPredictionsRow);
            }
        }

        /**
         * Updates the progress bar and status messages based on monitoring data.
         * @param {number} processedFrames - Number of frames processed.
         * @param {number} totalFrames - Total frames in the video.
         * @param {boolean} isMonitoringActive - True if monitoring is active, false otherwise.
         */
        function updateProgress(processedFrames, totalFrames, isMonitoringActive) {
            if (totalFrames > 0) {
                const progress = (processedFrames / totalFrames) * 100;
                progressBar.style.width = `${progress}%`;
                progressBar.textContent = `${progress.toFixed(1)}%`;
                processedFramesStatus.textContent = `Processed: ${processedFrames} frames`;
                totalFramesStatus.textContent = `Total: ${totalFrames} frames`;

                if (isMonitoringActive) {
                    const videoName = videoPlayer.src ? videoPlayer.src.split('/').pop() : 'video file';
                    currentVideoStatus.textContent = `Monitoring Active: ${videoName}`;
                    progressBar.style.backgroundColor = '#22c55e'; // Green for active (matching new palette)
                } else if (processedFrames === totalFrames && totalFrames > 0) {
                    currentVideoStatus.textContent = `Monitoring Finished.`;
                    progressBar.style.backgroundColor = '#16a34a'; // Darker green for finished (matching new palette)
                    clearMonitoringIntervals(); // Ensure intervals are cleared once finished
                } else {
                    currentVideoStatus.textContent = `Monitoring Inactive.`;
                    progressBar.style.backgroundColor = '#94a3b8'; // Grey for inactive (matching new palette)
                    if(progressIntervalId || detectionsIntervalId) {
                        clearMonitoringIntervals(); // Clear if it became inactive unexpectedly
                    }
                }
            } else {
                // Initial or no video state
                progressBar.style.width = '0%';
                progressBar.textContent = '0%';
                processedFramesStatus.textContent = 'Processed: 0 frames';
                totalFramesStatus.textContent = 'Total: 0 frames';
                currentVideoStatus.textContent = 'No video loaded / Monitoring Inactive.';
                progressBar.style.backgroundColor = '#94a3b8'; // Grey (matching new palette)
            }
        }

        // Initial data fetches when the page loads
        fetchProgress();
        fetchPredictions();
    });
})();


// --- Chatbot Section Logic ---
(function() {
    document.addEventListener('DOMContentLoaded', () => {
        // Get DOM elements for the chatbot section
        const chatWindow = document.getElementById('chat-window');
        const userInput = document.getElementById('user-input');
        const sendButton = document.getElementById('send-button');
        const attachmentButton = document.getElementById('attachment-button');
        const attachmentOptions = document.getElementById('attachment-options');
        const uploadImageButton = document.getElementById('upload-image-button');
        const imageUploadInput = document.getElementById('image-upload');

        let currentImageFile = null; // Stores the image file to be sent with the next message

        // IMPORTANT: Set the correct API URL for your chatbot backend
        const CHATBOT_API_URL = 'http://localhost:5000/chat'; // Corrected to port 5000

        /**
         * Displays a message in the chat window.
         * @param {string} message - The message content.
         * @param {'user'|'bot'} sender - The sender of the message ('user' or 'bot').
         */
        function displayMessage(message, sender) {
            const messageElement = document.createElement('div');
            messageElement.classList.add('message', `${sender}-message`);
            messageElement.textContent = message;
            chatWindow.appendChild(messageElement);
            chatWindow.scrollTop = chatWindow.scrollHeight; // Auto-scroll to the bottom
        }

        // Event listeners for sending messages
        sendButton.addEventListener('click', sendMessage);
        userInput.addEventListener('keypress', function(event) {
            if (event.key === 'Enter') {
                sendMessage();
            }
        });

        /**
         * Sends the user's message to the chatbot API.
         */
        async function sendMessage() {
            const message = userInput.value.trim();
            if (!message && !currentImageFile) {
                // Prevent sending empty messages without an image
                return;
            }

            // Display user's message immediately
            displayMessage(message || "(Image attached)", 'user');
            userInput.value = ''; // Clear input field

            // Show a loading indicator while waiting for bot's response
            const loadingMessageElement = document.createElement('div');
            loadingMessageElement.classList.add('message', 'bot-message');
            loadingMessageElement.innerHTML = `
                <div class="typing-indicator">
                    <span></span><span></span><span></span>
                </div>`;

            chatWindow.appendChild(loadingMessageElement);
            chatWindow.scrollTop = chatWindow.scrollHeight;

            const formData = new FormData();
            // CORRECTED: Using 'message' as the key for the user's text, matching your backend
            formData.append('message', message);
            if (currentImageFile) {
                formData.append('image', currentImageFile);
                currentImageFile = null; // Clear the image file after attaching it to FormData
                console.log("Image attached and sent.");
            }

            try {
                const response = await fetch(CHATBOT_API_URL, { // Use the defined CHATBOT_API_URL
                    method: 'POST',
                    body: formData
                });

                if (!response.ok) {
                    throw new Error(`HTTP error! Status: ${response.status}. Server response: ${await response.text()}`);
                }

                const data = await response.json();
                
                // Remove loading indicator after receiving response
                if (chatWindow.contains(loadingMessageElement)) {
                    chatWindow.removeChild(loadingMessageElement);
                }
                displayMessage(data.response, 'bot'); // Display bot's response

            } catch (error) {
                console.error('Error sending message to chatbot:', error);
                // Remove loading indicator on error
                if (chatWindow.contains(loadingMessageElement)) {
                    chatWindow.removeChild(loadingMessageElement);
                }
                // Provide user-friendly error message
                displayMessage(`Error: Could not connect to the chatbot or an issue occurred: ${error.message}. Please check if the chatbot backend is running on ${CHATBOT_API_URL}.`, 'bot');
            }
        }

        // Toggle visibility of attachment options
        attachmentButton.addEventListener('click', () => {
            attachmentOptions.classList.toggle('show');
        });

        // Trigger hidden file input when "Upload Image" button is clicked
        uploadImageButton.addEventListener('click', () => {
            imageUploadInput.click(); 
            attachmentOptions.classList.remove('show'); // Hide options after triggering input
        });

        // Handle file selection from the hidden image input
        imageUploadInput.addEventListener('change', (event) => {
            const file = event.target.files[0];
            if (file) {
                currentImageFile = file; // Store the selected file
                displayMessage(`Image selected: "${file.name}". This image will be sent with your next message.`, 'user');
            }
        });
    });
})();

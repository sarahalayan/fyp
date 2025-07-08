// script.js (Vanilla JavaScript for both Monitoring and Chatbot)

document.addEventListener('DOMContentLoaded', () => {
    // --- Dark Mode Toggle (present on all pages) ---
    const themeToggle = document.getElementById('theme-toggle');
    if (themeToggle) {
        themeToggle.addEventListener('click', function() {
            const html = document.documentElement;
            if (html.getAttribute('data-theme') === 'dark') {
                html.setAttribute('data-theme', 'light');
                this.innerHTML = '<i class="fas fa-moon"></i>';
            } else {
                html.setAttribute('data-theme', 'dark');
                this.innerHTML = '<i class="fas fa-sun"></i>';
            }
        });
    }

    // --- Monitoring Section Logic (for index.html) ---
    const uploadForm = document.getElementById('uploadForm');
    if (uploadForm) { // Check if monitoring elements are present on this page
        const videoFile = document.getElementById('videoFile');
        const responseMessage = document.getElementById('responseMessage');
        const videoPlayerContainer = document.getElementById('videoPlayerContainer');
        const videoPlayer = document.getElementById('videoPlayer');
        const progressBar = document.getElementById('progressBar');
        // No need for predictionTableBody on index.html anymore
        const detectionIntervalSelect = document.getElementById('detectionInterval');
        const enableTreeDetectionCheckbox = document.getElementById('enableTreeDetection');
        const currentVideoStatus = document.getElementById('currentVideoStatus');
        const processedFramesStatus = document.getElementById('processedFramesStatus');
        const totalFramesStatus = document.getElementById('totalFramesStatus');

        let uploadedVideoURL = null;
        let progressIntervalId = null;

        /**
         * Clears any active monitoring intervals (progress).
         */
        function clearMonitoringIntervals() {
            if (progressIntervalId) {
                clearInterval(progressIntervalId);
                progressIntervalId = null;
            }
        }

        /**
         * Handles the video file upload and initiates monitoring.
         * @param {Event} event - The form submission event.
         */
        uploadForm.addEventListener('submit', async function(event) {
            event.preventDefault(); // Prevent default form submission

            const formData = new FormData(uploadForm); // Use the form element directly

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

            clearMonitoringIntervals(); // Clear any previous monitoring sessions

            try {
                const response = await fetch('http://localhost:5002/upload_video', {
                    method: 'POST',
                    body: formData
                });

                const data = await response.json();

                if (response.ok) {
                    responseMessage.textContent = `Success! Monitoring initiated. Server message: ${JSON.stringify(data.status || data, null, 2)}`;
                    responseMessage.className = 'message-box success';
                    
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

                    // Start polling for progress
                    progressIntervalId = setInterval(fetchProgress, 1000); // Every 1 second

                } else {
                    // Handle server-side errors
                    responseMessage.textContent = `Error! Failed to upload or start monitoring. Server response: ${JSON.stringify(data.error || data, null, 2)}\nStatus: ${response.status}`;
                    responseMessage.className = 'message-box error';
                    clearMonitoringIntervals(); // Stop any pending intervals
                }
            } catch (error) {
                // Handle network errors or issues reaching the server
                responseMessage.textContent = `Network error: Could not connect to the monitoring server (http://localhost:5002). Please ensure the backend is running. Details: ${error.message}`;
                responseMessage.className = 'message-box error';
                clearMonitoringIntervals(); // Stop any pending intervals
            }
        });

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
                    if(progressIntervalId) { // Only clear progress interval if it exists
                        clearMonitoringIntervals();
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

        // Initial data fetch when the page loads
        fetchProgress();
    }

    // --- Latest Detections Section Logic (for detections.html) ---
    const predictionTableBody = document.getElementById('predictionTableBody');
    if (predictionTableBody) { // Check if detections table is present on this page
        let detectionsIntervalId = null; // Declare here for this scope

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
                    predictionTableBody.innerHTML = '<tr><td colspan="5" class="no-data">Failed to load predictions. Please check server.</td></tr>';
                }
            } catch (error) {
                console.error('Error fetching predictions:', error);
                predictionTableBody.innerHTML = '<tr><td colspan="5" class="no-data">Network error fetching predictions. Ensure API is running.</td></tr>';
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
                noPredictionsCell.classList.add('no-data');
                noPredictionsCell.textContent = 'No predictions yet. Upload a video on the Monitoring page to start!';
                noPredictionsRow.appendChild(noPredictionsCell);
                predictionTableBody.appendChild(noPredictionsRow);
            }
        }

        // Start polling for detections
        detectionsIntervalId = setInterval(fetchPredictions, 3000); // Every 3 seconds
        fetchPredictions(); // Initial fetch
    }


    // --- Chatbot Section Logic (for chatbot.html) ---
    const chatWindow = document.getElementById('chat-window');
    if (chatWindow) { // Check if chatbot elements are present on this page
        const userInput = document.getElementById('user-input');
        const sendButton = document.getElementById('send-button');
        const attachmentButton = document.getElementById('attachment-button');
        const attachmentOptions = document.getElementById('attachment-options');
        const uploadImageButton = document.getElementById('upload-image-button');
        const imageUploadInput = document.getElementById('image-upload');

        let currentImageFile = null; // Stores the image file to be sent with the next message

        const CHATBOT_API_URL = 'http://localhost:5000/chat';

        /**
         * Displays a message in the chat window.
         * @param {string} message - The message content.
         * @param {'user'|'bot'} sender - The sender of the message ('user' or 'bot').
         * @param {boolean} isImage - True if the message content is an image URL.
         */
        function displayMessage(message, sender, isImage = false) {
            const messageElement = document.createElement('div');
            messageElement.classList.add('message', `${sender}-message`);

            if (isImage) {
                const imgElement = document.createElement('img');
                imgElement.src = message;
                imgElement.alt = "User uploaded image";
                imgElement.style.maxWidth = '100%';
                imgElement.style.height = 'auto';
                imgElement.style.borderRadius = '8px';
                messageElement.appendChild(imgElement);
            } else {
                messageElement.textContent = message;
            }
            
            chatWindow.appendChild(messageElement);
            chatWindow.scrollTop = chatWindow.scrollHeight; // Auto-scroll to the bottom
        }

        // Event listeners for sending messages
        sendButton.addEventListener('click', handleSendMessage);
        userInput.addEventListener('keypress', function(event) {
            if (event.key === 'Enter') {
                event.preventDefault(); // Prevent default form submission if input is part of a form
                handleSendMessage();
            }
        });

        /**
         * Handles sending the user's message, including attached images.
         */
        async function handleSendMessage() {
            const message = userInput.value.trim();
            if (!message && !currentImageFile) {
                // Prevent sending empty messages without an image
                return;
            }

            // Display user's message immediately
            displayMessage(message || "(Image attached)", 'user');
            userInput.value = ''; // Clear input field

            // Display loading indicator
            const loadingMessageElement = document.createElement('div');
            loadingMessageElement.classList.add('message', 'bot-message', 'loading-indicator');
            loadingMessageElement.innerHTML = `
                <div class="typing-indicator">
                    <span></span><span></span><span></span>
                </div>`;
            chatWindow.appendChild(loadingMessageElement);
            chatWindow.scrollTop = chatWindow.scrollHeight;

            const formData = new FormData();
            formData.append('message', message); // Key for text message
            if (currentImageFile) {
                formData.append('image', currentImageFile); // Key for image file
                currentImageFile = null; // Clear the image file after attaching it
                imageUploadInput.value = ''; // Clear the file input as well
            }

            try {
                const response = await fetch(CHATBOT_API_URL, {
                    method: 'POST',
                    body: formData
                });

                const data = await response.json();
                
                // Remove loading indicator
                if (chatWindow.contains(loadingMessageElement)) {
                    chatWindow.removeChild(loadingMessageElement);
                }

                if (response.ok && data.response) {
                    if (typeof data.response === 'string' && data.response.trim() !== '') {
                        displayMessage(data.response, 'bot');
                    } else {
                        displayMessage(`Warning: Chatbot returned an empty response. Data received: ${JSON.stringify(data)}`, 'bot');
                    }
                } else {
                    throw new Error(`Server error: ${JSON.stringify(data.error || data)} (Status: ${response.status})`);
                }

            } catch (error) {
                console.error('Error sending message to chatbot:', error);
                // Remove loading indicator on error
                if (chatWindow.contains(loadingMessageElement)) {
                    chatWindow.removeChild(loadingMessageElement);
                }
                displayMessage(`Error: Could not connect to the chatbot or an issue occurred: ${error.message}. Please check if the chatbot backend is running on ${CHATBOT_API_URL}.`, 'bot');
            }
        }

        // Toggle visibility of attachment options
        attachmentButton.addEventListener('click', (event) => {
            event.stopPropagation(); // Prevent document click from immediately closing it
            attachmentOptions.classList.toggle('show');
        });

        // Trigger hidden file input when "Upload Image" button is clicked
        uploadImageButton.addEventListener('click', (event) => {
            event.stopPropagation(); // Prevent document click from immediately closing options
            imageUploadInput.click(); 
            attachmentOptions.classList.remove('show'); // Hide options after triggering input
        });

        // Handle file selection from the hidden image input
        imageUploadInput.addEventListener('change', (event) => {
            const file = event.target.files[0];
            if (file) {
                currentImageFile = file; // Store the selected file
                // Display image preview
                const reader = new FileReader();
                reader.onload = (e) => {
                    displayMessage(e.target.result, 'user', true); // Show image preview
                };
                reader.readAsDataURL(file);
                displayMessage(`Image selected: "${file.name}". This image will be sent with your next message.`, 'user');
            }
        });

        // Close attachment options when clicking outside
        document.addEventListener('click', (event) => {
            const attachmentContainer = document.querySelector('.attachment-container');
            if (attachmentContainer && !attachmentContainer.contains(event.target) && attachmentOptions.classList.contains('show')) {
                attachmentOptions.classList.remove('show');
            }
        });
    }
});

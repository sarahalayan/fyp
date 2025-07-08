// script.js (UPDATED: Image-only functionality, FormData key changed to 'image')

document.addEventListener('DOMContentLoaded', () => {
    const chatWindow = document.getElementById('chat-window');
    const userInput = document.getElementById('user-input');
    const sendButton = document.getElementById('send-button');

    // UI elements
    const attachmentButton = document.getElementById('attachment-button');
    const attachmentOptions = document.getElementById('attachment-options');
    const uploadImageButton = document.getElementById('upload-image-button');
    // REMOVED: uploadVideoButton

    // Hidden file input (only image now)
    const imageUpload = document.getElementById('image-upload');
    // REMOVED: videoUpload

    const CHATBOT_API_URL = 'http://localhost:5000/chat'; 

    function appendMessage(sender, message, isImage = false) {
        console.log(`[appendMessage START] Sender: ${sender}, IsImage: ${isImage}, Message Content Type: ${typeof message}`);
        if (!isImage && (!message || (typeof message === 'string' && message.trim() === ''))) {
            console.warn(`[appendMessage WARN] Attempted to append empty text message from ${sender}. Skipping.`);
            return; 
        }
        if (isImage && (typeof message !== 'string' || !message.startsWith('data:'))) {
            console.warn(`[appendMessage WARN] Attempted to append invalid image data from ${sender}. Skipping.`, message);
            return;
        }

        const messageDiv = document.createElement('div');
        messageDiv.classList.add('message', sender);
        
        if (isImage) {
            const imgElement = document.createElement('img');
            imgElement.src = message;
            imgElement.alt = "User uploaded image";
            imgElement.style.maxWidth = '100%';
            imgElement.style.height = 'auto';
            imgElement.style.borderRadius = '5px';
            messageDiv.appendChild(imgElement);
            console.log(`[appendMessage IMG] Appended image element for ${sender}.`);
        } else {
            messageDiv.textContent = message;
            console.log(`[appendMessage TEXT] Appended text "${message}" for ${sender}.`);
        }
        
        chatWindow.appendChild(messageDiv);
        chatWindow.scrollTop = chatWindow.scrollHeight;
        console.log(`[appendMessage END] Message element added to DOM for ${sender}. Current chatWindow children count: ${chatWindow.children.length}`);
    }

    sendButton.addEventListener('click', async (event) => {
        event.preventDefault(); 
        console.log("[DEBUG] sendButton click: event.preventDefault() called.");
        await handleSendMessage();
    });

    userInput.addEventListener('keypress', async (event) => {
        if (event.key === 'Enter') {
            event.preventDefault(); 
            console.log("[DEBUG] userInput keypress (Enter): event.preventDefault() called.");
            await handleSendMessage();
        }
    });

    // Toggle attachment options visibility
    attachmentButton.addEventListener('click', () => {
        attachmentOptions.classList.toggle('show');
    });

    // Trigger hidden image input
    uploadImageButton.addEventListener('click', () => {
        imageUpload.click(); 
        attachmentOptions.classList.remove('show'); 
    });

    // REMOVED: uploadVideoButton.addEventListener('click', ...)

    // Ensure the attachment options close if user clicks anywhere else
    document.addEventListener('click', (event) => {
        const attachmentContainer = document.querySelector('.attachment-container');
        if (attachmentContainer && !attachmentContainer.contains(event.target) && attachmentOptions.classList.contains('show')) {
            attachmentOptions.classList.remove('show');
        }
    });


    async function handleSendMessage() {
        console.log("[handleSendMessage START]");
        const messageText = userInput.value.trim();
        
        const imageFile = imageUpload.files[0]; 
        // REMOVED: videoFile

        if (!messageText && !imageFile) { 
            console.log("[handleSendMessage] No message or image. Returning.");
            return; 
        }

        if (messageText) {
            appendMessage('user', messageText);
        }
        
        let fileToUpload = null; 
        // REMOVED: fileType

        if (imageFile) {
            fileToUpload = imageFile;
            // REMOVED: fileType = 'image'; // Not needed if backend only expects images
            console.log("[handleSendMessage] Before FileReader readAsDataURL. Image file size (bytes):", imageFile.size);
            try {
                await new Promise((resolve, reject) => {
                    const reader = new FileReader();
                    reader.onload = (e) => { 
                        console.log("[FileReader] Image loaded, attempting to display preview.");
                        appendMessage('user', e.target.result, true); 
                        console.log("[FileReader] Image preview display complete. Data URL length:", e.target.result.length);
                        resolve(); 
                    };
                    reader.onerror = (e) => { 
                        console.error("[FileReader ERROR] Error reading file:", e);
                        appendMessage('bot', "Error loading image preview in browser.");
                        reject(new Error("FileReader error"));
                    };
                    reader.readAsDataURL(imageFile); 
                });
            } catch (error) {
                console.error("Error during image reading promise in handleSendMessage:", error);
            }
            console.log("[handleSendMessage] After FileReader readAsDataURL finished (or failed).");
        } 
        // REMOVED: else if (videoFile) ...

        console.log("[handleSendMessage] Data prepared, calling sendMessage.");

        userInput.value = ''; 
        imageUpload.value = ''; 
        // REMOVED: videoUpload.value = '';

        // Pass the message text and the image file to upload
        sendMessage(messageText, fileToUpload); // REMOVED fileType
    }

    async function sendMessage(messageText, fileToUpload) { // REMOVED fileType
        console.log("[sendMessage START]");
        
        console.log(`[sendMessage] Processing user input: Text="${messageText}", File present: ${!!fileToUpload ? fileToUpload.name : 'No'}`);

        const formData = new FormData();
        formData.append('message', messageText);
        if (fileToUpload) {
            // *** CRUCIAL CHANGE: Use 'image' as the key for the uploaded file ***
            formData.append('image', fileToUpload); 
            // REMOVED: formData.append('file_type', fileType); 
        }
        
        console.log("[sendMessage] FormData prepared. About to append 'Typing...' and send fetch.");
        
        appendMessage('bot', 'Typing...'); 
        console.log("[sendMessage] 'Typing...' message appended.");

        try {
            console.log("[sendMessage] Sending request to backend at:", CHATBOT_API_URL);
            const response = await fetch(CHATBOT_API_URL, {
                method: 'POST',
                body: formData 
            });

            console.log("[sendMessage] Fetch response received. Status:", response.status);

            if (!response.ok) {
                let errorDetails = `HTTP error! status: ${response.status}`;
                try {
                    const errorData = await response.json();
                    errorDetails = errorData.error || JSON.stringify(errorData);
                } catch (jsonError) {
                    errorDetails = `HTTP error! status: ${response.status}, message: ${response.statusText || 'Unknown Error'}`;
                }
                throw new Error(errorDetails);
            }

            const data = await response.json();
            console.log("[sendMessage] Raw backend response data (IMPORTANT):", data); 
            
            const typingIndicator = chatWindow.querySelector('.message.bot:last-child');
            if (typingIndicator && typingIndicator.textContent.includes('Typing')) { 
                typingIndicator.remove();
                console.log("[sendMessage] Typing indicator removed successfully.");
            } else {
                console.warn("[sendMessage] Typing indicator not found or text mismatch (expected 'Typing...').");
            }

            if (data.response) { 
                if (typeof data.response === 'string' && data.response.trim() !== '') {
                    appendMessage('bot', data.response);
                    console.log("[sendMessage] Final chatbot response appended.");
                } else {
                    console.warn("[sendMessage WARN] Backend 'response' key is empty or not a valid string:", data.response);
                    appendMessage('bot', `Warning: Chatbot returned an empty response. Data received: ${JSON.stringify(data)}`);
                }
            } else {
                console.error("[sendMessage ERROR] 'response' key not found in backend data:", data);
                appendMessage('bot', `Error: Chatbot did not return a 'response' key.`);
            }

        } catch (error) {
            console.error('[sendMessage CATCH] Error during fetch or processing:', error); 
            const typingIndicator = chatWindow.querySelector('.message.bot:last-child');
            if (typingIndicator && typingIndicator.textContent.includes('Typing')) { 
                typingIndicator.remove();
            }
            appendMessage('bot', `Error: ${error.message}. Please check browser console for details.`);
        }
        console.log("[sendMessage END]");
    }
});
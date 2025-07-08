document.addEventListener('DOMContentLoaded', () => {
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

    let uploadedVideoURL = null;
    let progressIntervalId = null;
    let detectionsIntervalId = null;

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

    uploadForm.addEventListener('submit', async function(event) {
        event.preventDefault();

        const form = event.target;
        const formData = new FormData(form);

        const selectedInterval = detectionIntervalSelect.value;
        formData.append('detectionInterval', selectedInterval);

        formData.append('enableTreeDetection', enableTreeDetectionCheckbox.checked);

        responseMessage.textContent = 'Uploading... Please wait.';
        responseMessage.className = 'uploading';
        videoPlayerContainer.style.display = 'none';
        progressBar.style.width = '0%';
        progressBar.textContent = '0%';
        currentVideoStatus.textContent = 'No video loaded.';
        processedFramesStatus.textContent = 'Processed: 0 frames';
        totalFramesStatus.textContent = 'Total: 0 frames';
        predictionTableBody.innerHTML = '<tr><td colspan="5">No predictions yet.</td></tr>';

        clearMonitoringIntervals();

        try {
            const response = await fetch('http://localhost:5002/upload_video', {
                method: 'POST',
                body: formData
            });

            const data = await response.json();

            if (response.ok) {
                responseMessage.textContent = 'Success!\n' + JSON.stringify(data, null, 2);
                responseMessage.className = 'success';
                
                if (uploadedVideoURL) {
                    URL.revokeObjectURL(uploadedVideoURL);
                }
                
                const videoFileObj = videoFile.files.item(0);
                if (videoFileObj) {
                    uploadedVideoURL = URL.createObjectURL(videoFileObj);
                    videoPlayer.src = uploadedVideoURL;
                    videoPlayerContainer.style.display = 'block';
                    videoPlayer.load();
                    videoPlayer.play();
                    currentVideoStatus.textContent = `Video: ${videoFileObj.name}`;
                }

                progressIntervalId = setInterval(fetchProgress, 1000);
                detectionsIntervalId = setInterval(fetchPredictions, 3000);

            } else {
                responseMessage.textContent = 'Error!\n' + JSON.stringify(data, null, 2) + '\nStatus: ' + response.status;
                responseMessage.className = 'error';
                clearMonitoringIntervals();
            }
        } catch (error) {
            responseMessage.textContent = 'Network error or server unreachable: ' + error.message;
            responseMessage.className = 'error';
            clearMonitoringIntervals();
        }
    });

    async function fetchPredictions() {
        let url = 'http://localhost:5002/api/monitoring/detections';
        
        try {
            const response = await fetch(url);
            if (response.ok) {
                const predictions = await response.json();
                displayPredictions(predictions);
            } else {
                console.error('Failed to fetch predictions:', response.status);
                predictionTableBody.innerHTML = '<tr><td colspan="5">Failed to load predictions.</td></tr>';
            }
        } catch (error) {
            console.error('Error fetching predictions:', error);
            predictionTableBody.innerHTML = '<tr><td colspan="5">Network error fetching predictions.</td></tr>';
        }
    }

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
                console.error('Failed to fetch progress:', response.status);
                updateProgress(0, 0, false); 
            }
        } catch (error) {
            console.error('Error fetching progress:', error);
            updateProgress(0, 0, false);
        }
    }

    function displayPredictions(predictions) {
        predictionTableBody.innerHTML = ''; 

        if (predictions && predictions.length > 0) {
            predictions.forEach(prediction => {
                const row = document.createElement('tr'); 

                const timeCell = document.createElement('td');
                timeCell.textContent = new Date(prediction.timestamp).toLocaleTimeString();
                row.appendChild(timeCell);

                const fruitCell = document.createElement('td');
                let fruitText = prediction.fruit_type && prediction.fruit_type !== 'unknown' ? prediction.fruit_type : 'N/A';
                if (prediction.confidence_fruit !== null && prediction.confidence_fruit !== undefined) {
                    fruitText += ` (${(prediction.confidence_fruit * 100).toFixed(2)}%)`;
                }
                fruitCell.textContent = fruitText;
                row.appendChild(fruitCell);

                const ripenessCell = document.createElement('td');
                let ripenessText = prediction.ripeness && prediction.ripeness !== 'unknown' ? prediction.ripeness : 'N/A';
                if (prediction.confidence_ripeness !== null && prediction.confidence_ripeness !== undefined) {
                    ripenessText += ` (${(prediction.confidence_ripeness * 100).toFixed(2)}%)`;
                }
                ripenessCell.textContent = ripenessText;
                row.appendChild(ripenessCell);

                const diseaseCell = document.createElement('td');
                let diseaseText = prediction.disease && prediction.disease !== 'unknown' ? prediction.disease : 'N/A';
                if (prediction.confidence_disease !== null && prediction.confidence_disease !== undefined) {
                    diseaseText += ` (${(prediction.confidence_disease * 100).toFixed(2)}%)`;
                }
                diseaseCell.textContent = diseaseText;
                row.appendChild(diseaseCell);

                const notesCell = document.createElement('td');
                notesCell.textContent = prediction.notes && prediction.notes !== 'unknown' ? prediction.notes : '';
                row.appendChild(notesCell);

                predictionTableBody.appendChild(row);
            });
        } else {
            const noPredictionsRow = document.createElement('tr');
            const noPredictionsCell = document.createElement('td');
            noPredictionsCell.colSpan = 5;
            noPredictionsCell.textContent = 'No predictions yet.';
            noPredictionsRow.appendChild(noPredictionsCell);
            predictionTableBody.appendChild(noPredictionsRow);
        }
    }

    function updateProgress(processedFrames, totalFrames, isMonitoringActive) {
        if (totalFrames > 0) {
            const progress = (processedFrames / totalFrames) * 100;
            progressBar.style.width = `${progress}%`;
            progressBar.textContent = `${progress.toFixed(1)}%`;
            processedFramesStatus.textContent = `Processed: ${processedFrames} frames`;
            totalFramesStatus.textContent = `Total: ${totalFrames} frames`;
            if (isMonitoringActive) {
                currentVideoStatus.textContent = `Monitoring Active: ${totalFrames > 0 ? (videoPlayer.src ? videoPlayer.src.split('/').pop() : 'video') : 'N/A'}`;
            } else if (processedFrames === totalFrames && totalFrames > 0) {
                currentVideoStatus.textContent = `Monitoring Finished.`;
                clearMonitoringIntervals();
            } else {
                currentVideoStatus.textContent = `Monitoring Inactive.`;
                if(progressIntervalId || detectionsIntervalId) {
                    clearMonitoringIntervals();
                }
            }
        } else {
            progressBar.style.width = '0%';
            progressBar.textContent = '0%';
            processedFramesStatus.textContent = 'Processed: 0 frames';
            totalFramesStatus.textContent = 'Total: 0 frames';
            currentVideoStatus.textContent = 'No video loaded/Monitoring Inactive.';
        }
    }

    fetchProgress();
    fetchPredictions();
});

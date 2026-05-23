// DOM Elements
const wsDot = document.getElementById('wsDot');
const wsStatus = document.getElementById('wsStatus');
const micDot = document.getElementById('micDot');
const micStatus = document.getElementById('micStatus');
const recordBtn = document.getElementById('recordBtn');
const languageSelect = document.getElementById('languageSelect');
const partialTranscript = document.getElementById('partialTranscript');
const finalTranscript = document.getElementById('finalTranscript');

// State
let ws = null;
let mediaRecorder = null;
let audioStream = null;
let isRecording = false;
let isMicPaused = false;
let chunkCount = 0;
let currentAppointmentId = null;

// Generate a random session ID
const sessionId = 'session_' + Math.random().toString(36).substring(2, 9);
console.log('[VoiceAI] Session ID:', sessionId);

// Reconnect when language changes
languageSelect.addEventListener('change', () => {
    if (ws) {
        console.log('[VoiceAI] Language changed to', languageSelect.value, '- Reconnecting...');
        disconnectWebSocket();
        setTimeout(connectWebSocket, 500); // Wait briefly before reconnecting
    }
});

// ==========================================
// WebSocket Management
// ==========================================

// Auto-connect on page load
document.addEventListener('DOMContentLoaded', () => {
    connectWebSocket();
});

function connectWebSocket() {
    wsStatus.textContent = "Connecting...";
    const WS_URL = `ws://localhost:8000/api/v1/ws/audio?session_id=${sessionId}&language=${languageSelect.value}`;
    console.log('[VoiceAI] Connecting to:', WS_URL);
    ws = new WebSocket(WS_URL);
    ws.binaryType = 'arraybuffer';

    ws.onopen = () => {
        console.log('[VoiceAI] WebSocket connected');
        wsStatus.textContent = `Connected (${sessionId})`;
        wsDot.classList.add('connected');
        // Connection established UI updates
        recordBtn.disabled = false;
    };

    ws.onmessage = (event) => {
        console.log('[VoiceAI] Message from server:', event.data);
        try {
            const data = JSON.parse(event.data);
            handleServerMessage(data);
        } catch (e) {
            console.error('[VoiceAI] Error parsing message:', e);
        }
    };

    ws.onclose = (e) => {
        console.log('[VoiceAI] WebSocket closed:', e.code, e.reason);
        wsStatus.textContent = "Disconnected";
        wsDot.classList.remove('connected');
        // Attempt to auto-reconnect if the connection drops unexpectedly
        setTimeout(connectWebSocket, 3000);
        recordBtn.disabled = true;
        if (isRecording) stopRecording();
    };

    ws.onerror = (error) => {
        console.error('[VoiceAI] WebSocket Error:', error);
        wsStatus.textContent = "Connection Error";
    };
}

function disconnectWebSocket() {
    if (ws) ws.close();
}

function handleServerMessage(data) {
    if (data.event_type === "partial_transcript") {
        partialTranscript.textContent = data.message;
    } else if (data.event_type === "final_transcript") {
        partialTranscript.textContent = "Waiting for speech...";
        const p = document.createElement('p');
        p.textContent = data.message;
        finalTranscript.appendChild(p);
        finalTranscript.scrollTop = finalTranscript.scrollHeight;
    } else if (data.event_type === "ai_response") {
        const aiResponseBox = document.getElementById('aiResponse');
        if (aiResponseBox) {
            aiResponseBox.textContent = data.message;
        }
        
        // Auto-pause the mic so STT doesn't pick up the user reading the AI response out loud
        if (isRecording && mediaRecorder && mediaRecorder.state === 'recording') {
            mediaRecorder.pause();
            isMicPaused = true;
            recordBtn.textContent = "Click to Speak Again";
            recordBtn.classList.remove('active');
            recordBtn.classList.add('paused');
            recordBtn.style.backgroundColor = "var(--warning-color)";
            micStatus.textContent = "Mic Paused (AI Responded)";
            micDot.classList.remove('recording');
            micDot.style.backgroundColor = "var(--warning-color)";
            console.log('[VoiceAI] Auto-paused microphone during AI response');
        }
    } else if (data.event_type === "appointment_state") {
        console.log('[VoiceAI] Appointment State Updated:', data.data);
        renderAppointmentBox(data.data);
    } else {
        console.log('[VoiceAI] Server message:', data);
    }
}

function renderAppointmentBox(appt) {
    const box = document.getElementById('appointmentBox');
    const details = document.getElementById('appointmentDetails');
    const badge = document.getElementById('appointmentBadge');
    
    currentAppointmentId = appt.id;
    box.style.display = 'block';
    
    // Update Badge
    badge.textContent = appt.status.toUpperCase();
    if (appt.status === 'canceled') {
        badge.style.backgroundColor = 'var(--danger-color)';
        box.style.borderColor = 'rgba(239, 68, 68, 0.3)';
        box.style.background = 'rgba(239, 68, 68, 0.05)';
    } else if (appt.status === 'rescheduled') {
        badge.style.backgroundColor = 'var(--warning-color)';
        box.style.borderColor = 'rgba(245, 158, 11, 0.3)';
        box.style.background = 'rgba(245, 158, 11, 0.05)';
    } else {
        badge.style.backgroundColor = 'var(--success-color)';
        box.style.borderColor = 'rgba(16, 185, 129, 0.3)';
        box.style.background = 'rgba(16, 185, 129, 0.05)';
    }
    
    // Update Details
    details.innerHTML = `
        <strong>Patient:</strong> ${appt.patient_name} <br>
        <strong>Date:</strong> ${appt.date} <br>
        <strong>Time:</strong> ${appt.time} <br>
        <strong>ID:</strong> <span style="color: var(--text-secondary); font-family: monospace;">${appt.id}</span>
    `;
}

// Button listeners for the voice agent
document.getElementById('rescheduleBtn')?.addEventListener('click', () => {
    alert('Voice Agent active: Please tell the AI "I want to reschedule my appointment." into the microphone!');
});

document.getElementById('cancelBtn')?.addEventListener('click', () => {
    alert('Voice Agent active: Please tell the AI "I want to cancel my appointment." into the microphone!');
});

// ==========================================
// Microphone & Recording Management
// ==========================================
recordBtn.addEventListener('click', toggleRecording);

async function toggleRecording() {
    if (!isRecording) {
        await startRecording();
    } else {
        if (isMicPaused) {
            // Resume recording
            mediaRecorder.resume();
            isMicPaused = false;
            
            // Update UI back to active recording
            recordBtn.textContent = "Stop Session";
            recordBtn.classList.remove('paused');
            recordBtn.classList.add('active');
            recordBtn.style.backgroundColor = ""; // reset to default css
            micStatus.textContent = "Recording...";
            micDot.classList.add('recording');
            micDot.style.backgroundColor = "var(--danger-color)";
            
            console.log('[VoiceAI] Resumed microphone');
        } else {
            // End the whole session
            stopRecording();
        }
    }
}

async function startRecording() {
    try {
        chunkCount = 0;
        audioStream = await navigator.mediaDevices.getUserMedia({
            audio: {
                channelCount: 1,
                echoCancellation: true,
                noiseSuppression: true
            }
        });

        // Pick a MIME type the browser supports
        const mimeType = getSupportedMimeType();
        console.log('[VoiceAI] Using MIME type:', mimeType);

        mediaRecorder = new MediaRecorder(audioStream, mimeType ? { mimeType } : {});

        mediaRecorder.ondataavailable = async (event) => {
            if (event.data && event.data.size > 0) {
                chunkCount++;
                console.log(`[VoiceAI] Sending chunk #${chunkCount}, size=${event.data.size} bytes`);
                if (ws && ws.readyState === WebSocket.OPEN) {
                    // Convert Blob to ArrayBuffer and send as binary
                    const arrayBuffer = await event.data.arrayBuffer();
                    ws.send(arrayBuffer);
                } else {
                    console.warn('[VoiceAI] WebSocket not open, dropping chunk');
                }
            }
        };

        // Start recording, emit a chunk every 250ms
        mediaRecorder.start(250);
        isRecording = true;

        // Update UI
        recordBtn.textContent = "Stop Session";
        recordBtn.classList.add('active');
        recordBtn.classList.remove('paused');
        recordBtn.style.backgroundColor = "";
        micStatus.textContent = "Recording...";
        micDot.classList.add('recording');
        micDot.style.backgroundColor = "var(--danger-color)";

        console.log('[VoiceAI] Recording started');

    } catch (error) {
        console.error('[VoiceAI] Error accessing microphone:', error);
        alert("Could not access microphone. Please ensure permissions are granted.");
    }
}

function stopRecording() {
    if (mediaRecorder && mediaRecorder.state !== 'inactive') {
        mediaRecorder.stop();
    }
    if (audioStream) {
        audioStream.getTracks().forEach(track => track.stop());
    }

    isRecording = false;
    isMicPaused = false;
    console.log(`[VoiceAI] Recording stopped. Total chunks sent: ${chunkCount}`);

    // Update UI
    recordBtn.textContent = "Start Recording";
    recordBtn.classList.remove('active', 'paused');
    recordBtn.style.backgroundColor = "";
    micStatus.textContent = "Mic Inactive";
    micDot.classList.remove('recording');
    micDot.style.backgroundColor = "var(--text-secondary)";
}

function getSupportedMimeType() {
    const types = [
        'audio/webm;codecs=opus',
        'audio/webm',
        'audio/ogg;codecs=opus',
        'audio/mp4',
        ''
    ];
    for (const type of types) {
        if (!type || MediaRecorder.isTypeSupported(type)) {
            return type;
        }
    }
    return '';
}

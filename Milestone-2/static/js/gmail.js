/**
 * Gmail Integration for Voice Assistant
 * Milestone 2: Voice-controlled Gmail operations
 */

// Gmail state
const gmailState = {
    connected: false,
    currentEmails: [],
    currentIndex: 0,
    selectedEmail: null,
    autoFetchDone: false,  // Prevent repeated auto-fetches
    lastSelectedByNumber: null,  // Track when user manually selected an email by number
    isReadingEmail: false,  // Flag to prevent interrupting email reading
    countAnnouncedOnce: false  // Prevent announcing email count multiple times
};

/**
 * Check Gmail connection status
 */
async function checkGmailStatus() {
    try {
        const response = await fetch('/api/gmail/status');
        
        // Handle 401 (not authenticated) gracefully
        if (response.status === 401) {
            console.log('User not authenticated yet');
            gmailState.connected = false;
            updateGmailUI();
            return false;
        }
        
        const data = await response.json();
        
        gmailState.connected = data.gmail_connected || false;
        console.log('[Gmail Status] Connected:', gmailState.connected, 'Emails loaded:', gmailState.currentEmails.length);
        
        // Always update UI first
        updateGmailUI();

        // Auto-fetch emails once when connected and none loaded yet
        // Only do this once per session to avoid overwriting user-selected views
        if (gmailState.connected && gmailState.currentEmails.length === 0 && !gmailState.autoFetchDone) {
            console.log('[Gmail Status] Auto-fetching emails...');
            gmailState.autoFetchDone = true;  // Mark as done to prevent repeated fetches
            const emails = await fetchGmailMessages('', 25, true);  // announceCount = true
            console.log('[Gmail Status] Auto-fetch retrieved', emails.length, 'emails');
        }
        
        return gmailState.connected;
    } catch (error) {
        console.error('Failed to check Gmail status:', error);
        gmailState.connected = false;
        updateGmailUI();
        return false;
    }
}

/**
 * Connect to Gmail
 */
async function connectGmail() {
    try {
        showResponse('Redirecting to Gmail authorization...');
        
        const response = await fetch('/api/gmail/auth', {
            credentials: 'same-origin'
        });
        const data = await response.json();
        
        if (data.authorization_url) {
            // Store that we're initiating Gmail auth
            sessionStorage.setItem('gmail_auth_pending', 'true');
            
            // Redirect to Google OAuth page
            window.location.href = data.authorization_url;
        } else {
            throw new Error('Failed to get authorization URL');
        }
    } catch (error) {
        console.error('Gmail connection error:', error);
        showError('Failed to connect Gmail: ' + error.message);
        if (typeof speak === 'function') {
            speak('Failed to connect to Gmail');
        }
    }
}

/**
 * Fetch Gmail messages
 */
async function fetchGmailMessages(query = '', maxResults = 25, announceCount = false) {
    try {
        updateStatus('Fetching emails... This may take a moment.');
        
        const url = `/api/gmail/messages?max_results=${maxResults}&query=${encodeURIComponent(query)}`;
        console.log('[Fetch Messages] Requesting:', url);
        
        const response = await fetch(url);
        const data = await response.json();
        
        console.log('[Fetch Messages] Response:', data);
        
        if (data.success) {
            gmailState.currentEmails = data.messages || [];
            
            // Only reset currentIndex if:
            // 1. We're doing a search query, OR
            // 2. The current index is out of bounds, OR
            // 3. No email was previously selected
            if (query !== '' || gmailState.currentIndex >= gmailState.currentEmails.length || gmailState.selectedEmail === null) {
                gmailState.currentIndex = 0;
                gmailState.lastSelectedByNumber = null;  // Clear the manual selection flag
            }
            // Otherwise preserve currentIndex and selectedEmail if valid
            
            console.log('[Fetch Messages] Loaded', gmailState.currentEmails.length, 'emails, currentIndex:', gmailState.currentIndex);
            
            // Always display even if auto-fetching
            displayEmails(gmailState.currentEmails);
            
            const count = gmailState.currentEmails.length;
            const message = `You have ${count} email${count !== 1 ? 's' : ''}`;
            // Only announce email count once on initial fetch AND if explicitly requested
            // (to avoid interrupting email reading)
            if (count > 0 && !gmailState.isReadingEmail && announceCount && !gmailState.countAnnouncedOnce) {
                gmailState.countAnnouncedOnce = true;
                speak(message);
            }
            showResponse(message);
            updateStatus('Ready');
            
            return gmailState.currentEmails;
        } else {
            throw new Error(data.error || 'Failed to fetch messages');
        }
    } catch (error) {
        console.error('Fetch messages error:', error);
        showError('Failed to fetch emails: ' + error.message);
        return [];
    }
}

/**
 * Display emails in UI
 */
function displayEmails(emails) {
    const container = document.getElementById('emailList');
    if (!container) return;
    
    // Always show the container when displaying emails
    container.classList.remove('hidden');
    
    if (!emails || emails.length === 0) {
        container.innerHTML = '<div class="email-empty">No emails found</div>';
        return;
    }
    
    const emailsHTML = emails.map((email, index) => `
        <div class="email-item ${index === gmailState.currentIndex ? 'active' : ''}" 
             onclick="selectEmail(${index})"
             data-email-index="${index}"
             data-email-number="${index + 1}">
            <div class="email-number-badge">${index + 1}</div>
            <div class="email-content">
                <div class="email-header">
                    <span class="email-from">${escapeHtml(email.from)}</span>
                    <span class="email-date">${formatEmailDate(email.date)}</span>
                </div>
                <div class="email-subject">${escapeHtml(email.subject)}</div>
                <div class="email-snippet">${escapeHtml(email.snippet)}</div>
                ${email.is_unread ? '<span class="unread-badge">●</span>' : ''}
            </div>
        </div>
    `).join('');
    
    const loadMoreButton = emails.length >= 25 ? `
        <div class="load-more-container">
            <button class="btn-secondary" onclick="loadMoreEmails()">Load More Emails</button>
        </div>
    ` : '';
    
    container.innerHTML = emailsHTML + loadMoreButton;
}

/**
 * Load more emails
 */
async function loadMoreEmails() {
    const currentCount = gmailState.currentEmails.length;
    const newEmails = await fetchGmailMessages('', currentCount + 25);
    // fetchGmailMessages already updates the display
}

/**
 * Select email by index
 */
function selectEmail(index) {
    if (index < 0 || index >= gmailState.currentEmails.length) {
        return;
    }
    
    gmailState.currentIndex = index;
    gmailState.selectedEmail = gmailState.currentEmails[index];
    
    // Update UI
    displayEmails(gmailState.currentEmails);
    displayEmailDetail(gmailState.selectedEmail);
}

/**
 * Display email detail
 */
function displayEmailDetail(email) {
    const container = document.getElementById('emailDetail');
    if (!container) return;
    
    container.innerHTML = `
        <div class="email-detail-header">
            <h3>${escapeHtml(email.subject)}</h3>
            <div class="email-detail-meta">
                <div><strong>From:</strong> ${escapeHtml(email.from)}</div>
                <div><strong>To:</strong> ${escapeHtml(email.to)}</div>
                <div><strong>Date:</strong> ${formatEmailDate(email.date)}</div>
            </div>
        </div>
        <div class="email-detail-body">
            ${formatEmailBody(email.body || email.snippet)}
        </div>
        <div class="email-detail-actions">
            <button class="btn btn-primary" onclick="readEmailAloud('${escapeHtml(email.id)}')">
                🔊 Read Aloud
            </button>
            <button class="btn btn-primary" onclick="showReplyForm('${escapeHtml(email.id)}')">
                ↩️ Reply
            </button>
            <button class="btn btn-danger" onclick="deleteEmail('${escapeHtml(email.id)}')">
                🗑️ Delete
            </button>
        </div>
    `;
    
    container.classList.remove('hidden');
}

/**
 * Read email aloud
 */
async function readEmailAloud(messageId) {
    try {
        // Set flag to prevent fetchGmailMessages from interrupting
        gmailState.isReadingEmail = true;
        
        console.log('Starting readEmailAloud for message:', messageId);
        
        // Cancel any ongoing speech first
        if (window.speechSynthesis.speaking) {
            window.speechSynthesis.cancel();
            // Wait a bit for cancellation to complete
            await new Promise(resolve => setTimeout(resolve, 100));
        }
        
        showResponse('Reading email...');
        
        const response = await fetch(`/api/gmail/message/${messageId}`, {
            method: 'GET'
        });
        
        console.log('Response status:', response.status);
        const data = await response.json();
        console.log('Email data:', data);
        
        if (!response.ok) {
            throw new Error(data.error || `Server error: ${response.status}`);
        }
        
        if (data.message) {
            // Use browser's speech synthesis to read the email
            const email = data.message;
            
            // Build speech text
            let speechText = '';
            if (email.subject) {
                speechText += `Email subject: ${email.subject}. `;
            }
            if (email.from) {
                const fromName = email.from.replace(/<[^>]+>/g, '').trim();
                speechText += `From: ${fromName}. `;
            }
            if (email.body) {
                // Clean HTML from body
                const tempDiv = document.createElement('div');
                tempDiv.innerHTML = email.body;
                const cleanBody = tempDiv.textContent || tempDiv.innerText || '';
                // Limit length
                const bodyText = cleanBody.length > 800 ? cleanBody.substring(0, 800) + '... Message continues.' : cleanBody;
                speechText += `Message: ${bodyText}`;
            }
            
            console.log('Speaking:', speechText.substring(0, 100));
            
            // Use the existing speak function from the main app
            if (typeof speak === 'function') {
                speak(speechText);
            } else {
                // Fallback to direct speech synthesis
                const utterance = new SpeechSynthesisUtterance(speechText);
                utterance.onend = () => {
                    gmailState.isReadingEmail = false;
                    console.log('[readEmailAloud] Email reading complete, cleared isReadingEmail flag');
                };
                window.speechSynthesis.speak(utterance);
            }
            
            // Clear the flag after email reading completes (estimate based on text length)
            const estimatedDuration = Math.min((speechText.length / 150) * 1000 + 1000, 60000); // ~150 chars/min, max 60s
            setTimeout(() => {
                gmailState.isReadingEmail = false;
                console.log('[readEmailAloud] Timeout cleared isReadingEmail flag');
            }, estimatedDuration);
            
            showResponse('📧 Email is being read aloud. Say "stop" to stop reading.');
        } else {
            throw new Error('Email data not found');
        }
    } catch (error) {
        console.error('Read email error:', error);
        showError('Failed to read email: ' + error.message);
    }
}

/**
 * Fetch sent emails
 */
async function fetchSentEmails() {
    try {
        speak('Fetching sent emails');
        showResponse('Loading sent emails...');
        
        const response = await fetch('/api/gmail/messages?query=' + encodeURIComponent('in:sent') + '&max_results=25');
        const data = await response.json();
        
        if (data.success) {
            gmailState.currentEmails = data.messages;
            gmailState.currentIndex = -1;
            
            displayEmails(data.messages);
            
            const count = data.messages.length;
            const message = count > 0 
                ? `You have ${count} sent email${count !== 1 ? 's' : ''}` 
                : 'No sent emails found';
            speak(message);
            showResponse(message);
            
            // Auto-select first email
            if (data.messages.length > 0) {
                selectEmail(0);
            }
        } else {
            showError('Failed to fetch sent emails: ' + (data.error || 'Unknown error'));
        }
    } catch (error) {
        console.error('Error fetching sent emails:', error);
        showError('Failed to fetch sent emails');
        speak('Failed to fetch sent emails');
    }
}

/**
 * Fetch deleted emails
 */
async function fetchDeletedEmails() {
    try {
        speak('Fetching deleted emails');
        showResponse('Loading deleted emails...');
        
        const url = '/api/gmail/messages?query=' + encodeURIComponent('in:trash') + '&max_results=25';
        console.log('[Fetch Deleted] URL:', url);
        
        const response = await fetch(url);
        const data = await response.json();
        
        console.log('[Fetch Deleted] Response messages count:', data.messages ? data.messages.length : 0);
        console.log('[Fetch Deleted] First message from:', data.messages && data.messages[0] ? data.messages[0].from : 'N/A');
        
        if (data.success) {
            gmailState.currentEmails = data.messages;
            gmailState.currentIndex = -1;
            
            displayEmails(data.messages);
            
            const count = data.messages.length;
            const message = count > 0 
                ? `You have ${count} deleted email${count !== 1 ? 's' : ''}` 
                : 'No deleted emails found';
            speak(message);
            showResponse(message);
            
            // Auto-select first email
            if (data.messages.length > 0) {
                selectEmail(0);
            }
        } else {
            showError('Failed to fetch deleted emails: ' + (data.error || 'Unknown error'));
        }
    } catch (error) {
        console.error('Error fetching deleted emails:', error);
        showError('Failed to fetch deleted emails');
        speak('Failed to fetch deleted emails');
    }
}

/**
 * Show compose email form
 */
function showComposeForm() {
    const container = document.getElementById('composeSection');
    if (!container) return;
    
    container.innerHTML = `
        <div class="compose-form">
            <h3>Compose Email</h3>
            <div class="input-group">
                <label for="composeTo">To:</label>
                <input type="email" id="composeTo" placeholder="recipient@example.com">
            </div>
            <div class="input-group">
                <label for="composeSubject">Subject:</label>
                <input type="text" id="composeSubject" placeholder="Email subject">
            </div>
            <div class="input-group">
                <label for="composeBody">Message:</label>
                <textarea id="composeBody" rows="10" placeholder="Type your message..."></textarea>
            </div>
            <div class="button-group">
                <button class="btn btn-primary" onclick="sendEmail()">📤 Send</button>
                <button class="btn btn-secondary" onclick="cancelCompose()">Cancel</button>
            </div>
        </div>
    `;
    
    container.classList.remove('hidden');
    
    // Set state for voice input
    if (typeof setState === 'function') {
        setState('WAITING_COMPOSE_TO');
    }
    
    // Prompt for recipient - combined announcement
    if (typeof speak === 'function') {
        speak('Opening compose form. Please say the recipient email address');
    }
    
    document.getElementById('composeTo').focus();
}

/**
 * Show reply form
 */
function showReplyForm(messageId) {
    const email = gmailState.currentEmails.find(e => e.id === messageId);
    if (!email) return;
    
    const container = document.getElementById('composeSection');
    if (!container) return;
    
    container.innerHTML = `
        <div class="compose-form">
            <h3>Reply to: ${escapeHtml(email.subject)}</h3>
            <div class="email-reply-context">
                <strong>To:</strong> ${escapeHtml(email.from)}
            </div>
            <div class="input-group">
                <label for="replyBody">Your Reply:</label>
                <textarea id="replyBody" rows="10" placeholder="Type your reply..."></textarea>
            </div>
            <div class="button-group">
                <button class="btn btn-primary" onclick="sendReplyUI('${messageId}')">↩️ Send Reply</button>
                <button class="btn btn-secondary" onclick="cancelCompose()">Cancel</button>
            </div>
        </div>
    `;
    
    container.classList.remove('hidden');
    document.getElementById('replyBody').focus();
}

/**
 * Send email
 */
async function sendEmail() {
    try {
        const to = document.getElementById('composeTo')?.value;
        const subject = document.getElementById('composeSubject')?.value;
        const body = document.getElementById('composeBody')?.value;
        
        if (!to || !subject || !body) {
            showError('Please fill in all fields');
            return;
        }
        
        updateStatus('Sending email...');
        
        const response = await fetch('/api/gmail/send', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ to, subject, body })
        });
        
        const data = await response.json();
        
        if (data.success) {
            speak('Email sent successfully');
            showResponse('✓ Email sent successfully!');
            cancelCompose();
            updateStatus('Ready');
            
            // Return to LOGGED_IN state
            if (typeof setState === 'function') {
                setState('LOGGED_IN');
            }
            
            // Restart recognition
            if (typeof recognition !== 'undefined' && recognition) {
                setTimeout(() => {
                    try { recognition.start(); } catch(e) {}
                }, 1000);
            }
        } else {
            throw new Error(data.error || 'Failed to send email');
        }
    } catch (error) {
        console.error('Send email error:', error);
        showError('Failed to send email: ' + error.message);
        speak('Failed to send email');
        
        // Return to LOGGED_IN state on error
        if (typeof setState === 'function') {
            setState('LOGGED_IN');
        }
    }
}

/**
 * Send reply
 */
async function sendReplyUI(messageId) {
    try {
        const body = document.getElementById('replyBody')?.value;
        
        if (!body) {
            showError('Please enter a reply message');
            return;
        }
        
        updateStatus('Sending reply...');
        
        const response = await fetch(`/api/gmail/reply/${messageId}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ body })
        });
        
        const data = await response.json();
        
        if (data.success) {
            speak('Reply sent successfully');
            showResponse('✓ Reply sent successfully!');
            cancelCompose();
            updateStatus('Ready');
        } else {
            throw new Error(data.error || 'Failed to send reply');
        }
    } catch (error) {
        console.error('Send reply error:', error);
        showError('Failed to send reply: ' + error.message);
        speak('Failed to send reply');
    }
}

/**
 * Delete email
 */
async function deleteEmail(messageId) {
    try {
        if (!confirm('Are you sure you want to delete this email?')) {
            return;
        }
        
        updateStatus('Deleting email...');
        
        const response = await fetch(`/api/gmail/delete/${messageId}`, {
            method: 'DELETE'
        });
        
        const data = await response.json();
        
        if (data.success) {
            speak('Email deleted');
            showResponse('✓ Email deleted');
            
            // Remove from list
            gmailState.currentEmails = gmailState.currentEmails.filter(e => e.id !== messageId);
            displayEmails(gmailState.currentEmails);
            
            updateStatus('Ready');
        } else {
            throw new Error(data.error || 'Failed to delete email');
        }
    } catch (error) {
        console.error('Delete email error:', error);
        showError('Failed to delete email: ' + error.message);
    }
}

/**
 * Cancel compose/reply
 */
function cancelCompose() {
    const container = document.getElementById('composeSection');
    if (container) {
        container.classList.add('hidden');
        container.innerHTML = '';
    }
    
    // Return to LOGGED_IN state
    if (typeof setState === 'function') {
        setState('LOGGED_IN');
    }
    
    // Restart recognition
    if (typeof recognition !== 'undefined' && recognition) {
        try { recognition.start(); } catch(e) {}
    }
}

/**
 * Search emails
 */
async function searchEmails(query) {
    if (!query) {
        showError('Please enter a search query');
        return;
    }
    
    speak(`Searching for ${query}`);
    await fetchGmailMessages(query);
}

/**
 * Update Gmail UI elements
 */
function updateGmailUI() {
    const connectBtn = document.getElementById('gmailConnectBtn');
    const gmailControls = document.getElementById('gmailControls');
    const emailList = document.getElementById('emailList');
    
    console.log('[Update Gmail UI] Connected:', gmailState.connected, 'Emails:', gmailState.currentEmails.length);
    
    if (gmailState.connected) {
        // Hide connect button, show email controls
        if (connectBtn) connectBtn.classList.add('hidden');
        if (gmailControls) gmailControls.classList.remove('hidden');
        // Keep email list visible if emails are loaded, hidden otherwise (will be shown by displayEmails)
        if (gmailState.currentEmails && gmailState.currentEmails.length > 0 && emailList) {
            emailList.classList.remove('hidden');
        }
    } else {
        // Show connect button, hide email controls
        if (connectBtn) connectBtn.classList.remove('hidden');
        if (gmailControls) gmailControls.classList.add('hidden');
        if (emailList) emailList.classList.add('hidden');
    }
}

/**
 * Convert ordinal words to numbers (first, second, third, etc.)
 */
function convertOrdinalWordToNumber(word) {
    const ordinalMap = {
        'first': 1, 'second': 2, 'third': 3, 'fourth': 4, 'fifth': 5,
        'sixth': 6, 'seventh': 7, 'eighth': 8, 'ninth': 9, 'tenth': 10,
        'eleventh': 11, 'twelfth': 12, 'thirteenth': 13, 'fourteenth': 14, 'fifteenth': 15,
        'sixteenth': 16, 'seventeenth': 17, 'eighteenth': 18, 'nineteenth': 19, 'twentieth': 20,
        'twenty first': 21, 'twenty second': 22, 'twenty third': 23, 'twenty fourth': 24, 'twenty fifth': 25,
        'thirtieth': 30, 'fortieth': 40, 'fiftieth': 50
    };
    return ordinalMap[word.toLowerCase()] || null;
}

/**
 * Process Gmail voice commands
 */
async function processGmailCommand(command) {
    const lowerCommand = command.toLowerCase();
    
    console.log('[Process Gmail Command] Input:', command, 'Lower:', lowerCommand, 'Selected email:', gmailState.selectedEmail);

    // Stop command - stop any ongoing speech
    if (lowerCommand.includes('stop') || lowerCommand.includes('pause') || lowerCommand.includes('quiet')) {
        console.log('[Process Gmail Command] Matched: stop speech');
        // Cancel any ongoing speech
        if (window.speechSynthesis.speaking) {
            window.speechSynthesis.cancel();
            console.log('[Process Gmail Command] Speech cancelled');
            // Give immediate feedback without speaking (to avoid starting new speech)
            showResponse('✋ Stopped reading email');
            // Optional: speak after a delay if you want audio confirmation
            setTimeout(() => {
                if (typeof speak === 'function') {
                    speak('Stopped');
                }
            }, 500);
        } else {
            if (typeof speak === 'function') {
                speak('Nothing is playing');
            }
        }
        return true;
    }

    // Open Gmail dashboard view
    if (lowerCommand.includes('open gmail') || lowerCommand.includes('go to gmail') || lowerCommand.includes('gmail assistant')) {
        if (typeof showGmailView === 'function') {
            showGmailView();
        }
        speak('Opening Gmail assistant');
        return true;
    }
    
    // EMAIL NUMBER COMMANDS - Check these FIRST before generic commands
    if (!gmailState.connected || !gmailState.currentEmails || gmailState.currentEmails.length === 0) {
        console.log('[Process Gmail Command] No Gmail context for number commands');
    } else {
        // Pattern: "read email 1" or "read email 10" etc
        let emailNumber = null;
        let readEmailMatch = lowerCommand.match(/read\s+(?:email|mail)\s+(\d+)/);
        if (readEmailMatch) {
            emailNumber = parseInt(readEmailMatch[1], 10);
            console.log('[Process Gmail Command] Matched: read email number', emailNumber);
            return handleEmailByNumber(emailNumber);
        }
        
        // Pattern: "read first email", "read second email", etc
        let readOrdinalWordMatch = lowerCommand.match(/read\s+(?:the\s+)?(\w+)\s+(?:email|mail)/);
        if (readOrdinalWordMatch) {
            const ordinalWord = readOrdinalWordMatch[1];
            const convertedNumber = convertOrdinalWordToNumber(ordinalWord);
            if (convertedNumber) {
                emailNumber = convertedNumber;
                console.log('[Process Gmail Command] Matched: read', ordinalWord, 'email (number:', emailNumber + ')');
                return handleEmailByNumber(emailNumber);
            }
        }
        
        // Pattern: "email 1" or "email 10" (standalone)
        let emailNumberMatch = lowerCommand.match(/^(?:(?:show|display)\s+)?(?:email|mail)\s+(\d+)/);
        if (emailNumberMatch) {
            emailNumber = parseInt(emailNumberMatch[1], 10);
            console.log('[Process Gmail Command] Matched: email number', emailNumber);
            return handleEmailByNumber(emailNumber);
        }
        
        // Pattern: "1st email", "2nd email", "10th email", etc
        let ordinalMatch = lowerCommand.match(/(\d+)(?:st|nd|rd|th)\s+(?:email|mail)/);
        if (ordinalMatch) {
            emailNumber = parseInt(ordinalMatch[1], 10);
            console.log('[Process Gmail Command] Matched: ordinal email', emailNumber);
            return handleEmailByNumber(emailNumber);
        }
        
        // Pattern: "delete email 1" or "delete email 10"
        let deleteEmailMatch = lowerCommand.match(/(?:delete|remove|trash)\s+(?:email|mail)\s+(\d+)/);
        if (deleteEmailMatch) {
            emailNumber = parseInt(deleteEmailMatch[1], 10);
            console.log('[Process Gmail Command] Matched: delete email number', emailNumber);
            return deleteEmailByNumber(emailNumber);
        }
        
        // Pattern: "delete first email" or "delete second email"
        let deleteOrdinalWordMatch = lowerCommand.match(/(?:delete|remove|trash)\s+(?:the\s+)?(\w+)\s+(?:email|mail)/);
        if (deleteOrdinalWordMatch) {
            const ordinalWord = deleteOrdinalWordMatch[1];
            const convertedNumber = convertOrdinalWordToNumber(ordinalWord);
            if (convertedNumber) {
                emailNumber = convertedNumber;
                console.log('[Process Gmail Command] Matched: delete', ordinalWord, 'email (number:', emailNumber + ')');
                return deleteEmailByNumber(emailNumber);
            }
        }
        
        // Pattern: "delete 1st email" or "delete 10th email"
        let deleteOrdinalMatch = lowerCommand.match(/(?:delete|remove|trash)\s+(\d+)(?:st|nd|rd|th)\s+(?:email|mail)/);
        if (deleteOrdinalMatch) {
            emailNumber = parseInt(deleteOrdinalMatch[1], 10);
            console.log('[Process Gmail Command] Matched: delete ordinal email', emailNumber);
            return deleteEmailByNumber(emailNumber);
        }
        
        // Pattern: "reply to email 1" or "reply email 1" or "reply 10th email"
        let replyEmailMatch = lowerCommand.match(/reply\s+(?:to\s+)?(?:email|mail)\s+(\d+)/);
        if (replyEmailMatch) {
            emailNumber = parseInt(replyEmailMatch[1], 10);
            console.log('[Process Gmail Command] Matched: reply email number', emailNumber);
            return replyToEmailByNumber(emailNumber);
        }
        
        // Pattern: "reply to first email" or "reply second email"
        let replyOrdinalWordMatch = lowerCommand.match(/reply\s+(?:to\s+)?(?:the\s+)?(\w+)\s+(?:email|mail)/);
        if (replyOrdinalWordMatch) {
            const ordinalWord = replyOrdinalWordMatch[1];
            const convertedNumber = convertOrdinalWordToNumber(ordinalWord);
            if (convertedNumber) {
                emailNumber = convertedNumber;
                console.log('[Process Gmail Command] Matched: reply to', ordinalWord, 'email (number:', emailNumber + ')');
                return replyToEmailByNumber(emailNumber);
            }
        }
        
        let replyOrdinalMatch = lowerCommand.match(/reply\s+(?:to\s+)?(\d+)(?:st|nd|rd|th)\s+(?:email|mail)/);
        if (replyOrdinalMatch) {
            emailNumber = parseInt(replyOrdinalMatch[1], 10);
            console.log('[Process Gmail Command] Matched: reply ordinal email', emailNumber);
            return replyToEmailByNumber(emailNumber);
        }
    }
    
    // Read aloud - check this AFTER numbered commands
    if ((lowerCommand.includes('read') && (lowerCommand.includes('email') || lowerCommand.includes('this') || lowerCommand.includes('message'))) 
        || lowerCommand.includes('read it')) {
        console.log('[Process Gmail Command] Matched: read email', 'Selected:', gmailState.selectedEmail);
        if (!gmailState.selectedEmail && gmailState.currentEmails.length > 0) {
            selectEmail(0);
        }
        if (gmailState.selectedEmail) {
            await readEmailAloud(gmailState.selectedEmail.id);
            return true;
        } else {
            console.warn('[Process Gmail Command] No email selected to read');
            speak('Please select an email first');
            return true;
        }
    }
    
    // Show sent emails - CHECK THIS FIRST before any "send" patterns
    if (lowerCommand.includes('sent email') || lowerCommand.includes('sent mail') || lowerCommand.includes('show sent') || lowerCommand.includes('open sent') || lowerCommand.includes('sent folder')) {
        console.log('[Process Gmail Command] Matched: sent emails');
        await fetchSentEmails();
        return true;
    }
    
    // Show deleted emails
    if (lowerCommand.includes('deleted email') || lowerCommand.includes('trash') || lowerCommand.includes('show deleted') || lowerCommand.includes('show trash')) {
        console.log('[Process Gmail Command] Matched: deleted emails');
        await fetchDeletedEmails();
        return true;
    }
    
    // Compose - must check AFTER "sent email" to avoid conflicts
    // Only match "send" if it's NOT "sent" (past tense) and NOT "sent emails" (folder)
    if (lowerCommand.includes('compose') || lowerCommand.includes('write email') || 
        (lowerCommand.includes('send email') && !lowerCommand.includes('sent'))) {
        console.log('[Process Gmail Command] Matched: compose email');
        showComposeForm();
        // showComposeForm already speaks and prompts for recipient
        return true;
    }
    
    // Check emails / Show inbox - check this AFTER sent/deleted to avoid conflicts
    if (lowerCommand.includes('check') || lowerCommand.includes('get my email') || lowerCommand.includes('fetch email') 
        || lowerCommand.includes('inbox') || lowerCommand.includes('my emails')) {
        console.log('[Process Gmail Command] Matched: check emails');
        await fetchGmailMessages();
        // Auto-select first email after fetching
        if (gmailState.currentEmails.length > 0) {
            selectEmail(0);
        }
        return true;
    }
    
    // Reply
    if (lowerCommand.includes('reply') && gmailState.selectedEmail) {
        console.log('[Process Gmail Command] Matched: reply');
        // Start voice reply flow
        if (typeof startVoiceReply === 'function') {
            startVoiceReply(gmailState.selectedEmail.id);
        } else {
            showReplyForm(gmailState.selectedEmail.id);
            speak('Opening reply form');
        }
        return true;
    }
    
    // Delete
    if (lowerCommand.includes('delete') && gmailState.selectedEmail) {
        console.log('[Process Gmail Command] Matched: delete');
        await deleteEmail(gmailState.selectedEmail.id);
        return true;
    }
    
    // Search
    const searchMatch = lowerCommand.match(/search (?:for |emails? )?(.+)/);
    if (searchMatch) {
        console.log('[Process Gmail Command] Matched: search for', searchMatch[1]);
        await searchEmails(searchMatch[1]);
        return true;
    }
    
    return false;
}

/**
 * Utility functions
 */
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function formatEmailDate(dateStr) {
    try {
        const date = new Date(dateStr);
        const now = new Date();
        const diff = now - date;
        
        if (diff < 86400000) { // Less than 24 hours
            return date.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' });
        } else if (diff < 604800000) { // Less than 7 days
            return date.toLocaleDateString('en-US', { weekday: 'short' });
        } else {
            return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
        }
    } catch (error) {
        return dateStr;
    }
}

function formatEmailBody(body) {
    if (!body) return '';

    // If the body contains HTML tags, sanitize and render as HTML
    const looksLikeHtml = /<\s*([a-zA-Z!][^>]*?)>/m.test(body);
    if (looksLikeHtml && typeof window.DOMPurify !== 'undefined') {
        try {
            // Sanitize potentially unsafe HTML from emails
            const clean = window.DOMPurify.sanitize(body, { USE_PROFILES: { html: true } });
            return clean;
        } catch (e) {
            console.warn('DOMPurify sanitize failed, falling back to text:', e);
        }
    }

    // Fallback: treat as plain text
    return escapeHtml(body).replace(/\n/g, '<br>');
}

// Initialize Gmail - only check status if user is authenticated
window.addEventListener('load', () => {
    // Check if returning from Gmail OAuth
    const urlParams = new URLSearchParams(window.location.search);
    const gmailAuth = urlParams.get('gmail_auth');
    const error = urlParams.get('error');
    const msg = urlParams.get('msg');
    
    if (gmailAuth === 'success') {
        // Clear the URL parameters
        window.history.replaceState({}, document.title, window.location.pathname);
        
        // Show success message
        if (typeof showResponse === 'function') {
            showResponse('✓ Gmail connected successfully! You can now use voice commands.');
        }
        if (typeof speak === 'function') {
            speak('Gmail connected successfully');
        }
        
        // Update Gmail status
        setTimeout(() => {
            checkGmailStatus();
            // Fetch messages after connection
            setTimeout(() => fetchGmailMessages(), 500);
        }, 500);
    } else if (error) {
        const errorMsg = msg ? decodeURIComponent(msg) : error;
        console.error('Gmail auth error:', error, errorMsg);
        if (typeof showError === 'function') {
            showError('Failed to connect Gmail: ' + errorMsg);
        }
        // Clear the URL parameter
        window.history.replaceState({}, document.title, window.location.pathname);
    } else {
        // Normal page load - wait a bit for authentication to be checked first
        setTimeout(() => {
            // Only check Gmail status if there's a dashboard section visible
            // (indicating user is logged in)
            const dashboard = document.getElementById('dashboardSection');
            if (dashboard && !dashboard.classList.contains('hidden')) {
                checkGmailStatus();
            }
        }, 1000);
    }
});

/**
 * Handle voice commands with email numbers
 * Called from the main voice command handler when a READ_EMAIL command with email_number is detected
 */
function handleEmailByNumber(emailNumber) {
    if (!gmailState.currentEmails || gmailState.currentEmails.length === 0) {
        speak('No emails loaded. Please fetch emails first by saying "check my emails"');
        showError('No emails available. Please fetch emails first.');
        return false;
    }
    
    // Convert to 0-based index
    const index = emailNumber - 1;
    
    if (index < 0 || index >= gmailState.currentEmails.length) {
        const count = gmailState.currentEmails.length;
        speak(`Email number ${emailNumber} not found. You have ${count} email${count !== 1 ? 's' : ''}.`);
        showError(`Email ${emailNumber} not found. You have ${count} emails.`);
        return false;
    }
    
    // Mark that user manually selected an email by number
    gmailState.lastSelectedByNumber = emailNumber;
    
    // Select the email (this will update UI with the correct index)
    selectEmail(index);
    
    // Read the email aloud using the proper function (instead of direct speak)
    const email = gmailState.currentEmails[index];
    readEmailAloud(email.id);
    
    return true;
}

/**
 * Delete email by number
 */
function deleteEmailByNumber(emailNumber) {
    if (!gmailState.currentEmails || gmailState.currentEmails.length === 0) {
        speak('No emails loaded');
        showError('No emails available.');
        return false;
    }
    
    const index = emailNumber - 1;
    
    if (index < 0 || index >= gmailState.currentEmails.length) {
        speak(`Email number ${emailNumber} not found`);
        return false;
    }
    
    const email = gmailState.currentEmails[index];
    // Store the email ID for deletion
    deleteEmail(email.id);
    speak(`Deleting email ${emailNumber}`);
    
    return true;
}

/**
 * Reply to email by number
 */
function replyToEmailByNumber(emailNumber) {
    if (!gmailState.currentEmails || gmailState.currentEmails.length === 0) {
        speak('No emails loaded');
        showError('No emails available.');
        return false;
    }
    
    const index = emailNumber - 1;
    
    if (index < 0 || index >= gmailState.currentEmails.length) {
        speak(`Email number ${emailNumber} not found`);
        return false;
    }
    
    // Select the email first
    selectEmail(index);
    
    // Show reply form
    const email = gmailState.currentEmails[index];
    currentReplyEmailId = email.id;
    speak(`Replying to email ${emailNumber} from ${email.from}`);
    showReplyForm(email);
    
    return true;
}


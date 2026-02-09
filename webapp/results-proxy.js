/**
 * Lightweight proxy server for fetching ElevenLabs conversation results.
 * Runs on port 3001 on the droplet. The web app calls this instead of
 * hitting the ElevenLabs API directly (which would expose the API key).
 * 
 * GET /api/results/:conversationId → returns analysis + data collection
 */

const http = require('http');
const https = require('https');

const API_KEY = process.env.ELEVENLABS_API_KEY;
const PORT = 3001;

function fetchConversation(conversationId) {
    return new Promise((resolve, reject) => {
        const options = {
            hostname: 'api.elevenlabs.io',
            path: `/v1/convai/conversations/${conversationId}`,
            headers: { 'xi-api-key': API_KEY }
        };
        https.get(options, (res) => {
            let data = '';
            res.on('data', chunk => data += chunk);
            res.on('end', () => {
                try { resolve(JSON.parse(data)); }
                catch (e) { reject(e); }
            });
        }).on('error', reject);
    });
}

const server = http.createServer(async (req, res) => {
    // CORS headers
    res.setHeader('Access-Control-Allow-Origin', '*');
    res.setHeader('Access-Control-Allow-Methods', 'GET');
    res.setHeader('Content-Type', 'application/json');

    const match = req.url.match(/^\/api\/results\/([a-zA-Z0-9_-]+)$/);
    if (!match) {
        res.writeHead(404);
        res.end(JSON.stringify({ error: 'Not found' }));
        return;
    }

    const conversationId = match[1];
    try {
        const convo = await fetchConversation(conversationId);
        // Return only the analysis portion — no transcript or audio
        res.writeHead(200);
        res.end(JSON.stringify({
            conversationId: convo.conversation_id,
            status: convo.status,
            analysis: convo.analysis || null
        }));
    } catch (e) {
        res.writeHead(500);
        res.end(JSON.stringify({ error: e.message }));
    }
});

server.listen(PORT, '127.0.0.1', () => {
    console.log(`Results proxy running on port ${PORT}`);
});

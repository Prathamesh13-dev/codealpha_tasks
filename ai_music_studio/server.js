// server.js
const express = require('express');
const path = require('path');
const app = express();

// Middleware to parse JSON data from the frontend
app.use(express.json());

// Serve your HTML file from the 'public' directory
app.use(express.static(path.join(__dirname, 'public')));

// --- API ENDPOINTS ---

// Example 1: Endpoint to save a user's composition
app.post('/api/save-composition', (req, res) => {
    const { userId, trackName, notes } = req.body;
    
    // In a complete app, you would save this to a database like MongoDB or PostgreSQL
    console.log(`Received track "${trackName}" with ${notes.length} notes.`);
    
    // Send a success response back to the frontend
    res.json({ 
        status: 'success', 
        message: 'Composition saved to backend!' 
    });
});

// Example 2: Endpoint to generate "AI" music from a backend ML model (Future feature)
app.post('/api/generate', (req, res) => {
    const { genre, key, scale } = req.body;
    // Here, you could connect to a Python script or AI model
    res.json({ message: `Backend received request to generate ${genre} in ${key} ${scale}` });
});

// Start the server
const PORT = process.env.PORT || 3000;
app.listen(PORT, () => {
    console.log(`🎵 AI Music Studio running at http://localhost:${PORT}`);
});
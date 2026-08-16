const express = require('express');
const router = express.Router();
const db = require('../db');
const auth = require('../middleware/auth');

// POST /api/messages - Public: send a contact message
router.post('/', (req, res) => {
  const { name, phone, message } = req.body;
  if (!name || !message) {
    return res.status(400).json({ error: 'Name and message are required' });
  }

  try {
    const result = db.prepare(`
      INSERT INTO messages (name, phone, message)
      VALUES (?, ?, ?)
    `).run(name.trim(), phone || '', message.trim());

    res.status(201).json({ message: 'Message sent successfully!', id: result.lastInsertRowid });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// GET /api/messages - Admin: list all messages
router.get('/', auth, (req, res) => {
  try {
    const messages = db.prepare('SELECT * FROM messages ORDER BY created_at DESC').all();
    res.json(messages);
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// PATCH /api/messages/:id/read - Admin: mark message as read
router.patch('/:id/read', auth, (req, res) => {
  const existing = db.prepare('SELECT * FROM messages WHERE id = ?').get(req.params.id);
  if (!existing) return res.status(404).json({ error: 'Message not found' });

  try {
    db.prepare('UPDATE messages SET read = 1 WHERE id = ?').run(req.params.id);
    res.json({ message: 'Marked as read' });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// DELETE /api/messages/:id - Admin: delete message
router.delete('/:id', auth, (req, res) => {
  const existing = db.prepare('SELECT * FROM messages WHERE id = ?').get(req.params.id);
  if (!existing) return res.status(404).json({ error: 'Message not found' });

  try {
    db.prepare('DELETE FROM messages WHERE id = ?').run(req.params.id);
    res.json({ message: 'Message deleted' });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

module.exports = router;

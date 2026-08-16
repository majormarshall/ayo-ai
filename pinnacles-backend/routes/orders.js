const express = require('express');
const router = express.Router();
const db = require('../db');
const auth = require('../middleware/auth');

// POST /api/orders - Public: place a new order
router.post('/', (req, res) => {
  const { customer_name, customer_phone, customer_address, items, total, notes } = req.body;

  if (!customer_name || !items || !Array.isArray(items) || items.length === 0) {
    return res.status(400).json({ error: 'Customer name and items are required' });
  }
  if (!total || isNaN(total)) {
    return res.status(400).json({ error: 'Valid total is required' });
  }

  try {
    const result = db.prepare(`
      INSERT INTO orders (customer_name, customer_phone, customer_address, items_json, total, notes)
      VALUES (?, ?, ?, ?, ?, ?)
    `).run(
      customer_name.trim(),
      customer_phone || '',
      customer_address || '',
      JSON.stringify(items),
      parseFloat(total),
      notes || ''
    );

    const order = db.prepare('SELECT * FROM orders WHERE id = ?').get(result.lastInsertRowid);
    res.status(201).json({ 
      message: 'Order placed successfully!', 
      orderId: order.id,
      order 
    });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// GET /api/orders - Admin: list all orders
router.get('/', auth, (req, res) => {
  try {
    const { status, limit = 50, offset = 0 } = req.query;
    let query = 'SELECT * FROM orders';
    const params = [];

    if (status) {
      query += ' WHERE status = ?';
      params.push(status);
    }

    query += ' ORDER BY created_at DESC LIMIT ? OFFSET ?';
    params.push(parseInt(limit), parseInt(offset));

    const orders = db.prepare(query).all(...params);
    // Parse items_json for each order
    const parsed = orders.map(o => ({ ...o, items: JSON.parse(o.items_json) }));
    res.json(parsed);
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// GET /api/orders/:id - Admin: single order
router.get('/:id', auth, (req, res) => {
  try {
    const order = db.prepare('SELECT * FROM orders WHERE id = ?').get(req.params.id);
    if (!order) return res.status(404).json({ error: 'Order not found' });
    res.json({ ...order, items: JSON.parse(order.items_json) });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// PATCH /api/orders/:id/status - Admin: update order status
router.patch('/:id/status', auth, (req, res) => {
  const { status } = req.body;
  const validStatuses = ['pending', 'confirmed', 'processing', 'delivered', 'cancelled'];
  if (!validStatuses.includes(status)) {
    return res.status(400).json({ error: `Status must be one of: ${validStatuses.join(', ')}` });
  }

  const existing = db.prepare('SELECT * FROM orders WHERE id = ?').get(req.params.id);
  if (!existing) return res.status(404).json({ error: 'Order not found' });

  try {
    db.prepare('UPDATE orders SET status = ? WHERE id = ?').run(status, req.params.id);
    const updated = db.prepare('SELECT * FROM orders WHERE id = ?').get(req.params.id);
    res.json({ ...updated, items: JSON.parse(updated.items_json) });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// DELETE /api/orders/:id - Admin: delete order
router.delete('/:id', auth, (req, res) => {
  const existing = db.prepare('SELECT * FROM orders WHERE id = ?').get(req.params.id);
  if (!existing) return res.status(404).json({ error: 'Order not found' });

  try {
    db.prepare('DELETE FROM orders WHERE id = ?').run(req.params.id);
    res.json({ message: 'Order deleted' });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

module.exports = router;

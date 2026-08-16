const express = require('express');
const router = express.Router();
const db = require('../db');
const auth = require('../middleware/auth');

// GET /api/products - Public: list all active products
router.get('/', (req, res) => {
  try {
    const products = db.prepare('SELECT * FROM products WHERE active = 1 ORDER BY id ASC').all();
    res.json(products);
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// GET /api/products/all - Admin: list all products including inactive
router.get('/all', auth, (req, res) => {
  try {
    const products = db.prepare('SELECT * FROM products ORDER BY id ASC').all();
    res.json(products);
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// POST /api/products - Admin: add new product
router.post('/', auth, (req, res) => {
  const { name, emoji, img, price, unit, description, category, tag } = req.body;
  if (!name || !price) return res.status(400).json({ error: 'Name and price are required' });

  try {
    const result = db.prepare(`
      INSERT INTO products (name, emoji, img, price, unit, description, category, tag)
      VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    `).run(
      name,
      emoji || '🌿',
      img || null,
      parseFloat(price),
      unit || 'per item',
      description || '',
      category || 'vegetables',
      tag || 'Fresh'
    );
    const product = db.prepare('SELECT * FROM products WHERE id = ?').get(result.lastInsertRowid);
    res.status(201).json(product);
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// PUT /api/products/:id - Admin: update product
router.put('/:id', auth, (req, res) => {
  const { name, emoji, img, price, unit, description, category, tag, active } = req.body;
  const { id } = req.params;

  const existing = db.prepare('SELECT * FROM products WHERE id = ?').get(id);
  if (!existing) return res.status(404).json({ error: 'Product not found' });

  try {
    db.prepare(`
      UPDATE products SET
        name = ?, emoji = ?, img = ?, price = ?, unit = ?,
        description = ?, category = ?, tag = ?, active = ?
      WHERE id = ?
    `).run(
      name ?? existing.name,
      emoji ?? existing.emoji,
      img ?? existing.img,
      price !== undefined ? parseFloat(price) : existing.price,
      unit ?? existing.unit,
      description ?? existing.description,
      category ?? existing.category,
      tag ?? existing.tag,
      active !== undefined ? (active ? 1 : 0) : existing.active,
      id
    );
    const updated = db.prepare('SELECT * FROM products WHERE id = ?').get(id);
    res.json(updated);
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// DELETE /api/products/:id - Admin: delete product
router.delete('/:id', auth, (req, res) => {
  const { id } = req.params;
  const existing = db.prepare('SELECT * FROM products WHERE id = ?').get(id);
  if (!existing) return res.status(404).json({ error: 'Product not found' });

  try {
    db.prepare('DELETE FROM products WHERE id = ?').run(id);
    res.json({ message: 'Product deleted' });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

module.exports = router;

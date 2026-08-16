require('dotenv').config();
const express = require('express');
const cors = require('cors');
const path = require('path');
const morgan = require('morgan');
const db = require('./db');

const app = express();
const PORT = process.env.PORT || 3001;

// ===== MIDDLEWARE =====
app.use(morgan('dev'));
app.use(cors());
app.use(express.json());

// ===== SERVE FRONTEND STATIC FILES =====
// Serve the Pinnacles farm frontend from the parent folder
const frontendPath = path.join(__dirname, '..', 'frontend');
app.use(express.static(frontendPath));

// Serve admin dashboard
const adminPath = path.join(__dirname, '..', 'admin');
app.use('/admin', express.static(adminPath));

// ===== ROUTES =====
app.use('/api/auth', require('./routes/auth'));
app.use('/api/products', require('./routes/products'));
app.use('/api/orders', require('./routes/orders'));
app.use('/api/messages', require('./routes/messages'));

// ===== STATS ENDPOINT (Admin) =====
const authMiddleware = require('./middleware/auth');
app.get('/api/stats', authMiddleware, (req, res) => {
  try {
    const totalOrders = db.prepare('SELECT COUNT(*) as count FROM orders').get().count;
    const pendingOrders = db.prepare("SELECT COUNT(*) as count FROM orders WHERE status = 'pending'").get().count;
    const totalRevenue = db.prepare("SELECT COALESCE(SUM(total), 0) as sum FROM orders WHERE status != 'cancelled'").get().sum;
    const unreadMessages = db.prepare('SELECT COUNT(*) as count FROM messages WHERE read = 0').get().count;
    const totalProducts = db.prepare('SELECT COUNT(*) as count FROM products WHERE active = 1').get().count;

    res.json({
      totalOrders,
      pendingOrders,
      totalRevenue,
      unreadMessages,
      totalProducts
    });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// ===== FALLBACK: serve index.html for all other GET routes =====
app.get('*', (req, res) => {
  if (req.path.startsWith('/admin')) {
    res.sendFile(path.join(adminPath, 'index.html'));
  } else {
    res.sendFile(path.join(frontendPath, 'index.html'));
  }
});

// ===== START =====
app.listen(PORT, () => {
  console.log(`\n🌿 Pinnacles Farm Server running at http://localhost:${PORT}`);
  console.log(`📊 Admin Dashboard at http://localhost:${PORT}/admin`);
  console.log(`🔌 API at http://localhost:${PORT}/api\n`);
});

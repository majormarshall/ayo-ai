const Database = require('better-sqlite3');
const path = require('path');
const bcrypt = require('bcrypt');

// Database file path
const dbPath = path.join(__dirname, 'pinnacles.db');
const db = new Database(dbPath);

// Enable WAL mode for better performance
db.pragma('journal_mode = WAL');

// ===== CREATE TABLES =====
db.exec(`
  CREATE TABLE IF NOT EXISTS products (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    emoji TEXT DEFAULT '🌿',
    img TEXT,
    price REAL NOT NULL,
    unit TEXT DEFAULT 'per item',
    description TEXT,
    category TEXT DEFAULT 'vegetables',
    tag TEXT DEFAULT 'Fresh',
    active INTEGER DEFAULT 1,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
  );

  CREATE TABLE IF NOT EXISTS orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_name TEXT NOT NULL,
    customer_phone TEXT,
    customer_address TEXT,
    items_json TEXT NOT NULL,
    total REAL NOT NULL,
    status TEXT DEFAULT 'pending',
    notes TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
  );

  CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    phone TEXT,
    message TEXT NOT NULL,
    read INTEGER DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
  );

  CREATE TABLE IF NOT EXISTS admins (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
  );
`);

// ===== SEED DEFAULT PRODUCTS =====
const productCount = db.prepare('SELECT COUNT(*) as count FROM products').get().count;
if (productCount === 0) {
  const insertProduct = db.prepare(`
    INSERT INTO products (name, emoji, img, price, unit, description, category, tag)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
  `);

  const defaultProducts = [
    ['Fresh Tomatoes', '🍅', 'images/tomatoes.png', 1500, 'per basket', 'Sun-ripened, juicy tomatoes grown naturally on our farm. Perfect for stews, sauces and salads.', 'vegetables', 'Bestseller'],
    ['Peppers', '🫑', 'images/pepper.png', 1200, 'per pack', 'Fresh bell peppers and chili peppers. Vibrant, crunchy, and full of flavour.', 'vegetables', 'Fresh'],
    ['Strawberries', '🍓', 'images/strawberry.png', 3500, 'per punnet', 'Sweet, juicy strawberries picked at peak ripeness. Great for desserts and smoothies.', 'fruits', 'Premium'],
    ['Sweet Maize', '🌽', 'images/maize.png', 800, 'per 3 cobs', 'Golden, sweet maize cobs freshly harvested. Roast, boil or grill — always delicious.', 'grains', 'Fresh'],
    ['Carrots', '🥕', 'images/carrots.png', 1000, 'per bunch', 'Crunchy, sweet orange carrots. Great for juices, soups and stir-fries.', 'vegetables', 'Organic'],
    ['Farm Fresh Eggs', '🥚', null, 2500, 'per crate (30)', 'Free-range farm eggs — rich, healthy and full of protein. From our hens to your kitchen.', 'proteins', 'Popular'],
    ['Green Peas', '🫛', null, 1800, 'per kg', 'Tender, sweet green peas freshly podded. Perfect for soups, rice dishes and snacks.', 'vegetables', 'Fresh'],
    ['Fresh Greens', '🥬', null, 600, 'per bunch', 'Assorted fresh leafy greens including spinach, ugwu and more.', 'vegetables', 'Daily Harvest'],
    ['Garden Cucumber', '🥒', null, 700, 'per pack', 'Cool, crisp cucumbers perfect for salads, juicing, and refreshing snacks.', 'vegetables', 'Fresh'],
    ['Spring Onions', '🧅', null, 500, 'per bunch', 'Fresh spring onions with a mild, sweet flavour. Great for garnishing and cooking.', 'vegetables', 'Fresh'],
    ['Sweet Pepper', '🌶️', null, 900, 'per pack', 'Colourful sweet peppers — red, yellow and green. Fresh and flavourful.', 'vegetables', 'Seasonal'],
    ['Farm Honey', '🍯', null, 4500, 'per jar', 'Pure, raw natural honey from our farm bees. Rich, golden and absolutely delicious.', 'fruits', 'Natural'],
  ];

  const seedMany = db.transaction((products) => {
    for (const p of products) insertProduct.run(...p);
  });
  seedMany(defaultProducts);
  console.log('✅ Seeded default products');
}

// ===== SEED DEFAULT ADMIN =====
const adminCount = db.prepare('SELECT COUNT(*) as count FROM admins').get().count;
if (adminCount === 0) {
  const adminPassword = process.env.ADMIN_PASSWORD || 'pinnacles2024';
  const adminUsername = process.env.ADMIN_USERNAME || 'admin';
  const hash = bcrypt.hashSync(adminPassword, 10);
  db.prepare('INSERT INTO admins (username, password_hash) VALUES (?, ?)').run(adminUsername, hash);
  console.log(`✅ Default admin created → username: "${adminUsername}", password: "${adminPassword}"`);
}

module.exports = db;

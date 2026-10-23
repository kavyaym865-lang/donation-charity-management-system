CREATE TABLE IF NOT EXISTS users(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    email TEXT UNIQUE,
    password TEXT
);

CREATE TABLE IF NOT EXISTS charities(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    category TEXT,
    location TEXT,
    address TEXT,
    money_required REAL,
    purpose TEXT,
    image_url TEXT,
    contact TEXT,
    trust_logo TEXT
);

CREATE TABLE IF NOT EXISTS donations(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    charity_id INTEGER,
    donor_name TEXT,
    donor_address TEXT,
    donor_mobile TEXT,
    donor_email TEXT,
    amount REAL,
    timestamp TEXT,
    stripe_payment_intent TEXT
);

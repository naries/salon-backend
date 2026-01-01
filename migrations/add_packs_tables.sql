-- Add packs table
CREATE TABLE IF NOT EXISTS packs (
    id SERIAL PRIMARY KEY,
    salon_id INTEGER NOT NULL REFERENCES salons(id) ON DELETE CASCADE,
    name VARCHAR NOT NULL,
    description TEXT,
    custom_price INTEGER,
    discount_percentage FLOAT DEFAULT 0,
    is_active INTEGER DEFAULT 1,
    deleted_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Add pack_products join table
CREATE TABLE IF NOT EXISTS pack_products (
    id SERIAL PRIMARY KEY,
    pack_id INTEGER NOT NULL REFERENCES packs(id) ON DELETE CASCADE,
    product_id INTEGER NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    quantity INTEGER DEFAULT 1 NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(pack_id, product_id)
);

-- Add pack_id column to order_items
ALTER TABLE order_items 
ALTER COLUMN product_id DROP NOT NULL,
ADD COLUMN IF NOT EXISTS pack_id INTEGER REFERENCES packs(id);

-- Add indexes for better performance
CREATE INDEX IF NOT EXISTS idx_packs_salon_id ON packs(salon_id);
CREATE INDEX IF NOT EXISTS idx_packs_is_active ON packs(is_active);
CREATE INDEX IF NOT EXISTS idx_pack_products_pack_id ON pack_products(pack_id);
CREATE INDEX IF NOT EXISTS idx_pack_products_product_id ON pack_products(product_id);
CREATE INDEX IF NOT EXISTS idx_order_items_pack_id ON order_items(pack_id);

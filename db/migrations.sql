-- LinkMasterBot Schema
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

CREATE TABLE IF NOT EXISTS users (
    telegram_id BIGINT PRIMARY KEY,
    username TEXT,
    is_admin BOOLEAN DEFAULT FALSE,
    shortener_api_key TEXT,
    shortener_type TEXT DEFAULT 'gplinks',
    total_shortened INTEGER DEFAULT 0,
    is_banned BOOLEAN DEFAULT FALSE,
    is_premium BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS generated_links (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    creator_id BIGINT REFERENCES users(telegram_id) ON DELETE CASCADE,
    original_url TEXT NOT NULL,
    bridge_code TEXT UNIQUE NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_links_creator ON generated_links(creator_id);

CREATE TABLE IF NOT EXISTS link_clicks (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    link_id UUID REFERENCES generated_links(id) ON DELETE CASCADE,
    visitor_ip TEXT NOT NULL,
    click_count INTEGER DEFAULT 1,
    last_click TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(link_id, visitor_ip)
);
CREATE INDEX IF NOT EXISTS idx_clicks_link ON link_clicks(link_id);

CREATE TABLE IF NOT EXISTS bot_settings (
    id INTEGER PRIMARY KEY DEFAULT 1,
    bypass_enabled BOOLEAN DEFAULT TRUE,
    global_redirect_enabled BOOLEAN DEFAULT TRUE,
    ip_logging_enabled BOOLEAN DEFAULT TRUE,
    admin_api_key TEXT,
    admin_shortener_type TEXT DEFAULT 'gplinks',
    maintenance_mode BOOLEAN DEFAULT FALSE
);

INSERT INTO bot_settings (id) VALUES (1) ON CONFLICT (id) DO NOTHING;

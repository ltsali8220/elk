CREATE TABLE IF NOT EXISTS users (
    id             SERIAL PRIMARY KEY,
    username       VARCHAR(64)  NOT NULL UNIQUE,
    email          VARCHAR(128) UNIQUE,
    password_hash  VARCHAR(64)  NOT NULL,
    salt           VARCHAR(64)  NOT NULL,
    role           VARCHAR(16)  NOT NULL DEFAULT 'user',
    created_at     TIMESTAMP    NOT NULL DEFAULT NOW(),
    last_login     TIMESTAMP,
    login_count    INTEGER      NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS activity_log (
    id          SERIAL PRIMARY KEY,
    user_id     INTEGER,
    username    VARCHAR(64),
    action      VARCHAR(32)  NOT NULL,
    outcome     VARCHAR(16)  NOT NULL,
    ip_address  VARCHAR(45),
    user_agent  TEXT,
    path        VARCHAR(256),
    created_at  TIMESTAMP    NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_users_username  ON users(username);
CREATE INDEX IF NOT EXISTS idx_users_email     ON users(email);
CREATE INDEX IF NOT EXISTS idx_activity_user   ON activity_log(user_id);
CREATE INDEX IF NOT EXISTS idx_activity_ts     ON activity_log(created_at);

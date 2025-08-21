CREATE TABLE IF NOT EXISTS tasks
(
    id SERIAL PRIMARY KEY,
    user_id bigint NOT NULL,
    name text NOT NULL,
    description text,
    is_completed boolean DEFAULT false,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    reminder timestamp without time zone,
    reminder_sent boolean DEFAULT false,
    priority boolean DEFAULT false
);

ALTER TABLE tasks
    OWNER to todo_user;
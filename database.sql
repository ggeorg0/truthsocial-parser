CREATE TYPE parser_status_type AS ENUM ('not parsed', 'parsing now', 'parsed', 'error');

CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(511),
    followers INT,
    following INT,
    registration_date DATE,
    location VARCHAR(511),
    personal_site VARCHAR(255),
    parser_status parser_status_type DEFAULT 'not parsed',
    bio TEXT DEFAULT ''
);

CREATE TABLE posts (
    id BIGINT PRIMARY KEY,
    post_text TEXT NOT NULL,
    owner_id INT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    reply_to_id BIGINT REFERENCES users(id),
    likes INT,
    reposts INT,
    replies INT,
    creation_date TIMESTAMP NOT NULL
);

CREATE TYPE interaction_type AS ENUM ('reposted', 'liked');

CREATE TABLE post_interactions (
    id SERIAL PRIMARY KEY,
    post_id BIGINT NOT NULL REFERENCES posts(id) ON DELETE CASCADE,
    user_id INT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    interaction interaction_type NOT NULL
);
CREATE TABLE followers (
    user_id INT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    follower INT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    PRIMARY KEY (user_id, follower)
);

-- see data

-- SELECT * FROM users LIMIT 100;
-- SELECT * FROM posts LIMIT 100;
-- SELECT * FROM post_interactions LIMIT 100;

-- drop statements

-- DROP TABLE followers;
-- DROP TABLE post_interactions;
-- DROP TABLE posts;
-- DROP TYPE interactiontype;
-- DROP TABLE users;

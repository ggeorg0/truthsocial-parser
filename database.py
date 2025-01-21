import logging

import asyncpg
from asyncpg import Pool
from asyncpg import create_pool

from entities import Post, User, Follower


class Database:
    _pool: Pool
    _max_pool_size: int

    def __init__(self, dsn, max_pool_size: int = 10):
        self.dsn = dsn
        self._max_pool_size = max_pool_size

    async def __aenter__(self):
        if not hasattr(self, "_pool") or self._pool.is_closing():
            await self.connect()
        return self

    async def __aexit__(self, exc_type, exc, tb):
        await self.close()

    async def connect(self):
        self._pool = await create_pool(self.dsn, max_size=self._max_pool_size)

    async def close(self):
        await self._pool.close()

    async def _get_user_id(self, conn: asyncpg.Connection, username: str):
        user_id = await conn.fetchval(
            "SELECT id FROM users WHERE username = $1", username
        )
        return int(user_id) if user_id is not None else None

    async def _save_username(self, conn: asyncpg.Connection, username: str) -> int:
        """
        Saves a user to the database if they do not already exist.
        Args:
            username (str): The username of the user to save.
            conn (asyncpg.Connection): The database connection object.
        Returns:
            user_id (int): The ID of the user if they already exist, otherwise None.
        """
        user_id = await self._get_user_id(conn, username)
        if not user_id:
            await conn.execute(
                """
                INSERT INTO users (username) VALUES ($1);
                """,
                username,
            )
            user_id = await self._get_user_id(conn, username)
        return user_id  # type: ignore

    async def save_post(self, post: Post):
        async with self._pool.acquire() as conn:
            async with conn.transaction():
                # 1. Get or create user
                user_id = await self._save_username(conn, post.owner)
                assert user_id is not None

                # 2. Check if it's a reply and get the user ID of the replied user
                if post.reply_to:
                    reply_to_id = await self._save_username(conn, post.reply_to)
                else:
                    reply_to_id = None

                # 3. Insert (or update) post
                await conn.execute(
                    """
                    INSERT INTO posts (
                        id, post_text, owner_id,
                        reply_to_id, likes, reposts,
                        replies, creation_date
                    )
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                    ON CONFLICT (id) DO UPDATE SET
                        post_text = EXCLUDED.post_text,
                        owner_id = EXCLUDED.owner_id,
                        reply_to_id = EXCLUDED.reply_to_id,
                        likes = EXCLUDED.likes,
                        reposts = EXCLUDED.reposts,
                        replies = EXCLUDED.replies,
                        creation_date = EXCLUDED.creation_date
                    """,
                    post.post_id,
                    post.text,
                    user_id,
                    reply_to_id,
                    post.likes,
                    post.reposts,
                    post.replies,
                    post.timestamp,
                )

                # 4. Add repost interaction if needed
                if post.is_repost and post.who_reposted:
                    reposter_id = await self._save_username(conn, post.who_reposted)
                    await conn.execute(
                        """
                        INSERT INTO post_interactions (post_id, user_id, interaction)
                        VALUES ($1, $2, 'reposted')
                        """,
                        int(post.post_id),
                        reposter_id,
                    )

    async def _insert_user(self, conn: asyncpg.Connection, user: User):
        return await conn.execute(
            """
            INSERT INTO users
                (username,
                name,
                followers,
                following,
                registration_date,
                location,
                personal_site,
                bio)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            ON CONFLICT (username) DO UPDATE SET
                name = EXCLUDED.name,
                followers = EXCLUDED.followers,
                following = EXCLUDED.following,
                registration_date = EXCLUDED.registration_date,
                location = EXCLUDED.location,
                personal_site = EXCLUDED.personal_site,
                bio = EXCLUDED.bio
            """,
            user.username,
            user.name,
            user.followers_num,
            user.following_num,
            user.registration_date,
            user.location,
            user.personal_site,
            user.bio,
        )

    async def save_user(self, user: User):
        async with self._pool.acquire() as conn:
            await self._insert_user(conn, user)

    async def save_follower(self, follower: Follower):
        async with self._pool.acquire() as conn:
            async with conn.transaction():
                user_id = await self._save_username(conn, follower.who_to_follow)

                follower_id = await self._get_user_id(conn, follower.username)
                if follower_id is None:
                    await self.save_user(
                        User(username=follower.username, name=follower.name)
                    )
                    follower_id = await self._get_user_id(conn, follower.username)

                await conn.execute(
                    """
                    INSERT INTO followers (user_id, follower)
                    VALUES ($1, $2) ON CONFLICT (user_id, follower) DO NOTHING
                    """,
                    user_id,
                    follower_id,
                )

    async def mark_user_parsed(self, username: str):
        await self._mark_user(username, "parsed")

    async def mark_user_error(self, username: str):
        await self._mark_user(username, "error")

    async def mark_user_parsing_now(self, username: str):
        await self._mark_user(username, "parsing now")

    async def _mark_user(self, username, status):
        # NOTE: This the the only database method enclosed in a try-except block.
        # because it's not _very_ critical for the application.
        # But if error occur in this method it will stop all the parsing process.
        try:
            async with self._pool.acquire() as conn:
                async with conn.transaction():
                    user_id = await self._save_username(conn, username)
                    await conn.execute(
                        """
                        UPDATE users SET parser_status = $1 WHERE id = $2
                        """,
                        status,
                        user_id,
                    )
        except (asyncpg.PostgresError, asyncpg.InterfaceError):
            logging.error(f"Cannot mark user as {status}")

    async def get_bunch_of_users(self, start_from_id: int = 1, limit: int = 10):
        async with self._pool.acquire() as conn:
            return await conn.fetch(
                """
                SELECT username FROM users
                WHERE
                    parser_status = 'not parsed'
                    OR parser_status = 'error'
                    AND id > $1
                LIMIT $2
                """,
                start_from_id,
                limit,
            )

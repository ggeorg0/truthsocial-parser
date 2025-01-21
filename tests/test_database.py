import os
from datetime import datetime

import pytest
from dotenv import load_dotenv

from database import Database
from entities import Post, User

# load database credentials from .env file
load_dotenv()
dsn = os.environ["TEST_DSN"]


@pytest.fixture
def sample_user():
    return User(
        username="testuser",
        name="Test User",
        bio="This is a test bio",
        followers_num=100,
        following_num=50,
        location="Test Location",
        personal_site="https://testsite.com",
        registration_date=datetime(2020, 1, 1),
    )


@pytest.fixture
def sample_post():
    return Post(
        post_id=113853838355066029,
        text="This is a test post",
        owner="testuser",
        reply_to=None,
        likes=200,
        reposts=1,
        replies=2,
        timestamp=datetime.now(),
        is_repost=False,
        who_reposted=None,
    )


def test_env_loaded():
    assert dsn is not None
    print(dsn)


@pytest.mark.asyncio
async def test_save_post(sample_post: Post):
    async with Database(dsn) as database:
        await database.save_post(sample_post)
        async with database._pool.acquire() as conn:
            post = await conn.fetchrow(
                "SELECT * FROM posts WHERE id = $1", sample_post.post_id
            )
        assert post is not None
        assert post["post_text"] == sample_post.text
        assert post["likes"] == sample_post.likes


@pytest.mark.asyncio
async def test_save_post_with_repost(sample_post: Post):
    sample_post.is_repost = True
    sample_post.who_reposted = "reposter"
    async with Database(dsn) as database:
        await database.save_post(sample_post)
        async with database._pool.acquire() as conn:
            interaction = await conn.fetchrow(
                "SELECT * FROM post_interactions WHERE post_id = $1", sample_post.post_id
            )
        assert interaction is not None
        assert interaction["interaction"] == "reposted"


@pytest.mark.asyncio
async def test_save_user(sample_user: User):
    async with Database(dsn) as database:
        await database.save_user(sample_user)
        async with database._pool.acquire() as conn:
            user = await conn.fetchrow(
                "SELECT * FROM users WHERE username = $1", sample_user.username
            )
        assert user is not None
        assert user["name"] == sample_user.name
        assert user["bio"] == sample_user.bio
        assert user["followers"] == sample_user.followers_num


@pytest.mark.asyncio
async def test_save_user_update(sample_user: User):
    async with Database(dsn) as database:
        await database.save_user(sample_user)
        sample_user.name = "Updated Test User"
        sample_user.bio = "Updated test bio"
        await database.save_user(sample_user)
        async with database._pool.acquire() as conn:
            user = await conn.fetchrow(
                "SELECT * FROM users WHERE username = $1", sample_user.username
            )
        assert user is not None
        assert user["name"] == "Updated Test User"
        assert user["bio"] == "Updated test bio"

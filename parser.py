import logging
import os
from time import time
from collections import deque
import traceback

from random import randint
from ordered_set import OrderedSet
from dotenv import load_dotenv

# nodriver was "undetected chrome" earlier so it's convinient to use 'uc' name
import nodriver as uc

from entities import Post, User, Follower
from database import Database

logging.basicConfig(level=logging.INFO)
load_dotenv()

PROXY = "socks5://localhost:2080"
BASE_URL = "https://truthsocial.com"

USERNAME = os.environ["TS_USERNAME"]
PASSWORD = os.environ["TS_PASSWORD"]
DSN = os.environ["DSN"]

POST_SELECTOR = ".status__wrapper.space-y-4.status-public.p-4"
REPLY_POST_SELECTOR = ".status__wrapper.space-y-4.status-public.status-reply.p-4"
USER_INFO_SELECTOR = "div.flex.flex-col.space-y-3.mt-6.min-w-0.flex-1.px-4"
FOLLOWER_SELECTOR = 'div[class="pb-4"] div[data-testid="account"]'

SCROLL_MIN = 80
SCROLL_MAX = 110

INTIAL_USERNAME = "realDonaldTrump"


class Parser:
    browser: uc.Browser
    _login_username: str
    _login_pass: str
    _dsn: str
    _db_pool_size: int
    _users_queue: deque[str]
    _seen_usenames: set[str]
    _iterations: int

    def __init__(
        self,
        proxy_url: str,
        login_username: str,
        login_pass: str,
        db_credentials: str,
        db_max_connections: int = 15,
        posts_per_user: int = 30,
        replies_per_user: int = 30,
        followers_per_user: int = 50,
        following_per_user: int = 50,
    ) -> None:
        self._proxy = proxy_url
        self._login_pass = login_pass
        self._login_username = login_username
        self._dsn = db_credentials
        self._db_pool_size = db_max_connections
        self._posts_per_user = posts_per_user
        self._replies_per_user = replies_per_user
        self._followers_per_user = followers_per_user
        self._following_per_user = following_per_user
        self._users_queue = deque()
        self._seen_usenames = set()
        self._iterations = 0

    async def create_browser(self):
        self.browser = await uc.start(
            browser_args=[f"--proxy-server={self._proxy}"],
        )

    async def parsing_loop(self, initial_username: str, max_iterations=100):
        await self.create_browser()
        await self.sign_in()

        async with Database(self._dsn, self._db_pool_size) as db:
            self._users_queue.append(initial_username)
            while self._iterations < max_iterations and self._users_queue:
                uname = self._users_queue.pop()
                user_parser = UserParser(self.browser, uname, db)
                logging.info(f"Parsing user @{uname}")
                try:
                    await db.mark_user_parsing_now(uname)
                    await user_parser.parse()
                    await db.mark_user_parsed(uname)
                except Exception:
                    await db.mark_user_error(uname)
                    logging.error(traceback.format_exc())
                    logging.error(f"Failed to parse user @{uname}")
                try:
                    if not self._users_queue:
                        for un in await db.get_bunch_of_usernames():
                            if un not in self._seen_usenames:
                                logging.info(f"adding user to queue @{un}")
                                self._users_queue.append(un)
                    else:
                        logging.info(f"queue length: {len(self._users_queue)}")
                except Exception:
                    logging.error(traceback.format_exc())
                    logging.info("Cannot add new users to queue")
                self._seen_usenames.add(uname)
                self._iterations += 1
        logging.info("Parsing finished!")

    async def sign_in(self, timeouts=1):
        """Login in to the truthsocial"""
        page = await self.browser.get(BASE_URL)

        await page.wait_for('div[data-testid="banner"]')
        cookies_accept = await page.find("Accept", best_match=True)
        if cookies_accept is None:
            raise ValueError("Cookies Accept button is not found")
        await cookies_accept.click()
        await page.wait(timeouts)

        popup_window_button = await page.find("Sign In", best_match=True)
        if popup_window_button is None:
            raise ValueError("Initial Sign In button was not found!")
        await popup_window_button.click()
        await page.wait(timeouts)

        username_field = await page.select('input[name="username"]')
        await username_field.send_keys(self._login_username)
        pass_field = await page.select('input[name="password"]')
        await pass_field.send_keys(self._login_pass)

        signin_button = await page.select('button[data-testid="submit"]')
        logging.info("Clicking to real signin button!")
        await signin_button.click()

        t0 = time()
        await page.wait_for("#compose-textarea")
        logging.info(f"Waited for main page loading {time() - t0:.5f}")
        await page.save_screenshot()


class UserParser:
    browser: uc.Browser
    database: None
    _database: Database

    def __init__(
        self,
        browser: uc.Browser,
        username: str,
        database: Database,
        max_posts: int = 35,
        max_replies: int = 35,
        max_followers=50,
        max_following=50,
    ):
        self.username = username
        self.browser = browser
        self._database = database
        self.max_posts = max_posts
        self.max_replies = max_replies
        self.max_followers = max_followers
        self.max_following = max_following
        self.scroll_retries = 4

    async def parse(self):
        async def handle_task(task, username, action):
            try:
                await task()
            except (TimeoutError, ValueError) as e:
                logging.error(f"Failed to {action} for @{username}: {e}")

        await handle_task(self.get_user_info, self.username, "parse profile info")
        await handle_task(self.download_main_posts, self.username, "download posts")
        await handle_task(self.download_replies, self.username, "download replies")
        await handle_task(self.get_users_followers, self.username, "obtain followers")
        await handle_task(self.get_users_following, self.username, "obtain following")

    async def get_user_info(self):
        url = f"{BASE_URL}/@{self.username}"
        tab = await self.browser.get(url, new_tab=True)

        try:
            info_div = await tab.wait_for(USER_INFO_SELECTOR)
            html_data = await info_div.get_html()
        finally:
            await tab.close()

        user = User(html_data=html_data)
        await self._database.save_user(user)

    async def download_main_posts(self):
        """
        Downloads posts from a user's page.

        Args:
            max_posts (int): Maximum number of posts to download. Defaults to 10.
            stay_tolerance (int): Number of scroll attempts before stopping if no new posts are found. Defaults to 6.
        """
        url = f"{BASE_URL}/@{self.username}"
        tab = await self.browser.get(url, new_tab=True)
        try:
            await tab.wait_for(POST_SELECTOR)

            posts = await self.scroll_posts(
                tab=tab,
                post_selector=POST_SELECTOR,
                max_posts=self.max_posts,
                stay_tolerance=self.scroll_retries,
            )
        finally:
            await tab.close()

        for p in posts:
            logging.info(f"saving post {p}")
            await self._database.save_post(p)

    async def download_replies(self):
        url = f"{BASE_URL}/@{self.username}/with_replies"
        tab = await self.browser.get(url, new_tab=True)
        try:
            await tab.wait_for(REPLY_POST_SELECTOR)

            posts = await self.scroll_posts(
                tab=tab,
                post_selector=REPLY_POST_SELECTOR,
                max_posts=self.max_replies,
                stay_tolerance=self.scroll_retries,
            )
        finally:
            await tab.close()

        for p in posts:
            logging.info(f"saving reply {p}")
            await self._database.save_post(p)

    async def get_users_followers(self):
        url = f"{BASE_URL}/@{self.username}/followers"
        tab = await self.browser.get(url, new_tab=True)

        try:
            followers = await self.scroll_followers(
                tab=tab,
                max_followers=self.max_followers,
                stay_tolerance=self.scroll_retries,
            )
        finally:
            await tab.close()

        for follower in followers:
            logging.info(f"saving follower: {follower}")
            await self._database.save_follower(follower)

    async def get_users_following(self):
        url = f"{BASE_URL}/@{self.username}/following"
        tab = await self.browser.get(url, new_tab=True)

        try:
            followers = await self.scroll_followers(
                tab,
                following_swap=True,
                stay_tolerance=self.scroll_retries,
                max_followers=self.max_following,
            )
        finally:
            await tab.close()

        for follower in followers:
            logging.info(f"saving following: {follower}")
            await self._database.save_follower(follower)

    async def scroll_posts(
        self,
        tab: uc.Tab,
        post_selector: str,
        *,
        max_posts: int,
        stay_tolerance: int,
    ):
        posts = OrderedSet()  # type: ignore
        height = await tab.evaluate("document.body.scrollHeight")
        same_height = 0
        while True:
            await tab.scroll_down(randint(SCROLL_MIN, SCROLL_MAX))
            new_height = await tab.evaluate("document.body.scrollHeight")

            logging.info("waiting for posts to load")
            await tab.wait(randint(1, 3))

            found_posts = await tab.find_all(post_selector)
            logging.info(f"Found {len(found_posts)}")

            for p in found_posts:
                html = await p.get_html()
                posts.add(Post(html_data=html))

            if len(posts) >= max_posts:
                logging.info("Max posts limit reached")
                break

            same_height += 1 if new_height == height else 0
            if same_height == stay_tolerance:
                logging.info(f"Cannot scroll more after {stay_tolerance} attempts")
                break
            height = new_height

        return posts

    async def scroll_followers(
        self,
        tab: uc.Tab,
        *,
        max_followers: int,
        stay_tolerance: int,
        following_swap: bool = False,
    ):
        await tab.wait_for(FOLLOWER_SELECTOR)

        followers = OrderedSet()  # type: ignore
        height = await tab.evaluate("document.body.scrollHeight")
        same_height = 0
        while True:
            follower_divs = await tab.find_all(FOLLOWER_SELECTOR)
            logging.info(f"Found {len(follower_divs)} followers on a page")

            for fd in follower_divs:
                html = await fd.get_html()
                follower = Follower(who_to_follow=self.username, html_data=html)
                if following_swap:
                    # swap direction in case 'followed by' people
                    follower.swap_direction()
                followers.add(follower)

            await tab.scroll_down(randint(SCROLL_MIN, SCROLL_MAX))
            new_height = await tab.evaluate("document.body.scrollHeight")

            logging.info("waiting for followers to load")
            await tab.wait(randint(1, 3))

            if len(followers) >= max_followers:
                logging.info("Max followers limit reached")
                break

            same_height += 1 if new_height == height else 0
            if same_height == stay_tolerance:
                logging.info(f"Cannot scroll more after {stay_tolerance} attempts")
                break
            height = new_height

        return followers

    async def _save_post_to_file(self, dir: str, post_id: str, post_data: str):
        """For testing purposes, saves post data to a file."""
        with open(f"{dir}/{post_id}.txt", "w") as f:
            f.write(post_data)


if __name__ == "__main__":
    parser = Parser(
        proxy_url=PROXY,
        login_username=USERNAME,
        login_pass=PASSWORD,
        db_credentials=DSN,
        db_max_connections=15,
        posts_per_user=30,
        replies_per_user=30,
        followers_per_user=50,
        following_per_user=50,
    )
    uc.loop().run_until_complete(
        parser.parsing_loop(INTIAL_USERNAME, max_iterations=500)
    )

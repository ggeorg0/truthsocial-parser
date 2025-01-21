from __future__ import annotations

from pyquery import PyQuery as pq
from datetime import datetime

class Post:
    __slots__ = (
        "post_id",
        "owner",
        "reply_to",
        "timestamp",
        "is_repost",
        "who_reposted",
        "text",
        "likes",
        "replies",
        "reposts",
        "_html_data",
    )
    _html_data: pq
    post_id: int
    owner: str
    reply_to: str | None
    timestamp: datetime

    is_repost: bool
    who_reposted: str | None

    text: str
    likes: int
    replies: int
    reposts: int

    def __init__(
        self,
        post_id: int | None = None,
        owner: str | None = None,
        reply_to: str | None = None,
        timestamp: datetime | None = None,
        is_repost: bool = False,
        who_reposted: str | None = None,
        text: str = '',
        likes: int = 0,
        replies: int = 0,
        reposts: int = 0,
        *,
        html_data: str | None = None,
    ):
        if html_data:
            self._html_data = pq(html_data)
            self._parse_html()
            return None
        if None in (post_id, owner, timestamp, text):
            raise ValueError("Post ID, owner, text, and timestamp are required")
        self.post_id = post_id      # type: ignore
        self.owner = owner          # type: ignore
        self.reply_to = reply_to
        self.timestamp = timestamp  # type: ignore
        self.is_repost = is_repost
        self.who_reposted = who_reposted
        self.text = text
        self.likes = likes
        self.replies = replies
        self.reposts = reposts

    def _parse_html(self):
        self.post_id = self.parse_post_id()
        self.owner = self.parse_owner()
        self.reply_to = self.parse_reply_to()
        self.timestamp = self.parse_timestamp()
        self.is_repost = self.parse_is_repost()
        self.who_reposted = self.parse_who_reposted()
        self.text = self.parse_text()
        self.likes = self.parse_likes()
        self.replies = self.parse_replies()
        self.reposts = self.parse_reposts()


    def __str__(self):
        return (
            f"Post id: {self.post_id}\n"
            f"\tOwner: {self.owner}\n"
            f"\tTimestamp: {self.timestamp}\n"
            f"\tIs repost: {self.is_repost}\n"
            f"\tWho reposted: {self.who_reposted}\n"
            f"\tReply to: {self.reply_to}\n"
            f"\tLikes: {self.likes}\n"
            f"\tReplies: {self.replies}\n"
            f"\tReposts: {self.reposts}\n"
            f"\tText: {self.text}"
        )

    def __repr__(self):
        return self.__str__()

    def __hash__(self) -> int:
        hash_str = f"{self.post_id}{self.is_repost}"
        return hash(hash_str)

    def parse_post_id(self):
        post_id = self._html_data("div[data-id]").attr("data-id")
        if not isinstance(post_id, str):
            raise ValueError('Post ID not found')
        return int(post_id)

    def parse_owner(self):
        owner_username = self._html_data("a[title]").attr("title")
        if not isinstance(owner_username, str):
            raise ValueError('Owner username not found')
        return owner_username

    def parse_reply_to(self):
        reply_link = self._html_data(".reply-mentions a").eq(0)
        if reply_link:
            # href looks like "/@examore"
            return reply_link.attr("href")[2:]
        else:
            return None

    def parse_timestamp(self) -> datetime:
        time_str = self._html_data("time").attr("title")
        return datetime.strptime(time_str, "%b %d, %Y, %I:%M %p")

    def parse_is_repost(self) -> bool:
        return "ReTruthed" in self._html_data('div[role="status-info"]').text()

    def parse_who_reposted(self) -> str | None:
        if self.is_repost:
            link_to_profile = self._html_data('div[role="status-info"] a').attr("href")
            return link_to_profile.split("/")[-1][1:]
        return None

    def parse_text(self):
        text_wrapper = self._html_data(".status__content-wrapper div.relative").eq(0)
        paragraphs = [item.text() for item in text_wrapper.items("p")]
        text = "\n".join(p for p in paragraphs if p)
        return text

    def __parse_stat_value(self, stat) -> int:
        text = str(self._html_data(f'button[title="{stat}"] span').text()).lower()
        if text:
            val = float(text.replace("k", "").replace("m", ""))
            if text.count("k"):
                val *= 1_000
            if text.count("m"):
                val *= 1_000_000
            return int(val)
        else:
            return 0

    def parse_likes(self) -> int:
        return self.__parse_stat_value("Like")

    def parse_replies(self) -> int:
        return (self.__parse_stat_value("Reply to thread")
            or self.__parse_stat_value("Reply"))

    def parse_reposts(self) -> int:
        return self.__parse_stat_value("ReTruth")

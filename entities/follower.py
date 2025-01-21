from pyquery import PyQuery as pq

class Follower:
    __slots__ = (
        "username",
        "name",
        "who_to_follow",
        "_html_data"
    )
    username: str
    name: str | None
    who_to_follow: str
    _html_data: pq

    def __init__(
        self,
        who_to_follow: str,
        username: str | None = None,
        name: str | None = None,
        html_data: str | None = None,
    ):
        if html_data:
            self._html_data = pq(html_data)
            self._parse_html()
        elif username is None:
            raise ValueError("`username` is required")
        else:
            self.username = username
            self.name = name
        self.who_to_follow = who_to_follow

    def swap_direction(self):
        self.username, self.who_to_follow = self.who_to_follow, self.username

    def _parse_html(self):
        self.username = self._parse_username()
        self.name = self._parse_name()

    def _parse_username(self) -> str:
        link_title = self._html_data.find('a').eq(0).attr('title')
        if link_title:
            return str(link_title)
        else:
            raise ValueError('Username not found!')

    def _parse_name(self) -> str | None:
        href = self._html_data.find('a').eq(0).attr('href')
        if href:
            # /@someusername
            return href.split('/')[-1][1:]
        else:
            return None

    def __repr__(self):
        return f"Follower(username={self.username}, name={self.name}, who_following={self.who_to_follow})"

    def __str__(self):
        return (
            f"Follower username: {self.username}\n"
            f"\tName: {self.name}\n"
            f"\tWho Following: {self.who_to_follow}\n"
        )

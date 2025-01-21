from __future__ import annotations

from pyquery import PyQuery as pq
from datetime import datetime


class User:
    __slots__ = (
        "username",
        "name",
        "bio",
        "followers_num",
        "following_num",
        "location",
        "personal_site",
        "registration_date",
        "_html_data",
    )
    _html_data: pq
    username: str
    name: str
    bio: str | None
    followers_num: int
    following_num: int
    location: str | None
    personal_site: str | None
    registration_date: datetime | None

    def __init__(
        self,
        username: str | None = None,
        name: str | None = None,
        bio: str | None = "" ,
        followers_num: int = 0,
        following_num: int = 0,
        location: str | None = None,
        registration_date: datetime | None = None,
        personal_site: str | None = None,
        *,
        html_data: str | None = None,
    ):
        if html_data:
            self._html_data = pq(html_data)
            self._parse_html()
            return None
        if None in (username, name):
            raise ValueError("Username, name are required")
        self.username = username  # type: ignore
        self.name = name  # type: ignore
        self.bio = bio
        self.followers_num = followers_num
        self.following_num = following_num
        self.location = location  # type: ignore
        self.registration_date = registration_date  # type: ignore
        self.personal_site = personal_site

    def _parse_html(self):
        self.username = self._parse_username()
        self.name = self._parse_name()
        self.bio = self._parse_bio()
        self.followers_num = self._parse_followers_num()
        self.following_num = self._parse_following_num()
        self.location = self._parse_location()
        self.registration_date = self._parse_registration_date()
        self.personal_site = self._parse_personal_site()

    def _parse_username(self) -> str:
        username = str(self._html_data('p.truncate.truncate.text-sm.text-gray-700').text())
        username = username[1:]
        return username

    def _parse_personal_site(self) -> str | None:
        site = self._html_data('p.truncate.text-sm.text-gray-900'
                               '.font-medium.tracking-normal.font-sans.normal-case')
        return str(site.eq(0).text()) if site else None

    def _parse_name(self) -> str:
        name = str(self._html_data('p.leading-5.truncate').text())
        return name

    def _parse_bio(self) -> str | None:
        bio = self._html_data('p[data-markup="true"] p')
        bio = bio.text()
        return str(bio) if bio else None

    def _parse_followers_num(self) -> int:
        followers_link = self._html_data('a[class~="hover:underline"]').eq(0)
        followers = followers_link.attr("title").replace(",", "")
        return int(followers)

    def _parse_following_num(self) -> int:
        followers_link = self._html_data('a[class~="hover:underline"]').eq(1)
        followers = followers_link.attr("title").replace(",", "")
        return int(followers)

    def _parse_location(self) -> str | None:
        icons = self._html_data.find('div[data-testid="icon"]')
        for ico in icons.items():
            # This magic numbers is svg path for location icon
            if 'M17.657 16.657l-4.243' in str(ico.html()):
                return ico.next().text() or None
        return None

    def _parse_registration_date(self) -> datetime | None:
        fields = self._html_data(
            "div.flex.rtl\\:space-x-reverse.items-center.space-x-1"
        )
        for field in fields.items():
            if field.text().startswith("Joined"):
                date_text = field.text()
                return datetime.strptime(date_text[7:], "%B %Y")
        return None

    def __str__(self):
        return (
            f"Username: {self.username}\n"
            f"\tName: {self.name}\n"
            f"\tBio: {self.bio}\n"
            f"\tFollowers: {self.followers_num}\n"
            f"\tFollowing: {self.following_num}\n"
            f"\tLocation: {self.location}\n"
            f"\tRegistration Date: {self.registration_date}\n"
            f"\tPersonal Site: {self.personal_site}\n"
        )

    def __repr__(self):
        return self.__str__()

    def __hash__(self) -> int:
        return hash(self.username)

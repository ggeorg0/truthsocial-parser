# Truthsocial parser

The TruthSocial Parser is a Python tool designed to scrape data from TruthSocial.

The project leverages:
- Nodriver: For browser automation without a graphical interface.
- Asyncpg: To interact asynchronously with a PostgreSQL database.
- PyQuery: For lightweight HTML parsing and manipulation.

### TODO:
- [ ] Beautify this Readme
- [ ] Code:
    - [ ] Split `parser.py` by separate files `Parser` and `UserParser`.
    - Add continue method to continue from last parsed user.

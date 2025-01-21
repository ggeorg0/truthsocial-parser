# Truthsocial parser

The TruthSocial Parser is a Python tool designed to scrape data from TruthSocial.

The project leverages:
- Nodriver: For browser automation without a graphical interface.
- Asyncpg: To interact asynchronously with a PostgreSQL database.
- PyQuery: For lightweight HTML parsing and manipulation.

![image](https://github.com/user-attachments/assets/464f71fb-3c42-407a-b95e-80fad03fe865)


### TODO:
- [ ] Beautify this Readme
- [ ] Code:
    - [ ] Split `parser.py` by separate files `Parser` and `UserParser`.
    - Add continue method to continue from last parsed user.

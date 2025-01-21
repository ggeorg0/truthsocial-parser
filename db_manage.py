# Description: This CLI script is used to manage the database. It can be used to drop all tables in the database or create them.

import asyncio
import asyncpg
import os
import argparse
from dotenv import load_dotenv

load_dotenv()

DSN = os.getenv("DSN")

HELP_MSG = """
Use this script to initialize the database of the parser:

Usage:
    python db_manage.py [--drop] [--create] [--help]
"""

async def drop_tables():
    conn = await asyncpg.connect(DSN)
    print("This will delete all of your data. Are you sure you want to continue?")
    if input('Yes/no?: ') != 'Yes':
        print("Aborted.")
        return
    try:
        await conn.execute("DROP SCHEMA public CASCADE; CREATE SCHEMA public;")
        print("Tables dropped successfully.")
    finally:
        await conn.close()

async def create_tables():
    conn = await asyncpg.connect(DSN)
    try:
        with open('database.sql', 'r') as f:
            sql = f.read()
        await conn.execute(sql)
        print("Tables created successfully.")
    finally:
        await conn.close()

def main():
    parser = argparse.ArgumentParser(description="Manage parser database (create/drop).")
    parser.add_argument('--drop', action='store_true',
                        help="Drop all tables in the database.")
    parser.add_argument('--create', action='store_true',
                        help="(Re)create all tables in the database. Could be used with --drop")
    args = parser.parse_args()

    if args.drop:
        asyncio.run(drop_tables())
    if args.create:
        asyncio.run(create_tables())
    if not any(vars(args).values()):
        print(HELP_MSG)

if __name__ == "__main__":
    main()
import asyncio
import asyncpg

async def main():
    conn = await asyncpg.connect('postgresql://user:password@localhost:5432/postgres')
    try:
        await conn.execute('CREATE DATABASE agentforge_test')
        print("Database created")
    except asyncpg.exceptions.DuplicateDatabaseError:
        print("Database already exists")
    finally:
        await conn.close()

if __name__ == '__main__':
    asyncio.run(main())
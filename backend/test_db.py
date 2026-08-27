import asyncio
from config.database import execute, fetchrow
from uuid import uuid4

async def test():
    camp_id = uuid4()
    result = await execute(
        "INSERT INTO campaigns (id, user_id, name, github_repo_url) VALUES ($1, $2, $3, $4)",
        camp_id, '00000000-0000-0000-0000-000000000000', 'Test Campaign', 'https://github.com/test/repo'
    )
    print(f"Result: {result}")
    
    row = await fetchrow("SELECT * FROM campaigns WHERE id = $1", camp_id)
    print(f"Campaign: {dict(row)}")

asyncio.run(test())
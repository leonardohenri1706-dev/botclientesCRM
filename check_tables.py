import asyncpg
import asyncio

async def check_tables():
    conn = await asyncpg.connect('postgresql://neondb_owner:npg_bpxcrGBnq03N@ep-shiny-term-acdawm5r-pooler.sa-east-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require')
    
    tables = await conn.fetch("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'")
    for t in tables:
        print(t['table_name'])
    
    await conn.close()

asyncio.run(check_tables())
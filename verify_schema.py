import asyncpg
import asyncio

async def verify_schema():
    conn = await asyncpg.connect('postgresql://neondb_owner:npg_bpxcrGBnq03N@ep-shiny-term-acdawm5r-pooler.sa-east-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require')
    
    # Check columns for key tables
    for table in ['campaigns', 'leads', 'users']:
        cols = await conn.fetch(f"""
            SELECT column_name, data_type, is_nullable, column_default
            FROM information_schema.columns 
            WHERE table_name = '{table}' AND table_schema = 'public'
            ORDER BY ordinal_position
        """)
        print(f"\n=== {table} ===")
        for c in cols:
            print(f"  {c['column_name']}: {c['data_type']} nullable={c['is_nullable']} default={c['column_default']}")
    
    # Check functions
    funcs = await conn.fetch("""
        SELECT routine_name FROM information_schema.routines 
        WHERE routine_schema = 'public'
    """)
    print("\n=== Functions ===")
    for f in funcs:
        print(f"  {f['routine_name']}")
    
    # Check triggers
    triggers = await conn.fetch("""
        SELECT trigger_name, event_object_table, action_timing, event_manipulation
        FROM information_schema.triggers 
        WHERE trigger_schema = 'public'
    """)
    print("\n=== Triggers ===")
    for t in triggers:
        print(f"  {t['trigger_name']} on {t['event_object_table']} {t['action_timing']} {t['event_manipulation']}")
    
    await conn.close()

asyncio.run(verify_schema())
import asyncpg
import asyncio

async def add_functions_and_triggers():
    conn = await asyncpg.connect('postgresql://neondb_owner:npg_bpxcrGBnq03N@ep-shiny-term-acdawm5r-pooler.sa-east-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require')
    
    # Function to update updated_at
    await conn.execute("""
        CREATE OR REPLACE FUNCTION update_updated_at_column()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = NOW();
            RETURN NEW;
        END;
        $$ language 'plpgsql';
    """)
    print("Created update_updated_at_column function")
    
    # Triggers
    triggers = [
        ("update_campaigns_updated_at", "campaigns"),
        ("update_leads_updated_at", "leads"),
        ("update_github_analyses_updated_at", "github_analyses"),
        ("update_users_updated_at", "users"),
    ]
    
    for trigger_name, table in triggers:
        await conn.execute(f"""
            DROP TRIGGER IF EXISTS {trigger_name} ON {table};
            CREATE TRIGGER {trigger_name} BEFORE UPDATE ON {table}
                FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
        """)
        print(f"Created trigger {trigger_name} on {table}")
    
    # Kanban stats function
    await conn.execute("""
        CREATE OR REPLACE FUNCTION get_campaign_kanban_stats(campaign_uuid UUID)
        RETURNS TABLE (
            status VARCHAR(50),
            count BIGINT
        ) LANGUAGE sql SECURITY DEFINER AS $$
            SELECT 
                l.status,
                COUNT(*) as count
            FROM leads l
            WHERE l.campaign_id = campaign_uuid
            GROUP BY l.status
            ORDER BY 
                CASE l.status
                    WHEN 'NOVO' THEN 1
                    WHEN 'APRESENTADO' THEN 2
                    WHEN 'NEGOCIACAO' THEN 3
                    WHEN 'FECHADO' THEN 4
                    WHEN 'REJEITADO' THEN 5
                END;
        $$;
    """)
    print("Created get_campaign_kanban_stats function")
    
    # Insert default user
    await conn.execute("""
        INSERT INTO users (id, email, name) 
        VALUES ('00000000-0000-0000-0000-000000000000', 'dev@botclientes.local', 'Dev User')
        ON CONFLICT (id) DO NOTHING
    """)
    print("Inserted default user")
    
    await conn.close()
    print("Done!")

asyncio.run(add_functions_and_triggers())
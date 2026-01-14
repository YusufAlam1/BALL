import os
from dotenv import load_dotenv
from supabase import create_client, Client

# loads .env from the SAME directory as this file
load_dotenv()

url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_KEY")

print("URL loaded?", bool(url))
print("KEY loaded?", bool(key))

if not url or not key:
    raise ValueError("Env vars not loaded")

supabase: Client = create_client(url, key)
print("Client created")

response = supabase.table("your_table_name").select("*").limit(1).execute()
print("Data:", response.data)
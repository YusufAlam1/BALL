'''
Periodically (daily) executes a trivial query to prevent supabase from pausing due to inactivity
Used a GitHub Workflow to allow daily execution
'''

from connect import supabase

res = supabase.table("players").select("*").limit(1).execute()
print("Pinged Supabase")
if res.data:
    print(res.data[0])
else:
    print("Error occured")
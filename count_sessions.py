import json
from collections import Counter

path = '/Users/masa/forback/github/mirai_DB_backup/backup-2025-11-14T03-19-14.json'

def count_sessions():
    with open(path, 'r') as f:
        data = json.load(f)
        
    sessions = data.get('tables', {}).get('interview_sessions', [])
    slug_counts = Counter(s.get('slug') for s in sessions)
    
    print("Session counts per slug:")
    for slug, count in slug_counts.most_common():
        print(f"{slug}: {count}")

if __name__ == "__main__":
    count_sessions()

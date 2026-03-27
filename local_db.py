import json
import os
from datetime import datetime

DB_FILE = "monitored_pages.json"

def init_db():
    if not os.path.exists(DB_FILE):
        with open(DB_FILE, 'w', encoding='utf-8') as f:
            json.dump({"pages": [], "logs": []}, f, indent=4)
        print(f"Initialized local DB: {DB_FILE}")

def get_db():
    init_db()
    with open(DB_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_db(data):
    with open(DB_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

def add_page(name, url):
    db = get_db()
    # Check if exists
    if any(p['url'] == url for p in db['pages']):
        return False, "Page already exists"
    
    new_page = {
        "id": len(db['pages']) + 1,
        "name": name,
        "url": url,
        "status": "unknown",
        "last_check": None,
        "created_at": datetime.now().isoformat()
    }
    db['pages'].append(new_page)
    save_db(db)
    return True, new_page

def log_metrics(page_id, followers, posts_count, image_url):
    db = get_db()
    new_log = {
        "page_id": page_id,
        "timestamp": datetime.now().isoformat(),
        "followers": followers,
        "posts_count": posts_count,
        "image_url": image_url
    }
    db['logs'].append(new_log)
    save_db(db)
    return True

if __name__ == "__main__":
    # Test initialization
    init_db()
    success, msg = add_page("Facebook Thailand", "https://www.facebook.com/facebookthailand")
    print(f"Add Page Test: {success}, {msg}")

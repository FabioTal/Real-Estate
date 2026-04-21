import sqlite3, os

DB_PATH = os.path.join(os.path.dirname(__file__), 'properties.db')

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS listings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source TEXT,
            listing_id TEXT UNIQUE,
            title TEXT,
            price TEXT,
            location TEXT,
            size TEXT,
            description TEXT,
            image_url TEXT,
            listing_url TEXT,
            found_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            phone TEXT DEFAULT '',
            contact_type TEXT DEFAULT 'unknown',
            status TEXT DEFAULT ''
        )
    ''')
    # migrate existing DB — add columns if missing
    for col, default in [('phone', "''"), ('contact_type', "'unknown'"), ('status', "''")]:
        try:
            c.execute(f"ALTER TABLE listings ADD COLUMN {col} TEXT DEFAULT {default}")
            conn.commit()
        except:
            pass
    c.execute('''
        CREATE TABLE IF NOT EXISTS contacts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            phone_number TEXT UNIQUE,
            name TEXT,
            type TEXT DEFAULT 'unknown',
            post_count INTEGER DEFAULT 1,
            google_hits INTEGER DEFAULT 0,
            first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()
    print('Database ready.')

def save_listing(source, listing_id, title, price, location,
                 size, description, image_url, listing_url):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    try:
        c.execute('''
            INSERT INTO listings
            (source,listing_id,title,price,location,size,description,image_url,listing_url)
            VALUES (?,?,?,?,?,?,?,?,?)
        ''', (source,listing_id,title,price,location,size,description,image_url,listing_url))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

def update_listing_contact(listing_id, phone, contact_type, status=''):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        'UPDATE listings SET phone=?, contact_type=?, status=? WHERE listing_id=?',
        (phone, contact_type, status, listing_id)
    )
    conn.commit()
    conn.close()

def save_contact(phone_number, contact_type='unknown', google_hits=0):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    try:
        c.execute('''
            INSERT INTO contacts (phone_number, type, google_hits)
            VALUES (?, ?, ?)
        ''', (phone_number, contact_type, google_hits))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        c.execute('''
            UPDATE contacts SET post_count = post_count + 1,
            last_seen = CURRENT_TIMESTAMP, type = ?, google_hits = ?
            WHERE phone_number = ?
        ''', (contact_type, google_hits, phone_number))
        conn.commit()
        return False
    finally:
        conn.close()

def get_contact_type(phone_number):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT type FROM contacts WHERE phone_number = ?', (phone_number,))
    row = c.fetchone()
    conn.close()
    return row[0] if row else 'unknown'

def get_all_listings():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT * FROM listings ORDER BY found_at DESC')
    rows = c.fetchall()
    conn.close()
    return rows

def get_all_contacts():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT * FROM contacts ORDER BY last_seen DESC')
    rows = c.fetchall()
    conn.close()
    return rows

if __name__ == '__main__':
    init_db()

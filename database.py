import sqlite3
import datetime
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_NAME = os.path.join(BASE_DIR, "traffic_data.db")

def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS traffic_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            cars INTEGER,
            bikes INTEGER,
            buses INTEGER,
            trucks INTEGER,
            total_pcu REAL,
            signal_decision TEXT
        )
    """)

    conn.commit()
    conn.close()
    print("Database & Table Ready")

def log_data(counts, pcu, signal):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    c.execute("""
        INSERT INTO traffic_logs
        (timestamp, cars, bikes, buses, trucks, total_pcu, signal_decision)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        now,
        counts["cars"],
        counts["bikes"],
        counts["buses"],
        counts["trucks"],
        pcu,
        signal
    ))

    conn.commit()
    conn.close()
    print("Data Inserted")

def show_data():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    c.execute("SELECT * FROM traffic_logs")
    rows = c.fetchall()

    print("\nTraffic Logs\n")
    print("ID | Time | Cars | Bikes | Buses | Trucks | PCU | Signal")
    print("-"*65)

    for row in rows:
        print(row[0], "|", row[1], "|", row[2], "|", row[3], "|", row[4], "|", row[5], "|", row[6], "|", row[7])

    conn.close()

if __name__ == "__main__":
    init_db()

    sample_counts = {
        "cars": 20,
        "bikes": 15,
        "buses": 3,
        "trucks": 2
    }

    log_data(sample_counts, 45.5, "GREEN")

    show_data()
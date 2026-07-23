import os
import pandas as pd
import psycopg2
import psycopg2.extras

# Ensure your DATABASE_URL is set in your environment before running this!
DB_URL = os.environ.get('DATABASE_URL')

def get_db_connection():
    if not DB_URL:
        raise RuntimeError("DATABASE_URL environment variable is missing.")
    return psycopg2.connect(DB_URL)

def init_ceidg_table():
    conn = get_db_connection()
    cur = conn.cursor()
    
    # Keep this line so the previous table gets replaced
    cur.execute('DROP TABLE IF EXISTS ceidg_registry CASCADE;')
    
    # Recreate the table using TEXT to allow unlimited string lengths
    cur.execute('''
        CREATE TABLE IF NOT EXISTS ceidg_registry (
            nip VARCHAR(15) PRIMARY KEY,
            regon VARCHAR(20),
            nazwa_pod TEXT,
            imie TEXT,
            nazwisko TEXT,
            status TEXT, 
            miejscowosc TEXT
        );
    ''')
    
    cur.execute('CREATE INDEX IF NOT EXISTS idx_ceidg_nip ON ceidg_registry(nip);')
    
    conn.commit()
    cur.close()
    conn.close()
    print("Table ceidg_registry initialized successfully.")

def import_csv_files(folder_path):
    conn = get_db_connection()
    cur = conn.cursor()

    # Find all CSV files in the designated folder
    csv_files = [f for f in os.listdir(folder_path) if f.endswith('.csv')]
    print(f"Found {len(csv_files)} files to process.")

    for file_name in csv_files:
        file_path = os.path.join(folder_path, file_name)
        print(f"Processing {file_name}...")
        
        # Read the file in chunks of 10,000 rows to prevent memory crashes
        # Adjust the delimiter (sep) if your Excel exports used a comma instead of a semicolon
        chunk_iterator = pd.read_csv(file_path, sep=';', dtype=str, chunksize=10000)
        
        for chunk in chunk_iterator:
            # Clean up the NIP column (remove dashes/spaces and drop empty NIPs)
            chunk['Nip'] = chunk['Nip'].astype(str).str.replace(r'\D', '', regex=True)
            chunk = chunk[chunk['Nip'] != '']
            chunk = chunk.dropna(subset=['Nip'])

            # Extract only the columns we mapped in the database
            # We use .get to prevent crashes if a column name is slightly different
            records = chunk[[
                'Nip', 'Regon', 'NazwaPodmiotu', 'Imie', 'Nazwisko', 'StatusDzialalnosci', 'Miejscowosc'
            ]].values.tolist()

            # Bulk insert using ON CONFLICT DO NOTHING to ignore duplicate NIPs across files
            insert_query = '''
                INSERT INTO ceidg_registry (nip, regon, nazwa_pod, imie, nazwisko, status, miejscowosc)
                VALUES %s
                ON CONFLICT (nip) DO NOTHING;
            '''
            
            psycopg2.extras.execute_values(cur, insert_query, records, page_size=10000)
            conn.commit()
            
        print(f"Finished {file_name}")

    cur.close()
    conn.close()
    print("All files imported successfully!")

if __name__ == '__main__':
    init_ceidg_table()
    # Assuming you put the 15 CSVs in a folder called 'ceidg_data' next to this script
    import_csv_files('./ceidg_data')
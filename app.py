from flask import Flask, render_template, request, redirect, url_for, jsonify
import psycopg2
import psycopg2.extras
import os
from datetime import datetime, date
import requests
from company_search import company_bp

app = Flask(__name__)
app.register_blueprint(company_bp)

# Dynamically find the absolute path to this folder
THIS_FOLDER = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(THIS_FOLDER, 'accounting.db')

def get_db_connection():
    db_url = os.environ.get('DATABASE_URL')
    if not db_url:
        raise RuntimeError("DATABASE_URL environment variable is missing in Render settings.")
    
    conn = psycopg2.connect(db_url)
    return conn

def init_db():
    conn = get_db_connection()
    cur = conn.cursor()
    
    # Initialize Sales Table
    cur.execute('''
        CREATE TABLE IF NOT EXISTS sales (
            id SERIAL PRIMARY KEY,
            document_number VARCHAR(100),
            nip VARCHAR(50),
            document_date VARCHAR(50),
            net_amount REAL,
            vat_rate REAL,
            vat_amount REAL,
            gross_amount REAL,
            kpir_category VARCHAR(100)
        );
    ''')
    
    # Initialize Purchases Table
    cur.execute('''
        CREATE TABLE IF NOT EXISTS purchases (
            id SERIAL PRIMARY KEY,
            document_number VARCHAR(100),
            nip VARCHAR(50),
            document_date VARCHAR(50),
            net_amount REAL,
            vat_rate REAL,
            vat_amount REAL,
            gross_amount REAL,
            kpir_category VARCHAR(100)
        );
    ''')

    # Initialize Contractors Table
    cur.execute('''
        CREATE TABLE IF NOT EXISTS contractors (
            id SERIAL PRIMARY KEY,
            nip VARCHAR(50),
            name VARCHAR(255),
            ksef_id VARCHAR(100)
        );
    ''')
    
    conn.commit()
    cur.close()
    conn.close()

# Run the initialization function on startup
init_db()


@app.route('/', methods=('GET', 'POST'))
def index():
    conn = get_db_connection()

    if request.method == 'POST':
        # Grab the data submitted from the HTML form
        doc_num = request.form['document_number']
        nip = request.form['nip']
        date = request.form['document_date']
        net = float(request.form['net_amount'])
        vat_rate = float(request.form['vat_rate'])
        category = request.form['kpir_category']

        try:
            # 1. Validate Date Format (will throw ValueError if it fails)
            valid_date = datetime.strptime(date, '%Y/%m/%d')

            # 2. Validate VAT Rate
            allowed_vat_rates = [0.23, 0.08, 0.05, 0.00]
            if vat_rate not in allowed_vat_rates:
                raise ValueError("Niedozwolona stawka VAT (Invalid VAT rate).")

        except ValueError as e:
            # If validation fails, abort the save and return an error message to the browser
            return f"Data Validation Error: {e}. Please use your browser's back button and try again.", 400

        # Calculate VAT amount and Gross amount
        vat_amount = net * vat_rate
        gross = net + vat_amount

        # Insert the new record using a standard cursor
        cur = conn.cursor()
        cur.execute('''
            INSERT INTO sales (document_number, nip, document_date, net_amount, vat_rate, vat_amount, gross_amount, kpir_category)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        ''', (doc_num, nip, date, net, vat_rate, vat_amount, gross, category))
        conn.commit()
        cur.close()

        # Redirect prevents form resubmission if the user refreshes the page
        return redirect(url_for('index'))

    # Fetch all records from the sales table using the Dictionary Cursor
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute('SELECT * FROM sales ORDER BY id DESC')
    sales_records = cur.fetchall()
    cur.close()
    conn.close()

    # Pass the records to the HTML template
    return render_template('index.html', sales=sales_records)


@app.route('/purchases', methods=('GET', 'POST'))
def purchases():
    conn = get_db_connection()

    if request.method == 'POST':
        # Grab the data submitted from the HTML form
        doc_num = request.form['document_number']
        nip = request.form['nip']
        date = request.form['document_date']
        net = float(request.form['net_amount'])
        vat_rate = float(request.form['vat_rate'])
        category = request.form['kpir_category']

        try:
            # 1. Validate Date Format (will throw ValueError if it fails)
            valid_date = datetime.strptime(date, '%Y/%m/%d')

            # 2. Validate VAT Rate
            allowed_vat_rates = [0.23, 0.08, 0.05, 0.00]
            if vat_rate not in allowed_vat_rates:
                raise ValueError("Niedozwolona stawka VAT (Invalid VAT rate).")

        except ValueError as e:
            # If validation fails, abort the save and return an error message to the browser
            return f"Data Validation Error: {e}. Please use your browser's back button and try again.", 400

        # Calculate VAT amount and Gross amount
        vat_amount = net * vat_rate
        gross = net + vat_amount

        # Insert the new record into the purchases table
        cur = conn.cursor()
        cur.execute('''
            INSERT INTO purchases (document_number, nip, document_date, net_amount, vat_rate, vat_amount, gross_amount, kpir_category)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        ''', (doc_num, nip, date, net, vat_rate, vat_amount, gross, category))
        conn.commit()
        cur.close()

        # Redirect to prevent form resubmission
        return redirect(url_for('purchases'))

    # Fetch all records from the purchases table
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute('SELECT * FROM purchases ORDER BY id DESC')
    purchases_records = cur.fetchall()
    cur.close()

    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute('SELECT nip, name FROM contractors ORDER BY name ASC')
    contractors_list = cur.fetchall()
    cur.close()

    conn.close()

    # Pass the records to the purchases HTML template
    return render_template('purchases.html', purchases=purchases_records, contractors=contractors_list)


@app.route('/kpir')
def kpir():
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    
    cur.execute('SELECT document_date, net_amount, kpir_category FROM sales')
    sales = cur.fetchall()
    
    cur.execute('SELECT document_date, net_amount, kpir_category FROM purchases')
    purchases = cur.fetchall()
    
    cur.close()
    conn.close()

    # Determine current operational year dynamically from data (defaulting to 2026)
    year = "2026"
    for row in sales + purchases:
        if row['document_date']:
            year = row['document_date'][:4]
            break

    # Bilingual month name mapping to match your exact spreadsheet design
    month_names = {
        "01": "Styczeń (January)",
        "02": "Luty (February)",
        "03": "Marzec (March)",
        "04": "Kwiecień (April)",
        "05": "Maj (May)",
        "06": "Czerwiec (June)",
        "07": "Lipiec (July)",
        "08": "Sierpień (August)",
        "09": "Wrzesień (September)",
        "10": "Październik (October)",
        "11": "Listopad (November)",
        "12": "Grudzień (December)"
    }

    kpir_months = []

    # Running tracking variables for cumulative calculation rows
    cum_sales_goods = 0.0
    cum_other_rev = 0.0
    cum_materials = 0.0
    cum_incidental = 0.0
    cum_payroll = 0.0
    cum_other_exp = 0.0

    # Explicitly loop over all 12 calendar months sequentially
    for m_num in sorted(month_names.keys()):
        month_str = f"{year}/{m_num}"

        # Fresh baseline tallies for this single month
        sales_goods = 0.0
        other_rev = 0.0
        materials = 0.0
        incidental_costs = 0.0
        payroll = 0.0
        other_expenses = 0.0

        # Calculate monthly revenue entries
        for row in sales:
            if row['document_date'][:7] == month_str:
                if row['kpir_category'] == 'Sprzedaż towarów':
                    sales_goods += row['net_amount']
                elif row['kpir_category'] == 'Pozostałe przychody':
                    other_rev += row['net_amount']

        # Calculate monthly cost entries
        for row in purchases:
            if row['document_date'][:7] == month_str:
                if row['kpir_category'] == 'Zakup materiałów':
                    materials += row['net_amount']
                elif row['kpir_category'] == 'Koszty dodatkowe':
                    incidental_costs += row['net_amount']
                elif row['kpir_category'] == 'Koszty wynagrodzeń':
                    payroll += row['net_amount']
                elif row['kpir_category'] == 'Pozostałe wydatki':
                    other_expenses += row['net_amount']

        # Build running cumulative calculations
        cum_sales_goods += sales_goods
        cum_other_rev += other_rev
        cum_materials += materials
        cum_incidental += incidental_costs
        cum_payroll += payroll
        cum_other_exp += other_expenses

        # 1. Append the Standard Monthly row
        kpir_months.append({
            'name': month_names[m_num],
            'type': 'monthly',
            'sales_goods': sales_goods,
            'other_rev': other_rev,
            'materials': materials,
            'incidental_costs': incidental_costs,
            'payroll': payroll,
            'other_expenses': other_expenses
        })

        # 2. Append the immediately following Cumulative row
        kpir_months.append({
            'name': 'Łączny (Cumulative)',
            'type': 'cumulative',
            'sales_goods': cum_sales_goods,
            'other_rev': cum_other_rev,
            'materials': cum_materials,
            'incidental_costs': cum_incidental,
            'payroll': cum_payroll,
            'other_expenses': cum_other_exp
        })

    # 3. Formulate the absolute Grand Total row dictionary
    grand_total = {
        'name': 'CAŁKOWITY (TOTAL)',
        'sales_goods': cum_sales_goods,
        'other_rev': cum_other_rev,
        'materials': cum_materials,
        'incidental_costs': cum_incidental,
        'payroll': cum_payroll,
        'other_expenses': cum_other_exp
    }

    return render_template('kpir.html', kpir_months=kpir_months, grand_total=grand_total)


@app.route('/search', methods=('GET', 'POST'))
def search():
    conn = get_db_connection()

    # Initialize empty lists to hold our results
    results_sales = []
    results_purchases = []
    search_nip = ''

    if request.method == 'POST':
        # Grab the NIP entered in the search bar
        search_nip = request.form['nip_search']

        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        # Query the sales table for this exact NIP
        cur.execute(
            'SELECT * FROM sales WHERE nip = %s ORDER BY document_date DESC',
            (search_nip,)
        )
        results_sales = cur.fetchall()

        # Query the purchases table for this exact NIP
        cur.execute(
            'SELECT * FROM purchases WHERE nip = %s ORDER BY document_date DESC',
            (search_nip,)
        )
        results_purchases = cur.fetchall()
        
        cur.close()

    conn.close()

    # Pass the results back to the template
    return render_template(
        'search.html',
        sales=results_sales,
        purchases=results_purchases,
        search_nip=search_nip
    )


@app.route('/contractors', methods=('GET', 'POST'))
def contractors():
    conn = get_db_connection()

    if request.method == 'POST':
        nip = request.form['nip']
        name = request.form['name']
        ksef_id = request.form['ksef_id']

        cur = conn.cursor()
        # Insert the new contractor into the database
        cur.execute('''
            INSERT INTO contractors (nip, name, ksef_id)
            VALUES (%s, %s, %s)
        ''', (nip, name, ksef_id))
        conn.commit()
        cur.close()
        
        return redirect(url_for('contractors'))

    # Fetch all saved contractors
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute('SELECT * FROM contractors ORDER BY name ASC')
    contractors_records = cur.fetchall()
    cur.close()
    conn.close()

    return render_template('contractors.html', contractors=contractors_records)

@app.route('/delete-sale/<int:id>', methods=['POST'])
def delete_sale(id):
    conn = get_db_connection()
    cur = conn.cursor()
    
    # Execute the SQL command to delete the row matching the unique ID
    cur.execute('DELETE FROM sales WHERE id = %s', (id,))
    conn.commit()
    
    cur.close()
    conn.close()
    return redirect(url_for('index'))

@app.route('/delete-purchase/<int:id>', methods=['POST'])
def delete_purchase(id):
    conn = get_db_connection()
    cur = conn.cursor()
    
    # Execute the SQL command to delete the row matching the unique ID
    cur.execute('DELETE FROM purchases WHERE id = %s', (id,))
    conn.commit()
    
    cur.close()
    conn.close()
    return redirect(url_for('purchases'))


@app.route('/api/lookup-nip/<nip>')
def lookup_nip(nip):
    # Strip any dashes or spaces from the NIP
    clean_nip = nip.replace("-", "").replace(" ", "").strip()

    # The API requires the current date for the search
    today = date.today().strftime('%Y-%m-%d')
    url = f"https://wl-api.mf.gov.pl/api/search/nip/{clean_nip}?date={today}"

    try:
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            # Check if the API returned a valid subject
            if data.get('result') and data['result'].get('subject'):
                company_name = data['result']['subject']['name']
                return jsonify({"success": True, "name": company_name})

        return jsonify({"success": False, "error": "Nie znaleziono (Not found or invalid NIP)."})
    except Exception as e:
        return jsonify({"success": False, "error": "Błąd serwera (Server error)."})

if __name__ == '__main__':
    app.run(debug=True)

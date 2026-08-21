# Polish Tax Ledger & Contractor Management (KPiR)

A robust, full-stack web application designed to streamline Polish accounting (Księga Przychodów i Rozchodów - KPiR) operations. Built with Flask and PostgreSQL, this application automates sales and purchase registries, dynamically calculates VAT, and features a highly fault-tolerant government API integration to instantly retrieve and verify company details.

## 🚀 Key Features

* **Automated KPiR Calculations:** Automatically categorizes transactions and generates real-time cumulative monthly profit/loss summaries.
* **Sales & Purchase Ledgers:** Streamlined document entry with dynamic sequential auto-numbering (e.g., `FV 1/08/2026`) and built-in mathematics for net, VAT, and gross amounts.
* **Intelligent Company Search:** Seamlessly fetches contractor data using NIP or KRS numbers through a multi-tiered fallback architecture.
* **Contractor Database:** Save verified entities locally alongside optional KSeF IDs for rapid document generation.
* **Responsive UI:** A clean, high-contrast, data-dense interface built with custom CSS for maximum scannability and ease of use.

## 🛠️ Tech Stack

* **Backend:** Python 3, Flask, `psycopg2`
* **Database:** PostgreSQL
* **Frontend:** HTML5, CSS3 (Jinja2 Templating)
* **External APIs:** `requests`, `RegonAPI`
* **Deployment Integration:** Configured for WSGI hosting (e.g., Render, Gunicorn)

## 📡 API Integrations & Fallback Logic

The application features a resilient company lookup system that queries official Polish government databases in sequence to ensure high hit rates, even for VAT-exempt entities:

1. **Biała Lista (Ministry of Finance):** Initial check for active VAT taxpayers.
2. **Krajowy Rejestr Sądowy (KRS):** Open data retrieval for registered corporations.
3. **GUS REGON (BIR1.1):** Primary fallback for VAT-exempt NGOs and LLCs (requires API key).
4. **CEIDG (Local DB Sync):** Final fallback for Sole Proprietorships (Jednoosobowa Działalność Gospodarcza).

## 💻 Local Setup & Installation

**1. Clone the repository**

```bash
git clone https://github.com/deonyamwanza1-cmyk/WebApp.git
cd WebApp

```

**2. Create and activate a virtual environment**

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS/Linux
python3 -m venv venv
source venv/bin/activate

```

**3. Install dependencies**

```bash
pip install -r requirements.txt

```

**4. Configure Environment Variables**
Create a `.env` file in the root directory (or export them in your terminal) with the following keys:

```env
DATABASE_URL=postgresql://user:password@localhost:5432/your_database
REGON_API_KEY=your_gus_regon_key  # Use abcde12345abcde12345 for sandbox testing
CEIDG_API_KEY=your_ceidg_key      # Optional

```

**5. Initialize the Database & Run the App**
The database tables (`sales`, `purchases`, `contractors`) will initialize automatically on the first run.

```bash
python app.py

```

*The application will be available at `[http://127.0.0.1:5000](http://127.0.0.1:5000)*`

## 📝 Usage Notes

* **Testing GUS REGON:** If using the universal test key, set `REGON_IS_PRODUCTION = False` in `company_search.py`. Search for sandbox NIPs like `8992689516` or `0684711351` to simulate successful data retrieval. For real NIP searches, a valid production key is required.

## 👤 Author

**Deon Tanaka Nyamwanza**

* GitHub: [@deonyamwanza1-cmyk](https://www.google.com/search?q=https://github.com/deonyamwanza1-cmyk)

"""
company_search.py
==================
Modul Flask (Blueprint) do wyszukiwania pelnych danych o firmie po numerze
NIP, laczacy KILKA oficjalnych, panstwowych rejestrow Polski:

  1. Biala Lista Podatnikow VAT (Ministerstwo Finansow)
     - dziala od razu, BEZ klucza API
     - zrodlo: https://wl-api.mf.gov.pl/

  2. Krajowy Rejestr Sadowy - KRS (Ministerstwo Sprawiedliwosci)
     - dziala od razu, BEZ klucza API (otwarte dane)
     - pobiera odpis aktualny na podstawie numeru KRS
       (numer KRS otrzymujemy automatycznie z Bialej Listy)
     - zrodlo: https://api-krs.ms.gov.pl/

  3. GUS REGON - BIR1.1 (Glowny Urzad Statystyczny)
     - WYMAGA bezplatnego klucza API (patrz sekcja KONFIGURACJA nizej)
     - dopoki klucz nie jest ustawiony, ta sekcja jest pomijana
     - zrodlo: https://api.stat.gov.pl/Home/RegonApi

  4. CEIDG (dla jednoosobowych dzialalnosci gospodarczych)
     - WYMAGA bezplatnego klucza API (patrz sekcja KONFIGURACJA nizej)
     - dopoki klucz nie jest ustawiony, ta sekcja jest pomijana
     - zrodlo: https://dane.biznes.gov.pl/

--------------------------------------------------------------------
JAK ZINTEGROWAC Z ISTNIEJACYM PROJEKTEM FLASK:
--------------------------------------------------------------------
1. Skopiuj ten plik do katalogu projektu jako company_search.py
2. Skopiuj plik search_company.html do katalogu templates/
3. W glownym pliku (np. flask_app.py) dodaj:

       from company_search import company_bp
       app.register_blueprint(company_bp)

4. Zainstaluj wymagane biblioteki:
       pip3.x install --user requests RegonAPI

5. (Opcjonalnie, dla pelnych danych) uzupelnij ponizej klucze API:
       REGON_API_KEY  - klucz z https://api.stat.gov.pl/Home/RegonApi
       CEIDG_API_KEY  - klucz z https://dane.biznes.gov.pl/

6. Kliknij "Reload" w panelu PythonAnywhere.
--------------------------------------------------------------------
Strona bedzie dostepna pod adresem: /szukaj
--------------------------------------------------------------------
"""

import re
from datetime import date

import requests
from flask import Blueprint, render_template, request

company_bp = Blueprint(
    "company_search",
    __name__,
    template_folder="templates",
)

# ======================================================================
# KONFIGURACJA - wpisz tutaj swoje klucze, gdy je otrzymasz
# ======================================================================
REGON_API_KEY = ""   # np. "a1b2c3d4e5f6g7h8i9j0"  -> zostaw puste, by pominac
CEIDG_API_KEY = ""   # np. "eyJhbGciOiJI..."        -> zostaw puste, by pominac
REGON_IS_PRODUCTION = False  # ustaw True po otrzymaniu klucza produkcyjnego
# ======================================================================


# ----------------------------------------------------------------------
# Funkcje pomocnicze
# ----------------------------------------------------------------------

def wyczysc_numer(surowy: str) -> str:
    """Usuwa spacje, myslniki itp. - zostawia same cyfry."""
    return re.sub(r"\D", "", surowy or "")


def czy_poprawny_nip(nip: str) -> bool:
    return bool(re.fullmatch(r"\d{10}", nip))


# ----------------------------------------------------------------------
# 1) Biala Lista Podatnikow VAT - bez klucza, dziala od razu
# ----------------------------------------------------------------------

def pobierz_z_bialej_listy(nip: str):
    """Zwraca (dane_slownik, blad)."""
    url = f"https://wl-api.mf.gov.pl/api/search/nip/{nip}"
    try:
        odp = requests.get(url, params={"date": date.today().isoformat()}, timeout=10)
    except requests.RequestException:
        return None, "Brak polaczenia z Biala Lista VAT."

    if odp.status_code != 200:
        return None, None  # po prostu brak danych, nie traktujemy jako blad krytyczny

    podmiot = odp.json().get("result", {}).get("subject")
    return podmiot, None


# ----------------------------------------------------------------------
# 2) KRS - otwarte API, bez klucza
# ----------------------------------------------------------------------

def pobierz_z_krs(numer_krs: str):
    """
    Pobiera odpis aktualny z otwartego API Ministerstwa Sprawiedliwosci.
    Zwraca (dane_slownik, blad).
    """
    numer_krs = numer_krs.zfill(10)  # KRS ma 10 cyfr, z wiodacymi zerami
    url = f"https://api-krs.ms.gov.pl/api/krs/OdpisAktualny/{numer_krs}"
    try:
        odp = requests.get(url, params={"rejestr": "P", "format": "json"}, timeout=10)
    except requests.RequestException:
        return None, "Brak polaczenia z API KRS."

    if odp.status_code != 200:
        return None, None

    try:
        return odp.json(), None
    except ValueError:
        return None, None


def wyciagnij_dane_krs(surowe_krs: dict) -> dict:
    """
    Odpis z KRS ma zlozona, zagniezdzona strukture, ktora rozni sie
    w zaleznosci od formy prawnej podmiotu. Ponizej wyciagamy
    najwazniejsze pola w sposob 'defensywny' (bez wyjatkow, jesli
    ktoregos pola brakuje).
    """
    wynik = {}
    try:
        dane = surowe_krs.get("odpis", {}).get("dane", {})
        dzial1 = dane.get("dzial1", {})

        nazwa = (
            dzial1.get("danePodmiotu", {}).get("nazwa")
            or dzial1.get("danePodmiotu", {}).get("nazwaSkr")
        )
        if nazwa:
            wynik["Nazwa (KRS)"] = nazwa

        siedziba = dzial1.get("siedzibaIAdres", {}).get("adres", {})
        if siedziba:
            czesci = [
                siedziba.get("ulica", ""),
                siedziba.get("nrDomu", ""),
                siedziba.get("miejscowosc", ""),
                siedziba.get("kodPocztowy", ""),
            ]
            wynik["Adres (KRS)"] = " ".join(c for c in czesci if c)

        kapital = dane.get("dzial1", {}).get("kapital", {}).get("wysokoscKapitaluZakladowego")
        if kapital:
            wynik["Kapital zakladowy"] = kapital

        dzial2 = dane.get("dzial2", {})
        reprezentacja = dzial2.get("reprezentacja", {}).get("sklad", [])
        if reprezentacja:
            osoby = []
            for osoba in reprezentacja:
                dane_osoby = osoba.get("osoba", {})
                imie = dane_osoby.get("imiona", [""])[0] if dane_osoby.get("imiona") else ""
                nazwisko = dane_osoby.get("nazwisko", "")
                funkcja = osoba.get("funkcjaWOrganie", "")
                if imie or nazwisko:
                    osoby.append(f"{imie} {nazwisko} ({funkcja})".strip())
            if osoby:
                wynik["Reprezentacja"] = "; ".join(osoby)

    except Exception:
        pass

    return wynik


# ----------------------------------------------------------------------
# 3) GUS REGON - wymaga klucza API
# ----------------------------------------------------------------------

def pobierz_z_regon(nip: str):
    """Zwraca (dane_slownik, blad). Pomija, jesli brak klucza."""
    if not REGON_API_KEY:
        return None, "pominieto (brak klucza API GUS)"

    try:
        from RegonAPI import RegonAPI
        from RegonAPI.exceptions import ApiAuthenticationError
    except ImportError:
        return None, "biblioteka RegonAPI nie jest zainstalowana"

    try:
        api = RegonAPI(bir_version="bir1.1", is_production=REGON_IS_PRODUCTION, timeout=10)
        api.authenticate(key=REGON_API_KEY)
        wyniki = api.searchData(nip=nip)
    except ApiAuthenticationError:
        return None, "bledny klucz API GUS"
    except Exception as e:
        return None, f"blad GUS REGON: {e}"

    if not wyniki:
        return None, None

    return wyniki[0], None


# ----------------------------------------------------------------------
# 4) CEIDG - wymaga klucza API
# ----------------------------------------------------------------------

def pobierz_z_ceidg(nip: str):
    """Zwraca (dane_slownik, blad). Pomija, jesli brak klucza."""
    if not CEIDG_API_KEY:
        return None, "pominieto (brak klucza API CEIDG)"

    url = "https://dane.biznes.gov.pl/api/ceidg/v2/firmy"
    headers = {"Authorization": f"Bearer {CEIDG_API_KEY}"}
    try:
        odp = requests.get(url, params={"nip": nip}, headers=headers, timeout=10)
    except requests.RequestException:
        return None, "brak polaczenia z CEIDG"

    if odp.status_code != 200:
        return None, None

    dane = odp.json().get("firmy", [])
    if not dane:
        return None, None

    return dane[0], None


# ----------------------------------------------------------------------
# Glowny widok
# ----------------------------------------------------------------------

@company_bp.route("/szukaj", methods=["GET", "POST"])
def szukaj():
    wpisany_numer = ""
    blad_glowny = None

    wynik_vat = None
    wynik_krs = None
    wynik_regon = None
    wynik_ceidg = None

    info_regon = None
    info_ceidg = None

    if request.method == "POST":
        wpisany_numer = request.form.get("numer", "")
        nip = wyczysc_numer(wpisany_numer)

        if not czy_poprawny_nip(nip):
            blad_glowny = "Wprowadz poprawny 10-cyfrowy numer NIP."
        else:
            # 1) Biala Lista VAT - zawsze probujemy
            wynik_vat, _ = pobierz_z_bialej_listy(nip)

            # 2) Jesli Biala Lista zwrocila numer KRS - pobieramy pelny odpis
            if wynik_vat and wynik_vat.get("krs"):
                surowe_krs, _ = pobierz_z_krs(wynik_vat["krs"])
                if surowe_krs:
                    wynik_krs = wyciagnij_dane_krs(surowe_krs)

            # 3) GUS REGON (jesli klucz skonfigurowany)
            wynik_regon, info_regon = pobierz_z_regon(nip)

            # 4) CEIDG (jesli klucz skonfigurowany)
            wynik_ceidg, info_ceidg = pobierz_z_ceidg(nip)

            if not any([wynik_vat, wynik_krs, wynik_regon, wynik_ceidg]):
                blad_glowny = "Nie znaleziono danych dla podanego NIP w dostepnych rejestrach."

    return render_template(
        "search_company.html",
        wpisany_numer=wpisany_numer,
        blad_glowny=blad_glowny,
        wynik_vat=wynik_vat,
        wynik_krs=wynik_krs,
        wynik_regon=wynik_regon,
        wynik_ceidg=wynik_ceidg,
        info_regon=info_regon,
        info_ceidg=info_ceidg,
    )


if __name__ == "__main__":
    from flask import Flask

    app = Flask(__name__)
    app.register_blueprint(company_bp)
    app.run(debug=True)

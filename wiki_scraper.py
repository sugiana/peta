import requests
from bs4 import BeautifulSoup
import json

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 "
        "Safari/537.36")
    }


def scrape_tangerang_data(url):
    print(f"Fetching {url}...")
    try:
        response = requests.get(url, headers=HEADERS)
        response.raise_for_status()
    except Exception as e:
        print(f"Error fetching page: {e}")
        return

    soup = BeautifulSoup(response.text, 'html.parser')

    # Find the table containing "Kecamatan" data
    # Wikipedia tables usually have class 'wikitable'
    tables = soup.find_all('table', class_='wikitable')

    target_table = None
    for table in tables:
        # Look for headers that match what we expect
        # Use " " as separator to handle potential <br> or newlines
        headers_text = [
            th.get_text(" ", strip=True) for th in table.find_all('th')]

        # Check if "Kode" and "Kecamatan" and "Status" are in the headers
        # Use partial matches to be robust against references like [13]
        has_kode = any("Kode" in h and "Kemendagri" in h for h in headers_text)
        has_kecamatan = any(
            "Kecamatan" == h or "Kecamatan" in h for h in headers_text)
        has_status = any("Status" == h for h in headers_text)

        if has_kode and has_kecamatan and has_status:
            target_table = table
            break

    if not target_table:
        print("Could not find the target table.")
        # Debug: print headers of all tables found
        for idx, table in enumerate(tables):
            h = [
                th.get_text(" ", strip=True)
                for th in table.find_all('th')][:5]
            print(f"Table {idx} first 5 headers: {h}")
        return

    data = []
    rows = target_table.find_all('tr')[1:]  # Skip header row

    current_kecamatan = None

    # We need to handle rowspans.
    # When a row has rowspan, those cells are omitted in subsequent <tr>
    # elements. However, for this specific Wikipedia table, the first row of a
    # district has all the info, and the second row (if it exists) only has
    # Status and Daftar.

    i = 0
    while i < len(rows):
        row = rows[i]
        cells = row.find_all(['td', 'th'])

        # Check for first row of a kecamatan (it usually has more cells or the
        # first cell is the code)
        if len(cells) >= 6:
            kode = cells[0].get_text(strip=True)
            nama_kec = cells[1].get_text(strip=True)
            ibu_kota = cells[2].get_text(strip=True)
            jml_kel = cells[3].get_text(strip=True)
            jml_desa = cells[4].get_text(strip=True)
            kodepos = cells[5].get_text(strip=True)

            # The next two cells are Status and Daftar
            status_cell = cells[-2]
            daftar_cell = cells[-1]

            status_label = status_cell.get_text(strip=True)
            item_list = []
            if daftar_cell.find('div', class_='hlist'):
                item_list = [
                    li.get_text(strip=True)
                    for li in daftar_cell.find_all('li')]
            else:
                # Fallback if hlist isn't used
                item_list = [
                    x.strip() for x in daftar_cell.get_text(',').split(',')
                    if x.strip()]

            kecamatan_entry = {
                "kode": kode,
                "nama": nama_kec,
                "ibu_kota": ibu_kota,
                "jumlah_kelurahan": jml_kel,
                "jumlah_desa": jml_desa,
                "kodepos": kodepos,
                "detail": {
                    status_label: item_list
                }
            }

            # Check if this row has a rowspan on the first cell
            if cells[0].has_attr('rowspan'):
                rowspan_val = int(cells[0]['rowspan'])
                # Consume subsequent rows for this kecamatan
                for r_idx in range(1, rowspan_val):
                    i += 1
                    if i < len(rows):
                        next_row = rows[i]
                        next_cells = next_row.find_all(['td', 'th'])
                        # In the second row of a rowspan group, cells[0] is
                        # Status, cells[1] is Daftar
                        if len(next_cells) >= 2:
                            next_status = next_cells[0].get_text(strip=True)
                            next_daftar_cell = next_cells[1]

                            next_item_list = []
                            if next_daftar_cell.find('div', class_='hlist'):
                                next_item_list = [
                                    li.get_text(strip=True)
                                    for li in next_daftar_cell.find_all('li')]
                            else:
                                next_item_list = [
                                    x.strip()
                                    for x in next_daftar_cell.get_text(',').
                                    split(',') if x.strip()]

                            kecamatan_entry["detail"][next_status] = \
                                next_item_list

            data.append(kecamatan_entry)

        i += 1

    # Output the result
    for entry in data:
        print(f"Kecamatan: {entry['nama']} ({entry['kode']})")
        for status, items in entry['detail'].items():
            print(f"  {status} ({len(items)}): {', '.join(items)}")
        print("-" * 20)

    # Save to JSON for easier verification
    with open('wiki.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print("\nData saved to wiki.json")


if __name__ == "__main__":
    import sys
    url = sys.argv[1]
    scrape_tangerang_data(url)

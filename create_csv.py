import requests
from bs4 import BeautifulSoup
import pandas as pd
import datetime as dt
import re
import os


def fetch_event_location_from_detail_page(
    url: str, session: requests.Session
) -> str | None:
    """Fetch location from event detail page's Veranstaltungsort section."""
    try:
        resp = session.get(url, timeout=15)
        if resp.status_code != 200:
            return None
        soup = BeautifulSoup(resp.content, "html.parser")
        # Look for the "Veranstaltungsort" section
        headings = soup.find_all(["h3", "h4"])
        for heading in headings:
            if heading.get_text(strip=True) == "Veranstaltungsort":
                # Get parent div's full text and extract location
                parent = heading.parent
                if parent:
                    full_text = parent.get_text("|", strip=True)
                    # Split by | and remove the heading, Deutschland, and empty parts
                    parts = [
                        p.strip()
                        for p in full_text.split("|")
                        if p.strip()
                        and p.strip() not in ["Veranstaltungsort", "Deutschland", ","]
                    ]
                    if parts:
                        return ", ".join(parts)
        return None
    except Exception:
        return None


def fetch_events():
    """Fetch events from the calendar website."""
    base_url = "https://www.aiterhofen.de/veranstaltungen/"
    session = requests.Session()
    session.headers.update({"User-Agent": "Mozilla/5.0"})

    month_map = {
        "Jan": 1,
        "Feb": 2,
        "Mär": 3,
        "Mar": 3,
        "Apr": 4,
        "Mai": 5,
        "Jun": 6,
        "Jul": 7,
        "Aug": 8,
        "Sep": 9,
        "Okt": 10,
        "Nov": 11,
        "Dez": 12,
    }

    def parse_date(
        date_text: str, default_year: int
    ) -> tuple[dt.date | None, str | None]:
        # Example: "24. Januar | 19:00 Uhr"
        day_match = re.search(r"(\d{1,2})\.", date_text)
        time_match = re.search(r"\|\s*([\d:]+)\s*Uhr", date_text)
        month_match = re.search(r"\.\s*([A-Za-zäöüÄÖÜ]+)", date_text)
        if not day_match or not month_match:
            return None, None
        day = int(day_match.group(1))
        month_name = (
            month_match.group(1)[:3]
            .replace("ä", "ä")
            .replace("ö", "ö")
            .replace("ü", "ü")
        )
        month = month_map.get(month_name, None)
        if not month:
            return None, None
        date_obj = dt.date(default_year, month, day)
        time_str = time_match.group(1) if time_match else None
        return date_obj, time_str

    events = []
    page = 1
    max_pages = 10

    while page <= max_pages:
        try:
            url = base_url if page == 1 else f"{base_url}?pno={page}"
            resp = session.get(url, timeout=15)
            if resp.status_code != 200:
                break
            soup = BeautifulSoup(resp.content, "html.parser")
            container = soup.select_one("div.em-events-list-grouped")
            if not container:
                break

            current_month_year = None
            for node in container.children:
                if (
                    getattr(node, "name", None) == "h2"
                    and node.get("class")
                    and "month-headline" in node.get("class")
                ):
                    span = node.find("span")
                    if span and span.text.strip():
                        # e.g., "Jan. 2026" or "Feb. 2026"
                        current_month_year = span.text.strip()
                if (
                    getattr(node, "name", None) == "div"
                    and node.get("class")
                    and "events-date" in node.get("class")
                ):
                    if not current_month_year:
                        continue
                    month_label = current_month_year
                    # extract year from month headline
                    year_match = re.search(r"(\d{4})", month_label)
                    year = (
                        int(year_match.group(1)) if year_match else dt.date.today().year
                    )

                    date_text_el = node.select_one(".events-infos .date p")
                    place_el = node.select_one(".events-infos .place")
                    title_el = place_el.find("a") if place_el else None
                    location_ps = place_el.find_all("p") if place_el else []
                    location_text = None
                    for p in location_ps:
                        txt = p.get_text(strip=True)
                        if txt.startswith("Ort:"):
                            location_text = txt.replace("Ort:", "").strip() or None

                    date_text = (
                        date_text_el.get_text(" ", strip=True) if date_text_el else ""
                    )
                    event_date, event_time = parse_date(date_text, year)

                    event_url = (
                        title_el["href"]
                        if title_el and title_el.has_attr("href")
                        else None
                    )

                    # If no location found in listing, try fetching from detail page
                    if not location_text and event_url:
                        location_text = fetch_event_location_from_detail_page(
                            event_url, session
                        )

                    events.append(
                        {
                            "date": event_date,
                            "time": event_time,
                            "title": title_el.get_text(strip=True)
                            if title_el
                            else None,
                            "url": event_url,
                            "location": location_text,
                            "month_label": month_label,
                            "raw_date_text": date_text,
                            "page": page,
                        }
                    )

            # pagination: stop if no "next" link
            next_link = soup.select_one(".em-pagination .next.page-numbers")
            if not next_link:
                break
            page += 1
        except Exception as e:
            print(f"Error fetching page {page}: {e}")
            break

    df = pd.DataFrame(events)
    return df[["date", "time", "title", "url", "location"]]


def load_existing_df():
    """Load existing events from CSV file."""
    file_path = os.path.join(os.path.dirname(__file__), "events_aiterhofen.csv")
    df = pd.DataFrame()
    if os.path.exists(file_path):
        df = pd.read_csv(file_path)
        return df
    else:
        return df


def get_new_events(df_events, df_original):
    """Get only new events that don't exist in the original dataframe."""
    if df_original.empty:
        df_diff = df_events
    else:
        df_events["key"] = (
            df_events["date"].astype(str) + "||" + df_events["title"].astype(str)
        )
        df_original["key"] = (
            df_original["date"].astype(str) + "||" + df_original["title"].astype(str)
        )
        df_diff = df_events[~df_events["key"].isin(df_original["key"])].copy()
        df_diff = df_diff.drop(columns=["key"])

    return df_diff


def order_events_by_date(df):
    """Order events by date and time."""
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values(by=["date", "time"]).reset_index(drop=True)
    return df


def save_new_events(df):
    """Save events to CSV file."""
    file_path = os.path.join(os.path.dirname(__file__), "events_aiterhofen.csv")
    df = df[["date", "time", "title", "url", "location"]]
    if not os.path.exists(file_path):
        df = order_events_by_date(df)
        df.to_csv(file_path, index=False)
    else:
        df_original = load_existing_df()
        df_combined = pd.concat([df_original, df]).reset_index(drop=True)
        # Remove duplicates based on date and title (not URL)
        df_combined = df_combined.drop_duplicates(subset=["date", "title"], keep="last")
        df_combined = order_events_by_date(df_combined)
        df_combined.to_csv(file_path, index=False)


def main():
    """Fetch events and save to CSV."""
    df_events = fetch_events()
    df_original = load_existing_df()
    df_diff = get_new_events(df_events, df_original)
    save_new_events(df_diff)


if __name__ == "__main__":
    main()

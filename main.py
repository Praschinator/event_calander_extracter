import requests
from bs4 import BeautifulSoup
import pandas as pd
import datetime as dt
import re
import os
import icalendar


def fetch_events():
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
    while True:
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
                year = int(year_match.group(1)) if year_match else dt.date.today().year

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

                events.append(
                    {
                        "date": event_date,
                        "time": event_time,
                        "title": title_el.get_text(strip=True) if title_el else None,
                        "url": title_el["href"]
                        if title_el and title_el.has_attr("href")
                        else None,
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

    df = pd.DataFrame(events)
    return df[["date", "time", "title", "url", "location"]]


def load_existing_df():
    file_path = os.path.join(os.path.dirname(__file__), "events_aiterhofen.csv")
    # file_path = "events_aiterhofen.csv"
    df = pd.DataFrame()
    if os.path.exists(file_path):
        df = pd.read_csv(file_path)
        return df
    else:
        df = pd.DataFrame()
        return df


def get_new_events(df_events, df_original):
    if df_original.empty:
        df_diff = df_events
    else:
        df_diff = df_events[~df_events["url"].isin(df_original["url"])]

    return df_diff


def create_calander_file(df):
    c = icalendar.Calendar()
    c.add('prodid', '-//Event Calendar Extractor//aiterhofen.de//')
    c.add('version', '2.0')
    
    for index, row in df.iterrows():
        event = icalendar.Event()
        event.add("summary", row["title"] if pd.notna(row["title"]) else "No Title")
        event.add("dtstart", pd.to_datetime(row["date"]).date())
        if pd.notna(row["time"]):
            time_parts = row["time"].split(":")
            event.add(
                "dtstart",
                pd.to_datetime(row["date"])
                .replace(
                    hour=int(time_parts[0]),
                    minute=int(time_parts[1]) if len(time_parts) > 1 else 0,
                )
                .to_pydatetime(),
            )
        event.add(
            "location", row["location"] if pd.notna(row["location"]) else "No Location"
        )
        event.add("url", row["url"] if pd.notna(row["url"]) else "No URL")
        
        # Add UID using the URL
        # uid = row["url"] if pd.notna(row["url"]) else f"event-{index}@aiterhofen.de"
        uid = f"{row['title']}-{row['date']}" 
        event.add("uid", uid)
        
        c.add_component(event)

    filepath = os.path.join(os.path.dirname(__file__), "events.ics")
    with open(filepath, "wb") as f:
        f.write(c.to_ical())


def save_new_events(df):
    file_path = os.path.join(os.path.dirname(__file__), "events_aiterhofen.csv")
    df = df[["date", "time", "title", "url", "location"]]
    if not os.path.exists(file_path):
        df = order_events_by_date(df)
        df.to_csv(file_path, index=False)
    else:
        df_original = load_existing_df()
        df_combined = (
            pd.concat([df_original, df]).drop_duplicates().reset_index(drop=True)
        )
        df_combined = order_events_by_date(df_combined)
        df_combined.to_csv(file_path, index=False)


def order_events_by_date(df):
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values(by=["date", "time"]).reset_index(drop=True)
    return df


if __name__ == "__main__":
    df_events = fetch_events()
    df_original = load_existing_df()

    df_diff = get_new_events(df_events, df_original)

    create_calander_file(df_diff)
    save_new_events(df_diff)

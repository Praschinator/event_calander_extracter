import pandas as pd
import os
import icalendar


def load_df():
    file_path = os.path.join(os.path.dirname(__file__), "events_aiterhofen.csv")
    df = pd.read_csv(file_path)
    return df


def create_calander_file(df):
    c = icalendar.Calendar()
    c.add("prodid", "-//Event Calendar Extractor//aiterhofen.de//")
    c.add("version", "2.0")

    for index, row in df.iterrows():
        event = icalendar.Event()
        event.add("summary", row["title"] if pd.notna(row["title"]) else "No Title")

        event.add("dtstart", pd.to_datetime(row["date"]).date())
        event.add("dtend", pd.to_datetime(row["date"]).date() + pd.Timedelta(days=1))

        event.add(
            "location", row["location"] if pd.notna(row["location"]) else "No Location"
        )
        event.add("url", row["url"] if pd.notna(row["url"]) else "No URL")

        # Add UID using the URL
        # uid = row["url"] if pd.notna(row["url"]) else f"event-{index}@aiterhofen.de"
        uid = f"{row['title']}-{row['date']}"
        event.add("uid", uid)

        c.add_component(event)

    filepath = os.path.join(os.path.dirname(__file__), "all_events.ics")
    with open(filepath, "wb") as f:
        f.write(c.to_ical())


def main():
    df = load_df()
    create_calander_file(df)


if __name__ == "__main__":
    main()

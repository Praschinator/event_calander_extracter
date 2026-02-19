# Event Calendar Extractor

A Python tool to scrape and extract event information from the Gemeinde Aiterhofen website and create a iCalander File from it

## Development Setup

### Requirements

- [`uv`](https://github.com/astral-sh/uv) installed

### Installation

```bash
git clone
uv sync
```

### Explaination

- `uv run create_csv.py` - runs the script to scrape and save events.
- `uv run create_full_calendar` - creates a full calendar ical-file, that can be imported into calendar applications.

## How to add to calander application

1. get the [raw link](https://raw.githubusercontent.com/Praschinator/event_calander_extracter/refs/heads/main/all_events.ics) of the ical-file served on github
2. add to your calendar application as a subscribed calendar using the raw link

## Limitations

1. Currently the script saves the Events as a full day event, even if there is a start time present on the website.

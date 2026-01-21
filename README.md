# Event Calendar Extractor

A Python tool to scrape and extract event information from the Aiterhofen community website and save it to CSV format.

## Features

- Scrapes events from https://www.aiterhofen.de/veranstaltungen/
- Handles pagination to fetch all available events
- Extracts event details: date, time, title, URL, and location
- Saves events to CSV file (`events_aiterhofen.csv`)
- Avoids duplicates when updating the CSV


## Development Setup

### Requirements

- `uv` installed 

### Installation

```bash
git clone
uv sync
```

### Explaination

`uv run main.py` - runs the main script to scrape and save events.
`uv run create_full_calendar` - creates a full calendar ical-file, that can be imported into calendar applications.

### How to add to calander application

1. get the raw link of the ical-file served on github
2. add to your calendar application as a subscribed calendar using the raw link


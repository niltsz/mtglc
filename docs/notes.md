# List of things to take into consideration

* start = datetime.datetime(2025, 7, 18, 14, 0)  
  end = datetime.datetime(2025, 7, 18, 15, 0)  
  selected_collection.search(dtstart = start, dtend = end)
  yields 13:50-14:00 and 15:00-15:10
  fix: [p for p in selected_collection.search(dtstart = start, dtend = end) if start <= p.sensing_start < end]

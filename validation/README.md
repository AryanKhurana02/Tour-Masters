# Validation data

This folder holds optional **ground-truth** data used to calibrate the
Holiday Climate Index (HCI) crowd model. Nothing here ships with the app; the
app never reads this folder at runtime.

## `local_ratings.csv`

Used by `scripts/check_ratings.py` to compare our estimates against real
on-the-ground observations. Add the file only when you have genuine, locally
reported data — do not fabricate rows.

| column | type | notes |
| --- | --- | --- |
| `destination_id` | string | historical-weather key (e.g. `mussoorie`) or numeric catalogue id (`1` = Almora … `11` = Rishikesh) |
| `date` | `YYYY-MM-DD` | date the crowd level was observed |
| `local_reported_crowd_level` | string | one of `Quiet`, `Moderate`, `Busy`, `Very busy` |

Example:

```csv
destination_id,date,local_reported_crowd_level
mussoorie,2025-10-12,Busy
nainital,2025-08-15,Very busy
binsar,2025-03-02,Quiet
```

Run the calibration:

```
py -3.12 scripts/check_ratings.py
```

The script reports exact-match %, within-one-level %, and a confidence score
that grows with both agreement and sample volume.

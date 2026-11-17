# Dataset file exports

`GET /api/datasets/{id}` exposes each generated file key in `files`. The value is the filename.

| Key | `GET /api/datasets/{id}/files/{kind}` attachment | Media type |
| --- | --- | --- |
| `dictionary_csv` | `data_dictionary.csv` | `text/csv` |
| `dictionary_md` | `data_dictionary.md` | `text/markdown` |
| `eda_md` | `eda.md` | `text/markdown` |

The CSV uses UTF-8 with BOM. Its columns are `gold_table`, `column`, `type`, `description`, `unit`, `source`, `missing_pct`, `sample`. Empty tables have a blank missing ratio. Unknown descriptions and units are blank. All values and samples are from the exported model. Text with spreadsheet formula prefixes is escaped. An invalid dataset ID, unknown file key or missing file returns 404.

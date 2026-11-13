"""Dates are written day first, 13/11/2026, whichever language the admin is shown in.

Django picks date formats from the active language, so an English browser would otherwise
get 2026-11-13 and a Danish one 13.11.2026. Both languages import these instead.
"""

SHORT_DATE_FORMAT = "d/m/Y"
SHORT_DATETIME_FORMAT = "d/m/Y H:i"
DATE_FORMAT = "j. F Y"
DATETIME_FORMAT = "j. F Y H:i"
TIME_FORMAT = "H:i"
FIRST_DAY_OF_WEEK = 1

# The first entry is what a form shows; the rest are also accepted when typed. ISO stays
# in the list because that is what a browser's own date picker submits.
DATE_INPUT_FORMATS = ["%d/%m/%Y", "%d.%m.%Y", "%d-%m-%Y", "%Y-%m-%d"]
TIME_INPUT_FORMATS = ["%H:%M", "%H:%M:%S", "%H:%M:%S.%f"]
DATETIME_INPUT_FORMATS = [
    f"{date} {time}" for date in DATE_INPUT_FORMATS for time in TIME_INPUT_FORMATS
]

from datetime import datetime, timezone

import click


class Timestamp(click.ParamType):
    """
    A custom Click parameter type that accepts Unix timestamps (as numbers)
    or datetime strings in specified formats, converting them to timezone-aware
    datetime objects (assuming UTC).
    """

    name = "timestamp"

    def __init__(self, formats=None):
        super().__init__()
        self.formats = formats or ["%Y-%m-%dT%H:%M:%S", "%Y-%m-%d", "%Y%m%d"]
        self.datetime_parser = click.DateTime(self.formats)

    def convert(self, value, param, ctx):
        if value is None:
            return None
        # First, try to convert from a numeric Unix timestamp
        try:
            # Assume UTC for numeric timestamps
            return datetime.fromtimestamp(float(value), tz=timezone.utc)
        except (ValueError, TypeError):
            # If that fails, fall back to the standard string format parser
            try:
                dt = self.datetime_parser.convert(value, param, ctx)
                # If the parsed datetime is naive, assume it's UTC
                if dt.tzinfo is None:
                    return dt.replace(tzinfo=timezone.utc)
                return dt
            except click.exceptions.BadParameter:
                self.fail(
                    f"'{value}' is not a valid timestamp. "
                    f"Expected a Unix timestamp (e.g., 1672531200) or a "
                    f"string in one of these formats: {', '.join(self.formats)}."
                )

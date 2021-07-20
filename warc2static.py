#!/usr/bin/env python3

""" Module Description """

import argparse
import logging
import sys
from pathlib import Path
from urllib.parse import urlparse

from warcio.archiveiterator import ArchiveIterator

OUTPUT_FOLDER = "output"


TEXT_TYPES = [
    "text/html",
    "text/css",
    "application/javascript",
]

try:
    assert sys.stdout.isatty()
    from termcolor import colored
except (AssertionError, ImportError):

    def colored(text, *args, **kwargs):
        """Dummy function to pass text through without escape codes if stdout is not a
        TTY or termcolor is not available."""
        return text


def make_path_from_uri(uri):
    scheme, netloc, path, *_ = urlparse(uri)
    if path.endswith("/"):
        path += "/index.html"
    return Path(f"{OUTPUT_FOLDER}/{netloc}/{path}").resolve()


def read_warc(warc_file):

    with open(warc_file, "rb") as stream:
        for record in ArchiveIterator(stream):
            if record.rec_type == "response":
                uri = record.rec_headers["WARC-Target-URI"]
                output_filepath = make_path_from_uri(uri)

                print(colored(uri, "green"))
                print(colored(output_filepath, "yellow"))

                # WARNING: explicitly dropping, e.g. "; charset=UTF-8" here...
                content_type = record.http_headers["content-type"].split(";")[0]

                # TODO: check return code here (checking for 404s, 500s, etc.)

                if content_type in TEXT_TYPES:
                    output_filepath.parent.mkdir(parents=True, exist_ok=True)

                    # TODO: check for existing files/content?

                    # TODO: parse content, update URLs/links?

                    with output_filepath.open("w") as _fh:
                        _fh.write(record.content_stream().read().decode("utf-8"))


def main():
    """Command-line entry-point."""

    parser = argparse.ArgumentParser(description="Description: {}".format(__file__))

    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        default=False,
        help="Show debug messages",
    )

    parser.add_argument(
        "warc",
        action="store",
        help="WARC file",
    )

    args = parser.parse_args()

    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(level=log_level, format="%(message)s")

    read_warc(args.warc)


if __name__ == "__main__":
    main()

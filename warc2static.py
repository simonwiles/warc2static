#!/usr/bin/env python3

""" Module Description """

import argparse
import logging
import re
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

BINARY_TYPES = [
    "image/jpeg",
    "image/gif",
    "image/png",
    "application/font-woff",
    "font/woff2",
]

try:
    assert sys.stdout.isatty()
    from termcolor import colored
except (AssertionError, ImportError):

    def colored(text, *args, **kwargs):
        """Dummy function to pass text through without escape codes if stdout is not a
        TTY or termcolor is not available."""
        return text


def make_path_from_uri(uri, base_domain):
    scheme, netloc, path, *_ = urlparse(uri)
    if path.endswith("/"):
        path += "/index.html"
    if netloc == base_domain:
        return Path(f"{OUTPUT_FOLDER}/{path}").resolve()
    return Path(f"{OUTPUT_FOLDER}/_/{netloc}/{path}").resolve()


def replace_uris(content, uris, base_domain):

    for uri in sorted(uris, key=len, reverse=True):

        scheme, netloc, path, *_ = urlparse(uri)
        if netloc == base_domain:
            new_uri = path
        else:
            new_uri = f"/_/{netloc}/{path}"

        reg = re.escape(uri).replace(r"\&", r"(?:\&|\&#038;)")
        content = re.sub(rf"\b{reg}\b", new_uri, content)

    return content


def read_warc(warc_file, base_domain):

    with open(warc_file, "rb") as stream:
        uris = [
            record.rec_headers["WARC-Target-URI"]
            for record in ArchiveIterator(stream)
            if record.rec_type == "response"
        ]

    with open(warc_file, "rb") as stream:
        for record in ArchiveIterator(stream):
            if record.rec_type == "response":
                uri = record.rec_headers["WARC-Target-URI"]
                output_filepath = make_path_from_uri(uri, base_domain)

                logging.debug(colored(uri, "green"))
                logging.debug(
                    colored(" → %s", "yellow"),
                    output_filepath.relative_to(Path(OUTPUT_FOLDER).resolve()),
                )

                # WARNING: explicitly dropping, e.g. "; charset=UTF-8" here...
                content_type = record.http_headers["content-type"].split(";")[0]

                # TODO: check return code here (checking for 404s, 500s, etc.)

                if content_type in TEXT_TYPES:
                    output_filepath.parent.mkdir(parents=True, exist_ok=True)

                    # TODO: check for existing files/content?

                    # TODO: parse content, update URLs/links?

                    content = record.content_stream().read().decode("utf-8")
                    content = replace_uris(content, uris, base_domain)

                    with output_filepath.open("w") as _fh:
                        _fh.write(content)

                elif content_type in BINARY_TYPES:
                    output_filepath.parent.mkdir(parents=True, exist_ok=True)
                    with output_filepath.open("wb") as _fh:
                        _fh.write(record.content_stream().read())

                else:
                    logging.warning(
                        colored("Unknown content_type `%s` (skipped)!", "red"),
                        content_type,
                    )


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
        "--base-domain",
        action="store",
        required=True,
        help="Base domain for relative links",
    )

    parser.add_argument(
        "warc",
        action="store",
        help="WARC file",
    )

    args = parser.parse_args()

    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(level=log_level, format="%(message)s")

    read_warc(args.warc, args.base_domain)


if __name__ == "__main__":
    main()

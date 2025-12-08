#!/usr/bin/env python3
"""Utility script to fetch the latest ServiceNow instances list."""

from __future__ import annotations

import logging

from browsergym.workarena.instance import fetch_instances, encrypt_instance_password


def main() -> None:
    logging.basicConfig(level=logging.INFO)

    logging.info("Encrypted sample password: %s", encrypt_instance_password("Tensor@34"))

    instances = fetch_instances()
    logging.info("Fetched %d instances from the dataset.", len(instances))
    for idx, entry in enumerate(instances, start=1):
        url = entry.get("url") if isinstance(entry, dict) else entry
        pwd = entry.get("password") if isinstance(entry, dict) else "N/A"
        logging.info("%02d. %s (password: %s)", idx, url, pwd)


if __name__ == "__main__":
    main()

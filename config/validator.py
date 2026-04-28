import logging
import os
import re
from pathlib import Path
from urllib.parse import urlparse

def validate_config(config):
    errors = []

    executor = config.get("executor")
    if not executor:
        errors.append("Missing 'executor' section in system_config.json.")
    else:
        if not isinstance(executor.get("url"), str) or not executor["url"]:
            logging.warning(f"Invalid URL: {executor.get('url', 'N/A')}")
            errors.append("Missing or invalid executor.url.")
        if not isinstance(executor.get("port"), int):
            logging.warning(f"Invalid executor.port: {executor.get('port', 'N/A')}")
            errors.append("executor.port must be an integer.")

    for name, url in [("executor", executor.get("url")),
                      ("database", config.get("database", {}).get("url")),
                      ("testrail", config.get("testrail", {}).get("url"))]:
        if url:
            parsed = urlparse(url)
            ipv4_re = re.compile(r"^((25[0-5]|2[0-4][0-9]|1[0-9]{2}|[1-9]?[0-9])\.){3}(25[0-5]|2[0-4][0-9]|1[0-9]{2}|[1-9]?[0-9])$")
            hostname_re = re.compile(r"^(?!-)[A-Za-z0-9-]{1,63}(?<!-)(\.[A-Za-z0-9-]{1,63})*$")
            valid = (
                    (parsed.scheme and parsed.netloc) or
                    ipv4_re.match(url) or
                    hostname_re.match(url)
            )

            if not valid:
                logging.warning(f"Invalid URL or hostname: {url}")
                errors.append(f"{name}.url is not a valid URL or hostname: {url}")

    required_env = [
        "TESTRAIL_API_KEY",
        "TESTRAIL_USER_NAME",
    ]

    missing = [var for var in required_env if not os.getenv(var)]
    if missing:
        logging.warning(f"Environment variables not found: {', '.join(missing)}")
        errors.append(f"Missing environment variables: {', '.join(missing)}")

    # # image_bank_root is optional - only validate if it's provided
    # path = config.get("image_bank_root", "")
    # if not path:
    #     logging.warning("Missing 'image_bank_root' in config (optional for pipelines without image comparisons)")
    # else:
    #     resolved = Path(path).expanduser()
    #     if not resolved.exists():
    #         logging.warning(f"Path for image_bank_root is not a valid path: {resolved}")
    #         errors.append(f"Path for image_bank_root does not exist: {resolved}")

    if errors:
        logging.warning(" Configuration validation failed:")
        for err in errors:
            logging.warning(f"  - {err}")
        raise SystemExit(1)
    else:
        logging.info("Configuration validation passed.")

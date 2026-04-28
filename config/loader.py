import json
import os
from pathlib import Path
from shutil import copyfile

from dotenv import load_dotenv
from config.validator import validate_config

def load_config():
    load_dotenv()
    config_path = Path(__file__).parent / "system_config.json"
    if not config_path.exists():
        template_path = Path(__file__).parent / "system_config_template.json"
        copyfile(template_path, config_path)
    with open(config_path) as f:
        config = json.load(f)
    config["testrail"]["username"] = os.getenv("TESTRAIL_USER_NAME")
    config["testrail"]["api_key"] = os.getenv("TESTRAIL_API_KEY")

    user_image_bank_root = os.getenv("IMAGE_BANK_REPO_PATH")
    if user_image_bank_root:
        config["image_bank_root"] = user_image_bank_root
    else:
        user_config_path = Path(__file__).parent / "user_config.json"
        if user_config_path.exists():
            with open(user_config_path) as f:
                user_config = json.load(f)
            config["image_bank_root"] = user_config.get("image_bank_root")

    validate_config(config)
    return config

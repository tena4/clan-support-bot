from collections import namedtuple
from datetime import date
from logging import getLogger
from typing import Optional

import requests
from bs4 import BeautifulSoup
from jinja2 import Template

import app_config

logger = getLogger(__name__)
config = app_config.Config.get_instance()

template: Template = Template(source=config.scraping_template_url)

bossMap = namedtuple("bossmap", ["num", "name", "hp"])


def scraping(nowdate: date) -> Optional[list[bossMap]]:
    scraping_url = template.render(year=nowdate.year, month=nowdate.month, day=nowdate.day)
    res = requests.get(scraping_url)
    if res.status_code != 200:
        logger.warn(f"failed to scraping. {scraping_url} is not found")
        return
    try:
        soup = BeautifulSoup(res.text, "html.parser")
        hp_tags = soup.find_all("img", {"alt": "4段階目", "title": "4段階目"})
        boss_map = []

        for i in range(1, 6):
            boss_name_tag = soup.find("a", {"class": "anchor_super", "name": f"boss_{i}"})
            boss_name = boss_name_tag.parent.get_text().strip()
            hp = int(hp_tags[i].parent.next_sibling.next_sibling.get_text().replace(",", ""))
            boss_map.append(bossMap(i, boss_name, hp))

        return boss_map

    except Exception as e:
        logger.warn(f"failed to scraping. {e}")
        return

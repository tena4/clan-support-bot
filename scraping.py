from collections import namedtuple
from datetime import date
from logging import getLogger
from typing import Optional

import urllib3
from bs4 import BeautifulSoup
from jinja2 import Template

import app_config

logger = getLogger(__name__)
config = app_config.Config.get_instance()

template: Template = Template(source=config.scraping_template_url)

bossMap = namedtuple("bossmap", ["num", "name", "hp"])


def scraping(nowdate: date) -> Optional[list[bossMap]]:
    scraping_url = template.render(year=nowdate.year, month=nowdate.month, day=nowdate.day)
    http = urllib3.PoolManager()

    try:
        res = http.request("GET", scraping_url)

        soup = BeautifulSoup(res.data.decode("utf-8"), "html.parser")
        boss_map = []

        for i in range(1, 6):
            boss_name_tag = soup.find("a", {"class": "anchor_super", "name": f"boss_{i}"})
            boss_name = boss_name_tag.parent.get_text().strip().split()[0]
            pre_hp_tag = boss_name_tag.find_next("img", {"alt": "4段階目", "title": "4段階目"})
            hp = int(pre_hp_tag.parent.next_sibling.next_sibling.get_text().replace(",", ""))
            boss_map.append(bossMap(i, boss_name, hp))

        return boss_map

    except urllib3.exceptions.HTTPError as e:
        print("scriping HTTP error occurred:", e)
        return
    except Exception as e:
        logger.warn(f"failed to scraping. {e}")
        return

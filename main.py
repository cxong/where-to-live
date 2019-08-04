import json
import os

import click
from munch import munchify

from finder import GSuburbFinder


@click.command()
@click.option("--config", type=click.Path(exists=True), default="config.json")
def main(config: str):
    with open(config) as f:
        cfg = munchify(json.load(f))
    gm_key = os.environ[cfg.gm_key_env]
    finder = GSuburbFinder(gm_key)

    for label, f in cfg.filters.items():
        finder.apply_filter(label, f)
    print(finder.suburbs)


if __name__ == "__main__":
    main()

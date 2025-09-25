"""Console script for inapps_pybackend."""

import typer
from rich.console import Console

from inapps_pybackend import utils

app = typer.Typer()
console = Console()


@app.command()
def main():
    """Console script for inapps_pybackend."""
    console.print("Replace this message by putting your code into "
               "inapps_pybackend.cli.main")
    console.print("See Typer documentation at https://typer.tiangolo.com/")
    utils.do_something_useful()


if __name__ == "__main__":
    app()

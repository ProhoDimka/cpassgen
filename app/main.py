import click

from app.generator import generate_password


@click.command()
@click.option("--username", prompt=True)
@click.option("--resource", prompt=True)
@click.option(
    "--secret",
    envvar="PASS_GEN_KEY_WORD",
    prompt=True,
    hide_input=True,
)
def generate(username: str, resource: str, secret: str):
    """
    Generate password based on given parameters.
    """
    password = generate_password(username, resource, secret)
    click.echo(password)


if __name__ == "__main__":
    generate()

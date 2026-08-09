import click

from app import models
from app.generator import generate_password_from_request


@click.command()
@click.option("--username", prompt=True)
@click.option("--resource", prompt=True)
@click.option(
    "--secret",
    envvar="PASS_GEN_KEY_WORD",
    prompt=True,
    hide_input=True,
)
@click.option("--min-length", type=int, default=24, show_default=True)
@click.option("--max-length", type=int, default=32, show_default=True)
@click.option("--upper", type=int, default=0, show_default=True)
@click.option("--lower", type=int, default=0, show_default=True)
@click.option("--digits", type=int, default=0, show_default=True)
@click.option("--specials", type=int, default=0, show_default=True)
@click.option("--mask", type=int, default=0, show_default=True)
def generate(
    username: str,
    resource: str,
    secret: str,
    min_length: int,
    max_length: int,
    upper: int,
    lower: int,
    digits: int,
    specials: int,
    mask: int,
):
    """Generate password based on given parameters."""
    try:
        request = models.PasswordGenerationRequest(
            profile=models.PasswordProfile(
                username=username,
                resource=resource,
                constraints=models.PasswordConstraints(
                    min_length=min_length,
                    max_length=max_length,
                    upper=upper,
                    lower=lower,
                    digits=digits,
                    specials=specials,
                    mask=mask,
                ),
            ),
            secret=secret,
        )
        password = generate_password_from_request(request)
    except ValueError as error:
        click.echo(f"Error: {error}")
        raise SystemExit(1) from error
    click.echo(password)


if __name__ == "__main__":
    generate()

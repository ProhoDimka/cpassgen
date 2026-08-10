import click

from app import models
from app.generator import generate_password_from_request
from app.persistence import load_repository_from_env
from app.sync_service import SyncError, SyncService


def _build_profile(
    username: str,
    resource: str,
    min_length: int,
    max_length: int,
    upper: int,
    lower: int,
    digits: int,
    specials: int,
    mask: int,
    generation_version: int,
):
    return models.PasswordProfile(
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
        generation_version=generation_version,
    )


def _constraint_options(func):
    option_decorator = click.option
    options = (
        "--min-length",
        "--max-length",
        "--upper",
        "--lower",
        "--digits",
        "--specials",
        "--mask",
    )
    defaults = {
        "--min-length": 24,
        "--max-length": 32,
        "--upper": 0,
        "--lower": 0,
        "--digits": 0,
        "--specials": 0,
        "--mask": 0,
    }
    for option_name in reversed(options):
        func = option_decorator(
            option_name,
            type=int,
            default=defaults[option_name],
            show_default=True,
        )(func)
    return func


def _offer_sync(repository, username: str, resource: str, action: str) -> None:
    try:
        prompt = "Sync changes with remote storage?"
        do_sync = click.confirm(prompt, default=False)
    except click.Abort:
        return
    if not do_sync:
        return
    try:
        sync_svc = SyncService(repository._root)
        msg = f"sync: {action} profile {username}/{resource}"
        click.echo(sync_svc.sync(msg))
    except SyncError as exc:
        if exc.conflict_info:
            click.echo(exc.conflict_info, err=True)
            raise SystemExit(1)
        click.echo(f"Sync skipped: {exc}", err=True)


@click.group()
def cli():
    """Manage password profiles and generate deterministic passwords."""


@cli.command("sync")
def sync_profiles():
    """Synchronize profile storage with the remote git repository."""
    try:
        repository = load_repository_from_env()
        sync_svc = SyncService(repository._root)
        click.echo(sync_svc.sync())
    except (ValueError, SyncError) as error:
        click.echo(f"Error: {error}")
        if isinstance(error, SyncError) and error.conflict_info:
            click.echo(error.conflict_info, err=True)
        raise SystemExit(1) from error


@cli.command("create")
@click.option("--username", prompt=True)
@click.option("--resource", prompt=True)
@click.option(
    "--generation-version",
    type=int,
    default=1,
    show_default=True,
    help="Generation version for the password derivation algorithm.",
)
@_constraint_options
def create_profile(
    username: str,
    resource: str,
    generation_version: int,
    min_length: int,
    max_length: int,
    upper: int,
    lower: int,
    digits: int,
    specials: int,
    mask: int,
):
    try:
        profile = _build_profile(
            username,
            resource,
            min_length,
            max_length,
            upper,
            lower,
            digits,
            specials,
            mask,
            generation_version,
        )
        repository = load_repository_from_env()
        repository.create(profile)
    except ValueError as error:
        click.echo(f"Error: {error}")
        raise SystemExit(1) from error
    click.echo("Profile created.")
    _offer_sync(repository, username, resource, "create")


@cli.command("set")
@click.option("--username", prompt=True)
@click.option("--resource", prompt=True)
@click.option(
    "--generation-version",
    type=int,
    default=1,
    show_default=True,
    help="Generation version for the password derivation algorithm.",
)
@_constraint_options
def set_profile(
    username: str,
    resource: str,
    generation_version: int,
    min_length: int,
    max_length: int,
    upper: int,
    lower: int,
    digits: int,
    specials: int,
    mask: int,
):
    try:
        profile = _build_profile(
            username,
            resource,
            min_length,
            max_length,
            upper,
            lower,
            digits,
            specials,
            mask,
            generation_version,
        )
        repository = load_repository_from_env()
        repository.set(profile)
    except ValueError as error:
        click.echo(f"Error: {error}")
        raise SystemExit(1) from error
    click.echo("Profile updated.")
    _offer_sync(repository, username, resource, "update")


@cli.command("get")
@click.option("--username", prompt=True)
@click.option("--resource", prompt=True)
@click.option(
    "--secret",
    envvar="PASS_GEN_KEY_WORD",
    prompt=True,
    hide_input=True,
)
def get_password(username: str, resource: str, secret: str):
    """Generate password from persisted profile and secret."""
    try:
        repository = load_repository_from_env()
        profile = repository.get(username, resource)
        request = models.PasswordGenerationRequest(
            profile=profile,
            secret=secret,
        )
        password = generate_password_from_request(request)
    except ValueError as error:
        click.echo(f"Error: {error}")
        raise SystemExit(1) from error
    click.echo(password)


if __name__ == "__main__":
    cli()

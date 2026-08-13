import click

from app import models
from app.config import load_config
from app.generator import generate_password_from_request
from app.persistence import load_repository_from_config
from app.sync_service import SyncError, SyncService


def _build_profile(
    username: str,
    resource: str,
    length: int,
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
            length=length,
            upper=upper,
            lower=lower,
            digits=digits,
            specials=specials,
            mask=mask,
        ),
        generation_version=generation_version,
    )


def _constraint_options(func):
    options = (
        ("--length", None),
        ("--upper", None),
        ("--lower", None),
        ("--digits", "-d"),
        ("--specials", None),
        ("--mask", "-m"),
    )
    defaults = {
        "--length": 24,
        "--upper": 0,
        "--lower": 0,
        "--digits": 0,
        "--specials": 0,
        "--mask": 0,
    }
    for long_name, short_name in reversed(options):
        args = [long_name] if short_name is None else [short_name, long_name]
        func = click.option(
            *args,
            type=int,
            default=defaults[long_name],
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
@click.option(
    "--config",
    type=click.Path(dir_okay=False),
    default=None,
    help=(
        "Path to a JSON config file. Takes priority over the home "
        "config file, environment variables take priority over both."
    ),
)
@click.pass_context
def cli(ctx, config):
    """Manage password profiles and generate deterministic passwords."""
    ctx.ensure_object(dict)
    ctx.obj["config"] = config


@cli.command("sync")
@click.pass_context
def sync_profiles(ctx):
    """Synchronize profile storage with the remote git repository."""
    try:
        config = load_config(ctx.obj["config"])
        repository = load_repository_from_config(config)
        sync_svc = SyncService(repository._root)
        click.echo(sync_svc.sync())
    except (ValueError, SyncError) as error:
        click.echo(f"Error: {error}")
        if isinstance(error, SyncError) and error.conflict_info:
            click.echo(error.conflict_info, err=True)
        raise SystemExit(1) from error


@cli.command("create")
@click.option("--username", "-u", prompt=True)
@click.option("--resource", "-r", prompt=True)
@click.option(
    "--generation-version",
    "-g",
    type=int,
    default=1,
    show_default=True,
    help="Generation version for the password derivation algorithm.",
)
@_constraint_options
@click.pass_context
def create_profile(
    ctx,
    username: str,
    resource: str,
    generation_version: int,
    length: int,
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
            length,
            upper,
            lower,
            digits,
            specials,
            mask,
            generation_version,
        )
        config = load_config(ctx.obj["config"])
        repository = load_repository_from_config(config)
        repository.create(profile)
    except ValueError as error:
        click.echo(f"Error: {error}")
        raise SystemExit(1) from error
    click.echo("Profile created.")
    _offer_sync(repository, username, resource, "create")


def _bump_option(func, name: str, short: str | None = None):
    args = [name] if short is None else [short, name]
    return click.option(
        *args,
        type=int,
        default=None,
        help="New constraint value (leave unset to keep existing).",
    )(func)


def _bump_constraint_options(func):
    options = (
        ("--length", None),
        ("--upper", None),
        ("--lower", None),
        ("--digits", "-d"),
        ("--specials", None),
        ("--mask", "-m"),
    )
    for long_name, short_name in reversed(options):
        func = _bump_option(func, long_name, short_name)
    return func


@cli.command("bump")
@click.option("--username", "-u", prompt=True)
@click.option("--resource", "-r", prompt=True)
@_bump_constraint_options
@click.pass_context
def bump_profile(
    ctx,
    username: str,
    resource: str,
    length: int | None,
    upper: int | None,
    lower: int | None,
    digits: int | None,
    specials: int | None,
    mask: int | None,
):
    try:
        config = load_config(ctx.obj["config"])
        repository = load_repository_from_config(config)
        existing = repository.get(username, resource)
        constraints = existing.constraints

        new_length = length if length is not None else constraints.length
        new_upper = upper if upper is not None else constraints.upper
        new_lower = lower if lower is not None else constraints.lower
        new_digits = digits if digits is not None else constraints.digits
        new_specials = (
            specials if specials is not None else constraints.specials
        )
        new_mask = mask if mask is not None else constraints.mask

        new_constraints_unchanged = (
            new_length == constraints.length
            and new_upper == constraints.upper
            and new_lower == constraints.lower
            and new_digits == constraints.digits
            and new_specials == constraints.specials
            and new_mask == constraints.mask
        )

        if new_constraints_unchanged:
            try:
                change = click.confirm(
                    "Modify password constraints before bumping?",
                    default=False,
                )
            except click.Abort:
                change = False
            if change:
                new_length = click.prompt(
                    "length",
                    type=int,
                    default=constraints.length,
                    show_default=True,
                )
                new_upper = click.prompt(
                    "upper",
                    type=int,
                    default=constraints.upper,
                    show_default=True,
                )
                new_lower = click.prompt(
                    "lower",
                    type=int,
                    default=constraints.lower,
                    show_default=True,
                )
                new_digits = click.prompt(
                    "digits",
                    type=int,
                    default=constraints.digits,
                    show_default=True,
                )
                new_specials = click.prompt(
                    "specials",
                    type=int,
                    default=constraints.specials,
                    show_default=True,
                )
                new_mask = click.prompt(
                    "mask",
                    type=int,
                    default=constraints.mask,
                    show_default=True,
                )
                result = repository.bump(
                    username,
                    resource,
                    new_constraints=models.PasswordConstraints(
                        length=new_length,
                        upper=new_upper,
                        lower=new_lower,
                        digits=new_digits,
                        specials=new_specials,
                        mask=new_mask,
                    ),
                )
            else:
                result = repository.bump(username, resource)
        else:
            result = repository.bump(
                username,
                resource,
                new_constraints=models.PasswordConstraints(
                    length=new_length,
                    upper=new_upper,
                    lower=new_lower,
                    digits=new_digits,
                    specials=new_specials,
                    mask=new_mask,
                ),
            )

        click.echo(f"Profile bumped to version {result.generation_version}.")
    except ValueError as error:
        click.echo(f"Error: {error}")
        raise SystemExit(1) from error
    _offer_sync(repository, username, resource, "bump")


@cli.command("get")
@click.option("--username", "-u", prompt=True)
@click.option("--resource", "-r", prompt=True)
@click.option("--secret", "-s", default=None)
@click.pass_context
def get_password(ctx, username: str, resource: str, secret: str):
    """Generate password from persisted profile and secret."""
    try:
        config = load_config(ctx.obj["config"])
        resolved_secret = secret
        if resolved_secret is None:
            resolved_secret = config.key_word
        if resolved_secret is None:
            resolved_secret = click.prompt("secret", hide_input=True)
        repository = load_repository_from_config(config)
        profile = repository.get(username, resource)
        request = models.PasswordGenerationRequest(
            profile=profile,
            secret=resolved_secret,
        )
        password = generate_password_from_request(request)
    except ValueError as error:
        click.echo(f"Error: {error}")
        raise SystemExit(1) from error
    click.echo(password)


if __name__ == "__main__":
    cli()

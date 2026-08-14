import json

import click

from app import models
from app.config import load_config
from app.generator import generate_password_from_request
from app.persistence import load_repository_from_config
from app.sync_service import SyncError, SyncService

_CONSTRAINT_OPTIONS = (
    ("--length", None),
    ("--upper", None),
    ("--lower", None),
    ("--digits", "-d"),
    ("--specials", None),
    ("--mask", "-m"),
)

DEFAULT_CONSTRAINTS = models.PasswordConstraints(
    length=24,
    upper=0,
    lower=0,
    digits=0,
    specials=0,
    mask=0,
)


def _build_profile(
    username: str,
    resource: str,
    constraints: models.PasswordConstraints,
    generation_version: int,
):
    return models.PasswordProfile(
        username=username,
        resource=resource,
        constraints=constraints,
        generation_version=generation_version,
    )


def _constraint_option(func, name: str, short: str | None = None):
    args = [name] if short is None else [short, name]
    return click.option(
        *args,
        type=int,
        default=None,
        help="New constraint value (leave unset to prompt interactively).",
    )(func)


def _constraint_options(func):
    for long_name, short_name in reversed(_CONSTRAINT_OPTIONS):
        func = _constraint_option(func, long_name, short_name)
    return func


def _prompt_constraints(
    defaults: models.PasswordConstraints,
) -> models.PasswordConstraints:
    length = click.prompt(
        "length", type=int, default=defaults.length, show_default=True
    )
    upper = click.prompt(
        "upper", type=int, default=defaults.upper, show_default=True
    )
    lower = click.prompt(
        "lower", type=int, default=defaults.lower, show_default=True
    )
    digits = click.prompt(
        "digits", type=int, default=defaults.digits, show_default=True
    )
    specials = click.prompt(
        "specials", type=int, default=defaults.specials, show_default=True
    )
    mask = click.prompt(
        "mask", type=int, default=defaults.mask, show_default=True
    )
    return models.PasswordConstraints(
        length=length,
        upper=upper,
        lower=lower,
        digits=digits,
        specials=specials,
        mask=mask,
    )


def _resolve_create_constraints(
    length: int | None,
    upper: int | None,
    lower: int | None,
    digits: int | None,
    specials: int | None,
    mask: int | None,
) -> models.PasswordConstraints:
    values = (length, upper, lower, digits, specials, mask)
    if any(value is not None for value in values):
        return models.PasswordConstraints(
            length=(
                length if length is not None else DEFAULT_CONSTRAINTS.length
            ),
            upper=upper if upper is not None else DEFAULT_CONSTRAINTS.upper,
            lower=lower if lower is not None else DEFAULT_CONSTRAINTS.lower,
            digits=(
                digits if digits is not None else DEFAULT_CONSTRAINTS.digits
            ),
            specials=(
                specials
                if specials is not None
                else DEFAULT_CONSTRAINTS.specials
            ),
            mask=mask if mask is not None else DEFAULT_CONSTRAINTS.mask,
        )
    return _prompt_constraints(DEFAULT_CONSTRAINTS)


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


@cli.command("list")
@click.pass_context
def list_profiles(ctx):
    """List stored password profiles."""
    try:
        config = load_config(ctx.obj["config"])
        repository = load_repository_from_config(config)
        entries = repository.list_profiles()
    except ValueError as error:
        click.echo(f"Error: {error}")
        raise SystemExit(1) from error

    if not entries:
        click.echo("No profiles found")
        return

    for profile, created_at in entries:
        line = (
            f"{profile.username}@{profile.resource}  "
            f"v{profile.generation_version}"
        )
        if created_at is not None:
            line += f"  {created_at}"
        click.echo(line)


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


@cli.command("get-config")
@click.pass_context
def get_config(ctx):
    """Print resolved configuration values (secret is omitted)."""
    try:
        config = load_config(ctx.obj["config"])
    except ValueError as error:
        click.echo(f"Error: {error}")
        raise SystemExit(1) from error
    click.echo(json.dumps(config.public_dict(), indent=2))


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
    length: int | None,
    upper: int | None,
    lower: int | None,
    digits: int | None,
    specials: int | None,
    mask: int | None,
):
    try:
        constraints = _resolve_create_constraints(
            length,
            upper,
            lower,
            digits,
            specials,
            mask,
        )
        profile = _build_profile(
            username,
            resource,
            constraints,
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


@cli.command("bump")
@click.option("--username", "-u", prompt=True)
@click.option("--resource", "-r", prompt=True)
@_constraint_options
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
                result = repository.bump(
                    username,
                    resource,
                    new_constraints=_prompt_constraints(constraints),
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

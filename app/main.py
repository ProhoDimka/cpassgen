import click


@click.command()
@click.option("--username", prompt=True)
@click.option("--resource", prompt=True)
@click.option("--secret", prompt=True, hide_input=True)
def generate(username: str, resource: str, secret: str):
    """
    Generate password based on given parameters.
    """
    import base64
    import hashlib

    data = f"{username}:{resource}:{secret}".encode("utf-8")
    b64_data = base64.urlsafe_b64encode(data)
    digest = hashlib.sha256(b64_data).digest()
    password = base64.urlsafe_b64encode(digest).decode("utf-8")
    click.echo(password)


if __name__ == "__main__":
    generate()

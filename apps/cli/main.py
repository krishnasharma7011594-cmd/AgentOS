"""Typer CLI application entrypoint for AgentOS."""

import typer

from core.config.settings import settings

cli_app = typer.Typer(name="agentos", help="AgentOS Command Line Interface")


@cli_app.command()
def info() -> None:
    """Display AgentOS system info."""
    typer.echo(f"AgentOS Environment: {settings.app_env}")
    typer.echo(f"Default LLM Provider: {settings.llm.default_provider}")


@cli_app.command()
def list_agents() -> None:
    """List available registered agents."""
    typer.echo("Registered Agents: ResearchAgent, CodingAgent, GitHubAgent, FinanceAgent")


if __name__ == "__main__":
    cli_app()

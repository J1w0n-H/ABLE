# Copyright (2025) Bytedance Ltd. and/or its affiliates

"""CLI interface for ABLE using Click"""

import click
import sys
import os
from pathlib import Path

try:
    from .config import Config
    from .__init__ import __version__
except ImportError:
    from config import Config
    from __init__ import __version__


@click.group()
@click.version_option(version=__version__, prog_name='able')
@click.option('--verbose', is_flag=True, help='Enable verbose output')
@click.option('--debug', is_flag=True, help='Enable debug mode')
@click.pass_context
def cli(ctx, verbose, debug):
    """ABLE - LLM-Driven Build Automation for C/C++ Projects"""
    ctx.ensure_object(dict)
    ctx.obj['verbose'] = verbose
    ctx.obj['debug'] = debug
    
    if verbose:
        Config.VERBOSE = True
    if debug:
        Config.DEBUG = True


@cli.command()
@click.argument('repository', metavar='REPOSITORY')
@click.argument('commit', metavar='COMMIT')
@click.option('--root-path', default='.', help='Root path (default: current directory)')
@click.option('--model', default=None, help=f'LLM model (default: {Config.LLM_MODEL})')
@click.option('--max-turns', type=int, default=None, help=f'Maximum turns (default: {Config.MAX_TURN})')
@click.option('--output', default=None, help=f'Output directory (default: {Config.OUTPUT_ROOT})')
@click.option('--timeout', type=int, default=None, help=f'Timeout in seconds (default: {Config.TIMEOUT})')
@click.pass_context
def build(ctx, repository, commit, root_path, model, max_turns, output, timeout):
    """
    Build a C/C++ project in Docker container.
    
    REPOSITORY: GitHub repository (e.g., ImageMagick/ImageMagick)
    COMMIT: Git commit SHA (e.g., 336f2b8)
    
    Examples:
    
      able build ImageMagick/ImageMagick 336f2b8
      
      able build curl/curl d9cecdd --model gpt-4 --max-turns 150
      
      able build ffmpeg/ffmpeg abc1234 --output ./my_output --verbose
    """
    # Apply CLI overrides
    if model:
        Config.LLM_MODEL = model
    if max_turns:
        Config.MAX_TURN = max_turns
    if output:
        Config.OUTPUT_ROOT = output
    if timeout:
        Config.TIMEOUT = timeout
    
    # Validate configuration
    try:
        Config.validate()
    except ValueError as e:
        click.secho(f"Configuration Error: {e}", fg='red', err=True)
        sys.exit(2)
    
    # Show configuration if verbose
    if ctx.obj['verbose']:
        click.secho("\n📋 Configuration:", fg='cyan', bold=True)
        for key, value in Config.get_summary().items():
            click.echo(f"  {key}: {value}")
        click.echo()
    
    # Import and run main logic
    try:
        from .main import run_build
    except ImportError:
        from main import run_build
    
    try:
        run_build(repository, commit, root_path)
        click.secho("\n✅ Build completed successfully!", fg='green', bold=True)
    except Exception as e:
        click.secho(f"\n❌ Build failed: {e}", fg='red', err=True)
        if ctx.obj['debug']:
            import traceback
            traceback.print_exc()
        sys.exit(1)


@cli.command()
@click.argument('dockerfile_path', type=click.Path(exists=True))
@click.option('--build-test', is_flag=True, help='Test building the Dockerfile')
@click.pass_context
def verify(ctx, dockerfile_path, build_test):
    """
    Verify a generated Dockerfile.
    
    DOCKERFILE_PATH: Path to Dockerfile to verify
    
    Examples:
    
      able verify output/ImageMagick/ImageMagick/Dockerfile
      
      able verify output/curl/curl/Dockerfile --build-test
    """
    click.secho(f"\n🔍 Verifying Dockerfile: {dockerfile_path}", fg='cyan', bold=True)
    
    # Check file exists
    if not os.path.exists(dockerfile_path):
        click.secho(f"❌ Dockerfile not found: {dockerfile_path}", fg='red', err=True)
        sys.exit(1)
    
    # Basic validation
    with open(dockerfile_path, 'r') as f:
        content = f.read()
    
    if not content.strip().startswith('FROM'):
        click.secho("❌ Invalid Dockerfile: Must start with FROM", fg='red', err=True)
        sys.exit(1)
    
    click.secho("✅ Dockerfile syntax OK", fg='green')
    
    # Optional: Test building
    if build_test:
        click.secho("\n🔨 Testing Docker build...", fg='cyan')
        import subprocess
        try:
            result = subprocess.run(
                ['docker', 'build', '-f', dockerfile_path, '.'],
                capture_output=True,
                timeout=600
            )
            if result.returncode == 0:
                click.secho("✅ Docker build test passed!", fg='green', bold=True)
            else:
                click.secho("❌ Docker build test failed", fg='red', err=True)
                click.echo(result.stderr.decode()[-500:])
                sys.exit(1)
        except subprocess.TimeoutExpired:
            click.secho("❌ Docker build timed out", fg='red', err=True)
            sys.exit(1)


@cli.command()
@click.option('--all', 'clean_all', is_flag=True, help='Clean everything including repo cache')
@click.option('--output', is_flag=True, help='Clean output directory only')
@click.option('--logs', is_flag=True, help='Clean log files only')
@click.option('--docker', is_flag=True, help='Clean Docker resources')
@click.confirmation_option(prompt='Are you sure you want to clean?')
@click.pass_context
def clean(ctx, clean_all, output, logs, docker):
    """
    Clean build artifacts and caches.
    
    Examples:
    
      able clean --output    # Clean output directory
      
      able clean --logs      # Clean log files
      
      able clean --docker    # Clean Docker resources
      
      able clean --all       # Clean everything (requires confirmation)
    """
    import shutil
    import subprocess
    
    cleaned = []
    
    if clean_all or output:
        output_dir = Config.OUTPUT_ROOT
        if os.path.exists(output_dir):
            shutil.rmtree(output_dir)
            cleaned.append(f"Output directory ({output_dir})")
            click.secho(f"✅ Cleaned {output_dir}", fg='green')
    
    if clean_all or logs:
        log_dir = Config.LOG_DIR
        if os.path.exists(log_dir):
            for log_file in Path(log_dir).glob('*.log'):
                log_file.unlink()
            cleaned.append(f"Log files ({log_dir})")
            click.secho(f"✅ Cleaned log files", fg='green')
    
    if clean_all or docker:
        click.echo("🐳 Cleaning Docker resources...")
        subprocess.run('docker system prune -f', shell=True, capture_output=True)
        subprocess.run('docker volume prune -f', shell=True, capture_output=True)
        cleaned.append("Docker resources")
        click.secho("✅ Cleaned Docker resources", fg='green')
    
    if clean_all:
        repo_cache = './build_agent/utils/repo'
        if os.path.exists(repo_cache):
            # Clean but keep directory structure
            for item in os.listdir(repo_cache):
                item_path = os.path.join(repo_cache, item)
                if os.path.isdir(item_path):
                    shutil.rmtree(item_path)
            cleaned.append(f"Repository cache ({repo_cache})")
            click.secho(f"✅ Cleaned repository cache", fg='green')
    
    if not cleaned:
        click.secho("ℹ️  No cleaning options specified. Use --help for options.", fg='yellow')
    else:
        click.secho(f"\n🎉 Cleaned: {', '.join(cleaned)}", fg='green', bold=True)


@cli.command()
@click.pass_context
def config(ctx):
    """
    Show current configuration.
    
    Examples:
    
      able config
    """
    click.secho("\n📋 ABLE Configuration", fg='cyan', bold=True)
    click.secho("=" * 70, fg='cyan')
    
    summary = Config.get_summary()
    
    click.secho("\nLLM Settings:", fg='yellow', bold=True)
    click.echo(f"  Model:        {summary['llm_model']}")
    click.echo(f"  Max turns:    {summary['max_turn']}")
    click.echo(f"  Timeout:      {summary['timeout']}s")
    
    click.secho("\nDocker Settings:", fg='yellow', bold=True)
    click.echo(f"  Image:        {summary['docker_image']}")
    
    click.secho("\nPaths:", fg='yellow', bold=True)
    click.echo(f"  Output:       {summary['output_root']}")
    
    click.secho("\nFlags:", fg='yellow', bold=True)
    click.echo(f"  Verbose:      {summary['verbose']}")
    click.echo(f"  Debug:        {summary['debug']}")
    
    click.secho("\n" + "=" * 70, fg='cyan')
    
    # Check API keys
    click.secho("\n🔑 API Keys:", fg='yellow', bold=True)
    if Config.OPENAI_API_KEY:
        click.secho(f"  OpenAI:       ✅ Configured (ends with ...{Config.OPENAI_API_KEY[-4:]})", fg='green')
    else:
        click.secho("  OpenAI:       ❌ Not configured", fg='red')
    
    if Config.ANTHROPIC_API_KEY:
        click.secho(f"  Anthropic:    ✅ Configured (ends with ...{Config.ANTHROPIC_API_KEY[-4:]})", fg='green')
    else:
        click.secho("  Anthropic:    ❌ Not configured", fg='yellow')
    
    click.echo()


@cli.command()
@click.pass_context
def version(ctx):
    """Show version information."""
    click.secho(f"\nABLE {__version__}", fg='cyan', bold=True)
    click.echo(f"LLM-Driven Build Automation for C/C++ Projects")
    click.echo(f"Copyright (2025) Bytedance Ltd.\n")


@cli.command()
@click.pass_context
def docs(ctx):
    """
    View detailed usage guide.
    
    Opens USAGE_GUIDE.md in terminal pager.
    
    Example:
      able docs                  # View complete usage guide
    """
    from pathlib import Path
    
    doc_file = 'USAGE_GUIDE.md'
    
    # Try relative to cli.py location
    cli_dir = Path(__file__).parent.parent
    doc_path = cli_dir / doc_file
    
    if not doc_path.exists():
        # Try current directory
        doc_path = Path.cwd() / doc_file
    
    if doc_path.exists():
        click.echo()
        click.secho("📖 ABLE Usage Guide", fg='cyan', bold=True)
        click.secho(f"File: {doc_file}", fg='blue')
        click.echo("─" * 70)
        click.echo()
        
        with open(doc_path, 'r', encoding='utf-8') as f:
            content = f.read()
            # Use pager for long content
            click.echo_via_pager(content)
    else:
        click.secho(f"\n❌ Document not found: {doc_file}", fg='red', err=True)
        click.echo(f"Expected location: {doc_path}")
        click.echo("\n💡 Make sure you're running from the ABLE directory.")
        click.echo("📄 Or view on GitHub: https://github.com/YOUR_USERNAME/ABLE/blob/main/USAGE_GUIDE.md")
        sys.exit(1)



def main_cli():
    """Entry point for CLI"""
    cli(obj={})


if __name__ == '__main__':
    main_cli()


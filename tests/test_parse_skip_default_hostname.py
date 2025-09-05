import textwrap
from click.testing import CliRunner
from pathlib import Path

from ssh_manager.cli import main


def test_parse_skips_hostname_star(monkeypatch, tmp_path):
    fake_home = tmp_path
    ssh_dir = fake_home / '.ssh'
    ssh_dir.mkdir()
    config_path = ssh_dir / 'config'

    monkeypatch.setenv('HOME', str(fake_home))
    from pathlib import Path as _P
    monkeypatch.setattr(_P, 'home', lambda: fake_home)

    sample = textwrap.dedent(
        """
        Host defaults-block
          HostName *
          User root
        Host actual1
          HostName actual1.example.com
        """
    ).strip() + "\n"
    config_path.write_text(sample, encoding='utf-8')

    runner = CliRunner()
    result = runner.invoke(main, ['parse', '--input', str(config_path), '--no-backup'])
    assert result.exit_code == 0, result.output

    cfgd = ssh_dir / 'config.d'
    files = [p.name for p in cfgd.glob('*.conf')]
    assert 'defaults-block.conf' not in files
    assert 'actual1.conf' in files

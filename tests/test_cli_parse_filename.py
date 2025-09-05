import textwrap
from pathlib import Path
import json

from click.testing import CliRunner

from ssh_manager.cli import main


def test_cli_parse_uses_first_alias_and_no_spaces(monkeypatch, tmp_path):
    # Fake home so CLI writes into temp .ssh
    fake_home = tmp_path
    ssh_dir = fake_home / '.ssh'
    ssh_dir.mkdir()
    config_path = ssh_dir / 'config'

    monkeypatch.setenv('HOME', str(fake_home))
    # Monkeypatch Path.home to return our fake home
    from pathlib import Path as _P
    monkeypatch.setattr(_P, 'home', lambda: fake_home)

    sample = textwrap.dedent(
        """\n        # legacy config\n        Host alpha-server alpha2 alpha3\n          HostName alpha.example.com\n        Host beta beta-alt\n          HostName beta.example.com\n        Host *.conf wildcard\n          HostName github.com\n        Host bigbastard bb\n          HostName bb-zt\n        """
    ).strip() + "\n"
    config_path.write_text(sample, encoding='utf-8')

    runner = CliRunner()
    result = runner.invoke(main, ['parse', '--input', str(config_path), '--no-backup'])
    assert result.exit_code == 0, result.output

    cfgd = ssh_dir / 'config.d'
    files = sorted(p.name for p in cfgd.glob('*.conf'))
    assert 'alpha-server.conf' in files
    assert 'beta.conf' in files
    assert 'conf.conf' in files  # from *.conf
    assert 'bigbastard.conf' in files
    for name in files:
        assert ' ' not in name

    # Ensure host alias inside file matches first alias
    alpha_text = (cfgd / 'alpha-server.conf').read_text()
    assert alpha_text.splitlines()[0].strip() == 'Host alpha-server'

    # Ensure main config was regenerated
    assert (ssh_dir / 'config').exists()

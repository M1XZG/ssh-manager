import textwrap
from click.testing import CliRunner
from pathlib import Path

from ssh_manager.cli import main


def test_parse_duplicate_identity_file_copies(monkeypatch, tmp_path):
    fake_home = tmp_path
    ssh_dir = fake_home / '.ssh'
    ssh_dir.mkdir()
    config_path = ssh_dir / 'config'

    monkeypatch.setenv('HOME', str(fake_home))
    from pathlib import Path as _P
    monkeypatch.setattr(_P, 'home', lambda: fake_home)

    legacy_dir = tmp_path / 'legacy'
    legacy_dir.mkdir()
    priv = legacy_dir / 'to-bigbastard'
    priv.write_text('PRIVATEKEY', encoding='utf-8')
    pub = legacy_dir / 'to-bigbastard.pub'
    pub.write_text('PUBLICKEY', encoding='utf-8')

    sample = textwrap.dedent(f"""
    # Two hosts sharing same key
    Host bigbastard bb
      HostName bigbastard.letmeshoot.it
      User rmckenzi
      Port 21075
      Compression no
      IdentityFile {priv}
    Host bb-zt
      HostName bigbastard.zt.rpmdp.com
      User rmckenzi
      Port 21075
      Compression no
      IdentityFile {priv}
    """).strip() + "\n"
    config_path.write_text(sample, encoding='utf-8')

    runner = CliRunner()
    result = runner.invoke(main, ['parse', '--input', str(config_path), '--no-backup'])
    assert result.exit_code == 0, result.output

    keys_dir = ssh_dir / 'keys'
    # Expect two separate copies
    copies = sorted(p.name for p in keys_dir.iterdir() if p.is_file() and not p.name.endswith('.pub'))
    assert len(copies) == 2
    assert any(name.startswith('bigbastard_') for name in copies)
    assert any(name.startswith('bb-zt_') for name in copies)

    # Original key remains
    assert priv.exists()

    # Host config files each reference their dedicated copy
    for host_alias in ['bigbastard', 'bb-zt']:
        conf_text = (ssh_dir / 'config.d' / f'{host_alias}.conf').read_text()
        assert 'IdentityFile ~/.ssh/keys/' not in conf_text  # should be absolute path now
        assert 'IdentityFile ' in conf_text
        # The identity path inside file must point to keys dir
        assert any(line.strip().startswith('IdentityFile ') and '/.ssh/keys/' in line for line in conf_text.splitlines())

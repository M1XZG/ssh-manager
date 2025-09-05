import textwrap
from pathlib import Path
from click.testing import CliRunner

from ssh_manager.cli import main


def test_parse_relocates_identity_files(monkeypatch, tmp_path):
    fake_home = tmp_path
    ssh_dir = fake_home / '.ssh'
    ssh_dir.mkdir()
    config_path = ssh_dir / 'config'
    keys_out = ssh_dir / 'keys'

    monkeypatch.setenv('HOME', str(fake_home))
    from pathlib import Path as _P
    monkeypatch.setattr(_P, 'home', lambda: fake_home)

    # Set up a legacy key outside of keys dir
    legacy_key_dir = tmp_path / 'legacy'
    legacy_key_dir.mkdir()
    (legacy_key_dir / 'id_ed25519').write_text('PRIVATEKEY', encoding='utf-8')
    (legacy_key_dir / 'id_ed25519.pub').write_text('PUBLICKEY', encoding='utf-8')

    sample = textwrap.dedent(f"""
    Host app1
      HostName app1.example.com
      User ubuntu
      IdentityFile {legacy_key_dir}/id_ed25519
    """).strip() + "\n"
    config_path.write_text(sample, encoding='utf-8')

    runner = CliRunner()
    result = runner.invoke(main, ['parse', '--input', str(config_path), '--no-backup'])
    assert result.exit_code == 0, result.output

    # Key should be relocated
    priv_candidates = list(keys_out.glob('app1_id_ed25519'))
    assert priv_candidates, 'relocated private key missing'
    priv = priv_candidates[0]
    assert priv.read_text() == 'PRIVATEKEY'
    assert (keys_out / 'app1_id_ed25519.pub').read_text() == 'PUBLICKEY'

    # Config.d file should reference new location
    host_conf = (ssh_dir / 'config.d' / 'app1.conf').read_text()
    assert f'IdentityFile {priv}' in host_conf

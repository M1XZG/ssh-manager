from pathlib import Path

from ssh_manager.core.util import sanitize_filename
from ssh_manager.core.model import HostConfig
from ssh_manager.core.store import write_host_config


def test_sanitize_filename_basic():
    assert sanitize_filename('example') == 'example'
    assert sanitize_filename('example host') == 'example'
    assert sanitize_filename('  spaced\tname ') == 'spaced'
    assert sanitize_filename('*.corp') == 'corp'
    assert sanitize_filename('weird!name') == 'weird-name'


def test_write_host_config_sanitizes(tmp_path):
    cfg_dir = tmp_path / 'config.d'
    h = HostConfig(host='router.asus.com router another', hostname='router.asus.com')
    p = write_host_config(cfg_dir, h)
    # first token becomes stem, dots preserved
    assert p.name == 'router.asus.com.conf'
    assert 'Host router.asus.com' in p.read_text()


def test_write_host_config_wildcard(tmp_path):
    cfg_dir = tmp_path / 'config.d'
    h = HostConfig(host='*.conf', hostname='*.conf')
    p = write_host_config(cfg_dir, h)
    assert p.name == 'conf.conf'  # leading * removed

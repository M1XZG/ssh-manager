from ssh_manager.core import parser

SAMPLE = """# comment\nHost test\n  HostName example.com\n  User ubuntu\n  Port 2201\n  IdentityFile ~/.ssh/keys/test_ed25519\n  ForwardAgent yes\n"""

def test_parse_basic(): 
    hosts = parser.parse_ssh_config(SAMPLE)
    assert len(hosts) == 1
    h = hosts[0]
    assert h.host == 'test'
    assert h.hostname == 'example.com'
    assert h.user == 'ubuntu'
    assert h.port == 2201
    assert h.identity_file.endswith('test_ed25519')
    assert any('ForwardAgent' in o for o in h.extra_options)

def test_parse_multi_alias_first_only():
    text = """Host web1 web1-alt web1-backup\n  HostName web1.example.com\n"""
    hosts = parser.parse_ssh_config(text)
    assert len(hosts) == 1
    assert hosts[0].host == 'web1'
    assert hosts[0].hostname == 'web1'

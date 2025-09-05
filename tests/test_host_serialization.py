from ssh_manager.core.model import HostConfig

def test_serialize_minimal():
    h = HostConfig(host='web', hostname='web.example')
    text = h.serialize()
    assert text.startswith('Host web')
    assert 'HostName web.example' in text
    assert 'User ' in text  # default root

def test_serialize_with_identity():
    h = HostConfig(host='db', hostname='10.0.0.5', user='ubuntu', port=2201, identity_file='~/.ssh/keys/db_ed25519')
    t = h.serialize()
    assert 'Port 2201' in t
    assert 'IdentityFile ~/.ssh/keys/db_ed25519' in t

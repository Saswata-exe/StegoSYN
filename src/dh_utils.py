"""
Diffie-Hellman key exchange utilities.
Fixed serialisation using SubjectPublicKeyInfo (DER).
"""

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import dh
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.backends import default_backend

# 2048-bit MODP group from RFC 3526 (group 14)
def get_parameters():
    p = int("""
    0xFFFFFFFFFFFFFFFFC90FDAA22168C234C4C6628B80DC1CD129024E08
    8A67CC74020BBEA63B139B22514A08798E3404DDEF9519B3CD3A431B
    302B0A6DF25F14374FE1356D6D51C245E485B576625E7EC6F44C42E9
    A637ED6B0BFF5CB6F406B7EDEE386BFB5A899FA5AE9F24117C4B1FE6
    49286651ECE45B3DC2007CB8A163BF0598DA48361C55D39A69163FA8
    FD24CF5F83655D23DCA3AD961C62F356208552BB9ED529077096966D
    670C354E4ABC9804F1746C08CA237327FFFFFFFFFFFFFFFF
    """.replace('\n', '').replace(' ', '').replace('0x', ''), 16)
    g = 2
    return dh.DHParameterNumbers(p, g)

def generate_key_pair():
    params = get_parameters()
    private_key = params.parameters(default_backend()).generate_private_key()
    public_key = private_key.public_key()
    return private_key, public_key

def serialize_public_key(public_key):
    """Export public key in DER format (SubjectPublicKeyInfo)."""
    return public_key.public_bytes(
        encoding=serialization.Encoding.DER,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    )

def deserialize_public_key(der_bytes):
    """Load a public key from DER bytes."""
    return serialization.load_der_public_key(der_bytes, backend=default_backend())

def compute_shared_secret(private_key, peer_public_key_bytes):
    """Compute shared secret and derive a 32‑byte HMAC key via HKDF."""
    peer_public = deserialize_public_key(peer_public_key_bytes)
    shared = private_key.exchange(peer_public)
    hkdf = HKDF(
        algorithm=hashes.SHA256(),
        length=32,
        salt=None,
        info=b'hmac-key-for-coverless-stego',
        backend=default_backend()
    )
    return hkdf.derive(shared)  # 32 bytes, ready for HMAC

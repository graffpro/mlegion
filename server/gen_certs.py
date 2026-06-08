"""
Generate a local CA + server cert so the portal can serve the client's https:// endpoints.

Outputs to server/certs/:
  ca.crt / ca.key          - our root CA (install ca.crt as a SYSTEM cert on the emulator)
  server.crt / server.key  - cert for *.ml.fragon.com etc., signed by the CA
  android/<hash>.0         - ca.crt renamed for /system/etc/security/cacerts/ (Android trust)

The game (2017 Unity) almost certainly trusts the system store rather than pinning, so
installing ca.crt as a system CA on the rooted emulator makes our TLS portal trusted.
"""
import os, datetime, subprocess, shutil
from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
import ipaddress
import config

CERTDIR = os.path.join(os.path.dirname(__file__), "certs")
os.makedirs(CERTDIR, exist_ok=True)

# Fixed validity window (Date.now() is fine here — this is a build-time script).
NOT_BEFORE = datetime.datetime(2020, 1, 1)
NOT_AFTER = datetime.datetime(2035, 1, 1)

SANS = [
    "*.ml.fragon.com", "ml.fragon.com", "*.fragon.com", "fragon.com",
    "android.ml.fragon.com", "android1.ml.fragon.com",
    "account.ml.fragon.com", "account1.ml.fragon.com",
    "push.ml.fragon.com", "translate.ml.fragon.com", "gmip.ml.fragon.com",
    "op-cdn.prishen.com", "localhost",
]


def _key():
    return rsa.generate_private_key(public_exponent=65537, key_size=2048)


def _save(name, key, cert):
    with open(os.path.join(CERTDIR, name + ".key"), "wb") as f:
        f.write(key.private_bytes(serialization.Encoding.PEM,
                                  serialization.PrivateFormat.TraditionalOpenSSL,
                                  serialization.NoEncryption()))
    with open(os.path.join(CERTDIR, name + ".crt"), "wb") as f:
        f.write(cert.public_bytes(serialization.Encoding.PEM))


def main():
    # ---- CA ----
    ca_key = _key()
    ca_name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "ML Revival Root CA"),
                         x509.NameAttribute(NameOID.ORGANIZATION_NAME, "mlegion")])
    ca = (x509.CertificateBuilder()
          .subject_name(ca_name).issuer_name(ca_name)
          .public_key(ca_key.public_key())
          .serial_number(x509.random_serial_number())
          .not_valid_before(NOT_BEFORE).not_valid_after(NOT_AFTER)
          .add_extension(x509.BasicConstraints(ca=True, path_length=None), critical=True)
          .add_extension(x509.KeyUsage(digital_signature=True, key_cert_sign=True,
                                       crl_sign=True, key_encipherment=False,
                                       content_commitment=False, data_encipherment=False,
                                       key_agreement=False, encipher_only=False,
                                       decipher_only=False), critical=True)
          .add_extension(x509.SubjectKeyIdentifier.from_public_key(ca_key.public_key()),
                         critical=False)
          .sign(ca_key, hashes.SHA256()))
    _save("ca", ca_key, ca)

    # ---- server cert (SANs cover all portal hosts + our IP) ----
    san = [x509.DNSName(d) for d in SANS]
    for ip in {config.HOST_IP, "127.0.0.1"}:
        try:
            san.append(x509.IPAddress(ipaddress.ip_address(ip)))
        except ValueError:
            pass
    srv_key = _key()
    srv = (x509.CertificateBuilder()
           .subject_name(x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "*.ml.fragon.com")]))
           .issuer_name(ca_name)
           .public_key(srv_key.public_key())
           .serial_number(x509.random_serial_number())
           .not_valid_before(NOT_BEFORE).not_valid_after(NOT_AFTER)
           .add_extension(x509.SubjectAlternativeName(san), critical=False)
           .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
           .add_extension(x509.SubjectKeyIdentifier.from_public_key(srv_key.public_key()),
                          critical=False)
           .add_extension(x509.AuthorityKeyIdentifier.from_issuer_public_key(ca_key.public_key()),
                          critical=False)
           .sign(ca_key, hashes.SHA256()))
    _save("server", srv_key, srv)

    # ---- Android system-CA filename (<subject_hash_old>.0) ----
    andir = os.path.join(CERTDIR, "android")
    os.makedirs(andir, exist_ok=True)
    openssl = r"C:\Program Files\Git\usr\bin\openssl.exe"
    hashname = None
    if os.path.exists(openssl):
        try:
            out = subprocess.check_output([openssl, "x509", "-subject_hash_old", "-noout",
                                           "-in", os.path.join(CERTDIR, "ca.crt")], text=True)
            hashname = out.strip().splitlines()[0]
            shutil.copy(os.path.join(CERTDIR, "ca.crt"), os.path.join(andir, hashname + ".0"))
        except Exception as e:
            print("warn: could not compute Android hash:", e)

    print("certs written to", CERTDIR)
    print("  SANs:", ", ".join(SANS), "+ IPs", config.HOST_IP, "127.0.0.1")
    if hashname:
        print(f"  Android system CA -> certs/android/{hashname}.0  "
              f"(adb push to /system/etc/security/cacerts/)")


if __name__ == "__main__":
    main()

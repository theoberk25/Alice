DEMONSTRATION KEY MATERIAL ONLY.

The private key here signs the simulated permissions bundle so the
verification path can be exercised end to end. It is not a trust
root and must never sign anything real.

On the Pi, install ONLY permissions-signing.ed25519.pk, and install
it into the read-only root filesystem -- never onto the USB it
validates. A verifying key that travels with the data it verifies
means swapping the drive also swaps the trust root.

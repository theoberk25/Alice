import unittest

from dcamr.audit import signing


RFC8032_PRIVATE_KEY = bytes.fromhex(
    "9d61b19deffd5a60ba844af492ec2cc4"
    "4449c5697b326919703bac031cae7f60"
)
RFC8032_PUBLIC_KEY = bytes.fromhex(
    "d75a980182b10ab7d54bfed3c964073a"
    "0ee172f3daa62325af021a68f707511a"
)
RFC8032_SIGNATURE = bytes.fromhex(
    "e5564300c360ac729086e2cc806e828a"
    "84877f1eb8e5d974d873e06522490155"
    "5fb8821590a33bacc61e39701cf9b46b"
    "d25bf5f0595bbe24655141438e7a100b"
)


class AuditSigningTest(unittest.TestCase):
    def test_ed25519_matches_rfc8032_empty_message_vector(self):
        signer = signing.Ed25519Signer(RFC8032_PRIVATE_KEY, "checkpoint-key")
        verifier = signing.Ed25519Verifier(RFC8032_PUBLIC_KEY)

        signature = signer.sign(b"")

        self.assertEqual(signer.algorithm_id, "ed25519")
        self.assertEqual(signer.key_id, "checkpoint-key")
        self.assertEqual(signature, RFC8032_SIGNATURE)
        self.assertIsNone(verifier.verify(signature, b""))

    def test_trust_store_accepts_the_configured_signature(self):
        signer = signing.Ed25519Signer(RFC8032_PRIVATE_KEY, "checkpoint-key")
        trust = signing.TrustStore(
            {
                (signer.algorithm_id, signer.key_id): signing.Ed25519Verifier(
                    RFC8032_PUBLIC_KEY
                )
            }
        )

        self.assertIsNone(
            trust.verify(
                signer.algorithm_id,
                signer.key_id,
                b"checkpoint",
                signer.sign(b"checkpoint"),
            )
        )

    def test_trust_store_rejects_a_changed_message(self):
        trust = signing.TrustStore(
            {
                ("ed25519", "checkpoint-key"): signing.Ed25519Verifier(
                    RFC8032_PUBLIC_KEY
                )
            }
        )

        with self.assertRaises(signing.TrustError):
            trust.verify(
                "ed25519", "checkpoint-key", b"changed", RFC8032_SIGNATURE
            )

    def test_trust_store_rejects_a_signature_from_the_wrong_key(self):
        wrong_public_key = bytes.fromhex(
            "3d4017c3e843895a92b70aa74d1b7ebc"
            "9c982ccf2ec4968cc0cd55f12af4660c"
        )
        trust = signing.TrustStore(
            {
                ("ed25519", "checkpoint-key"): signing.Ed25519Verifier(
                    wrong_public_key
                )
            }
        )

        with self.assertRaises(signing.TrustError):
            trust.verify("ed25519", "checkpoint-key", b"", RFC8032_SIGNATURE)

    def test_trust_store_rejects_unknown_algorithm_and_key_without_fallback(self):
        trust = signing.TrustStore(
            {
                ("ed25519", "checkpoint-key"): signing.Ed25519Verifier(
                    RFC8032_PUBLIC_KEY
                )
            }
        )

        with self.assertRaises(signing.TrustError):
            trust.verify("unknown", "checkpoint-key", b"", RFC8032_SIGNATURE)
        with self.assertRaises(signing.TrustError):
            trust.verify("ed25519", "unknown-key", b"", RFC8032_SIGNATURE)

    def test_replacement_signer_and_verifier_use_the_same_interfaces(self):
        class ReplacementSigner:
            algorithm_id = "test-hardware-v1"
            key_id = "slot-7"

            def sign(self, message):
                return b"hardware-signature:" + message

        class ReplacementVerifier:
            def verify(self, signature, message):
                if signature != b"hardware-signature:" + message:
                    raise ValueError("invalid replacement signature")

        signer: signing.Signer = ReplacementSigner()
        trust = signing.TrustStore(
            {(signer.algorithm_id, signer.key_id): ReplacementVerifier()}
        )
        message = b"canonical checkpoint bytes"

        self.assertIsNone(
            trust.verify(
                signer.algorithm_id,
                signer.key_id,
                message,
                signer.sign(message),
            )
        )
        with self.assertRaises(signing.TrustError):
            trust.verify(
                signer.algorithm_id,
                signer.key_id,
                message + b"!",
                signer.sign(message),
            )

    def test_trust_configuration_is_copied_at_construction(self):
        configured = {
            ("ed25519", "checkpoint-key"): signing.Ed25519Verifier(
                RFC8032_PUBLIC_KEY
            )
        }
        trust = signing.TrustStore(configured)
        configured[("ed25519", "added-later")] = signing.Ed25519Verifier(
            RFC8032_PUBLIC_KEY
        )

        with self.assertRaises(signing.TrustError):
            trust.verify("ed25519", "added-later", b"", RFC8032_SIGNATURE)

    def test_adapter_errors_are_bounded_and_do_not_leak_raw_exceptions(self):
        with self.assertRaises(signing.SigningError) as signer_error:
            signing.Ed25519Signer(b"short", "checkpoint-key")
        with self.assertRaises(signing.TrustError) as verifier_error:
            signing.Ed25519Verifier(b"short")

        self.assertLessEqual(len(str(signer_error.exception)), 160)
        self.assertLessEqual(len(str(verifier_error.exception)), 160)
        self.assertIsNone(signer_error.exception.__cause__)
        self.assertIsNone(verifier_error.exception.__cause__)

        class ExplodingVerifier:
            def verify(self, signature, message):
                raise RuntimeError("raw-sensitive-verifier-detail")

        trust = signing.TrustStore({("replacement", "key"): ExplodingVerifier()})
        with self.assertRaises(signing.TrustError) as trust_error:
            trust.verify("replacement", "key", b"message", b"signature")

        self.assertNotIn("raw-sensitive", str(trust_error.exception))
        self.assertLessEqual(len(str(trust_error.exception)), 160)
        self.assertIsNone(trust_error.exception.__cause__)

    def test_public_operations_wrap_malformed_inputs_in_domain_errors(self):
        signer = signing.Ed25519Signer(RFC8032_PRIVATE_KEY, "checkpoint-key")
        verifier = signing.Ed25519Verifier(RFC8032_PUBLIC_KEY)
        trust = signing.TrustStore({("ed25519", "checkpoint-key"): verifier})

        with self.assertRaises(signing.SigningError):
            signer.sign("not-bytes")
        with self.assertRaises(signing.TrustError):
            verifier.verify(RFC8032_SIGNATURE, "not-bytes")
        with self.assertRaises(signing.TrustError):
            trust.verify([], "checkpoint-key", b"", RFC8032_SIGNATURE)


if __name__ == "__main__":
    unittest.main()

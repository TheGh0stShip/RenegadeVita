import unittest

try:
    from .query_renegade_server import parse_info
except ImportError:
    from query_renegade_server import parse_info


class InfoQueryTests(unittest.TestCase):
    def test_game_port_is_distinct_from_query_port(self):
        packet = b"\\hostname\\Example\\hostport\\5000\\mapname\\C&C_Field\\final\\"
        self.assertEqual(parse_info(packet)["hostport"], "5000")

    def test_never_retains_player_fields(self):
        self.assertEqual(parse_info(b"\\player_0\\private\\queryid\\1.1\\final\\"), {})

    def test_rejects_malformed_and_conflicting_fields(self):
        for packet in (b"bad", b"\\hostport", b"\\hostport\\0", b"\\hostport\\65536",
                       b"\\hostport\\5000\\hostport\\7000", b"\\hostname\\bad\nname",
                       b"\\hostname\\" + b"a" * 8192):
            with self.subTest(packet=packet[:40]), self.assertRaises(ValueError):
                parse_info(packet)


if __name__ == "__main__":
    unittest.main()

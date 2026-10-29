"""Pruebas del núcleo de CONECTA. Sin Telegram, sin token, sin red.

Datos ficticios de prueba, nunca presentados como personas reales.
"""
import unittest

from conecta import db as store
from conecta.i18n import t
from conecta.matching import mutually_compatible


def make_user(conn, tid, **kw):
    store.create_or_get_user(conn, tid)
    base = dict(language="es", display_name=f"Test{tid}", age=30,
                gender="female", seeking="any", relationship="friendship",
                languages="Español", interests="música", bio="Hola",
                age_min=18, age_max=99, status="active")
    base.update(kw)
    store.update_profile(conn, tid, **base)
    return store.get_user(conn, tid)


class TestConecta(unittest.TestCase):
    def setUp(self):
        self.conn = store.connect(":memory:")

    def test_language_persistence(self):
        store.create_or_get_user(self.conn, 1)
        store.set_language(self.conn, 1, "pt")
        self.assertEqual(store.get_user(self.conn, 1)["language"], "pt")
        self.assertIn("Idioma", t("pt", "language_saved"))
        self.assertEqual(t("pt", "language_saved"), t("pt", "language_saved"))

    def test_i18n_files_have_same_keys(self):
        import json
        from pathlib import Path
        base = None
        for lang in ("es", "en", "pt", "it"):
            data = json.loads((Path(__file__).parent.parent / "locales" / f"{lang}.json").read_text())
            if base is None:
                base = set(data)
            else:
                self.assertEqual(base, set(data), lang)

    def test_mutual_match_only(self):
        make_user(self.conn, 1)
        make_user(self.conn, 2, gender="male")
        self.assertFalse(store.record_action(self.conn, 1, 2, "like"))
        self.assertTrue(store.record_action(self.conn, 2, 1, "like"))
        self.assertEqual(len(store.list_matches(self.conn, 1)), 1)

    def test_filters_both_ways(self):
        make_user(self.conn, 1, age=30, gender="male", seeking="female", age_min=25, age_max=35)
        make_user(self.conn, 2, age=40, gender="female", seeking="any")
        make_user(self.conn, 3, age=30, gender="female", seeking="male")
        cands = store.discover(self.conn, 1)
        self.assertEqual([c["telegram_id"] for c in cands], [3])

    def test_blocked_and_discarded_excluded(self):
        make_user(self.conn, 1)
        make_user(self.conn, 2, gender="male")
        make_user(self.conn, 3, gender="male")
        store.record_action(self.conn, 1, 2, "pass")
        store.block_user(self.conn, 1, 3)
        self.assertEqual(store.discover(self.conn, 1), [])

    def test_inactive_excluded(self):
        make_user(self.conn, 1)
        make_user(self.conn, 2, gender="male", status="paused")
        self.assertEqual(store.discover(self.conn, 1), [])

    def test_daily_like_limit_count(self):
        make_user(self.conn, 1)
        for tid in (2, 3):
            make_user(self.conn, tid, gender="male")
            store.record_action(self.conn, 1, tid, "like")
        self.assertEqual(store.daily_likes(self.conn, 1), 2)

    def test_chat_only_between_matches(self):
        make_user(self.conn, 1)
        make_user(self.conn, 2, gender="male")
        self.assertFalse(store.can_message(self.conn, 1, 2))
        with self.assertRaises(ValueError):
            store.send_message(self.conn, 1, 2, "hola")
        store.record_action(self.conn, 1, 2, "like")
        store.record_action(self.conn, 2, 1, "like")
        self.assertTrue(store.can_message(self.conn, 1, 2))
        store.send_message(self.conn, 1, 2, "hola")
        store.block_user(self.conn, 2, 1)
        self.assertFalse(store.can_message(self.conn, 1, 2))

    def test_report_recorded(self):
        make_user(self.conn, 1)
        make_user(self.conn, 2, gender="male")
        store.report_user(self.conn, 1, 2)
        row = self.conn.execute("SELECT COUNT(*) c FROM reports").fetchone()
        self.assertEqual(row["c"], 1)

    def test_delete_account_cleans_profile(self):
        make_user(self.conn, 1)
        store.add_photo(self.conn, 1, "file123", is_main=True)
        store.delete_account(self.conn, 1)
        user = store.get_user(self.conn, 1)
        self.assertEqual(user["status"], "deleted")
        self.assertIsNone(user["bio"])
        self.assertIsNone(store.get_main_photo(self.conn, 1))

    def test_age_validation_is_in_matching_layer(self):
        a = dict(age=20, gender="female", seeking="any", age_min=18, age_max=30)
        b = dict(age=40, gender="male", seeking="any", age_min=18, age_max=99)
        self.assertFalse(mutually_compatible(a, b))


if __name__ == "__main__":
    unittest.main()

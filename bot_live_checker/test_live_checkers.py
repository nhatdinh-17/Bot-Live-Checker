import sys
import unittest
from services.checkers import clean_target, check_facebook_uid_status, check_instagram_user, check_tiktok_user

class TestCheckers(unittest.TestCase):
    def test_clean_target(self):
        self.assertEqual(clean_target("https://www.facebook.com/zuck"), "zuck")
        self.assertEqual(clean_target("https://www.instagram.com/zuck/"), "zuck")
        self.assertEqual(clean_target("https://www.tiktok.com/@tiktok"), "tiktok")
        self.assertEqual(clean_target("@user123"), "user123")

    def test_fb_checker_live(self):
        res = check_facebook_uid_status("zuck")
        self.assertTrue(res["live"], f"Expected zuck to be LIVE, got: {res}")

    def test_fb_checker_die(self):
        res = check_facebook_uid_status("99999999999999999999999999")
        self.assertFalse(res["live"], f"Expected invalid UID to be DIE, got: {res}")

    def test_ig_checker_live(self):
        res = check_instagram_user("zuck")
        self.assertTrue(res["live"], f"Expected zuck IG to be LIVE, got: {res}")

    def test_ig_checker_die(self):
        res = check_instagram_user("non_existent_account_99999999999999")
        self.assertFalse(res["live"], f"Expected invalid username IG to be DIE, got: {res}")

    def test_tiktok_checker_live(self):
        res = check_tiktok_user("tiktok")
        self.assertTrue(res["live"], f"Expected tiktok to be LIVE, got: {res}")

    def test_tiktok_checker_die(self):
        res = check_tiktok_user("non_existent_account_99999999999999")
        self.assertFalse(res["live"], f"Expected invalid username TikTok to be DIE, got: {res}")

if __name__ == "__main__":
    unittest.main()

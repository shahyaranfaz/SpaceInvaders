import gc
import tempfile
import unittest
from pathlib import Path

import application


class DatabaseTests(unittest.TestCase):
    def setUp(self):
        self.temp_directory = tempfile.TemporaryDirectory()
        self.original_db_path = application.DB_PATH
        application.DB_PATH = str(Path(self.temp_directory.name) / "scores.db")
        application.init_db()

    def tearDown(self):
        application.DB_PATH = self.original_db_path
        gc.collect()
        self.temp_directory.cleanup()

    def register(self, username):
        self.assertIsNone(application.register_user(username, "secret"))
        return application.login_user(username, "secret")

    def test_registration_and_login(self):
        user = self.register("player-one")

        self.assertEqual("player-one", user[1])
        self.assertIsNone(application.login_user("player-one", "wrong"))
        self.assertEqual(
            "Username already taken.",
            application.register_user("player-one", "another-secret"),
        )

    def test_registered_scores_are_ranked_and_track_personal_best(self):
        first = self.register("first")
        second = self.register("second")

        self.assertTrue(application.record_score(100, 4, first))
        self.assertFalse(application.record_score(80, 2, first))
        self.assertTrue(application.record_score(120, 5, second))

        leaderboard = application.get_global_leaderboard()
        self.assertEqual(["second", "first", "first"], [row[0] for row in leaderboard])
        self.assertEqual([100, 80], [row[0] for row in application.get_personal_scores(first[0])])

    def test_local_scores_stay_out_of_global_leaderboard(self):
        self.assertFalse(application.record_score(500, 9))

        self.assertEqual([], application.get_global_leaderboard())
        local_scores = application.get_local_scores()
        self.assertEqual((500, 9), local_scores[0][:2])

    def test_friend_validation_and_leaderboard(self):
        owner = self.register("owner")
        friend = self.register("friend")
        outsider = self.register("outsider")
        application.record_score(50, 1, owner)
        application.record_score(75, 2, friend)
        application.record_score(999, 9, outsider)

        self.assertEqual("User not found.", application.add_friend(owner[0], "missing"))
        self.assertEqual("You cannot add yourself.", application.add_friend(owner[0], "owner"))
        self.assertIsNone(application.add_friend(owner[0], "friend"))
        self.assertEqual("Already friends.", application.add_friend(owner[0], "friend"))
        self.assertEqual([friend], application.get_friends(owner[0]))

        leaderboard = application.get_friends_leaderboard(owner[0])
        self.assertEqual(["friend", "owner"], [row[0] for row in leaderboard])


if __name__ == "__main__":
    unittest.main()

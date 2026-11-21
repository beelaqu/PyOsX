import unittest

from aliases import resolve_alias


class TestAliases(unittest.TestCase):

    def test_list_alias(self):
        self.assertEqual(
            resolve_alias(["list", "-l"]),
            ["ls", "-l"]
        )

    def test_show_alias(self):
        self.assertEqual(
            resolve_alias(["show", "file.txt"]),
            ["cat", "file.txt"]
        )

    def test_copy_alias(self):
        self.assertEqual(
            resolve_alias(["copy", "a.txt", "b.txt"]),
            ["cp", "a.txt", "b.txt"]
        )

    def test_move_alias(self):
        self.assertEqual(
            resolve_alias(["move", "a.txt", "b.txt"]),
            ["mv", "a.txt", "b.txt"]
        )

    def test_del_alias(self):
        self.assertEqual(
            resolve_alias(["del", "a.txt"]),
            ["rm", "a.txt"]
        )

    def test_newdir_alias(self):
        self.assertEqual(
            resolve_alias(["newdir", "folder"]),
            ["mkdir", "folder"]
        )

    def test_newfile_alias(self):
        self.assertEqual(
            resolve_alias(["newfile", "file.txt"]),
            ["touch", "file.txt"]
        )

    def test_unknown_command(self):
        self.assertEqual(
            resolve_alias(["python3", "script.py"]),
            ["python3", "script.py"]
        )

    def test_empty_arguments(self):
        self.assertEqual(resolve_alias([]), [])


if __name__ == "__main__":
    unittest.main()

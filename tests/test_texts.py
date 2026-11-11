import string
import unittest

from fog_launch.i18n import GERMAN, set_language, t

from .texts import english_texts


def placeholders(text):
    return sorted(name for _, name, _, _ in string.Formatter().parse(text) if name)


class TextTests(unittest.TestCase):
    def test_every_text_has_a_german_version(self):
        missing = sorted(english_texts() - set(GERMAN))
        self.assertEqual(missing, [], "add these to fog_launch/i18n.py")

    def test_no_german_text_is_left_over(self):
        self.assertEqual(sorted(set(GERMAN) - english_texts()), [])

    def test_placeholders_match(self):
        for english, german in GERMAN.items():
            self.assertEqual(placeholders(english), placeholders(german), english)

    def test_language_switch(self):
        self.addCleanup(set_language, "en")
        set_language("de")
        self.assertEqual(t("Sequence {name}", name="Duo"), "Folge Duo")
        set_language("en")
        self.assertEqual(t("Sequence {name}", name="Duo"), "Sequence Duo")


if __name__ == "__main__":
    unittest.main()

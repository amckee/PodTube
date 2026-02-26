#!/usr/bin/python

"""
Unit tests for PodTube
"""

import unittest
import sys
import podtube

class TestPodTube(unittest.TestCase):
    """Run unit tests on PodTube."""
    def test_run_without_error(self):
        """
        Test that podtube.py runs without throwing an error.
        """
        try:
            sys.argv = ["", "podtube.py"]
            podtube.main()
        except Exception as e:
            self.fail(f"podtube.py threw an error: {e}")

if __name__ == '__main__':
    unittest.main()

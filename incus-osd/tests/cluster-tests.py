#!/usr/bin/python3

from common import _check_deps, _download_images, _run_tests
from incusos_tests import ClusterTests

_check_deps()

_, current_image_img, _ = _download_images()

tests = ClusterTests(current_image_img)

# Each test runs a three member cluster, so limit how many run at once.
_run_tests(tests, max_workers=2)

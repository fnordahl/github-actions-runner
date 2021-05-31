# Copyright 2021 Canonical
# See LICENSE file for licensing details.

import sys
import unittest.mock

sys.path.append('src')

sys.modules['tenacity'] = unittest.mock.MagicMock()

# Copyright 2021 Canonical
# See LICENSE file for licensing details.

import unittest
import unittest.mock as mock


# The PatchHelper class is authored by Alex Kavanagh and stolen with pride from
# https://github.com/openstack/charms.openstack/blob/master/charms_openstack/test_utils.py
class PatchHelper(unittest.TestCase):
    """Helper Test Class based on unittest.TestCase which provides an easy way
    to patch object for a test without using a decorator and then clean them up
    afterwards
    """

    def setUp(self):
        self._patches = {}
        self._patches_start = {}

    def tearDown(self):
        for k, v in self._patches.items():
            v.stop()
            setattr(self, k, None)
        self._patches = None
        self._patches_start = None

    def patch(self, patchee, name=None, **kwargs):
        """Patch a patchable thing.  Uses mock.patch() to do the work.
        Automatically unpatches at the end of the test.

        The mock gets added to the test object (self) using 'name' or the last
        part of the patchee string, after the final dot.

        :param patchee: <string> representing module.object that is to be
            patched.
        :param name: optional <string> name to call the mock.
        :param **kwargs: any other args to pass to mock.patch()
        """
        mocked = mock.patch(patchee, **kwargs)
        if name is None:
            name = patchee.split('.')[-1]
        started = mocked.start()
        self._patches[name] = mocked
        self._patches_start[name] = started
        setattr(self, name, started)

    def patch_object(self, obj, attr, name=None, **kwargs):
        """Patch a patchable thing.  Uses mock.patch.object() to do the work.
        Automatically unpatches at the end of the test.

        The mock gets added to the test object (self) using 'name' or the attr
        passed in the arguments.

        :param obj: an object that needs to have an attribute patched.
        :param attr: <string> that represents the attribute being patched.
        :param name: optional <string> name to call the mock.
        :param **kwargs: any other args to pass to mock.patch()
        """
        mocked = mock.patch.object(obj, attr, **kwargs)
        if name is None:
            name = attr
        started = mocked.start()
        self._patches[name] = mocked
        self._patches_start[name] = started
        setattr(self, name, started)

    def patch_charm(self, attr, return_value=None):
        """Patch attributes of an instanciated charm instance.

        :param attr: <string> that represents the attribute being patched.
        :param return_value: <any> return value for the started mock.
        """
        mocked = mock.patch.object(self.harness.charm, attr)
        self._patches[attr] = mocked
        started = mocked.start()
        started.return_value = return_value
        self._patches_start[attr] = started
        setattr(self, attr, started)

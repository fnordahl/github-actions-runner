# Copyright 2021 Canonical
# See LICENSE file for licensing details.

import contextlib
import os
import unittest
import unittest.mock

import ops.model
import ops.testing
import ops.pebble

import charm

from . import test_utils


class TestCharm(test_utils.PatchHelper):
    def setUp(self):
        super().setUp()
        self.harness = ops.testing.Harness(charm.GithubActionsRunnerCharm)
        self.addCleanup(self.harness.cleanup)
        self.harness.begin()

    def test__confirm_runner_configured(self):
        self.patch_object(charm.tenacity, 'Retrying')

        @contextlib.contextmanager
        def _fake_context_manager():
            # TODO: Replace with `contextlib.nullcontext()` once we have
            # deprecated support for Python 3.4, 3.5 and 3.6
            yield None

        # Check return value when pull succeeds
        self.Retrying.return_value = [_fake_context_manager()]
        container = unittest.mock.MagicMock()
        self.assertEqual(
            self.harness.charm._confirm_runner_configured(container),
            True)
        container.pull.assert_called_once_with(os.path.join(charm.RUNNER_HOME,
                                                            '.runner'))
        # Check return value when pull raises
        self.Retrying.return_value = [_fake_context_manager()]
        container.pull.side_effect = ops.pebble.PathError(None, None)
        self.assertEqual(
            self.harness.charm._confirm_runner_configured(container),
            False)

    def test__reset_runner(self):
        container = unittest.mock.MagicMock()
        container.get_service().is_running.return_value = True
        self.harness.charm._reset_runner(container)
        container.stop.assert_called_once_with(charm.RUNNER_PEBBLE_SVC)
        container.remove_path.assert_has_calls([
            unittest.mock.call(os.path.join(charm.RUNNER_HOME,
                                            '.credentials')),
            unittest.mock.call(os.path.join(charm.RUNNER_HOME,
                                            '.credentials_rsaparams')),
            unittest.mock.call(os.path.join(charm.RUNNER_HOME,
                                            '.env')),
            unittest.mock.call(os.path.join(charm.RUNNER_HOME,
                                            '.path')),
            unittest.mock.call(os.path.join(charm.RUNNER_HOME,
                                            '.runner')),
        ])

    def test__ensure_pebble_layer(self):
        self.patch_charm('_on_config_changed')
        self.harness.update_config({
            'repository': 'fakerepo',
            'token': 'faketoken',
            'labels': 'fakelabel',
        })
        self.maxDiff = None
        container = unittest.mock.MagicMock()
        expected_plan = {
            'summary': 'GitHub Actions Runner layer',
            'description': 'pebble config layer for GitHub Actions Runner',
            'services': {
                'runner': {
                    'override': 'replace',
                    'summary': 'runner',
                    'command': '/entrypoint.sh {}'.format(
                        os.path.join(charm.RUNNER_HOME, 'run.sh')),
                    'startup': 'enabled',
                    'environment': {
                        'RUNNER_NAME': 'None-github-actions-runner-0',
                        'REPO_URL': 'fakerepo',
                        'RUNNER_TOKEN': 'faketoken',
                        'LABELS': 'fakelabel'
                    }
                }
            }
        }
        container.get_plan().to_dict().get.return_value = (
            expected_plan['services'])
        self.assertFalse(self.harness.charm._ensure_pebble_layer(container))
        self.assertFalse(container.add_layer.called)
        container.get_plan().to_dict().get.return_value = {}
        self.assertTrue(self.harness.charm._ensure_pebble_layer(container))
        container.add_layer.assert_called_once_with(
            'runner', expected_plan, combine=True)

    def test__handle_service(self):
        self.patch_charm('_ensure_pebble_layer')
        self.patch_charm('_reset_runner')
        self.patch_charm('_confirm_runner_configured')
        container = unittest.mock.MagicMock()
        # Layer not changed, service not running, and fails to start
        self.harness.charm._handle_service(container)
        self._confirm_runner_configured.assert_called_once_with(container)
        self.assertEqual(
            self.harness.charm.unit.status,
            ops.model.BlockedStatus(
                'Runner failed to start. '
                'Confirm repository URL, token and check logs.'))
        # Layer not changed, service not running
        container.reset_mock()
        container.get_service().is_running.return_value = False
        self._confirm_runner_configured.return_value = True
        self.harness.charm._handle_service(container)
        self.assertEqual(
            self.harness.charm.unit.status,
            ops.model.ActiveStatus())
        container.autostart.assert_called_once_with()
        # Layer changed while service is running
        container.reset_mock()
        self._ensure_pebble_layer.return_value = True
        container.get_service().is_running.return_value = False
        self._confirm_runner_configured.return_value = True
        self.harness.charm._handle_service(container)
        self.assertEqual(
            self.harness.charm.unit.status,
            ops.model.ActiveStatus())
        self._reset_runner.assert_called_once_with(container)
        container.autostart.assert_called_once_with()

    def test__on_github_actions_runner_pebble_ready(self):
        self.maxDiff = None
        self.patch_charm('_reset_runner')
        self.patch_charm('_confirm_runner_configured', return_value=True)
        # Check the initial Pebble plan is empty
        initial_plan = self.harness.get_container_pebble_plan(
            'github-actions-runner')
        self.assertEqual(initial_plan.to_yaml(), '{}\n')
        self.harness.update_config({
            'repository': 'fakerepo',
            'token': 'faketoken',
            'labels': 'fakelabel',
        })
        # Expected plan after Pebble ready with default config
        expected_plan = {
            'services': {
                'runner': {
                    'override': 'replace',
                    'summary': 'runner',
                    'command': '/entrypoint.sh {}'.format(
                        os.path.join(charm.RUNNER_HOME, 'run.sh')),
                    'startup': 'enabled',
                    'environment': {
                        'RUNNER_NAME': 'None-github-actions-runner-0',
                        'REPO_URL': 'fakerepo',
                        'LABELS': 'fakelabel',
                        'RUNNER_TOKEN': 'faketoken'
                    },
                }
            },
        }
        # Get the github-actions-runner container from the model
        container = self.harness.model.unit.get_container(
            'github-actions-runner')
        # Emit the PebbleReadyEvent with the github-actions-runner container
        self.harness.charm.on.github_actions_runner_pebble_ready.emit(
            container)
        # Get the plan now we've run PebbleReady
        updated_plan = self.harness.get_container_pebble_plan(
            'github-actions-runner').to_dict()
        # Check we've got the plan we expected
        self.assertEqual(expected_plan, updated_plan)
        # Check the service was started
        service = self.harness.model.unit.get_container(
            'github-actions-runner').get_service('runner')
        self.assertTrue(service.is_running())
        # Ensure we set an ActiveStatus with no message
        self.assertEqual(self.harness.model.unit.status,
                         ops.model.ActiveStatus())

    def test__on_config_changed(self):
        self.patch_charm('_handle_service')
        container = self.harness.model.unit.get_container(
            'github-actions-runner')
        self.harness.charm.on.config_changed.emit()
        self._handle_service.assert_called_once_with(container)

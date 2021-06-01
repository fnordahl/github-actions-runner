#!/usr/bin/env python3
# Copyright 2021 Canonical
# See LICENSE file for licensing details.

"""GitHub Actions Runner Charmed Operator."""

import logging
import os
import tenacity

import ops.charm
import ops.framework
import ops.main
import ops.model
import ops.pebble

logger = logging.getLogger(__name__)

RUNNER_HOME = '/actions-runner'
RUNNER_PEBBLE_SVC = 'runner'


class GithubActionsRunnerCharm(ops.charm.CharmBase):
    """GitHub Actions Runner Charmed Operator."""

    def __init__(self, *args):
        super().__init__(*args)
        self.framework.observe(
            self.on.github_actions_runner_pebble_ready,
            self._on_github_actions_runner_pebble_ready)
        self.framework.observe(self.on.config_changed, self._on_config_changed)

    @staticmethod
    def _confirm_runner_configured(container: ops.model.Container) -> bool:
        """Workaround for https://github.com/canonical/pebble/issues/46."""
        try:
            for attempt in tenacity.Retrying(
                    stop=tenacity.stop_after_attempt(9),
                    wait=tenacity.wait_exponential(
                        multiplier=1, min=2, max=10),
                    reraise=True):
                with attempt:
                    logging.info('Checking if configuration is done...')
                    with container.pull(os.path.join(RUNNER_HOME, '.runner')):
                        return True
        except ops.pebble.PathError:
            return False

    @staticmethod
    def _reset_runner(container: ops.model.Container):
        """Reset runner configuration."""
        logging.info('Resetting runner configuration')
        if container.get_service(RUNNER_PEBBLE_SVC).is_running():
            container.stop(RUNNER_PEBBLE_SVC)
        for filename in ('.credentials', '.credentials_rsaparams',
                         '.env', '.path', '.runner'):
            try:
                container.remove_path(os.path.join(RUNNER_HOME, filename))
            except ops.pebble.PathError:
                pass

    def _ensure_runner_running(self, container: ops.model.Container) -> bool:
        """Ensure the runner service is started and configured."""
        if not container.get_service(RUNNER_PEBBLE_SVC).is_running():
            container.start(RUNNER_PEBBLE_SVC)
        return self._confirm_runner_configured(container)

    def _ensure_pebble_layer(self, container: ops.model.Container) -> bool:
        """Ensure the Pebble plan matches our desired state.

        :returns: True if something changed, False otherwise
        """
        desired_layer = {
            'summary': 'GitHub Actions Runner layer',
            'description': 'pebble config layer for GitHub Actions Runner',
            'services': {
                RUNNER_PEBBLE_SVC: {
                    'override': 'replace',
                    'summary': RUNNER_PEBBLE_SVC,
                    'command': '/entrypoint.sh {}'.format(
                        os.path.join(RUNNER_HOME, 'run.sh')),
                    'startup': 'enabled',
                    'environment': {
                        'RUNNER_NAME': '{}-{}'.format(
                            self.model.name,
                            self.unit.name.replace('/', '-')),
                        'REPO_URL': self.model.config['repository'],
                        'RUNNER_TOKEN': self.model.config['runner-token'],
                        'LABELS': self.model.config.get('labels', ''),
                    }
                }
            }
        }
        runtime_services = container.get_plan().to_dict().get('services', {})
        if desired_layer['services'] != runtime_services:
            logging.info('desired_services: "{}"'
                         .format(desired_layer['services']))
            logging.info('runtime_services: "{}"'
                         .format(runtime_services))
            # Update the plan
            container.add_layer(RUNNER_PEBBLE_SVC, desired_layer, combine=True)
            return True
        return False

    def _handle_runner(self, container: ops.model.Container):
        """Handle service life cycle on change events."""
        # Add Pebble config layer using the Pebble API
        if self._ensure_pebble_layer(container):
            # Layer changed, reconfigure runner
            self._reset_runner(container)
        if not self._ensure_runner_running(container):
            container.stop(RUNNER_PEBBLE_SVC)
            self.unit.status = ops.model.BlockedStatus(
                'Runner failed to start. '
                'Confirm repository URL, token and check logs.')
            return
        self.unit.status = ops.model.ActiveStatus()

    def _on_github_actions_runner_pebble_ready(
            self, event: ops.charm.PebbleReadyEvent):
        """Define and start runner using the Pebble API."""
        # Get a reference the container attribute on the PebbleReadyEvent
        container = event.workload

        # Handle the service
        self._handle_runner(container)

    def _on_config_changed(self, _):
        """Compare runtime state to desired state and update if necessary."""
        container = self.unit.get_container('github-actions-runner')

        # Handle the service
        self._handle_runner(container)


if __name__ == '__main__':
    ops.main.main(GithubActionsRunnerCharm)

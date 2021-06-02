# github-actions-runner

## Description

Host your own fleet of GitHub Actions runners.

Please refer to https://docs.github.com/en/actions/hosting-your-own-runners
for more information about self-hosted runners.

## Usage

First get Runner Token for your repository from GitHub, please refer to
https://docs.github.com/en/actions/hosting-your-own-runners/adding-self-hosted-runners
for more information.

Then you can deploy the GitHub Actions Runner Charmed Operator:

    juju deploy --channel beta \
        --config repository=https://github.com/github/your-repository \
        --config runner-token=YOUR-RUNNER-TOKEN \
        github-actions-runner

To scale out your deployment:

    juju add-unit github-actions-runner

To update the runner token:

    juju config github-actions-runner token=YOUR-NEW-RUNNER-TOKEN

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

    juju deploy \
        --resource github-actions-runner=myoung34/github-runner:latest \
        --config repository=https://github.com/github/your-repository \
        --config runner-token=YOUR-RUNNER-TOKEN \
        github-actions-runner

To scale out your deployment:

    juju add-unit github-actions-runner

To update the runner token:

    juju config github-actions-runner token=YOUR-NEW-RUNNER-TOKEN

## Developing

Create and activate a virtualenv with the development requirements:

    virtualenv -p python3 venv
    source venv/bin/activate
    pip install -r requirements-dev.txt

## Testing

The Python operator framework includes a very nice harness for testing
operator behaviour without full deployment. Just `run_tests`:

    ./run_tests

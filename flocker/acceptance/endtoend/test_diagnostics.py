# Copyright ClusterHQ Inc.  See LICENSE file for details.

"""
Tests for the flocker-diagnostics.
"""

import os
from subprocess import check_output
import tarfile

from twisted.trial.unittest import TestCase

from ..testtools import require_cluster


class DiagnosticsTests(TestCase):
    """
    Tests for ``flocker-diagnostics``.
    """
    @require_cluster(1)
    def test_export(self, cluster):
        """
        ``flocker-diagnostics`` creates an archive of all Flocker service logs
        and server diagnostics information.
        """
        node_address = cluster.control_node.public_address
        remote_archive_path = check_output(
            ['ssh',
             'root@{}'.format(node_address),
             'flocker-diagnostics']
        ).rstrip()

        local_archive_path = self.mktemp()

        check_output(
            ['scp',
             'root@{}:{}'.format(node_address, remote_archive_path),
             local_archive_path]
        ).rstrip()

        with tarfile.open(local_archive_path) as f:
            actual_basenames = []
            for name in f.getnames():
                basename = os.path.basename(name)
                if name == basename:
                    # Ignore the directory entry
                    continue
                actual_basenames.append(basename)

        expected_basenames = [
            'flocker-control.tar.gz',
            'flocker-dataset-agent.tar.gz',
            'flocker-container-agent.tar.gz',
            'flocker-version',
            'docker-info',
            'docker-version',
            'os-release',
            'syslog.gz',
            'uname',
            'service-status',
        ]

        missing_basenames = set(expected_basenames) - set(actual_basenames)
        unexpected_basenames = set(actual_basenames) - set(expected_basenames)

        message = []
        if unexpected_basenames:
            message.append(
                'Unexpected entries: {!r}'.format(unexpected_basenames)
            )

        if missing_basenames:
            message.append('Missing entries: {!r}'.format(missing_basenames))

        if message:
            self.fail(
                'Unexpected Archive Content\n'
                + '\n'.join(message)
            )

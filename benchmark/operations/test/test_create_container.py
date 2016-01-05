# Copyright 2015 ClusterHQ Inc.  See LICENSE file for details.
"""
Create Container operation tests for the control service benchmarks.
"""
from uuid import uuid4

from ipaddr import IPAddress
from zope.interface.verify import verifyClass

from twisted.internet.task import Clock
from twisted.trial.unittest import SynchronousTestCase

from flocker.apiclient import FakeFlockerClient, Node

from benchmark.cluster import BenchmarkCluster
from benchmark._interfaces import IOperation, IProbe
from benchmark.operations.create_container import (
    CreateContainer, CreateContainerProbe,
    EmptyClusterError,
)


class CreateContainerTests(SynchronousTestCase):
    """
    CreateContainer operation tests.
    """

    def test_implements_IOperation(self):
        """
        CreateContainer provides the IOperation interface.
        """
        verifyClass(IOperation, CreateContainer)

    def test_implements_IProbe(self):
        """
        CreateContainerProbe provides the IProbe interface.
        """
        verifyClass(IProbe, CreateContainerProbe)

    def test_create_container(self):
        """
        CreateContainer probe waits for cluster to converge.
        """
        clock = Clock()

        node_id = uuid4()
        node = Node(uuid=node_id, public_address=IPAddress('10.0.0.1'))
        control_service = FakeFlockerClient([node], node_id)

        cluster = BenchmarkCluster(
            IPAddress('10.0.0.1'),
            lambda reactor: control_service,
            {},
            None,
        )
        operation = CreateContainer(clock, cluster)
        d = operation.get_probe()

        def run_probe(probe):
            def cleanup(result):
                cleaned_up = probe.cleanup()
                cleaned_up.addCallback(lambda _ignored: result)
                return cleaned_up
            d = probe.run()
            d.addCallback(cleanup)
            return d
        d.addCallback(run_probe)

        # Advance the clock because probe periodically polls the state.
        # Due to multiple steps, need to synchronize state a few times.
        control_service.synchronize_state()  # creation of pull container
        clock.advance(1)
        control_service.synchronize_state()  # deletion of pull container
        clock.advance(1)

        # The Deferred does not fire before the container has been created.
        self.assertNoResult(d)

        control_service.synchronize_state()  # creation of test container
        clock.advance(1)

        # The Deferred fires once the container has been created.
        self.successResultOf(d)

    def test_empty_cluster(self):
        """
        CreateContainer fails if no nodes in cluster.
        """
        control_service = FakeFlockerClient()

        cluster = BenchmarkCluster(
            IPAddress('10.0.0.1'),
            lambda reactor: control_service,
            {},
            None,
        )

        d = CreateContainer(Clock(), cluster).get_probe()

        self.failureResultOf(d, EmptyClusterError)

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import oci
from oci.exceptions import ServiceError
from oci.pagination import list_call_get_all_results

from collectors.oci.errors import OCIConfigurationError, is_access_denied, oci_error_message
from collectors.oci.normalizers import (
    normalize_alarm,
    normalize_block_volume,
    normalize_compartment,
    normalize_compute_instance,
    normalize_identity_resource,
    normalize_load_balancer,
    normalize_network_resource,
)
from collectors.oci.session import OCISessionFactory
from models.cloud_account import CloudAccount


class OCIInventoryCollector:
    def __init__(self, cloud_account: CloudAccount, *, timeout_seconds: int | None = None) -> None:
        self.cloud_account = cloud_account
        self.timeout_seconds = timeout_seconds
        self.session_factory = OCISessionFactory(cloud_account)
        self.config = self.session_factory.create_config()
        self.region = cloud_account.region or cloud_account.default_region or self.config["region"]
        self.root_compartment_id = self.session_factory.root_compartment_id(self.config)
        client_kwargs = {"timeout": timeout_seconds} if timeout_seconds else {}
        self.identity_client = oci.identity.IdentityClient(self.config, **client_kwargs)
        self.compute_client = oci.core.ComputeClient(self.config, **client_kwargs)
        self.block_storage_client = oci.core.BlockstorageClient(self.config, **client_kwargs)
        self.network_client = oci.core.VirtualNetworkClient(self.config, **client_kwargs)
        self.load_balancer_client = oci.load_balancer.LoadBalancerClient(self.config, **client_kwargs)
        self.monitoring_client = oci.monitoring.MonitoringClient(self.config, **client_kwargs)
        self.partial_errors: list[dict[str, str]] = []
        self.compartments_scanned = 0

    def collect_all(self) -> tuple[list[dict[str, Any]], list[dict[str, str]], int]:
        compartments = self.list_active_compartments()
        self.compartments_scanned = len(compartments)
        collectors: list[Callable[[list[str]], list[dict[str, Any]]]] = [
            self.collect_compute_instances,
            self.collect_block_volumes,
            self.collect_vcns_subnets_security_lists_nsgs,
            self.collect_load_balancers,
            self.collect_compartments,
            self.collect_iam_users_groups_policies_basic,
            self.collect_monitoring_alarms_basic,
        ]
        resources: list[dict[str, Any]] = []
        for collect in collectors:
            resources.extend(collect(compartments))
        return resources, self.partial_errors, self.compartments_scanned

    def list_active_compartments(self) -> list[str]:
        compartment_ids = [self.root_compartment_id]
        if self.cloud_account.compartment_ocid:
            return compartment_ids
        try:
            response = list_call_get_all_results(
                self.identity_client.list_compartments,
                self.root_compartment_id,
                compartment_id_in_subtree=True,
                access_level="ACCESSIBLE",
            )
            for compartment in response.data:
                if getattr(compartment, "lifecycle_state", None) != "DELETED":
                    compartment_ids.append(compartment.id)
        except ServiceError as exc:
            self._record_partial_error("identity_compartments", self.root_compartment_id, exc)
        return compartment_ids

    def _record_partial_error(self, service: str, compartment_id: str | None, error: Exception) -> None:
        error_type = "access_denied" if is_access_denied(error) else "oci_error"
        self.partial_errors.append(
            {
                "service": service,
                "compartment_id": compartment_id or "",
                "type": error_type,
                "message": oci_error_message(error),
            }
        )

    def _safe_collect_compartment(
        self,
        service: str,
        compartment_id: str,
        collect: Callable[[], list[dict[str, Any]]],
    ) -> list[dict[str, Any]]:
        try:
            return collect()
        except (ServiceError, OCIConfigurationError) as exc:
            self._record_partial_error(service, compartment_id, exc)
            return []

    def collect_compute_instances(self, compartment_ids: list[str]) -> list[dict[str, Any]]:
        resources: list[dict[str, Any]] = []
        for compartment_id in compartment_ids:
            resources.extend(
                self._safe_collect_compartment(
                    "compute_instances",
                    compartment_id,
                    lambda compartment_id=compartment_id: [
                        normalize_compute_instance(instance, self.region)
                        for instance in list_call_get_all_results(
                            self.compute_client.list_instances,
                            compartment_id,
                        ).data
                    ],
                )
            )
        return resources

    def collect_block_volumes(self, compartment_ids: list[str]) -> list[dict[str, Any]]:
        resources: list[dict[str, Any]] = []
        availability_domains = self._availability_domains()
        for compartment_id in compartment_ids:
            for availability_domain in availability_domains:
                resources.extend(
                    self._safe_collect_compartment(
                        "block_volumes",
                        compartment_id,
                        lambda compartment_id=compartment_id, availability_domain=availability_domain: [
                            normalize_block_volume(volume, self.region, raw_type="OCI::Core::Volume")
                            for volume in list_call_get_all_results(
                                self.block_storage_client.list_volumes,
                                compartment_id,
                                availability_domain=availability_domain,
                            ).data
                        ],
                    )
                )
                resources.extend(
                    self._safe_collect_compartment(
                        "boot_volumes",
                        compartment_id,
                        lambda compartment_id=compartment_id, availability_domain=availability_domain: [
                            normalize_block_volume(volume, self.region, raw_type="OCI::Core::BootVolume")
                            for volume in list_call_get_all_results(
                                self.block_storage_client.list_boot_volumes,
                                availability_domain,
                                compartment_id=compartment_id,
                            ).data
                        ],
                    )
                )
        return resources

    def collect_vcns_subnets_security_lists_nsgs(self, compartment_ids: list[str]) -> list[dict[str, Any]]:
        resources: list[dict[str, Any]] = []
        for compartment_id in compartment_ids:
            resources.extend(
                self._safe_collect_compartment(
                    "vcns",
                    compartment_id,
                    lambda compartment_id=compartment_id: [
                        normalize_network_resource(vcn, self.region, raw_type="OCI::Core::VCN")
                        for vcn in list_call_get_all_results(self.network_client.list_vcns, compartment_id).data
                    ],
                )
            )
            resources.extend(
                self._safe_collect_compartment(
                    "subnets",
                    compartment_id,
                    lambda compartment_id=compartment_id: [
                        normalize_network_resource(subnet, self.region, raw_type="OCI::Core::Subnet")
                        for subnet in list_call_get_all_results(self.network_client.list_subnets, compartment_id).data
                    ],
                )
            )
            resources.extend(
                self._safe_collect_compartment(
                    "security_lists",
                    compartment_id,
                    lambda compartment_id=compartment_id: [
                        normalize_network_resource(security_list, self.region, raw_type="OCI::Core::SecurityList")
                        for security_list in list_call_get_all_results(
                            self.network_client.list_security_lists, compartment_id
                        ).data
                    ],
                )
            )
            resources.extend(
                self._safe_collect_compartment(
                    "network_security_groups",
                    compartment_id,
                    lambda compartment_id=compartment_id: [
                        normalize_network_resource(nsg, self.region, raw_type="OCI::Core::NetworkSecurityGroup")
                        for nsg in list_call_get_all_results(
                            self.network_client.list_network_security_groups, compartment_id
                        ).data
                    ],
                )
            )
        return resources

    def collect_load_balancers(self, compartment_ids: list[str]) -> list[dict[str, Any]]:
        resources: list[dict[str, Any]] = []
        for compartment_id in compartment_ids:
            resources.extend(
                self._safe_collect_compartment(
                    "load_balancers",
                    compartment_id,
                    lambda compartment_id=compartment_id: [
                        normalize_load_balancer(load_balancer, self.region)
                        for load_balancer in list_call_get_all_results(
                            self.load_balancer_client.list_load_balancers,
                            compartment_id=compartment_id,
                        ).data
                    ],
                )
            )
        return resources

    def collect_compartments(self, compartment_ids: list[str]) -> list[dict[str, Any]]:
        if self.cloud_account.compartment_ocid:
            return []
        return self._safe_collect_compartment(
            "identity_compartments",
            self.root_compartment_id,
            lambda: [
                normalize_compartment(compartment, self.region)
                for compartment in list_call_get_all_results(
                    self.identity_client.list_compartments,
                    self.root_compartment_id,
                    compartment_id_in_subtree=True,
                    access_level="ACCESSIBLE",
                ).data
                if getattr(compartment, "lifecycle_state", None) != "DELETED"
            ],
        )

    def collect_iam_users_groups_policies_basic(self, compartment_ids: list[str]) -> list[dict[str, Any]]:
        resources: list[dict[str, Any]] = []
        tenancy_id = self.config.get("tenancy")
        if not tenancy_id:
            return resources
        resources.extend(
            self._safe_collect_compartment(
                "identity_users",
                tenancy_id,
                lambda: [
                    normalize_identity_resource(user, self.region, raw_type="OCI::Identity::User")
                    for user in list_call_get_all_results(self.identity_client.list_users, tenancy_id).data
                ],
            )
        )
        resources.extend(
            self._safe_collect_compartment(
                "identity_groups",
                tenancy_id,
                lambda: [
                    normalize_identity_resource(group, self.region, raw_type="OCI::Identity::Group")
                    for group in list_call_get_all_results(self.identity_client.list_groups, tenancy_id).data
                ],
            )
        )
        for compartment_id in compartment_ids:
            resources.extend(
                self._safe_collect_compartment(
                    "identity_policies",
                    compartment_id,
                    lambda compartment_id=compartment_id: [
                        normalize_identity_resource(policy, self.region, raw_type="OCI::Identity::Policy")
                        for policy in list_call_get_all_results(
                            self.identity_client.list_policies, compartment_id
                        ).data
                    ],
                )
            )
        return resources

    def collect_monitoring_alarms_basic(self, compartment_ids: list[str]) -> list[dict[str, Any]]:
        resources: list[dict[str, Any]] = []
        for compartment_id in compartment_ids:
            resources.extend(
                self._safe_collect_compartment(
                    "monitoring_alarms",
                    compartment_id,
                    lambda compartment_id=compartment_id: [
                        normalize_alarm(alarm, self.region)
                        for alarm in list_call_get_all_results(
                            self.monitoring_client.list_alarms,
                            compartment_id,
                        ).data
                    ],
                )
            )
        return resources

    def _availability_domains(self) -> list[str]:
        try:
            return [
                availability_domain.name
                for availability_domain in list_call_get_all_results(
                    self.identity_client.list_availability_domains,
                    self.root_compartment_id,
                ).data
            ]
        except ServiceError as exc:
            self._record_partial_error("identity_availability_domains", self.root_compartment_id, exc)
            return []

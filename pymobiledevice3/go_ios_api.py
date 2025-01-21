from typing import Optional

import requests

from pymobiledevice3.exceptions import GoIOSConnectionError
from pymobiledevice3.remote.remote_service_discovery import RemoteServiceDiscoveryService
from pymobiledevice3.utils import get_asyncio_loop

GO_IOS_AGENT_DEFAULT_ADDRESS = ('127.0.0.1', 60105)


async def async_get_go_ios_devices(
    go_ios_address: tuple[str, int] = GO_IOS_AGENT_DEFAULT_ADDRESS,
    userspace_hostname: Optional[str] = None,
) -> list[RemoteServiceDiscoveryService]:
    tunnels = _list_tunnels(go_ios_address)
    return await _create_rsds_from_tunnels(
        tunnels,
        userspace_hostname if userspace_hostname else go_ios_address[0]
    )


def get_go_ios_devices(
    tunneld_address: tuple[str, int] = GO_IOS_AGENT_DEFAULT_ADDRESS,
    userspace_hostname: Optional[str] = None,
) -> list[RemoteServiceDiscoveryService]:
    return get_asyncio_loop().run_until_complete(
        async_get_go_ios_devices(tunneld_address, userspace_hostname)
    )


async def async_get_go_ios_device_by_udid(
    udid: str,
    go_ios_address: tuple[str, int] = GO_IOS_AGENT_DEFAULT_ADDRESS,
    userspace_hostname: Optional[str] = None,
) -> Optional[RemoteServiceDiscoveryService]:
    tunnels = _list_tunnels(go_ios_address)
    for tunnel_details in tunnels:
        if tunnel_details["udid"] == udid:
            return (await _create_rsds_from_tunnels(
                [tunnel_details],
                userspace_hostname if userspace_hostname else go_ios_address[0]
                ))[0]
    return None


def get_tunneld_device_by_udid(
    udid: str,
    go_ios_address: tuple[str, int] = GO_IOS_AGENT_DEFAULT_ADDRESS,
    userspace_hostname: Optional[str] = None,
) -> Optional[RemoteServiceDiscoveryService]:
    return get_asyncio_loop().run_until_complete(
        async_get_go_ios_device_by_udid(udid, go_ios_address, userspace_hostname)
    )


def _list_tunnels(go_ios_agent_address: tuple[str, int] = GO_IOS_AGENT_DEFAULT_ADDRESS) -> list[dict]:
    try:
        # Get the list of tunnels from the specified address
        resp = requests.get(
                f'http://{go_ios_agent_address[0]}:{go_ios_agent_address[1]}/tunnels'
        )
        tunnels = resp.json()
    except requests.exceptions.ConnectionError:
        raise GoIOSConnectionError()
    return tunnels


async def _create_rsds_from_tunnels(tunnels: list[dict], userspace_hostname: str) -> list[RemoteServiceDiscoveryService]:
    rsds = []
    for tunnel_details in tunnels:
        if tunnel_details['userspaceTun']:
            userspace_address = (userspace_hostname, tunnel_details['userspaceTunPort'])
        else:
            userspace_address = None
        rsd = RemoteServiceDiscoveryService(
            (tunnel_details['address'], tunnel_details['rsdPort']),
            name=f"go_ios-{tunnel_details['udid']}",
            userspace_address=userspace_address
        )

        try:
            await rsd.connect()
            rsds.append(rsd)
        except (TimeoutError, ConnectionError):
            continue
    return rsds

#!/usr/bin/env python3
from __future__ import annotations

import argparse
import asyncio
from dataclasses import asdict
import json
import sys
from pathlib import Path
import importlib.util
import sys as _sys

ROOT = Path(__file__).resolve().parents[1]
from aiohttp import ClientSession
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "custom_components" / "noma_iq"))


def _load_ayla_client():
    spec = importlib.util.find_spec("ayla")
    if spec is None or spec.loader is None:
        raise RuntimeError("Unable to locate custom_components/noma_iq/ayla.py")
    module = importlib.util.module_from_spec(spec)
    _sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module.NomaIqClient


async def _main() -> int:
    parser = argparse.ArgumentParser(description="Dump NOMA iQ devices and properties via Ayla.")
    parser.add_argument("--username", required=True)
    parser.add_argument("--password", required=True)
    parser.add_argument("--dsn")
    parser.add_argument("--json", action="store_true", dest="as_json")
    args = parser.parse_args()
    NomaIqClient = _load_ayla_client()

    async with ClientSession() as session:
        client = NomaIqClient(args.username, args.password, session)
        if not args.dsn:
            devices = await client.async_list_devices()
            payload = [asdict(device) for device in devices]
            if args.as_json:
                print(json.dumps(payload, indent=2))
            else:
                for device in devices:
                    print(
                        f"{device.name} | dsn={device.dsn} | oem_model={device.oem_model} "
                        f"| product={device.product_name} | ip={device.lan_ip} | mac={device.mac}"
                    )
            return 0

        device = await client.async_get_device(args.dsn)
        payload = {
            "dsn": device.serial_number,
            "name": device.name,
            "oem_model": device.oem_model_number,
            "model": device.device_model_number,
            "ip": device._device_ip_address,
            "mac": device._device_mac_address,
            "properties": device.properties_full,
        }
        print(json.dumps(payload, indent=2, default=str))
        return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(_main()))

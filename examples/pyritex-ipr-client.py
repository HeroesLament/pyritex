import anyio
from typing import List

from oxitrait.enum import Enum, auto
from oxitrait.struct import Struct
from oxitrait.impl import Impl
from oxitrait.trait import Trait
from oxitrait.runtime import requires_traits

from pyritex import NetlinkSocket
from pyritex_ipr import (
    IPRouteClient,
    IPRouteError,
    LinkState,
    Link
)

async def main():
    async with NetlinkSocket() as sock:
        ipr = IPRouteClient(sock=sock)

        result = await ipr.link_get()

        if result.is_ok():
            links: List[Link] = result.unwrap()
            for link in links:
                if link.state == LinkState.UP:
                    print(f"[UP]   {link.name} (index {link.index})")
                elif link.state == LinkState.DOWN:
                    print(f"[DOWN] {link.name} (index {link.index})")
                else:
                    print(f"[??]   {link.name} (index {link.index})")
        else:
            error = result.unwrap_err()
            print(f"Failed to get link list: {error}")

if __name__ == "__main__":
    anyio.run(main)

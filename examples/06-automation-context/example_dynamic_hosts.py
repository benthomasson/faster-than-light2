#!/usr/bin/env python3
"""Example: Dynamic host registration and host-scoped proxy.

Demonstrates:
1. ftl.add_host() - Register hosts at runtime
2. ftl.<host>.module() - Cleaner syntax for targeting hosts/groups

This pattern is useful for provisioning workflows where you create
infrastructure and immediately configure it.
"""

import asyncio

from ftl2.automation import automation


async def main():
    """Demonstrate dynamic hosts and host-scoped proxy."""

    async with automation(verbose=True) as ftl:
        # =====================================================
        # Part 1: Dynamic Host Registration
        # =====================================================

        # Simulate provisioning servers (in real use, this would be
        # a cloud module like community.general.linode_v4)
        print("\n=== Simulating server provisioning ===")

        # Register newly "provisioned" servers
        ftl.add_host(
            hostname="web01",
            ansible_host="localhost",  # Using localhost for demo
            groups=["webservers", "production"],
        )

        ftl.add_host(
            hostname="web02",
            ansible_host="localhost",
            groups=["webservers", "production"],
        )

        ftl.add_host(
            hostname="db01",
            ansible_host="localhost",
            groups=["databases", "production"],
            db_type="postgres",  # Custom host variable
        )

        # Verify hosts are registered
        print(f"\nRegistered hosts: {list(ftl.hosts.keys())}")
        print(f"Groups: {ftl.hosts.groups}")
        print(f"Webservers: {[h.name for h in ftl.hosts['webservers']]}")

        # =====================================================
        # Part 2: Host-Scoped Proxy Syntax
        # =====================================================

        print("\n=== Using host-scoped proxy syntax ===")

        # Target localhost explicitly
        await ftl.localhost.command(cmd="echo 'Hello from localhost'")

        # Target a specific host
        await ftl.web01.command(cmd="echo 'Hello from web01'")

        # Target a group (runs on all hosts in group)
        await ftl.webservers.command(cmd="echo 'Hello from webservers'")

        # =====================================================
        # Part 3: Comparison with run_on()
        # =====================================================

        print("\n=== Syntax comparison ===")

        # Old way (still works)
        await ftl.run_on("db01", "command", cmd="echo 'Using run_on'")

        # New way (cleaner)
        await ftl.db01.command(cmd="echo 'Using host-scoped proxy'")

        # =====================================================
        # Part 4: Real-world provisioning pattern
        # =====================================================

        print("\n=== Provisioning workflow pattern ===")

        # In a real script, you would:
        #
        # 1. Provision the server:
        #    server = await ftl.community.general.linode_v4(
        #        label="web03",
        #        type="g6-nanode-1",
        #        region="us-east",
        #        image="linode/ubuntu22.04",
        #    )
        #
        # 2. Register it:
        #    ftl.add_host(
        #        hostname="web03",
        #        ansible_host=server["instance"]["ipv4"][0],
        #        ansible_user="root",
        #        groups=["webservers"],
        #    )
        #
        # 3. Configure it immediately:
        #    await ftl.web03.apt(name="nginx", state="present")
        #    await ftl.web03.service(name="nginx", state="started")

        # For this demo, we'll just show the pattern works
        ftl.add_host("web03", ansible_host="localhost", groups=["webservers"])
        await ftl.web03.command(cmd="echo 'Newly provisioned server configured!'")

        # =====================================================
        # Summary
        # =====================================================

        print("\n=== Summary ===")
        print(f"Total results: {len(ftl.results)}")
        print(f"All succeeded: {not ftl.failed}")


async def fqcn_example():
    """Demonstrate FQCN with host-scoped proxy."""

    print("\n=== FQCN with host-scoped proxy ===")

    async with automation(verbose=True) as ftl:
        # Register a group
        ftl.add_host("web01", ansible_host="localhost", groups=["webservers"])

        # FQCN modules work with host-scoped syntax
        # (This would call ansible.builtin.command on webservers)
        await ftl.webservers.ansible.builtin.command(cmd="echo 'FQCN works!'")

        # Real-world examples (commented out as they need actual modules):
        # await ftl.webservers.ansible.posix.firewalld(port="80/tcp", state="enabled")
        # await ftl.databases.community.postgresql.postgresql_db(name="myapp")


if __name__ == "__main__":
    asyncio.run(main())
    asyncio.run(fqcn_example())

#!/usr/bin/env python3
"""Example: Using ping() to test FTL2 connectivity.

ping() tests the full FTL2 execution pipeline:
1. TCP - Port reachable
2. SSH - Authentication works
3. Gate setup - Remote gate process starts
4. Command execution - Can run commands
5. Response - Round-trip communication works

When ping() succeeds, you KNOW module execution will work.
"""

import asyncio

from ftl2 import automation


async def example_local_ping():
    """Test local execution with ping."""
    print("=" * 60)
    print("Example: Local ping")
    print("=" * 60)

    async with automation(quiet=True) as ftl:
        # Ping localhost - tests local execution pipeline
        result = await ftl.local.ping()
        print(f"Local ping result: {result}")
        # Output: {'ping': 'pong'}

        # Can also use the Ansible module name (shadowed)
        result = await ftl.local.ansible.builtin.ping()
        print(f"FQCN ping result: {result}")
        # Output: {'ping': 'pong'}

    print("✓ Local ping successful\n")


async def example_remote_ping():
    """Test remote SSH connectivity with ping."""
    print("=" * 60)
    print("Example: Remote ping")
    print("=" * 60)

    # Define inventory with remote hosts
    inventory = {
        "webservers": {
            "hosts": {
                "web01": {
                    "ansible_host": "192.168.1.10",
                    "ansible_user": "admin",
                },
                "web02": {
                    "ansible_host": "192.168.1.11",
                    "ansible_user": "admin",
                },
            }
        }
    }

    async with automation(inventory=inventory, quiet=True) as ftl:
        # Ping a specific host
        try:
            result = await ftl.web01.ping()
            print(f"web01 ping result: {result}")
        except Exception as e:
            print(f"web01 ping failed: {e}")

        # Ping all hosts in a group
        for host_config in ftl.hosts["webservers"]:
            host_name = host_config.name
            try:
                # Access host via underscore (dashes converted automatically)
                host_proxy = getattr(ftl, host_name.replace("-", "_"))
                result = await host_proxy.ping()
                print(f"{host_name}: {result}")
            except Exception as e:
                print(f"{host_name}: FAILED - {e}")

    print("✓ Remote ping complete\n")


async def example_ping_before_work():
    """Use ping to verify connectivity before running tasks."""
    print("=" * 60)
    print("Example: Ping before doing work")
    print("=" * 60)

    inventory = {
        "databases": {
            "hosts": {
                "db-primary": {
                    "ansible_host": "192.168.1.20",
                    "ansible_user": "postgres",
                }
            }
        }
    }

    async with automation(inventory=inventory, quiet=True) as ftl:
        # Verify connectivity before running database operations
        try:
            await ftl.db_primary.ping()
            print("✓ Database server is reachable")

            # Now safe to run database operations
            # await ftl.db_primary.command(cmd="pg_dump mydb > backup.sql")
            print("  (would run database backup here)")

        except TimeoutError:
            print("✗ Database server connection timed out")
            print("  Check: Is the server running? Firewall rules?")

        except Exception as e:
            print(f"✗ Database server unreachable: {e}")
            print("  Check: SSH credentials, network connectivity")

    print()


async def example_ping_after_provisioning():
    """Use ping to verify a newly provisioned server is ready."""
    print("=" * 60)
    print("Example: Ping after provisioning")
    print("=" * 60)

    async with automation(quiet=True) as ftl:
        # Simulate provisioning a new server
        print("1. Provisioning new server...")
        # server = await ftl.local.community.general.linode_v4(...)
        # ip = server["instance"]["ipv4"][0]
        ip = "192.168.1.100"  # Simulated

        print(f"2. Server provisioned with IP: {ip}")

        # Register the new host
        ftl.add_host(
            "new-server",
            ansible_host=ip,
            ansible_user="root",
            groups=["webservers"],
        )

        # Wait for SSH to be ready
        print("3. Waiting for SSH...")
        try:
            await ftl.new_server.wait_for_ssh(timeout=120, delay=10)
            print("   SSH is ready!")

            # Ping to verify full pipeline
            print("4. Verifying FTL2 connectivity...")
            result = await ftl.new_server.ping()
            print(f"   Ping result: {result}")

            # Now safe to configure the server
            print("5. Server ready for configuration!")
            # await ftl.new_server.dnf(name="nginx", state="present")
            # await ftl.new_server.service(name="nginx", state="started")

        except TimeoutError:
            print("   ✗ SSH not available after 120 seconds")
        except Exception as e:
            print(f"   ✗ Connection failed: {e}")

    print()


async def example_ping_error_handling():
    """Demonstrate ping error handling."""
    print("=" * 60)
    print("Example: Ping error handling")
    print("=" * 60)

    from ftl2.exceptions import ConnectionError as FTL2ConnectionError

    inventory = {
        "test": {
            "hosts": {
                # This IP is in the TEST-NET range - guaranteed unreachable
                "unreachable": {"ansible_host": "192.0.2.1"},
            }
        }
    }

    async with automation(inventory=inventory, quiet=True) as ftl:
        try:
            await ftl.unreachable.ping()
            print("Ping succeeded (unexpected)")
        except TimeoutError as e:
            print(f"TimeoutError: {e}")
            print("  → Host did not respond within timeout")
        except FTL2ConnectionError as e:
            print(f"ConnectionError: {e}")
            print("  → Could not establish connection")
        except Exception as e:
            print(f"Other error: {type(e).__name__}: {e}")

    print()


async def main():
    """Run all ping examples."""
    # Local ping always works
    await example_local_ping()

    # Remote examples - these will fail without real hosts
    # Uncomment to test with real infrastructure:
    # await example_remote_ping()
    # await example_ping_before_work()
    # await example_ping_after_provisioning()

    # Error handling example - demonstrates failure cases
    await example_ping_error_handling()

    print("=" * 60)
    print("All examples complete!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())

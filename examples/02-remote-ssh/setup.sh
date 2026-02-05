#!/bin/bash
# FTL2 Remote SSH Example - Setup Script
# Manages the Docker container lifecycle for the SSH server

set -e

COMPOSE_FILE="docker-compose.yml"
CONTAINER_NAME="ftl2-example-remote"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if Docker is available
check_docker() {
    if ! command -v docker &> /dev/null; then
        echo -e "${RED}Error: docker command not found${NC}"
        echo "Please install Docker or start Colima"
        echo
        echo "For macOS with Colima:"
        echo "  brew install colima docker"
        echo "  colima start"
        exit 1
    fi

    if ! docker info &> /dev/null; then
        echo -e "${RED}Error: Docker daemon not running${NC}"
        echo
        echo "For macOS with Colima:"
        echo "  colima start"
        exit 1
    fi
}

# Set up SSH key authentication
setup_ssh_key() {
    local ssh_key="$HOME/.ssh/ftl2_example_rsa"

    # Generate SSH key if it doesn't exist
    if [ ! -f "$ssh_key" ]; then
        echo "  Generating SSH key..."
        ssh-keygen -t rsa -b 4096 -f "$ssh_key" -N "" -C "ftl2-example" > /dev/null 2>&1
    fi

    # Copy public key to container
    echo "  Copying SSH key to container..."
    docker compose exec -T remote-server mkdir -p /config/.ssh
    docker compose exec -T remote-server sh -c "cat > /config/.ssh/authorized_keys" < "${ssh_key}.pub"
    docker compose exec -T remote-server chmod 700 /config/.ssh
    docker compose exec -T remote-server chmod 600 /config/.ssh/authorized_keys
    docker compose exec -T remote-server chown -R 1000:1000 /config/.ssh

    echo -e "${GREEN}  SSH key configured: $ssh_key${NC}"
}

# Start the SSH server container
start_container() {
    echo -e "${GREEN}Starting SSH server container...${NC}"
    docker compose -f "$COMPOSE_FILE" up -d

    echo -e "${YELLOW}Waiting for SSH server to be ready...${NC}"

    # Wait for health check
    for i in {1..30}; do
        if docker compose -f "$COMPOSE_FILE" ps | grep -q "healthy"; then
            echo -e "${GREEN}SSH server is ready!${NC}"

            # Install Python in the container
            echo -e "${YELLOW}Installing Python in container...${NC}"
            docker compose exec -T remote-server apk add python3 > /dev/null 2>&1
            echo -e "${GREEN}Python installed${NC}"

            # Set up SSH key authentication
            echo -e "${YELLOW}Setting up SSH key authentication...${NC}"
            setup_ssh_key

            echo
            show_info
            return 0
        fi
        sleep 1
    done

    echo -e "${YELLOW}Warning: Health check timeout, but container may still work${NC}"

    # Try to install Python anyway
    echo -e "${YELLOW}Installing Python in container...${NC}"
    docker compose exec -T remote-server apk add python3 > /dev/null 2>&1
    echo -e "${GREEN}Python installed${NC}"

    # Set up SSH key authentication
    echo -e "${YELLOW}Setting up SSH key authentication...${NC}"
    setup_ssh_key

    show_info
}

# Stop the SSH server container
stop_container() {
    echo -e "${YELLOW}Stopping SSH server container...${NC}"
    docker compose -f "$COMPOSE_FILE" down
    echo -e "${GREEN}Container stopped${NC}"
}

# Show container status
status_container() {
    echo -e "${GREEN}Container Status:${NC}"
    docker compose -f "$COMPOSE_FILE" ps
    echo

    if docker compose -f "$COMPOSE_FILE" ps | grep -q "Up"; then
        show_info
    fi
}

# Show connection information
show_info() {
    echo -e "${GREEN}Connection Information:${NC}"
    echo "  Host: 127.0.0.1"
    echo "  Port: 2222"
    echo "  User: testuser"
    echo "  Auth: SSH key (~/.ssh/ftl2_example_rsa)"
    echo
    echo -e "${GREEN}Test SSH Connection:${NC}"
    echo "  ssh -p 2222 -i ~/.ssh/ftl2_example_rsa testuser@localhost"
    echo
    echo -e "${GREEN}Run FTL2 Examples:${NC}"
    echo "  ./run_examples.sh"
    echo
}

# Show container logs
logs_container() {
    echo -e "${GREEN}Container Logs:${NC}"
    docker compose -f "$COMPOSE_FILE" logs -f
}

# Restart the container
restart_container() {
    stop_container
    echo
    start_container
}

# Show usage
usage() {
    echo "FTL2 Remote SSH Example - Setup Script"
    echo
    echo "Usage: $0 {start|stop|restart|status|logs|help}"
    echo
    echo "Commands:"
    echo "  start   - Start the SSH server container"
    echo "  stop    - Stop and remove the container"
    echo "  restart - Restart the container"
    echo "  status  - Show container status"
    echo "  logs    - Show container logs (follow mode)"
    echo "  help    - Show this help message"
    echo
    echo "Examples:"
    echo "  $0 start          # Start the SSH server"
    echo "  $0 status         # Check if running"
    echo "  $0 logs           # View logs"
    echo "  $0 stop           # Stop the server"
}

# Main command handler
main() {
    case "$1" in
        start)
            check_docker
            start_container
            ;;
        stop)
            check_docker
            stop_container
            ;;
        restart)
            check_docker
            restart_container
            ;;
        status)
            check_docker
            status_container
            ;;
        logs)
            check_docker
            logs_container
            ;;
        help|--help|-h)
            usage
            ;;
        *)
            echo -e "${RED}Error: Unknown command '$1'${NC}"
            echo
            usage
            exit 1
            ;;
    esac
}

# Run main with all arguments
if [ $# -eq 0 ]; then
    echo -e "${RED}Error: No command specified${NC}"
    echo
    usage
    exit 1
fi

main "$@"

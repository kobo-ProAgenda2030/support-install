version: '3'

services:
  support-postgres:
    image: postgres:12.5-alpine
    container_name: support-postgres
    restart: unless-stopped
    env_file: 
      - ./database.txt
    ports:
      - "${SUPPORT_DB_PORT}:${SUPPORT_DB_INTERNAL_PORT}"
    volumes:
      - support-postgres-data:/var/lib/postgres
      - ./postgres-scripts:/postgres-scripts
    networks:
      - api-network
  
  support-postgres-bootstrap:
    image: proagenda2030/support_bootstrap:latest
    container_name: support-postgres-bootstrap
    restart: 'no'
    depends_on:
      - support-postgres
    env_file:
      - ./database.txt
    networks:
      - api-network

  support-postgres-backup:
    image: support_postgres_backup:latest
    container_name: support-postgres-backup
    restart: unless-stopped
    env_file: 
      - ./database.txt
      - ./aws.txt
    volumes:
      - support-postgres-data:/var/lib/postgres
      - ./postgres-scripts:/postgres-scripts
    command: "bash ./postgres-scripts/entrypoint.sh"
    networks:
      - api-network
    
volumes:
  support-postgres-data:
    driver: local

networks:
  api-network:
    driver: bridge
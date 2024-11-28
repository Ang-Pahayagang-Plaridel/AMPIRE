# AMPIRE
 
## Description

## Installation
### Pre-Requisites
1. Docker
https://docs.docker.com/engine/install/

```
sudo apt update -y && sudo apt upgrade -y
git clone https://github.com/Ang-Pahayagang-Plaridel/AMPIRE
docker compose -f ~/AMPIRE/docker-compose.yml up --build -d
```
## Reset Setup
```
sudo apt update -y && sudo apt upgrade -y
docker stop $(docker ps -q)
docker rm $(docker ps -aq)
docker rmi $(docker images -q)
docker volume rm $(docker volume ls -q)
docker network rm $(docker network ls -q)
docker system prune -a --volumes --force
sudo rm -rf /var/lib/docker
sudo rm -rf /etc/docker
sudo systemctl restart docker
sudo rm -rf ~/AMPIRE
git clone https://github.com/Ang-Pahayagang-Plaridel/AMPIRE
docker compose -f ~/AMPIRE/docker-compose.yml up --build -d
```
Generate Token
- Contents Read-only
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
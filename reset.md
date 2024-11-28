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
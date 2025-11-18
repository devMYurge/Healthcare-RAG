# Deploying Healthcare-RAG to AWS (EC2 + EBS/EFS)

This document explains a simple, reproducible pattern to host the backend and ChromaDB on AWS. The approach uses an EC2 instance with Docker and an attached persistent volume (EBS or EFS) mounted at `/data`.

High-level steps
- Provision an EC2 instance (Ubuntu 22.04 or Amazon Linux 2023) with Docker & Docker Compose.
- Create and attach an EBS volume (or use EFS for multiple hosts). Mount it at `/data` on the EC2 instance.
- Clone this repository on the EC2 instance, build backend image, and run `docker-compose -f docker-compose.aws.yml up -d`.

Key configuration
- The backend reads `CHROMA_PERSIST_DIR` to decide where to persist Chroma data. In `docker-compose.aws.yml` it's set to `/data/chroma` and the host mount should ensure `/data` is backed by EBS/EFS.
- The embedding model can be changed with `EMBEDDING_MODEL` env var.

Example EC2 preparation (run on your local machine with AWS CLI configured)

1) Launch an EC2 instance (example using AWS CLI)

```bash
# Adjust AMI/instance type as appropriate
aws ec2 run-instances \
  --image-id ami-0abcdef1234567890 \
  --count 1 \
  --instance-type t3.large \
  --key-name MyKeyPair \
  --security-group-ids sg-0123456789abcdef0 \
  --subnet-id subnet-0123456789abcdef0 \
  --associate-public-ip-address
```

2) Create and attach an EBS volume

```bash
# create volume
aws ec2 create-volume --availability-zone us-east-1a --size 200 --volume-type gp3
# attach volume to instance (use instance-id from step 1 and volume-id returned above)
aws ec2 attach-volume --volume-id vol-0123456789abcdef0 --instance-id i-0123456789abcdef0 --device /dev/xvdf
```

3) SSH into EC2 and format/mount the volume

```bash
sudo mkfs -t ext4 /dev/xvdf
sudo mkdir -p /data
sudo mount /dev/xvdf /data
sudo chown -R ubuntu:ubuntu /data
# Persist in /etc/fstab (careful — use UUIDs)
```

4) Install Docker & Docker Compose and clone the repo

```bash
# Ubuntu example
sudo apt update && sudo apt install -y docker.io git
sudo systemctl enable --now docker
sudo usermod -aG docker $USER
sudo curl -L "https://github.com/docker/compose/releases/download/v2.20.2/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Clone and start
git clone https://github.com/devMYurge/Healthcare-RAG.git
cd Healthcare-RAG
docker-compose -f docker-compose.aws.yml up -d --build
```

5) Verify

```bash
curl http://localhost:8000/api/health
```

Notes and recommendations
- EBS is a block device; if you want multiple instances to share the same storage, use EFS (NFS) instead.
- Make sure security group opens port 8000 (and 3000 if you're serving frontend from the host).
- Back up `/data` regularly (snapshots for EBS; standard backups for EFS).
- If you need a managed vector DB, consider Chromadb Cloud (if available) or other managed vector DBs; that requires changing the retrieval code to use a remote client.

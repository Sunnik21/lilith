# Securing your own server (VPS)

Use this only if the user runs the app on their own Linux server (Hetzner, DigitalOcean, OVH, Contabo, AWS EC2...). If they host on Vercel, Netlify, Lovable, Railway or Render, they don't need this: those platforms handle the server.

This guide covers the basics. Advanced hardening (Tailscale, Traefik, CrowdSec, backups) is out of scope; say so if the user asks for it.

## How to guide

- One phase at a time. Never paste the whole guide.
- Before every command: one line on **what it does and why**.
- After every phase: ask the user to confirm it worked before moving on.
- Assume Ubuntu LTS. Commands run on the server unless marked **(on your computer)**.

Open with: an unprotected server on the internet gets scanned by bots within minutes. They guess passwords, then use the server for crypto mining or attacks, or steal the data. We'll close the doors in 4 short steps.

## Phase 1. Updates and firewall (10 min)

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install ufw unattended-upgrades -y
sudo dpkg-reconfigure -plow unattended-upgrades   # choose "Yes": security updates install themselves
sudo ufw default deny incoming                    # close every door...
sudo ufw default allow outgoing
sudo ufw allow OpenSSH                            # ...except SSH, or you lock yourself out
sudo ufw allow 80/tcp && sudo ufw allow 443/tcp   # only if this server serves a website
sudo ufw enable
```
Check: `sudo ufw status` shows "Status: active".

## Phase 2. Log in with a key, not a password (10 min)

A password can be guessed. A key can't.

```bash
ssh-keygen -t ed25519            # (on your computer) skip if you already have a key
ssh-copy-id user@SERVER_IP       # (on your computer)
```
**Test before locking:** open a new terminal and run `ssh user@SERVER_IP`. It must log in without asking for the server password. Keep this session open.

Then on the server, edit `sudo nano /etc/ssh/sshd_config` and set:
```
PermitRootLogin no
PasswordAuthentication no
```
(On recent Ubuntu also check `/etc/ssh/sshd_config.d/*.conf` for a `PasswordAuthentication yes` line that overrides this.)
```bash
sudo systemctl restart ssh
```
Check: from a new terminal you can still log in. Make sure you know where your provider's **web console** is, as a back door if something goes wrong.

## Phase 3. Don't expose what doesn't need to be public (10 min)

- Databases (Postgres 5432, MySQL 3306, Redis 6379, MongoDB 27017) must not be open to the internet. Check: `sudo ss -tulpn` and look for `0.0.0.0:5432` or similar. Bind them to `127.0.0.1` or keep them inside a Docker network.
- **Docker warning:** `ports: - "5432:5432"` in docker-compose opens the port to the world **and skips ufw**. Use `"127.0.0.1:5432:5432"` or remove the `ports` line if only other containers need it.
- Admin panels (Portainer, pgAdmin, Coolify dashboards): protect with a strong password and, ideally, reach them only through a VPN like Tailscale.
- Keep `.env` files out of the web root and readable only by the app user: `chmod 600 .env`.

## Phase 4. HTTPS and automatic bans (15 min)

- HTTPS: use a reverse proxy that gets free certificates automatically (Caddy is the simplest; Traefik or Nginx + Certbot also work).
- Fail2ban or CrowdSec bans IPs that keep guessing passwords: `sudo apt install fail2ban -y` works out of the box for SSH.
- Backups: turn on the provider's snapshot backups, and back up the database somewhere else too.

## Final check

```bash
sudo ufw status                       # active, only the ports you need
sudo systemctl is-active unattended-upgrades
sudo sshd -T | grep -E 'passwordauthentication|permitrootlogin'   # both "no"
sudo ss -tulpn | grep -v 127.0.0.1    # nothing unexpected listening publicly
```

Report what passed and what's left, using the same severity levels as the main report.

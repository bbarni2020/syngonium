Deploy

1) Create env file:
   sudo cp deploy/prod.env.example /etc/default/syngonium && sudo chmod 0600 /etc/default/syngonium && sudo chown root:root /etc/default/syngonium
   sudoedit /etc/default/syngonium

2) Clone, run once:
   sudo useradd --system --no-create-home --shell /usr/sbin/nologin syngonium || true
   sudo mkdir -p /opt/syngonium && sudo chown syngonium:syngonium /opt/syngonium
   sudo -u syngonium git clone https://github.com/bbarni2020/syngonium.git /opt/syngonium || (cd /opt/syngonium && sudo -u syngonium git pull)
   sudo -u syngonium chmod +x /opt/syngonium/run.sh && sudo -u syngonium /opt/syngonium/run.sh

3) Optional: systemd:
   copy `deploy/syngonium.service.example` to `/etc/systemd/system/syngonium.service` and set `EnvironmentFile` as needed.
   sudo systemctl daemon-reload && sudo systemctl enable --now syngonium.service

Security: do not commit secrets; use a secret manager and keep env file 0600.

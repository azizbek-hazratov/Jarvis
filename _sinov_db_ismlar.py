import config, shlex, subprocess


def ssh_psql(host, name, user, pw, sql):
    remote = f"PGPASSWORD={shlex.quote(pw)} psql -h {host} -U {user} -d {name} -t -A -F'|' -c {shlex.quote(sql)}"
    cmd = ["ssh", "-i", config.HETZNER_NISHON_SERVER_SSH_KEY, "-o", "StrictHostKeyChecking=accept-new",
           "-o", "ConnectTimeout=15", f"root@{config.HETZNER_NISHON_SERVER_IP}", remote]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    if r.returncode != 0:
        raise RuntimeError(r.stderr)
    return r.stdout.strip()


oy = "2026-09"
sql = f"""SELECT COALESCE(g.nomi, 'Guruhsiz'), o.ism
FROM oquvchilar o
LEFT JOIN guruhlar g ON g.id = o.guruh_id
WHERE o.organization_id='{config.AZIZEDU_ORG_ID}' AND o.faol=true
AND o.id NOT IN (SELECT oquvchi_id FROM tolovlar WHERE oy='{oy}' AND holat='tolangan')
ORDER BY 1, 2
LIMIT 15"""
print(ssh_psql(config.AZIZEDU_DB_HOST, config.AZIZEDU_DB_NAME, config.AZIZEDU_DB_USER, config.AZIZEDU_DB_PASSWORD, sql))

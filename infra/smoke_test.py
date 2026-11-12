"""Check local MongoDB read/write and Weaviate readiness without project data."""

import subprocess
import urllib.request
import uuid


def main() -> None:
    record_id = uuid.uuid4().hex
    js = f'''const d = db.getSiblingDB("news_intel_verification");
const c = d.smoke_checks;
const id = "{record_id}";
try {{
  c.insertOne({{_id: id, purpose: "infra smoke check"}});
  const result = c.findOne({{_id: id}});
  if (!result || result.purpose !== "infra smoke check") throw new Error("Mongo read-after-write failed");
  print("MONGO_READ_WRITE_OK");
}} finally {{
  c.deleteOne({{_id: id}});
}}'''
    subprocess.run(
        [
            "docker",
            "compose",
            "-f",
            "infra/docker-compose.yml",
            "exec",
            "-T",
            "mongodb",
            "mongosh",
            "--quiet",
            "--eval",
            js,
        ],
        check=True,
        capture_output=True,
        text=True,
        timeout=15,
    )

    with urllib.request.urlopen(
        "http://localhost:8080/v1/.well-known/ready", timeout=3
    ) as response:
        if response.status != 200:
            raise RuntimeError(f"Weaviate readiness returned HTTP {response.status}")

    print("MongoDB read/write: PASS (temporary record removed)")
    print("Weaviate readiness: PASS")


if __name__ == "__main__":
    main()

"""Check local MongoDB read/write and Weaviate readiness without project data."""

import subprocess
import urllib.request
import uuid


def check_weaviate_round_trip() -> None:
    import weaviate
    from weaviate.classes.config import Configure, DataType, Property

    name = f"Slice01Smoke{uuid.uuid4().hex[:12]}"
    client = weaviate.connect_to_local()
    created = False
    try:
        collection = client.collections.create(
            name,
            properties=[Property(name="label", data_type=DataType.TEXT)],
            vector_config=Configure.Vectors.self_provided(),
        )
        created = True
        object_id = uuid.uuid4()
        vector = [0.0, 1.0, 0.0]
        collection.data.insert(
            uuid=object_id, properties={"label": "infra smoke check"}, vector=vector
        )
        result = collection.query.fetch_object_by_id(object_id, include_vector=True)
        if (
            result is None
            or result.properties.get("label") != "infra smoke check"
            or result.vector.get("default") != vector
        ):
            raise RuntimeError("Weaviate read-after-write failed")
    finally:
        try:
            if created:
                client.collections.delete(name)
        finally:
            client.close()


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

    check_weaviate_round_trip()

    print("MongoDB read/write: PASS (temporary record removed)")
    print("Weaviate readiness and isolated read/write: PASS (temporary collection removed)")


if __name__ == "__main__":
    main()

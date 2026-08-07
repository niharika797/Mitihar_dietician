"""Deploy mityahar-api to Cloud Run staging and repoint pinned jobs to the new image.

Cloud Run jobs (mityahar-migrate, mityahar-seed-runner) are pinned to an image
digest, not `:latest` -- a bare `gcloud run deploy` never updates them, so they
silently keep running whatever image was pinned at the last repoint. This
script makes the repoint part of the deploy instead of a step someone has to
remember.
"""
import shutil
import subprocess
import sys

REGION = "asia-south1"
SERVICE = "mityahar-api"
PINNED_JOBS = ["mityahar-migrate", "mityahar-seed-runner"]

# On Windows `gcloud` is a .cmd shim, and subprocess without shell=True won't
# resolve it from a bare name -- it raises FileNotFoundError. Resolve the real
# path once via PATH lookup instead (works on every platform, and avoids
# shell=True quoting problems).
GCLOUD = shutil.which("gcloud")
if GCLOUD is None:
    raise SystemExit("gcloud not found on PATH -- install the Google Cloud SDK first")


def run(args: list[str]) -> str:
    args = [GCLOUD if a == "gcloud" else a for a in args]
    result = subprocess.run(args, capture_output=True, text=True)
    if result.returncode != 0:
        print(result.stdout)
        print(result.stderr, file=sys.stderr)
        raise SystemExit(f"command failed: {' '.join(args)}")
    return result.stdout.strip()


def main() -> None:
    print(f"Deploying {SERVICE} from source...")
    run(["gcloud", "run", "deploy", SERVICE, "--source", ".", "--region", REGION])

    image = run([
        "gcloud", "run", "services", "describe", SERVICE,
        "--region", REGION,
        "--format", "value(spec.template.spec.containers[0].image)",
    ])
    print(f"Deployed image: {image}")

    for job in PINNED_JOBS:
        print(f"Repointing job {job} -> {image}")
        run(["gcloud", "run", "jobs", "update", job, "--region", REGION, "--image", image])

    print("Done. Service and pinned jobs are now on the same image.")


if __name__ == "__main__":
    main()

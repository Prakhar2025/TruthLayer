"""
Build and deploy TruthLayer to AWS using SAM CLI.

Usage:
    python scripts/deploy.py build       # Build the SAM application
    python scripts/deploy.py deploy      # Deploy to AWS
    python scripts/deploy.py all         # Build and deploy
    python scripts/deploy.py outputs     # Show stack outputs (API URL, etc.)
    python scripts/deploy.py delete      # Delete the stack
"""

import subprocess
import sys
import os
import json

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STACK_NAME = "truthlayer"
REGION = os.environ.get("AWS_REGION", "us-east-1")
S3_BUCKET = os.environ.get("SAM_S3_BUCKET", "")


def run_cmd(cmd, cwd=None):
    """Run a command and print output."""
    print(f"\n🚀 Running: {cmd}\n")
    result = subprocess.run(
        cmd, shell=True, cwd=cwd or PROJECT_ROOT,
        capture_output=False
    )
    if result.returncode != 0:
        print(f"\n❌ Command failed with exit code {result.returncode}")
        sys.exit(1)
    return result


def setup_layer():
    """Copy source code into the Lambda layer structure."""
    layer_src_dir = os.path.join(PROJECT_ROOT, "layer", "python", "src")
    os.makedirs(layer_src_dir, exist_ok=True)

    # Copy src/ into layer/python/src/
    import shutil

    src_dir = os.path.join(PROJECT_ROOT, "src")

    # Clean existing layer src
    if os.path.exists(layer_src_dir):
        shutil.rmtree(layer_src_dir)

    shutil.copytree(src_dir, layer_src_dir)
    print("✅ Copied src/ to layer/python/src/")


def build():
    """Build the SAM application."""
    print("\n" + "=" * 60)
    print("  📦 Building TruthLayer")
    print("=" * 60)

    setup_layer()
    run_cmd("sam build --use-container")
    print("\n✅ Build complete!")


def deploy():
    """Deploy to AWS."""
    print("\n" + "=" * 60)
    print("  🚀 Deploying TruthLayer to AWS")
    print("=" * 60)

    cmd = (
        f"sam deploy "
        f"--stack-name {STACK_NAME} "
        f"--region {REGION} "
        f"--capabilities CAPABILITY_IAM "
        f"--resolve-s3 "
        f"--no-confirm-changeset "
        f"--no-fail-on-empty-changeset"
    )

    run_cmd(cmd)
    print("\n✅ Deployment complete!")
    show_outputs()


def show_outputs():
    """Show CloudFormation stack outputs."""
    print("\n" + "=" * 60)
    print("  📋 Stack Outputs")
    print("=" * 60)

    try:
        result = subprocess.run(
            f"aws cloudformation describe-stacks --stack-name {STACK_NAME} --region {REGION} --query \"Stacks[0].Outputs\"",
            shell=True, capture_output=True, text=True, cwd=PROJECT_ROOT
        )
        if result.returncode == 0:
            outputs = json.loads(result.stdout)
            for output in outputs:
                print(f"  {output['OutputKey']}: {output['OutputValue']}")
        else:
            print(f"  ⚠️  Could not retrieve outputs: {result.stderr}")
    except Exception as e:
        print(f"  ⚠️  Error: {e}")


def delete():
    """Delete the CloudFormation stack."""
    print("\n" + "=" * 60)
    print(f"  🗑️  Deleting stack: {STACK_NAME}")
    print("=" * 60)

    run_cmd(f"sam delete --stack-name {STACK_NAME} --region {REGION} --no-prompts")
    print("\n✅ Stack deleted!")


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    action = sys.argv[1].lower()

    if action == "build":
        build()
    elif action == "deploy":
        deploy()
    elif action == "all":
        build()
        deploy()
    elif action == "outputs":
        show_outputs()
    elif action == "delete":
        delete()
    else:
        print(f"Unknown action: {action}")
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    main()
